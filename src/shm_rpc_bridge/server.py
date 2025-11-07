"""
RPC server implementation.
"""

from __future__ import annotations

import logging
import traceback
from typing import Any, Callable

from shm_rpc_bridge.data import RPCCodec, RPCResponse
from shm_rpc_bridge.exceptions import RPCError, RPCTimeoutError
from shm_rpc_bridge.transport import SharedMemoryTransport

logger = logging.getLogger(__name__)


class RPCServer:
    """RPC server using shared memory transport."""

    def __init__(
        self,
        name: str,
        buffer_size: int = SharedMemoryTransport.DEFAULT_BUFFER_SIZE,
        timeout: float | None = None,
    ):
        """
        Initialize the RPC server.

        Args:
            name: Name of the shared memory channel
            buffer_size: Size of shared memory buffers
            timeout: Timeout for operations in seconds (None for blocking)
        """
        self.name = name
        self.timeout = timeout
        self.transport = SharedMemoryTransport(
            name=name,
            buffer_size=buffer_size,
            create=True,
            timeout=timeout,
        )
        self.codec = RPCCodec()
        self.methods: dict[str, Callable[..., Any]] = {}
        self._running = False

    def register(self, name: str, func: Callable[..., Any]) -> None:
        self.methods[name] = func
        logger.info(f"Registered method: {name}")

    def register_function(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to register a function."""
        self.register(func.__name__, func)
        return func

    def _receive_request(self) -> bytes | None:
        try:
            return self.transport.receive_request()
        except RPCTimeoutError:
            return None

    def _handle_request(self) -> None:
        if (request_data := self._receive_request()) is None:
            return

        request = self.codec.decode_request(request_data)

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
            logger.error(
                f"Request {request.request_id} failed: {error_msg}\n{traceback.format_exc()}"
            )
            response = RPCResponse(
                request_id=request.request_id,
                result=None,
                error=error_msg,
            )

        # Send response
        response_data = self.codec.encode_response(response)
        try:
            self.transport.send_response(response_data)
        except RPCTimeoutError as e:
            # Timeout sending response is a REAL error - client not reading
            logger.error(f"Timeout sending response: {e}")
            raise

    def start(self) -> None:
        """
        Start the server and handle requests in a loop.

        This will block until stop() is called or an error occurs.
        """
        logger.info(f"Server started on channel: {self.name}")
        self._running = True

        try:
            while self._running:
                self._handle_request()
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        except Exception as e:
            logger.error(f"Server error: {e}\n{traceback.format_exc()}")
            raise
        finally:
            logger.info("Server stopped")

    def stop(self) -> None:
        self._running = False

    def close(self) -> None:
        self.stop()
        self.transport.cleanup()

    def __enter__(self) -> RPCServer:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        self.close()
