from __future__ import annotations

import multiprocessing
import time

import pytest

from shm_rpc_bridge.client import RPCClient
from shm_rpc_bridge.exceptions import RPCMethodError
from shm_rpc_bridge.server import RPCServer


class TestClientServerIntegration:
    """Integration tests for client-server RPC communication."""

    @staticmethod
    def _run_test_server(channel_name: str) -> None:
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
        server.start()

    @staticmethod
    def _run_stateful_test_server(channel_name: str) -> None:
        """Run a test server that keeps state."""

        server = RPCServer(channel_name, timeout=2.0)

        totals: dict[str, float] = {}

        def accumulate(client_id: str, val: float) -> float:
            totals[client_id] = totals.get(client_id, 0.0) + val
            return totals[client_id]

        def clear(client_id: str) -> None:
            del totals[client_id]

        server.register("accumulate", accumulate)
        server.register("clear", clear)
        server.start()

    def test_simple_rpc_call(self) -> None:
        """Test a simple RPC call from client to server."""
        channel = "t_sc"

        # Start server in separate process
        server_process = multiprocessing.Process(target=self._run_test_server, args=(channel,))
        server_process.start()

        # Give server time to start
        time.sleep(0.2)

        try:
            with RPCClient(channel, timeout=2.0) as client:
                result = client.call("add", a=5, b=3)
                assert result == 8
        finally:
            server_process.terminate()

    def test_multiple_rpc_calls_from_same_client(self) -> None:
        channel = "t_mc"

        # Start server
        server_process = multiprocessing.Process(target=self._run_test_server, args=(channel,))
        server_process.start()
        time.sleep(0.2)

        try:
            with RPCClient(channel, timeout=2.0) as client:
                result = client.call("add", a=10, b=20)
                assert result == 30

                result = client.call("multiply", x=4, y=5)
                assert result == 20

                result = client.call("greet", name="Alice")
                assert result == "Hello, Alice!"
        finally:
            server_process.terminate()

    def test_rpc_calls_from_diff_clients(self) -> None:
        channel = "t_dc"

        # Start server
        server_process = multiprocessing.Process(target=self._run_test_server, args=(channel,))
        server_process.start()
        time.sleep(0.2)

        try:
            client1 = RPCClient(channel, timeout=2.0)
            client2 = RPCClient(channel, timeout=2.0)

            result = client1.call("greet", name="Alice")
            assert result == "Hello, Alice!"
            result = client2.call("greet", name="Bob")
            assert result == "Hello, Bob!"
            result = client1.call("greet", name="Alice, again")
            assert result == "Hello, Alice, again!"

        finally:
            server_process.terminate()

    def test_stateful_rpc_calls(self) -> None:
        channel = "t_sc"

        # Start server
        server_process = multiprocessing.Process(
            target=self._run_stateful_test_server, args=(channel,)
        )
        server_process.start()
        time.sleep(0.2)

        try:
            client1 = RPCClient(channel, timeout=2.0)
            client2 = RPCClient(channel, timeout=2.0)

            result = client1.call("accumulate", client_id="1", val=1)
            assert result == 1
            result = client2.call("accumulate", client_id="2", val=2)
            assert result == 2
            result = client1.call("accumulate", client_id="1", val=1)
            assert result == 2
            result = client2.call("accumulate", client_id="2", val=2)
            assert result == 4
            # test clear
            client2.call("clear", client_id="2")
            result = client2.call("accumulate", client_id="2", val=1)
            assert result == 1

        finally:
            server_process.terminate()

    def test_server_side_error_propagation(self) -> None:
        """Test that server-side errors are properly propagated to client."""
        channel = "t_me"

        server_process = multiprocessing.Process(target=self._run_test_server, args=(channel,))
        server_process.start()
        time.sleep(0.2)

        try:
            with RPCClient(channel, timeout=2.0) as client:
                # Call divide by zero - should raise error
                with pytest.raises(RPCMethodError, match="Division by zero"):
                    client.call("divide", a=10, b=0)
        finally:
            server_process.terminate()

    def test_unknown_method_error(self) -> None:
        """Test that calling unknown method raises appropriate error."""
        channel = "t_um"

        server_process = multiprocessing.Process(target=self._run_test_server, args=(channel,))
        server_process.start()
        time.sleep(0.2)

        try:
            with RPCClient(channel, timeout=2.0) as client:
                with pytest.raises(RPCMethodError, match="Unknown method"):
                    client.call("nonexistent_method", arg=1)

        finally:
            server_process.terminate()
