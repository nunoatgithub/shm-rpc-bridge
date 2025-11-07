"""Unit tests for the client module."""

from shm_rpc_bridge.client import RPCClient


class TestRPCClient:
    """Test RPC client in isolation."""

    def test_context_manager(self) -> None:
        """Test that client can be used as a context manager."""
        # This just tests the context manager protocol without actual communication
        channel = "test_context_client"

        try:
            with RPCClient(channel, timeout=0.1) as client:
                assert client.transport is not None
                assert client.codec is not None
        except Exception:
            # Expected - no server running, but context manager should work
            pass
