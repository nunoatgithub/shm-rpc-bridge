"""
RPC server implementation.
"""

from __future__ import annotations

import logging
import signal
from enum import Enum
from typing import Any, Callable

from shm_rpc_bridge._internal.data import RPCCodec, RPCRequest, RPCResponse
from shm_rpc_bridge.exceptions import RPCError, RPCTimeoutError, RPCTransportError
from shm_rpc_bridge.transport.transport_chooser import SharedMemoryTransport

logger = logging.getLogger(__name__)


class RPCServer:
    """RPC server using shared memory transport."""

    class Status(str, Enum):
        INITIALIZED = "INITIALIZED"
        RUNNING = "RUNNING"
        CLOSED = "CLOSED"
        ERROR = "ERROR"

    class _ServerInterruptionError(RPCTransportError):
        """Raised when server receive method is interrupted by ANY signal
        (there is no api available to detect only SIGTERM or SIGINT)."""

        pass

    @staticmethod
    def __running__() -> bool:
        return True

    @staticmethod
    def _assert_no_resources_left_behind(server_name: str) -> None:
        SharedMemoryTransport.assert_no_resources_left_behind(server_name)

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
        self.name: str = name
        self._transport: SharedMemoryTransport | None = None
        self._codec: RPCCodec | None = None
        self._methods: dict[str, Callable[..., Any]] = {}
        self._running: bool = False
        self._signal_handler: _SignalHandler | None = None

        self._signal_handler = _SignalHandler(close_callback=self.close)
        self._signal_handler.start()

        try:
            self._transport = SharedMemoryTransport.create(name, buffer_size, timeout)
            self._codec = RPCCodec()
            self.register("__running__", self.__running__)
        except Exception:
            if self._transport is not None:
                self._transport.close()
            raise

    def register(self, name: str, func: Callable[..., Any]) -> None:
        self._methods[name] = func
        logger.info("[Server %s]: registered method %s", self.name, name)

    def register_function(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to register a function."""
        self.register(func.__name__, func)
        return func

    def start(self) -> None:
        """
        Start the server and handle requests in a loop.

        This will block until close() is called (in another thread) or an error occurs.
        """
        assert self._transport is not None
        logger.info("[Server %s]: started", self.name)
        self._running = True

        try:
            while self._running:
                self._handle_request()
        except self._ServerInterruptionError:
            logger.debug("[Server %s]: interrupted", self.name, exc_info=True)
        except Exception:
            logger.error("[Server %s]: error", self.name, exc_info=True)
            raise
        finally:
            self.close()
            logger.warning("[Server %s]: successfully decommissioned.", self.name)

    def close(self) -> None:
        self._running = False
        if self._transport is not None:
            try:
                self._transport.close()
            finally:
                self._transport = None

        if self._signal_handler is not None:
            self._signal_handler.stop()

    def _status(self) -> Status:
        if self._transport is None:
            return self.Status.ERROR if self._running else self.Status.CLOSED

        if not self._running:
            return self.Status.INITIALIZED

        # Probe the running state by opening a short-lived transport and calling the health method
        probe_transport: SharedMemoryTransport | None = None
        try:
            probe_transport = SharedMemoryTransport.open(
                self._transport.name, self._transport.buffer_size
            )
            assert self._codec is not None
            encoded_request = self._codec.encode_request(RPCRequest("0", "__running__", {}))
            probe_transport.send_request(encoded_request)
            encoded_response = probe_transport.receive_response()
            response = self._codec.decode_response(encoded_response)
            return self.Status.RUNNING if response.error is None else self.Status.ERROR
        except RPCError:
            return self.Status.ERROR
        finally:
            if probe_transport is not None:
                probe_transport.close()

    def _receive_request(self) -> bytes | None:
        assert self._transport is not None
        try:
            return self._transport.receive_request()
        # ignore as the normal consequence of waiting for a request that hasn't arrived yet
        except RPCTimeoutError:
            return None
        except Exception as e:
            if SharedMemoryTransport.is_caused_by_a_signal(e):
                raise self._ServerInterruptionError from e
            else:
                raise e

    def _handle_request(self) -> RPCResponse | None:
        data = self._receive_request()
        if data is None:
            return None

        assert self._codec is not None
        request = self._codec.decode_request(data)
        logger.debug(
            "[Server %s]: received request : %s",
            self.name,
            f"{request.method} ({request.request_id})",
        )

        # Execute method and create response
        try:
            if request.method not in self._methods:
                raise RPCError(f"Unknown method: {request.method}")

            method = self._methods[request.method]
            result = method(**request.params)

            response = RPCResponse(
                request_id=request.request_id,
                result=result,
                error=None,
            )
            logger.debug("[Server %s]: Request %s succeeded", self.name, request.request_id)

        except Exception as e:
            logger.error(
                "[Server %s]: Request %s failed", self.name, request.request_id, exc_info=True
            )
            error_msg = f"{type(e).__name__}: {str(e)}"
            response = RPCResponse(
                request_id=request.request_id,
                result=None,
                error=error_msg,
            )

        # Send response
        assert self._codec is not None
        response_data = self._codec.encode_response(response)
        assert self._transport is not None
        try:
            logger.debug(
                "[Server %s]: Sending response %s to client", self.name, request.request_id
            )
            self._transport.send_response(response_data)
        except RPCTimeoutError as e:
            # Timeout sending response is a REAL error - client not reading
            logger.error(
                "[Server %s]: Timeout sending response % : %s",
                self.name,
                request.request_id,
                str(e),
            )
            raise

        logger.debug("[Server %s]: Response %s sent", self.name, request.request_id)

        return response

    def __enter__(self) -> RPCServer:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            logger.warning(
                "[Server %s]: Exception during RPCServer.__del__", self.name, exc_info=True
            )


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
        logger.info("Received signal %d; shutting down RPCServer", signum)
        try:
            self._close_callback()
        except Exception:
            logger.info("Error while closing server from signal handler", exc_info=True)
