"""Tests for the server module."""

from shm_rpc_bridge.server import RPCServer


class TestRPCServer:
    """Test RPC server."""

    def test_register_method(self) -> None:
        """Test registering a method."""
        server = RPCServer("test_register")

        def test_func(x: int) -> int:
            return x * 2

        server.register("test", test_func)
        assert "test" in server.methods
        assert server.methods["test"] == test_func
        server.close()

    def test_register_decorator(self) -> None:
        """Test registering with decorator."""
        server = RPCServer("test_decorator")

        @server.register_function
        def multiply(x: int, y: int) -> int:
            return x * y

        assert "multiply" in server.methods
        server.close()

    def test_context_manager(self) -> None:
        """Test using server as context manager."""
        with RPCServer("test_context_server", timeout=1.0) as server:
            assert server.transport is not None
            server.register("test", lambda: None)
