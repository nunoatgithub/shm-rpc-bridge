from __future__ import annotations

import errno
import logging
import mmap
import os
import struct
import threading
import time
from dataclasses import dataclass
from typing import Callable, ClassVar

import posix_ipc

from shm_rpc_bridge.exceptions import RPCTimeoutError, RPCTransportError

from .linux_futex import FutexWord  # type: ignore[import]
from .transport import SharedMemoryTransportABC


class SharedMemoryTransportFutex(SharedMemoryTransportABC):
    """
    Linux-only transport using POSIX shared memory + mmap for data,
    and futex-backed synchronization instead of POSIX semaphores.
    """

    DEFAULT_BUFFER_SIZE: ClassVar[int] = 4096
    DEFAULT_TIMEOUT: ClassVar[float] = 5.0

    @staticmethod
    def create(
        name: str,
        buffer_size: int | None = DEFAULT_BUFFER_SIZE,
        timeout: float | None = DEFAULT_TIMEOUT,
    ) -> SharedMemoryTransportFutex:
        assert buffer_size is not None
        assert timeout is not None
        return SharedMemoryTransportFutex(
            name=name,
            buffer_size=buffer_size,
            create=True,
            timeout=timeout,
        )

    @staticmethod
    def open(
        name: str,
        buffer_size: int | None = DEFAULT_BUFFER_SIZE,
        timeout: float | None = DEFAULT_TIMEOUT,
        wait_for_creation: float = 0,
    ) -> SharedMemoryTransportFutex:
        assert buffer_size is not None
        assert timeout is not None

        start = time.monotonic()
        while True:
            try:
                return SharedMemoryTransportFutex(
                    name=name,
                    buffer_size=buffer_size,
                    create=False,
                    timeout=timeout,
                )
            except RPCTransportError as e:
                if wait_for_creation <= 0.0:
                    raise
                if time.monotonic() - start > wait_for_creation:
                    raise RPCTransportError(
                        f"Timed out waiting for shared memory transport {name}.{e}"
                    )
            time.sleep(0.01)

    def __init__(
        self,
        name: str,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
        create: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.name = name
        self.buffer_size = buffer_size
        self.timeout = timeout
        # Avoid shadowing the class staticmethod `create`
        self.owner = create

        # Lock to synchronize cleanup with send/receive operations
        self._lock = threading.RLock()

        self.request_shm_name = f"/shm_rpc_bridge_{name}_req"
        self.response_shm_name = f"/shm_rpc_bridge_{name}_resp"

        self.request_shm: posix_ipc.SharedMemory | None = None
        self.response_shm: posix_ipc.SharedMemory | None = None

        self.request_mmap: mmap.mmap | None = None
        self.response_mmap: mmap.mmap | None = None

        self._request_sync: _BufferSync | None = None
        self._response_sync: _BufferSync | None = None

        self._initialize()

    def _initialize(self) -> None:
        logging.info("Starting {}", self.__class__.__name__)
        try:
            if self.owner:
                # Server creates resources
                self._create_resources()
            else:
                # Client opens existing resources
                self._open_resources()
        except Exception as e:
            self.close()
            raise RPCTransportError(f"Failed to initialize transport: {e}") from e

    def _create_resources(self) -> None:
        self.request_shm = posix_ipc.SharedMemory(
            self.request_shm_name,
            # It tells the call to create the named IPC object and fail if it already exists
            flags=posix_ipc.O_CREX,
            mode=0o600,  # same as chmod 600. This restricts access to the creating user.
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

        # Close file descriptors early - mmap keeps the mapping valid
        self.request_shm.close_fd()
        self.response_shm.close_fd()

        self._request_sync = _BufferSync(self.request_mmap, self.buffer_size)
        self._response_sync = _BufferSync(self.response_mmap, self.buffer_size)
        self._request_sync.init_empty()
        self._response_sync.init_empty()

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

        # Close file descriptors early - mmap keeps the mapping valid
        self.request_shm.close_fd()
        self.response_shm.close_fd()

        self._request_sync = _BufferSync(self.request_mmap, self.buffer_size)
        self._response_sync = _BufferSync(self.response_mmap, self.buffer_size)

    def send_request(self, data: bytes) -> None:
        with self._lock:
            try:
                assert self._request_sync is not None
                self._request_sync.send(data, timeout=self.timeout)
            except RPCTimeoutError:
                raise
            except Exception as e:
                raise RPCTransportError(f"Failed to send request: {e}") from e

    def receive_request(self) -> bytes:
        with self._lock:
            try:
                assert self._request_sync is not None
                return self._request_sync.recv(timeout=self.timeout)
            except RPCTimeoutError:
                raise
            except Exception as e:
                raise RPCTransportError(f"Failed to receive request: {e}") from e

    def send_response(self, data: bytes) -> None:
        with self._lock:
            try:
                assert self._response_sync is not None
                self._response_sync.send(data, timeout=self.timeout)
            except RPCTimeoutError:
                raise
            except Exception as e:
                raise RPCTransportError(f"Failed to send response: {e}") from e

    def receive_response(self) -> bytes:
        with self._lock:
            try:
                assert self._response_sync is not None
                return self._response_sync.recv(timeout=self.timeout)
            except RPCTimeoutError:
                raise
            except Exception as e:
                raise RPCTransportError(f"Failed to receive response: {e}") from e

    def close(self) -> None:
        with self._lock:

            def safe_call(func: Callable[[], None]) -> None:
                try:
                    func()
                except Exception:
                    pass

            def cleanup_mmap(mmap_obj: mmap.mmap | None) -> None:
                if mmap_obj:
                    safe_call(mmap_obj.close)

            def cleanup_shm(shm_obj: posix_ipc.SharedMemory | None, shm_name: str) -> None:
                # Note: FD already closed early after mmap creation
                if shm_obj and self.owner:
                    safe_call(lambda: posix_ipc.unlink_shared_memory(shm_name))

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

            self._request_sync = None
            self._response_sync = None

    @staticmethod
    def delete_resources() -> None:
        """
        Removes shared memory files on Linux
        """
        shm_prefix = SharedMemoryTransportABC._TRANSPORT_PREFIX
        # primary target on Linux
        shm_dir = "/dev/shm"
        if not os.path.exists(shm_dir):
            return

        for filename in os.listdir(shm_dir):
            if filename.startswith(shm_prefix):
                path = os.path.join(shm_dir, filename)
                try:
                    os.unlink(path)
                except Exception:
                    pass

    @staticmethod
    def assert_no_resources_left_behind(transport_name: str, *exclusions: str) -> None:
        for shm_name in SharedMemoryTransportABC.get_shared_mem_names(transport_name):
            if shm_name in exclusions:
                continue  # Skip excluded resources
            try:
                shm = posix_ipc.SharedMemory(shm_name, flags=0)  # flags=0 means open only
                shm.close_fd()
                raise AssertionError(f"Shared memory {shm_name} still exists")
            except posix_ipc.ExistentialError:
                pass  # doesn't exist — good

    @staticmethod
    def is_caused_by_a_signal(exc: BaseException) -> bool:
        """
        Return True if *exc* or any exception in its `__cause__` chain is caused by EINTR
        """
        cause = getattr(exc, "__cause__", None)
        while cause is not None:
            # Check common errno attribute for EINTR
            errno_val = getattr(cause, "errno", None)
            if isinstance(errno_val, int) and errno_val == errno.EINTR:
                return True
            cause = getattr(cause, "__cause__", None)
        return False


@dataclass
class _BufferSync:
    """
    Synchronization for one unidirectional buffer (request or response).

    (Written by AI)

    Layout in the mmap'd region:

        0..4   : state word (int32) for futex (0 = EMPTY, 1 = FULL)
        4..8   : length (uint32, big-endian)
        8..N   : payload bytes
    """

    mmap_obj: mmap.mmap
    buf_size: int

    STATE_OFFSET: int = 0
    LEN_OFFSET: int = 4
    HEADER_SIZE: int = 8

    EMPTY: int = 0
    FULL: int = 1

    def __post_init__(self) -> None:
        if self.buf_size < self.HEADER_SIZE:
            raise ValueError("buffer_size too small")
        state_view = memoryview(self.mmap_obj)[self.STATE_OFFSET : self.STATE_OFFSET + 4]
        self._state = FutexWord(state_view)

    def init_empty(self) -> None:
        """Explicitly set state to EMPTY (call only on creator side)."""
        self._state.store(self.EMPTY)

    def _write_payload(self, data: bytes) -> None:
        max_payload = self.buf_size - self.HEADER_SIZE
        if len(data) > max_payload:
            raise RPCTransportError(f"Message too large for buffer: {len(data)} > {max_payload}")
        struct.pack_into(">I", self.mmap_obj, self.LEN_OFFSET, len(data))
        self.mmap_obj[self.HEADER_SIZE : self.HEADER_SIZE + len(data)] = data

    def _read_payload(self) -> bytes:
        (length,) = struct.unpack_from(">I", self.mmap_obj, self.LEN_OFFSET)
        max_payload = self.buf_size - self.HEADER_SIZE
        if length > max_payload:
            raise RPCTransportError(f"Corrupted message length: {length} > {max_payload}")
        return bytes(self.mmap_obj[self.HEADER_SIZE : self.HEADER_SIZE + length])

    def send(self, data: bytes, timeout: float | None) -> None:
        """
        Writer: block in C until state == EMPTY, write, set FULL, wake reader.
        No Python-level busy wait.
        """
        timeout_ns = -1 if timeout is None else int(timeout * 1e9)

        if not self._state.wait_for_value(self.EMPTY, timeout_ns=timeout_ns):
            raise RPCTimeoutError("Timeout waiting for buffer to become EMPTY")

        self._write_payload(data)
        self._state.store(self.FULL)
        self._state.wake(1)

    def recv(self, timeout: float | None) -> bytes:
        """
        Reader: block in C until state == FULL, read, set EMPTY, wake writer.
        No Python-level busy wait.
        """
        timeout_ns = -1 if timeout is None else int(timeout * 1e9)

        if not self._state.wait_for_value(self.FULL, timeout_ns=timeout_ns):
            raise RPCTimeoutError("Timeout waiting for buffer to become FULL")

        data = self._read_payload()
        self._state.store(self.EMPTY)
        self._state.wake(1)
        return data
