from __future__ import annotations

import logging
import mmap
import os
import struct
import sys
import threading
import time
from typing import Callable, ClassVar

import posix_ipc

from shm_rpc_bridge.exceptions import RPCTimeoutError, RPCTransportError

from .transport import SharedMemoryTransportABC

logger = logging.getLogger(__name__)


class SharedMemoryTransportPosix(SharedMemoryTransportABC):
    """
    Transport layer using POSIX shared memory (via posix_ipc) and mmap with POSIX semaphores.

    Implements a producer-consumer pattern with two buffers:
    - Request buffer: client writes, server reads
    - Response buffer: server writes, client reads

    Timeout Behavior:
    - All send/receive operations support configurable timeouts
    - POSIX semaphore acquire() with timeout raises posix_ipc.BusyError on timeout
    - BusyError is caught and converted to RPCTimeoutError for consistent API
    - Timeout semantics are platform-dependent but generally reliable on Linux/macOS

    See (Stevens & Rago, 2013; Tanenbaum & Bos, 2015)
    """

    HEADER_SIZE: ClassVar[int] = 4  # 4 bytes for message length
    DEFAULT_BUFFER_SIZE: ClassVar[int] = 4096  # 4KB default buffer
    DEFAULT_TIMEOUT: ClassVar[float] = 5.0  # 5 seconds

    @staticmethod
    def create(
        name: str,
        buffer_size: int | None = DEFAULT_BUFFER_SIZE,
        timeout: float | None = DEFAULT_TIMEOUT,
    ) -> SharedMemoryTransportPosix:
        assert buffer_size is not None
        assert timeout is not None
        return SharedMemoryTransportPosix(
            name=name, buffer_size=buffer_size, create=True, timeout=timeout
        )

    @staticmethod
    def open(
        name: str,
        buffer_size: int | None = DEFAULT_BUFFER_SIZE,
        timeout: float | None = DEFAULT_TIMEOUT,
        wait_for_creation: float = 0,
    ) -> SharedMemoryTransportPosix:
        assert buffer_size is not None
        assert timeout is not None

        start = time.monotonic()
        while True:
            try:
                return SharedMemoryTransportPosix(
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

    @staticmethod
    def _get_request_semaphore_names(name: str) -> tuple[str, str]:
        return (
            f"/{SharedMemoryTransportABC._TRANSPORT_PREFIX}_{name}_req_empty",
            f"/{SharedMemoryTransportABC._TRANSPORT_PREFIX}_{name}_req_full",
        )

    @staticmethod
    def _get_response_semaphore_names(name: str) -> tuple[str, str]:
        return (
            f"/{SharedMemoryTransportABC._TRANSPORT_PREFIX}_{name}_resp_empty",
            f"/{SharedMemoryTransportABC._TRANSPORT_PREFIX}_{name}_resp_full",
        )

    def __init__(
        self,
        name: str,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
        create: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
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
        # Avoid shadowing the class staticmethod `create`
        self.owner = create

        # Lock to synchronize cleanup with send/receive operations
        self._lock = threading.RLock()

        # Names for POSIX shared memory segments (need / prefix)
        self.request_shm_name, self.response_shm_name = self.get_shared_mem_names(name)

        # Semaphore names (POSIX semaphores need / prefix)
        self.request_empty_sem_name, self.request_full_sem_name = self._get_request_semaphore_names(
            name
        )
        self.response_empty_sem_name, self.response_full_sem_name = (
            self._get_response_semaphore_names(name)
        )

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
        logger.info("Creating POSIX resources for channel %s", self.name)

        # Create POSIX shared memory segments
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
        logger.info("All POSIX resources for channel %s successfully created.", self.name)

    def _open_resources(self) -> None:
        logger.info("Opening POSIX resources for channel %s", self.name)

        # Open existing POSIX shared memory segments
        self.request_shm = posix_ipc.SharedMemory(
            self.request_shm_name,
            flags=0,
        )
        self.response_shm = posix_ipc.SharedMemory(
            self.response_shm_name,
            flags=0,
        )

        # Fail if actual size is smaller than requested;
        # allow larger to account for page-size rounding in macOS

        request_stat = os.fstat(self.request_shm.fd)
        response_stat = os.fstat(self.response_shm.fd)

        actual_req_size = request_stat.st_size
        actual_resp_size = response_stat.st_size

        if actual_req_size < self.buffer_size:
            raise RPCTransportError(
                f"Request shared memory size mismatch: expected at least {self.buffer_size}, "
                f"got {actual_req_size}"
            )
        if actual_resp_size < self.buffer_size:
            raise RPCTransportError(
                f"Response shared memory size mismatch: expected at least {self.buffer_size}, "
                f"got {actual_resp_size}"
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

        # Open semaphores
        self.request_empty_sem = posix_ipc.Semaphore(self.request_empty_sem_name)
        self.request_full_sem = posix_ipc.Semaphore(self.request_full_sem_name)
        self.response_empty_sem = posix_ipc.Semaphore(self.response_empty_sem_name)
        self.response_full_sem = posix_ipc.Semaphore(self.response_full_sem_name)

        logger.info("All POSIX resources for channel %s successfully opened.", self.name)

    def __del__(self) -> None:
        self.close()

    def send_request(self, data: bytes) -> None:
        logger.debug("Sending request on channel %s.", self.name)

        if len(data) > self.buffer_size - self.HEADER_SIZE:
            raise RPCTransportError(f"Message too large: {len(data)} bytes exceeds buffer size")

        logger.debug("send_request -> waiting for lock in channel %s...", self.name)

        with self._lock:
            logger.debug("send_request -> acquired lock in channel %s...", self.name)

            try:
                # Wait for empty slot
                assert self.request_empty_sem is not None
                assert self.request_full_sem is not None

                logger.debug(
                    "send_request -> acquiring semaphore %s...",
                    self.request_empty_sem_name,
                )

                self.portable_acquire(self.request_empty_sem, self.timeout)

                logger.debug(
                    "send_request -> semaphore %s acquired. ready to send request!",
                    self.request_empty_sem_name,
                )

                # Zero-copy write using mmap
                assert self.request_mmap is not None
                size = len(data)
                # Write size header (4 bytes)
                self.request_mmap.seek(0)
                self.request_mmap.write(struct.pack("I", size))
                # Zero-copy write of data
                self.request_mmap.write(data)

                logger.debug(
                    "send_request -> request written (%d bytes). releasing semaphore %s...",
                    len(data),
                    self.request_full_sem_name,
                )

                # Signal full slot
                self.request_full_sem.release()

                logger.debug(
                    "send_request -> released semaphore %s.",
                    self.request_full_sem_name,
                )

            except posix_ipc.BusyError as e:
                raise RPCTimeoutError("Timeout sending request") from e
            except Exception as e:
                raise RPCTransportError(f"Failed to send request: {e}") from e

            finally:
                logger.debug("send_request -> releasing lock in channel %s...", self.name)

    def receive_request(self) -> bytes:
        logger.debug("receive_request -> waiting for lock in channel %s...", self.name)

        with self._lock:
            logger.debug("receive_request -> acquired lock in channel %s...", self.name)

            try:
                # Wait for full slot
                assert self.request_full_sem is not None
                assert self.request_empty_sem is not None

                logger.debug(
                    "receive_request -> acquiring semaphore %s...",
                    self.request_full_sem_name,
                )

                self.portable_acquire(self.request_full_sem, self.timeout)

                logger.debug(
                    "receive_request -> semaphore %s acquired. ready to read request!",
                    self.request_full_sem_name,
                )

                # Zero-copy read using mmap
                assert self.request_mmap is not None
                # Read size header
                self.request_mmap.seek(0)
                size_bytes = self.request_mmap.read(self.HEADER_SIZE)
                size = struct.unpack("I", size_bytes)[0]
                # Validate size
                if size < 0 or size > self.buffer_size - self.HEADER_SIZE:
                    raise RPCTransportError(f"Invalid message size: {size}")
                # Read data
                data = self.request_mmap.read(size)

                # Signal empty slot
                self.request_empty_sem.release()

                logger.debug(
                    "receive_request -> semaphore %s released. "
                    "returning received request (%d bytes)!",
                    self.request_empty_sem_name,
                    len(data),
                )

                return data

            except posix_ipc.BusyError as e:
                raise RPCTimeoutError("Timeout receiving request") from e
            except Exception as e:
                raise RPCTransportError(f"Failed to receive request: {e}") from e

            finally:
                logger.debug("receive_request -> releasing lock in channel %s...", self.name)

    def send_response(self, data: bytes) -> None:
        if len(data) > self.buffer_size - self.HEADER_SIZE:
            raise RPCTransportError(f"Message too large: {len(data)} bytes exceeds buffer size")

        logger.debug("send_response -> waiting for lock in channel %s...", self.name)

        with self._lock:
            logger.debug("send_response -> acquired lock in channel %s...", self.name)

            try:
                # Wait for empty slot
                assert self.response_empty_sem is not None
                assert self.response_full_sem is not None

                logger.debug(
                    "send_response -> acquiring semaphore %s...",
                    self.response_empty_sem_name,
                )

                self.portable_acquire(self.response_empty_sem, self.timeout)

                logger.debug(
                    "send_response -> semaphore %s acquired. ready to send response!",
                    self.response_empty_sem_name,
                )

                # Zero-copy write using mmap
                assert self.response_mmap is not None
                size = len(data)
                # Write size header (4 bytes)
                self.response_mmap.seek(0)
                self.response_mmap.write(struct.pack("I", size))
                # Zero-copy write of data
                self.response_mmap.write(data)

                logger.debug(
                    "send_response -> response written (%d bytes). releasing semaphore %s...",
                    len(data),
                    self.response_full_sem_name,
                )

                # Signal full slot
                self.response_full_sem.release()

                logger.debug(
                    "send_response -> released semaphore %s.",
                    self.response_full_sem_name,
                )

            except posix_ipc.BusyError as e:
                raise RPCTimeoutError("Timeout sending response") from e
            except Exception as e:
                raise RPCTransportError(f"Failed to send response: {e}") from e

            finally:
                logger.debug("send_response -> releasing lock in channel %s...", self.name)

    def receive_response(self) -> bytes:
        logger.debug("receive_response -> waiting for lock in channel %s...", self.name)

        with self._lock:
            logger.debug("receive_response -> acquired lock in channel %s...", self.name)

            try:
                # Wait for full slot
                assert self.response_full_sem is not None
                assert self.response_empty_sem is not None

                logger.debug(
                    "receive_response -> acquiring semaphore %s...",
                    self.response_full_sem_name,
                )

                self.portable_acquire(self.response_full_sem, self.timeout)

                logger.debug(
                    "receive_response -> semaphore %s acquired. ready to read response!",
                    self.response_full_sem_name,
                )

                # Zero-copy read using mmap
                assert self.response_mmap is not None
                # Read size header
                self.response_mmap.seek(0)
                size_bytes = self.response_mmap.read(self.HEADER_SIZE)
                size = struct.unpack("I", size_bytes)[0]
                # Validate size
                if size < 0 or size > self.buffer_size - self.HEADER_SIZE:
                    raise RPCTransportError(f"Invalid message size: {size}")
                # Read data
                data = self.response_mmap.read(size)

                # Signal empty slot
                self.response_empty_sem.release()

                logger.debug(
                    "receive_response -> semaphore %s released. "
                    "returning received response (%d bytes)!",
                    self.response_empty_sem_name,
                    len(data),
                )

                return data

            except posix_ipc.BusyError as e:
                raise RPCTimeoutError("Timeout receiving response") from e
            except Exception as e:
                raise RPCTransportError(f"Failed to receive response: {e}") from e

            finally:
                logger.debug("receive_response -> releasing lock in channel %s...", self.name)

    def close(self) -> None:
        logger.debug("close -> waiting for lock in channel %s...", self.name)

        with self._lock:
            logger.debug("close -> acquired lock in channel %s...", self.name)

            def safe_call(func: Callable[[], None]) -> None:
                """Execute a callable safely, ignoring all exceptions."""
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

            def cleanup_sem(sem_obj: posix_ipc.Semaphore | None, sem_name: str) -> None:
                if sem_obj:
                    safe_call(sem_obj.close)
                    if self.owner:
                        safe_call(lambda: posix_ipc.unlink_semaphore(sem_name))

            try:
                logger.info("close -> unlinking resources in channel %s...", self.name)

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

                logger.info("close -> unlinked all resources in channel %s.", self.name)

            finally:
                logger.debug("close -> releasing lock in channel %s...", self.name)

    # ------------------------------------------------------------------
    # Portability Linux / MacOS
    # ------------------------------------------------------------------

    @staticmethod
    def portable_acquire(sem: posix_ipc.Semaphore, timeout: float) -> None:
        # Fast path for Linux and other sane platforms
        if sys.platform != "darwin":
            # BusyError is raised by when timeout expires
            sem.acquire(timeout)  # native timed wait, very efficient
            return

        deadline = time.time() + timeout
        delay = 0.0001  # small, grows

        while True:
            try:
                sem.acquire(timeout=0)
                return
            except posix_ipc.BusyError:
                if time.time() >= deadline:
                    raise posix_ipc.BusyError("Semaphore acquire timed out")
                time.sleep(delay)
                if delay < 0.005:
                    delay *= 2

    # ------------------------------------------------------------------
    # Cleanup and others
    # ------------------------------------------------------------------
    @staticmethod
    def delete_resources() -> None:
        """
        Removes candidate shared memory and semaphore files on Linux and attempts
        POSIX unlink via libc on macOS; failures are ignored.
        """
        import ctypes
        import platform

        shm_prefix = SharedMemoryTransportABC._TRANSPORT_PREFIX
        sem_prefix = f"sem.{shm_prefix}"
        # primary target on Linux
        shm_dir = "/dev/shm"
        # additional dirs to probe (macOS often doesn't expose /dev/shm)
        probe_dirs = [shm_dir, "/var/run", "/private/var/run", "/var/tmp", "/tmp"]

        is_darwin = platform.system() == "Darwin"
        libc = None
        if is_darwin:
            try:
                libc = ctypes.CDLL("libc.dylib")
            except Exception:
                libc = None

        for d in probe_dirs:
            if not os.path.exists(d):
                continue
            for filename in os.listdir(d):
                if filename.startswith(shm_prefix) or filename.startswith(sem_prefix):
                    path = os.path.join(d, filename)
                    try:
                        os.unlink(path)
                    except Exception:
                        pass
                    # on macOS try POSIX unlink for named objects as a fallback
                    if is_darwin and libc is not None:
                        try:
                            # try both with and without leading slash
                            candidate_names = [filename]
                            if not filename.startswith("/"):
                                candidate_names.insert(0, "/" + filename)
                            for name in candidate_names:
                                bname = name.encode()
                                if filename.startswith(sem_prefix):
                                    try:
                                        libc.sem_unlink(bname)
                                    except Exception:
                                        pass
                                else:
                                    try:
                                        libc.shm_unlink(bname)
                                    except Exception:
                                        pass
                        except Exception:
                            pass

    @staticmethod
    def assert_no_resources_left_behind(transport_name: str, *exclusions: str) -> None:
        """
        Assert that no IPC resources are left behind for the given transport name.
        Exclusions represent names to ignore during the verification
        """
        for shm_name in SharedMemoryTransportABC.get_shared_mem_names(transport_name):
            if shm_name in exclusions:
                continue  # Skip excluded resources
            try:
                shm = posix_ipc.SharedMemory(shm_name, flags=0)  # flags=0 means open only
                shm.close_fd()
                raise AssertionError(f"Shared memory {shm_name} still exists")
            except posix_ipc.ExistentialError:
                pass  # doesn't exist — good

        for sem_name in SharedMemoryTransportPosix._get_request_semaphore_names(
            transport_name
        ) + SharedMemoryTransportPosix._get_response_semaphore_names(transport_name):
            if sem_name in exclusions:
                continue  # Skip excluded resources
            try:
                sem = posix_ipc.Semaphore(sem_name, flags=0)
                sem.close()
                raise AssertionError(f"Semaphore {sem_name} still exists")
            except posix_ipc.ExistentialError:
                pass  # doesn't exist — good

    @staticmethod
    def is_caused_by_a_signal(exc: BaseException) -> bool:
        """
        Return True if *exc* or any exception in its `__cause__` chain is a
        `posix_ipc.SignalError`
        """
        cause = getattr(exc, "__cause__", None)
        while cause is not None:
            if isinstance(cause, posix_ipc.SignalError):
                # the following code always returns False, making inviable to
                # discriminate sigterm and sigint only
                #     # Some implementations expose the signal number under different names.
                #     signo = getattr(cause, "signo", None)
                #     if signo is None:
                #         signo = getattr(cause, "signum", None)
                #     if signo is None:
                #         signo = getattr(cause, "sig", None)
                #     if signo in (signal.SIGTERM, signal.SIGINT):
                #         return True
                #     return False
                return True
            cause = getattr(cause, "__cause__", None)
        return False
