from __future__ import annotations

import multiprocessing

import pytest

from shm_rpc_bridge.client import RPCClient
from shm_rpc_bridge.exceptions import RPCMethodError
from shm_rpc_bridge.server import RPCServer
from shm_rpc_bridge.transport.transport_chooser import SharedMemoryTransport


class TestClientServerIntegration:
    """Integration tests for client-server RPC communication."""

    @staticmethod
    def _run_test_server(
        channel_name: str,
        buffer_size: int = SharedMemoryTransport.DEFAULT_BUFFER_SIZE,
        timeout: float = SharedMemoryTransport.DEFAULT_TIMEOUT,
    ) -> None:
        """Run a test server that handles a specific number of requests."""
        server = RPCServer(channel_name, buffer_size=buffer_size, timeout=timeout)

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

        server_process = multiprocessing.Process(target=self._run_test_server, args=(channel,))
        server_process.start()

        try:
            with RPCClient(channel, timeout=2.0, wait_for_server=5.0) as client:
                result = client.call("add", a=5, b=3)
                assert result == 8
        finally:
            server_process.terminate()

    def test_multiple_rpc_calls_from_same_client(self) -> None:
        channel = "t_mc"

        server_process = multiprocessing.Process(target=self._run_test_server, args=(channel,))
        server_process.start()

        try:
            with RPCClient(channel, timeout=2.0, wait_for_server=5.0) as client:
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

        server_process = multiprocessing.Process(target=self._run_test_server, args=(channel,))
        server_process.start()

        try:
            client1 = RPCClient(channel, timeout=2.0, wait_for_server=5.0)
            client2 = RPCClient(channel, timeout=2.0, wait_for_server=5.0)

            result = client1.call("greet", name="Alice")
            assert result == "Hello, Alice!"
            result = client2.call("greet", name="Bob")
            assert result == "Hello, Bob!"
            result = client1.call("greet", name="Alice, again")
            assert result == "Hello, Alice, again!"

        finally:
            server_process.terminate()

    def test_stateful_rpc_calls(self) -> None:
        channel = "t_stc"

        server_process = multiprocessing.Process(
            target=self._run_stateful_test_server, args=(channel,)
        )
        server_process.start()

        try:
            client1 = RPCClient(channel, timeout=2.0, wait_for_server=5.0)
            client2 = RPCClient(channel, timeout=2.0, wait_for_server=5.0)

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
        channel = "t_ep"

        server_process = multiprocessing.Process(target=self._run_test_server, args=(channel,))
        server_process.start()

        try:
            with RPCClient(channel, timeout=2.0, wait_for_server=5.0) as client:
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

        try:
            with RPCClient(channel, timeout=2.0, wait_for_server=5.0) as client:
                with pytest.raises(RPCMethodError, match="Unknown method"):
                    client.call("nonexistent_method", arg=1)

        finally:
            server_process.terminate()

    @pytest.mark.timeout(120)
    def test_rpc_calls_using_many_diff_channels(self) -> None:
        def interaction_per_channel(channel: str) -> None:
            buffer_size = 2_000_000  # use a big buffer to make it even harder
            timeout = 5.0  # lower than this will likely not work in github CI...
            server_process = multiprocessing.Process(
                target=self._run_test_server, args=(channel, buffer_size, timeout)
            )
            server_process.start()
            try:
                client = RPCClient(
                    channel, buffer_size=buffer_size, timeout=timeout, wait_for_server=5.0
                )
                result = client.call("greet", name="Alice")
                assert result == "Hello, Alice!"
            finally:
                server_process.terminate()

        for i in range(200):
            chan = f"t_{i}"
            interaction_per_channel(chan)

    @pytest.mark.timeout(120)
    def test_concurrent_rpc_calls_using_many_diff_channels(self) -> None:
        import concurrent.futures

        def interaction_per_channel(channel: str) -> None:
            buffer_size = 2_000_000  # use a big buffer to make it even harder
            timeout = 20.0  # lower than this will likely not work in github CI...
            server_process = multiprocessing.Process(
                target=self._run_test_server, args=(channel, buffer_size, timeout)
            )
            server_process.start()
            try:
                client = RPCClient(
                    channel, buffer_size=buffer_size, timeout=timeout, wait_for_server=20.0
                )
                result = client.call("greet", name="Alice")
                assert result == "Hello, Alice!"
            finally:
                server_process.terminate()

        channels = [f"tc_{i}" for i in range(100)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(interaction_per_channel, ch) for ch in channels]
            for fut in concurrent.futures.as_completed(futures):
                fut.result()
