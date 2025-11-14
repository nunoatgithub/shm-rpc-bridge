from __future__ import annotations

import types
from abc import ABC, abstractmethod
from typing import ClassVar


class SharedMemoryTransportABC(ABC):
    """
    Transport layer using shared memory.

    Implements a producer-consumer pattern with two buffers:
    - Request buffer: client writes, server reads
    - Response buffer: server writes, client reads
    """

    DEFAULT_BUFFER_SIZE: ClassVar[int]
    DEFAULT_TIMEOUT: ClassVar[float]

    # ------------------------------------------------------------------
    # Lifecycle methods
    # ------------------------------------------------------------------

    @staticmethod
    @abstractmethod
    def create(
        name: str,
        buffer_size: int | None = None,
        timeout: float | None = None,
    ) -> SharedMemoryTransportABC: ...

    @staticmethod
    @abstractmethod
    def open(
        name: str,
        buffer_size: int | None = None,
        timeout: float | None = None,
    ) -> SharedMemoryTransportABC: ...

    @abstractmethod
    def close(self) -> None:
        """Clean up all IPC resources."""
        ...

    # ------------------------------------------------------------------
    # Send / Receive API
    # ------------------------------------------------------------------

    @abstractmethod
    def send_request(self, data: bytes) -> None:
        """
        Send request data (client -> server).

        Args:
            data: Data to send

        Raises:
            RPCTransportError: If send fails
            RPCTimeoutError: If operation times out
        """
        ...

    @abstractmethod
    def receive_request(self) -> bytes:
        """
        Receive request data (server side).

        Returns:
            Received data

        Raises:
            RPCTransportError: If receive fails
            RPCTimeoutError: If operation times out
        """
        ...

    @abstractmethod
    def send_response(self, data: bytes) -> None:
        """
        Send response data (server -> client).

        Args:
            data: Data to send

        Raises:
            RPCTransportError: If send fails
            RPCTimeoutError: If operation times out
        """
        ...

    @abstractmethod
    def receive_response(self) -> bytes:
        """
        Receive response data (client side).

        Returns:
            Received data

        Raises:
            RPCTransportError: If receive fails
            RPCTimeoutError: If operation times out
        """
        ...

    # ------------------------------------------------------------------
    # Context Management
    # ------------------------------------------------------------------

    def __enter__(self) -> SharedMemoryTransportABC:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Cleanup and Other Utilities
    # ------------------------------------------------------------------
    _TRANSPORT_PREFIX: ClassVar[str] = "shm_rpc_bridge"

    @staticmethod
    @abstractmethod
    def delete_resources() -> None:
        """Best-effort removal of leftover IPC objects."""
        ...

    @staticmethod
    @abstractmethod
    def assert_no_resources_left_behind(transport_name: str, *exclusions: str) -> None:
        """
        Assert that no IPC resources are left behind for the given transport name.
        Exclusions represent names to ignore during the verification
        """
        ...

    @staticmethod
    @abstractmethod
    def is_caused_by_a_signal(exc: BaseException) -> bool:
        """Return True if *exc* or any exception in its `__cause__` chain is a
        related with a signal interrupt; depending on the transport the stack traces
        will differ
        """
        ...

    @staticmethod
    def get_shared_mem_names(name: str) -> tuple[str, str]:
        return (
            f"/{SharedMemoryTransportABC._TRANSPORT_PREFIX}_{name}_req",
            f"/{SharedMemoryTransportABC._TRANSPORT_PREFIX}_{name}_resp",
        )
