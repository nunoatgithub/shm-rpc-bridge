import sys

import pytest

from shm_rpc_bridge import RPCServer, RPCTimeoutError, RPCTransportError
from shm_rpc_bridge._internal.transport_chooser import SharedMemoryTransport
from shm_rpc_bridge.client import RPCClient


class TestRPCClient:
    def test_create_and_close(self, server) -> None:
        client = RPCClient(
            server.transport.name, server.transport.buffer_size, server.transport.timeout
        )
        assert client.transport.name == server.transport.name
        assert client.transport.buffer_size == server.transport.buffer_size
        assert client.transport.timeout == server.transport.timeout
        assert client.codec is not None
        client.close()
        assert client.transport is None
        assert client.codec is None

        # default constructor, using context manager protocol
        with RPCClient(server.transport.name, buffer_size=server.transport.buffer_size) as client:
            assert client.transport.name == server.transport.name
            assert client.transport.buffer_size == server.transport.buffer_size
            assert client.transport.timeout == SharedMemoryTransport.DEFAULT_TIMEOUT
            assert client.codec is not None

    def test_create_without_server_fails(self) -> None:
        with pytest.raises(
            RPCTransportError,
            match=r"Failed to initialize transport: No shared memory exists with the "
            r"specified name",
        ):
            RPCClient("t_na")

    def test_create_with_capacity_diff_than_server_fails(self, server) -> None:
        # macOS is only sensitive to page differences (16KB pages in Apple silicon)
        difference = 16384 if sys.platform == "darwin" else 1
        with pytest.raises(
            RPCTransportError,
            match=r".*shared memory size mismatch.*",
        ):
            RPCClient(server.transport.name, server.transport.buffer_size + difference)

    def test_timeout_when_server_not_running(self) -> None:
        channel = "t_cto"
        with RPCServer(channel, timeout=1.0):
            client = RPCClient(channel, timeout=0.1)
            with pytest.raises(RPCTimeoutError):
                client.call("add", a=1, b=2)
