"""Integration tests for client-server communication."""

import multiprocessing
import time

import pytest

from shm_rpc_bridge.client import RPCClient
from shm_rpc_bridge.exceptions import RPCMethodError
from shm_rpc_bridge.server import RPCServer


def run_test_server(channel_name: str, num_requests: int = 1) -> None:
    """Run a test server that handles a specific number of requests."""
    server = RPCServer(channel_name, timeout=2.0)

    def add(a: float, b: float) -> float:
        return a + b

    def multiply(x: float, y: float) -> float:
        return x * y

    def divide(a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Division by zero")
        return a / b

    def greet(name: str) -> str:
        return f"Hello, {name}!"

    server.register("add", add)
    server.register("multiply", multiply)
    server.register("divide", divide)
    server.register("greet", greet)

    # Handle the specified number of requests then exit
    count = 0
    try:
        while count < num_requests:
            try:
                server._handle_request()
                count += 1
            except Exception:
                break
    finally:
        server.close()


class TestClientServerIntegration:
    """Integration tests for client-server RPC communication."""

    def test_simple_rpc_call(self) -> None:
        """Test a simple RPC call from client to server."""
        channel = "test_simple_call"

        # Start server in separate process
        server_process = multiprocessing.Process(
            target=run_test_server,
            args=(channel, 1),
        )
        server_process.start()

        # Give server time to start
        time.sleep(0.2)

        try:
            # Make client call
            with RPCClient(channel, timeout=2.0) as client:
                result = client.call("add", a=5, b=3)
                assert result == 8

        finally:
            server_process.join(timeout=2.0)
            if server_process.is_alive():
                server_process.terminate()

    def test_multiple_rpc_calls(self) -> None:
        """Test multiple sequential RPC calls."""
        channel = "test_multiple_calls"

        # Start server
        server_process = multiprocessing.Process(
            target=run_test_server,
            args=(channel, 3),
        )
        server_process.start()
        time.sleep(0.2)

        try:
            with RPCClient(channel, timeout=2.0) as client:
                # Test add
                result = client.call("add", a=10, b=20)
                assert result == 30

                # Test multiply
                result = client.call("multiply", x=4, y=5)
                assert result == 20

                # Test greet
                result = client.call("greet", name="Alice")
                assert result == "Hello, Alice!"

        finally:
            server_process.join(timeout=2.0)
            if server_process.is_alive():
                server_process.terminate()

    def test_server_side_error_propagation(self) -> None:
        """Test that server-side errors are properly propagated to client."""
        channel = "test_method_error"

        server_process = multiprocessing.Process(
            target=run_test_server,
            args=(channel, 1),
        )
        server_process.start()
        time.sleep(0.2)

        try:
            with RPCClient(channel, timeout=2.0) as client:
                # Call divide by zero - should raise error
                with pytest.raises(RPCMethodError, match="Division by zero"):
                    client.call("divide", a=10, b=0)

        finally:
            server_process.join(timeout=2.0)
            if server_process.is_alive():
                server_process.terminate()

    def test_unknown_method_error(self) -> None:
        """Test that calling unknown method raises appropriate error."""
        channel = "test_unknown_method"

        server_process = multiprocessing.Process(
            target=run_test_server,
            args=(channel, 1),
        )
        server_process.start()
        time.sleep(0.2)

        try:
            with RPCClient(channel, timeout=2.0) as client:
                with pytest.raises(RPCMethodError, match="Unknown method"):
                    client.call("nonexistent_method", arg=1)

        finally:
            server_process.join(timeout=2.0)
            if server_process.is_alive():
                server_process.terminate()

    def test_timeout_when_no_server(self) -> None:
        """Test that client times out when server is not running."""
        channel = "test_timeout_no_server"

        # Don't start a server
        with pytest.raises(Exception):  # Transport or timeout error
            with RPCClient(channel, timeout=0.5) as client:
                client.call("add", a=1, b=2)
