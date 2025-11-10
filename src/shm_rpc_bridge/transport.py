from __future__ import annotations

import mmap
import struct
import threading

import posix_ipc

from shm_rpc_bridge.exceptions import RPCTimeoutError, RPCTransportError


class SharedMemoryTransport:
    """
    Transport layer using POSIX shared memory (via posix_ipc) and mmap with POSIX semaphores.

    Implements a producer-consumer pattern with two buffers:
    - Request buffer: client writes, server reads
    - Response buffer: server writes, client reads

    See (Stevens & Rago, 2013; Tanenbaum & Bos, 2015)
    """

    HEADER_SIZE = 4  # 4 bytes for message length
    DEFAULT_BUFFER_SIZE = 3145728  # 3MB default buffer

    @staticmethod
    def create(
            name: str,
            buffer_size: int = DEFAULT_BUFFER_SIZE,
            timeout: float | None = None,
    ) -> SharedMemoryTransport:
        return SharedMemoryTransport(name=name, buffer_size=buffer_size, create=True, timeout=timeout)

    @staticmethod
    def open(
            name: str,
            buffer_size: int = DEFAULT_BUFFER_SIZE,
            timeout: float | None = None,
    ) -> SharedMemoryTransport:
        return SharedMemoryTransport(name=name, buffer_size=buffer_size, create=False, timeout=timeout)

    def __init__(
            self,
            name: str,
            buffer_size: int = DEFAULT_BUFFER_SIZE,
            create: bool = False,
            timeout: float | None = None,
    ):
        """
        Initialize the shared memory transport.

        Args:
            name: Base name for shared memory and semaphores
            buffer_size: Size of each buffer in bytes
            create: Whether to create new shared memory (server) or open existing (client)
            timeout: Default timeout for operations in seconds
        """
        self.name = name
        self.buffer_size = buffer_size
        self.timeout = timeout
        self.create = create

        # Lock to synchronize cleanup with send/receive operations
        self._lock = threading.RLock()

        # Names for POSIX shared memory segments (need / prefix)
        self.request_shm_name = f"/{name}_request"
        self.response_shm_name = f"/{name}_response"

        # Semaphore names (POSIX semaphores need / prefix)
        self.request_empty_sem_name = f"/{name}_req_empty"  # Counts empty slots
        self.request_full_sem_name = f"/{name}_req_full"  # Counts full slots
        self.response_empty_sem_name = f"/{name}_resp_empty"
        self.response_full_sem_name = f"/{name}_resp_full"

        self.request_shm: posix_ipc.SharedMemory | None = None
        self.response_shm: posix_ipc.SharedMemory | None = None
        self.request_mmap: mmap.mmap | None = None
        self.response_mmap: mmap.mmap | None = None

        self.request_empty_sem: posix_ipc.Semaphore | None = None
        self.request_full_sem: posix_ipc.Semaphore | None = None
        self.response_empty_sem: posix_ipc.Semaphore | None = None
        self.response_full_sem: posix_ipc.Semaphore | None = None

        self._initialize()

    def _initialize(self) -> None:
        try:
            if self.create:
                # Server creates resources
                self._create_resources()
            else:
                # Client opens existing resources
                self._open_resources()
        except Exception as e:
            self.cleanup()
            raise RPCTransportError(f"Failed to initialize transport: {e}") from e

    def _create_resources(self) -> None:
        # Create POSIX shared memory segments
        self.request_shm = posix_ipc.SharedMemory(
            self.request_shm_name,
            flags=posix_ipc.O_CREX,
            mode=0o600,
            size=self.buffer_size,
        )
        self.response_shm = posix_ipc.SharedMemory(
            self.response_shm_name,
            flags=posix_ipc.O_CREX,
            mode=0o600,
            size=self.buffer_size,
        )

        # Create mmap objects for zero-copy memory access
        self.request_mmap = mmap.mmap(
            self.request_shm.fd,
            self.buffer_size,
            mmap.MAP_SHARED,
            mmap.PROT_READ | mmap.PROT_WRITE,
        )
        self.response_mmap = mmap.mmap(
            self.response_shm.fd,
            self.buffer_size,
            mmap.MAP_SHARED,
            mmap.PROT_READ | mmap.PROT_WRITE,
        )

        # Create semaphores (initialized to 1 for empty, 0 for full)
        self.request_empty_sem = posix_ipc.Semaphore(
            self.request_empty_sem_name,
            flags=posix_ipc.O_CREX,
            initial_value=1,
        )
        self.request_full_sem = posix_ipc.Semaphore(
            self.request_full_sem_name,
            flags=posix_ipc.O_CREX,
            initial_value=0,
        )
        self.response_empty_sem = posix_ipc.Semaphore(
            self.response_empty_sem_name,
            flags=posix_ipc.O_CREX,
            initial_value=1,
        )
        self.response_full_sem = posix_ipc.Semaphore(
            self.response_full_sem_name,
            flags=posix_ipc.O_CREX,
            initial_value=0,
        )

    def _open_resources(self) -> None:
        # Open existing POSIX shared memory segments
        self.request_shm = posix_ipc.SharedMemory(
            self.request_shm_name,
            flags=0,
        )
        self.response_shm = posix_ipc.SharedMemory(
            self.response_shm_name,
            flags=0,
        )

        # Create mmap objects for zero-copy memory access
        self.request_mmap = mmap.mmap(
            self.request_shm.fd,
            self.buffer_size,
            mmap.MAP_SHARED,
            mmap.PROT_READ | mmap.PROT_WRITE,
        )
        self.response_mmap = mmap.mmap(
            self.response_shm.fd,
            self.buffer_size,
            mmap.MAP_SHARED,
            mmap.PROT_READ | mmap.PROT_WRITE,
        )

        # Open semaphores
        self.request_empty_sem = posix_ipc.Semaphore(self.request_empty_sem_name)
        self.request_full_sem = posix_ipc.Semaphore(self.request_full_sem_name)
        self.response_empty_sem = posix_ipc.Semaphore(self.response_empty_sem_name)
        self.response_full_sem = posix_ipc.Semaphore(self.response_full_sem_name)

    def send_request(self, data: bytes) -> None:
        """
        Send request data (client -> server).

        Args:
            data: Data to send

        Raises:
            RPCTransportError: If send fails
            RPCTimeoutError: If operation times out
        """
        if len(data) > self.buffer_size - self.HEADER_SIZE:
            raise RPCTransportError(f"Message too large: {len(data)} bytes exceeds buffer size")

        with self._lock:
            try:
                # Wait for empty slot
                assert self.request_empty_sem is not None
                assert self.request_full_sem is not None
                if self.timeout is not None:
                    self.request_empty_sem.acquire(timeout=self.timeout)
                else:
                    self.request_empty_sem.acquire()

                # Zero-copy write using mmap
                assert self.request_mmap is not None
                size = len(data)
                # Write size header (4 bytes)
                self.request_mmap.seek(0)
                self.request_mmap.write(struct.pack("I", size))
                # Zero-copy write of data
                self.request_mmap.write(data)

                # Signal full slot
                self.request_full_sem.release()
            except posix_ipc.BusyError as e:
                raise RPCTimeoutError("Timeout sending request") from e
            except Exception as e:
                raise RPCTransportError(f"Failed to send request: {e}") from e

    def receive_request(self) -> bytes:
        """
        Receive request data (server side).

        Returns:
            Received data

        Raises:
            RPCTransportError: If receive fails
            RPCTimeoutError: If operation times out
        """
        with self._lock:
            try:
                # Wait for full slot
                assert self.request_full_sem is not None
                assert self.request_empty_sem is not None
                if self.timeout is not None:
                    self.request_full_sem.acquire(timeout=self.timeout)
                else:
                    self.request_full_sem.acquire()

                # Zero-copy read using mmap
                assert self.request_mmap is not None
                # Read size header
                self.request_mmap.seek(0)
                size_bytes = self.request_mmap.read(self.HEADER_SIZE)
                size = struct.unpack("I", size_bytes)[0]
                # Read data
                data = self.request_mmap.read(size)

                # Signal empty slot
                self.request_empty_sem.release()

                return data
            except posix_ipc.BusyError as e:
                raise RPCTimeoutError("Timeout receiving request") from e
            except Exception as e:
                raise RPCTransportError(f"Failed to receive request: {e}") from e

    def send_response(self, data: bytes) -> None:
        """
        Send response data (server -> client).

        Args:
            data: Data to send

        Raises:
            RPCTransportError: If send fails
            RPCTimeoutError: If operation times out
        """
        if len(data) > self.buffer_size - self.HEADER_SIZE:
            raise RPCTransportError(f"Message too large: {len(data)} bytes exceeds buffer size")

        with self._lock:
            try:
                # Wait for empty slot
                assert self.response_empty_sem is not None
                assert self.response_full_sem is not None
                if self.timeout is not None:
                    self.response_empty_sem.acquire(timeout=self.timeout)
                else:
                    self.response_empty_sem.acquire()

                # Zero-copy write using mmap
                assert self.response_mmap is not None
                size = len(data)
                # Write size header (4 bytes)
                self.response_mmap.seek(0)
                self.response_mmap.write(struct.pack("I", size))
                # Zero-copy write of data
                self.response_mmap.write(data)

                # Signal full slot
                self.response_full_sem.release()
            except posix_ipc.BusyError as e:
                raise RPCTimeoutError("Timeout sending response") from e
            except Exception as e:
                raise RPCTransportError(f"Failed to send response: {e}") from e

    def receive_response(self) -> bytes:
        """
        Receive response data (client side).

        Returns:
            Received data

        Raises:
            RPCTransportError: If receive fails
            RPCTimeoutError: If operation times out
        """
        with self._lock:
            try:
                # Wait for full slot
                assert self.response_full_sem is not None
                assert self.response_empty_sem is not None
                if self.timeout is not None:
                    self.response_full_sem.acquire(timeout=self.timeout)
                else:
                    self.response_full_sem.acquire()

                # Zero-copy read using mmap
                assert self.response_mmap is not None
                # Read size header
                self.response_mmap.seek(0)
                size_bytes = self.response_mmap.read(self.HEADER_SIZE)
                size = struct.unpack("I", size_bytes)[0]
                # Read data
                data = self.response_mmap.read(size)

                # Signal empty slot
                self.response_empty_sem.release()

                return data
            except posix_ipc.BusyError as e:
                raise RPCTimeoutError("Timeout receiving response") from e
            except Exception as e:
                raise RPCTransportError(f"Failed to receive response: {e}") from e

    def cleanup(self) -> None:
        """Clean up all IPC resources."""

        with self._lock:
            def safe_call(func) -> None:
                """Execute a callable safely, ignoring all exceptions."""
                try:
                    func()
                except Exception:
                    pass

            def cleanup_mmap(mmap_obj: mmap.mmap | None) -> None:
                if mmap_obj:
                    safe_call(mmap_obj.close)

            def cleanup_shm(shm_obj: posix_ipc.SharedMemory | None, shm_name: str) -> None:
                if shm_obj:
                    safe_call(shm_obj.close_fd)
                    if self.create:
                        safe_call(lambda: posix_ipc.unlink_shared_memory(shm_name))

            def cleanup_sem(sem_obj: posix_ipc.Semaphore | None, sem_name: str) -> None:
                if sem_obj:
                    safe_call(sem_obj.close)
                    if self.create:
                        safe_call(lambda: posix_ipc.unlink_semaphore(sem_name))

            # Close mmap objects
            cleanup_mmap(self.request_mmap)
            self.request_mmap = None
            cleanup_mmap(self.response_mmap)
            self.response_mmap = None

            # Close and unlink shared memory (only if created by this instance)
            cleanup_shm(self.request_shm, self.request_shm_name)
            self.request_shm = None
            cleanup_shm(self.response_shm, self.response_shm_name)
            self.response_shm = None

            # Close and unlink semaphores (only if created by this instance)
            cleanup_sem(self.request_empty_sem, self.request_empty_sem_name)
            self.request_empty_sem = None
            cleanup_sem(self.request_full_sem, self.request_full_sem_name)
            self.request_full_sem = None
            cleanup_sem(self.response_empty_sem, self.response_empty_sem_name)
            self.response_empty_sem = None
            cleanup_sem(self.response_full_sem, self.response_full_sem_name)
            self.response_full_sem = None

    def __enter__(self) -> SharedMemoryTransport:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        self.cleanup()
