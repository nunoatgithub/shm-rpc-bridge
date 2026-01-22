"""
RPC client implementation.
"""

from __future__ import annotations

import uuid
from typing import Any

from shm_rpc_bridge._internal.data import RPCCodec, RPCRequest
from shm_rpc_bridge.exceptions import RPCError, RPCMethodError
from shm_rpc_bridge.transport.transport_chooser import SharedMemoryTransport


class RPCClient:
    """RPC client using shared memory transport."""

    def __init__(
        self,
        name: str,
        buffer_size: int = SharedMemoryTransport.DEFAULT_BUFFER_SIZE,
        timeout: float = SharedMemoryTransport.DEFAULT_TIMEOUT,
        wait_for_server: float = 0,
    ):
        """
        Initialize the RPC client.

        Args:
            name: Name of the shared memory channel (must match server)
            buffer_size: Size of shared memory buffers
            timeout: Timeout for RPC calls in seconds
        """

        self.name = name
        self._transport = SharedMemoryTransport.open(
            name=name, buffer_size=buffer_size, timeout=timeout, wait_for_creation=wait_for_server
        )
        self._codec: RPCCodec = RPCCodec()

    def call(self, method: str, **params: Any) -> Any:
        """
        Make an RPC call to the server.

        Args:
            method: Name of the method to call
            **params: Method parameters as keyword arguments

        Returns:
            The result from the server

        Raises:
            RPCError: If the call fails
            RPCMethodError: If the remote method raises an error
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Create request
        request = RPCRequest(
            request_id=request_id,
            method=method,
            params=params,
        )

        # Encode and send request
        request_data = self._codec.encode_request(request)
        self._transport.send_request(request_data)

        # Receive and decode response
        response_data = self._transport.receive_response()
        response = self._codec.decode_response(response_data)

        # Verify request ID matches
        if response.request_id != request_id:
            raise RPCError(
                f"Response ID mismatch: expected {request_id}, got {response.request_id}"
            )

        # Check for errors
        if response.error:
            raise RPCMethodError(response.error)

        return response.result

    def close(self) -> None:
        try:
            self._transport.close()
        finally:
            # Inform the type checker these are intentionally cleared
            self._transport = None  # type: ignore[assignment]
            self._codec = None  # type: ignore[assignment]

    def __enter__(self) -> RPCClient:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        self.close()

    def __delete__(self, instance: Any) -> None:
        self.close()
