"""
Transport layer using shared memory and POSIX semaphores.
"""

from __future__ import annotations

import struct
from multiprocessing import shared_memory

import posix_ipc

from shm_rpc_bridge.exceptions import RPCTimeoutError, RPCTransportError


class SharedMemoryTransport:
    """
    Transport layer using shared memory with POSIX semaphores.

    Implements a producer-consumer pattern with two buffers:
    - Request buffer: client writes, server reads
    - Response buffer: server writes, client reads
    """

    HEADER_SIZE = 4  # 4 bytes for message length
    DEFAULT_BUFFER_SIZE = 3145728  # 3MB default buffer

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

        # Names for shared memory segments (no / prefix for multiprocessing.shared_memory)
        self.request_shm_name = f"{name}_request"
        self.response_shm_name = f"{name}_response"

        # Semaphore names (POSIX semaphores need / prefix)
        self.request_empty_sem_name = f"/{name}_req_empty"  # Counts empty slots
        self.request_full_sem_name = f"/{name}_req_full"  # Counts full slots
        self.response_empty_sem_name = f"/{name}_resp_empty"
        self.response_full_sem_name = f"/{name}_resp_full"

        self.request_shm: shared_memory.SharedMemory | None = None
        self.response_shm: shared_memory.SharedMemory | None = None
        self.request_view: memoryview | None = None
        self.response_view: memoryview | None = None

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
        # Create shared memory segments
        self.request_shm = shared_memory.SharedMemory(
            name=self.request_shm_name,
            create=True,
            size=self.buffer_size,
        )
        self.response_shm = shared_memory.SharedMemory(
            name=self.response_shm_name,
            create=True,
            size=self.buffer_size,
        )

        # Create zero-copy memory views
        self.request_view = memoryview(self.request_shm.buf)
        self.response_view = memoryview(self.response_shm.buf)

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
        # Open existing shared memory segments
        self.request_shm = shared_memory.SharedMemory(
            name=self.request_shm_name,
            create=False,
        )
        self.response_shm = shared_memory.SharedMemory(
            name=self.response_shm_name,
            create=False,
        )

        # Create zero-copy memory views
        self.request_view = memoryview(self.request_shm.buf)
        self.response_view = memoryview(self.response_shm.buf)

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

        try:
            # Wait for empty slot
            assert self.request_empty_sem is not None
            assert self.request_full_sem is not None
            if self.timeout is not None:
                self.request_empty_sem.acquire(timeout=self.timeout)
            else:
                self.request_empty_sem.acquire()

            # Zero-copy write using memoryview
            assert self.request_view is not None
            size = len(data)
            # Write size header (4 bytes)
            self.request_view[0 : self.HEADER_SIZE] = struct.pack("I", size)
            # Zero-copy write of data
            self.request_view[self.HEADER_SIZE : self.HEADER_SIZE + size] = data

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
        try:
            # Wait for full slot
            assert self.request_full_sem is not None
            assert self.request_empty_sem is not None
            if self.timeout is not None:
                self.request_full_sem.acquire(timeout=self.timeout)
            else:
                self.request_full_sem.acquire()

            # Zero-copy read using memoryview
            assert self.request_view is not None
            # Read size header
            size = struct.unpack("I", self.request_view[0 : self.HEADER_SIZE])[0]
            # Read data (only copy when converting to bytes)
            data = bytes(self.request_view[self.HEADER_SIZE : self.HEADER_SIZE + size])

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

        try:
            # Wait for empty slot
            assert self.response_empty_sem is not None
            assert self.response_full_sem is not None
            if self.timeout is not None:
                self.response_empty_sem.acquire(timeout=self.timeout)
            else:
                self.response_empty_sem.acquire()

            # Zero-copy write using memoryview
            assert self.response_view is not None
            size = len(data)
            # Write size header (4 bytes)
            self.response_view[0 : self.HEADER_SIZE] = struct.pack("I", size)
            # Zero-copy write of data
            self.response_view[self.HEADER_SIZE : self.HEADER_SIZE + size] = data

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
        try:
            # Wait for full slot
            assert self.response_full_sem is not None
            assert self.response_empty_sem is not None
            if self.timeout is not None:
                self.response_full_sem.acquire(timeout=self.timeout)
            else:
                self.response_full_sem.acquire()

            # Zero-copy read using memoryview
            assert self.response_view is not None
            # Read size header
            size = struct.unpack("I", self.response_view[0 : self.HEADER_SIZE])[0]
            # Read data (only copy when converting to bytes)
            data = bytes(self.response_view[self.HEADER_SIZE : self.HEADER_SIZE + size])

            # Signal empty slot
            self.response_empty_sem.release()

            return data
        except posix_ipc.BusyError as e:
            raise RPCTimeoutError("Timeout receiving response") from e
        except Exception as e:
            raise RPCTransportError(f"Failed to receive response: {e}") from e

    def cleanup(self) -> None:
        # Release memory views
        if self.request_view:
            try:
                self.request_view.release()
            except Exception:
                pass
        if self.response_view:
            try:
                self.response_view.release()
            except Exception:
                pass

        # Close and unlink shared memory (only if created by this instance)
        if self.request_shm:
            try:
                self.request_shm.close()
            except Exception:
                pass
            if self.create:
                try:
                    self.request_shm.unlink()
                except FileNotFoundError:
                    pass  # Already unlinked
                except Exception:
                    pass
        if self.response_shm:
            try:
                self.response_shm.close()
            except Exception:
                pass
            if self.create:
                try:
                    self.response_shm.unlink()
                except FileNotFoundError:
                    pass  # Already unlinked
                except Exception:
                    pass

        # Close and unlink semaphores (only if created by this instance)
        if self.request_empty_sem:
            try:
                self.request_empty_sem.close()
            except Exception:
                pass
            if self.create:
                try:
                    posix_ipc.unlink_semaphore(self.request_empty_sem_name)
                except Exception:
                    pass
        if self.request_full_sem:
            try:
                self.request_full_sem.close()
            except Exception:
                pass
            if self.create:
                try:
                    posix_ipc.unlink_semaphore(self.request_full_sem_name)
                except Exception:
                    pass
        if self.response_empty_sem:
            try:
                self.response_empty_sem.close()
            except Exception:
                pass
            if self.create:
                try:
                    posix_ipc.unlink_semaphore(self.response_empty_sem_name)
                except Exception:
                    pass
        if self.response_full_sem:
            try:
                self.response_full_sem.close()
            except Exception:
                pass
            if self.create:
                try:
                    posix_ipc.unlink_semaphore(self.response_full_sem_name)
                except Exception:
                    pass

    def __enter__(self) -> SharedMemoryTransport:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        self.cleanup()
