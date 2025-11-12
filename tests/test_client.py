import pytest

from shm_rpc_bridge import RPCServer, RPCTimeoutError, RPCTransportError
from shm_rpc_bridge.client import RPCClient
from shm_rpc_bridge.transport import SharedMemoryTransport


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
            RPCClient("test_nonexistent")

    def test_create_with_capacity_diff_than_server_fails(self, server) -> None:
        with pytest.raises(
            RPCTransportError,
            match=r"Failed to initialize transport: mmap length is greater than file size",
        ):
            RPCClient(server.transport.name, server.transport.buffer_size + 1)

    def test_timeout_when_server_not_running(self) -> None:
        channel = "test_client_timeout"
        with RPCServer(channel, timeout=1.0):
            client = RPCClient(channel, timeout=0.1)
            with pytest.raises(RPCTimeoutError):
                client.call("add", a=1, b=2)
