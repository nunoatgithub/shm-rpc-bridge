"""
RPC server implementation.
"""

from __future__ import annotations

import logging
import signal
from enum import Enum
from typing import Any, Callable

from shm_rpc_bridge.data import RPCCodec, RPCRequest, RPCResponse
from shm_rpc_bridge.exceptions import RPCError, RPCTimeoutError
from shm_rpc_bridge.transport import SharedMemoryTransport

logger = logging.getLogger(__name__)


class RPCServer:
    """RPC server using shared memory transport."""

    class Status(str, Enum):
        INITIALIZED = "INITIALIZED"
        RUNNING = "RUNNING"
        CLOSED = "CLOSED"
        ERROR = "ERROR"

    @staticmethod
    def __running__() -> bool:
        return True

    @staticmethod
    def _assert_no_resources_left_behind(server_name: str) -> None:
        SharedMemoryTransport._assert_no_resources_left_behind(server_name)

    def __init__(
        self,
        name: str,
        buffer_size: int = SharedMemoryTransport.DEFAULT_BUFFER_SIZE,
        timeout: float = SharedMemoryTransport.DEFAULT_TIMEOUT,
    ):
        """
        Initialize the RPC server.

        Args:
            name: Name of the shared memory channel
            buffer_size: Size of shared memory buffers
            timeout: Timeout for operations in seconds (None for blocking)
        """
        self.transport: SharedMemoryTransport | None = None
        self.codec: RPCCodec | None = None
        self.methods: dict[str, Callable[..., Any]] = {}
        self._running: bool = False
        self._signal_handler: _SignalHandler | None = None

        self._signal_handler = _SignalHandler(close_callback=self.close)
        self._signal_handler.start()

        try:
            self.transport = SharedMemoryTransport.create(name, buffer_size, timeout)
            self.codec = RPCCodec()
            self.register("__running__", self.__running__)
        except Exception:
            if self.transport is not None:
                self.transport.close()
            raise

    def register(self, name: str, func: Callable[..., Any]) -> None:
        self.methods[name] = func
        logger.info(f"Registered method: {name}")

    def register_function(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to register a function."""
        self.register(func.__name__, func)
        return func

    def start(self) -> None:
        """
        Start the server and handle requests in a loop.

        This will block until close() is called (in another thread) or an error occurs.
        """
        assert self.transport is not None
        logger.info(f"Server started on channel: {self.transport.name}")
        self._running = True

        try:
            while self._running:
                self._handle_request()
        except Exception:
            logger.error("Server error", exc_info=True)
            raise
        finally:
            self.close()
            logger.warning("Server successfully decommissioned.")

    def close(self) -> None:
        self._running = False
        if self.transport is not None:
            try:
                self.transport.close()
            finally:
                self.transport = None

        # Unregister signal/atexit handlers managed by the helper
        if self._signal_handler is not None:
            self._signal_handler.stop()

    def _status(self) -> Status:
        if self.transport is None:
            return self.Status.ERROR if self._running else self.Status.CLOSED

        if not self._running:
            return self.Status.INITIALIZED

        # Probe the running state by opening a short-lived transport and calling the health method
        probe_transport: SharedMemoryTransport | None = None
        try:
            probe_transport = SharedMemoryTransport.open(
                self.transport.name, self.transport.buffer_size
            )
            assert self.codec is not None
            encoded_request = self.codec.encode_request(RPCRequest("0", "__running__", {}))
            probe_transport.send_request(encoded_request)
            encoded_response = probe_transport.receive_response()
            response = self.codec.decode_response(encoded_response)
            return self.Status.RUNNING if response.error is None else self.Status.ERROR
        except RPCError:
            return self.Status.ERROR
        finally:
            if probe_transport is not None:
                probe_transport.close()

    def _receive_request(self) -> bytes | None:
        assert self.transport is not None
        try:
            return self.transport.receive_request()
        except RPCTimeoutError:
            return None

    def _handle_request(self) -> None:
        data = self._receive_request()
        if data is None:
            return

        assert self.codec is not None
        request = self.codec.decode_request(data)
        logger.debug(f"Received request: {request.method} ({request.request_id})")

        # Execute method and create response
        try:
            if request.method not in self.methods:
                raise RPCError(f"Unknown method: {request.method}")

            method = self.methods[request.method]
            result = method(**request.params)

            response = RPCResponse(
                request_id=request.request_id,
                result=result,
                error=None,
            )
            logger.debug(f"Request {request.request_id} succeeded")

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Request {request.request_id} failed", exc_info=True)
            response = RPCResponse(
                request_id=request.request_id,
                result=None,
                error=error_msg,
            )

        # Send response
        assert self.codec is not None
        response_data = self.codec.encode_response(response)
        assert self.transport is not None
        try:
            self.transport.send_response(response_data)
        except RPCTimeoutError as e:
            # Timeout sending response is a REAL error - client not reading
            logger.error(f"Timeout sending response: {e}")
            raise

    def __enter__(self) -> RPCServer:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            logger.warning("Exception during RPCServer.__del__", exc_info=True)


class _SignalHandler:
    """Internal helper that registers signal handlers (SIGTERM, SIGINT) to call a provided
    cleanup callback.

    Responsibilities:
    - Register signal handlers and save previous handlers so they can be restored.

    The implementation is defensive (wraps platform differences in try/except).
    """

    def __init__(self, close_callback: Callable[[], None]):
        self._close_callback = close_callback
        self._prev_handlers: dict[str, Any] = {}
        self._started = False

    def start(self) -> None:
        try:
            # Save previous handlers
            try:
                self._prev_handlers["sigterm"] = signal.getsignal(signal.SIGTERM)
                self._prev_handlers["sigint"] = signal.getsignal(signal.SIGINT)
                # Install our handler
                signal.signal(signal.SIGTERM, self._handler)
                signal.signal(signal.SIGINT, self._handler)
            except Exception:
                # Non-fatal: signal support may be restricted on some platforms
                logger.warning("Could not register signal handlers for RPCServer", exc_info=True)

            self._started = True
        except Exception:
            # Defensive: ensure no exception escapes the manager
            logger.warning("Unexpected error while registering signal handlers", exc_info=True)

    def stop(self) -> None:
        """Restore previous signal handlers and unregister atexit handler if registered."""
        try:
            if not self._started:
                return

            try:
                if "sigterm" in self._prev_handlers:
                    signal.signal(signal.SIGTERM, self._prev_handlers["sigterm"])
                if "sigint" in self._prev_handlers:
                    signal.signal(signal.SIGINT, self._prev_handlers["sigint"])
            except Exception:
                logger.info("Could not restore previous signal handlers", exc_info=True)

            self._started = False
        except Exception:
            # Defensive catch-all to prevent propagation to RPCServer
            logger.info("Unexpected error while unregistering signal handlers", exc_info=True)

        self._started = False

    def _handler(self, signum: int, frame: Any) -> None:
        """Signal handler that attempts a clean shutdown by calling the provided callback."""
        logger.info(f"Received signal {signum}; shutting down RPCServer")
        try:
            self._close_callback()
        except Exception:
            logger.info("Error while closing server from signal handler", exc_info=True)
