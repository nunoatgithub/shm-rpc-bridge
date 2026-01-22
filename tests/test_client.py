import sys

import pytest

from shm_rpc_bridge import RPCServer, RPCTimeoutError, RPCTransportError
from shm_rpc_bridge.client import RPCClient
from shm_rpc_bridge.transport.transport_chooser import SharedMemoryTransport
from shm_rpc_bridge.transport.transport_posix import SharedMemoryTransportPosix


class TestRPCClient:
    def test_create_and_close(self, server) -> None:
        client = RPCClient(
            server._transport.name, server._transport.buffer_size, server._transport.timeout
        )
        assert client._transport.name == server._transport.name
        assert client._transport.buffer_size == server._transport.buffer_size
        assert client._transport.timeout == server._transport.timeout
        assert client._codec is not None
        client.close()
        assert client._transport is None
        assert client._codec is None

        # default constructor, using context manager protocol
        with RPCClient(server._transport.name, buffer_size=server._transport.buffer_size) as client:
            assert client._transport.name == server._transport.name
            assert client._transport.buffer_size == server._transport.buffer_size
            assert client._transport.timeout == SharedMemoryTransport.DEFAULT_TIMEOUT
            assert client._codec is not None

    def test_create_without_server_fails(self) -> None:
        with pytest.raises(
            RPCTransportError,
            match=r"Failed to initialize transport: No shared memory exists with the "
            r"specified name",
        ):
            RPCClient("t_na")

    def test_create_with_wait_without_server_fails(self) -> None:
        with pytest.raises(
            RPCTransportError, match=r"Timed out waiting for shared memory transport."
        ):
            RPCClient("t_na", timeout=1.0, wait_for_server=1.0)

    def test_create_with_capacity_diff_than_server_fails(self, server) -> None:
        # macOS is only sensitive to page differences (16KB pages in Apple silicon)
        difference = 16384 if sys.platform == "darwin" else 1
        if SharedMemoryTransport == SharedMemoryTransportPosix:
            expected_exception_msg_pattern = r".*shared memory size mismatch.*"
        else:
            expected_exception_msg_pattern = r".*mmap length is greater than file size.*"
        with pytest.raises(
            RPCTransportError,
            match=expected_exception_msg_pattern,
        ):
            RPCClient(
                name=server._transport.name, buffer_size=server._transport.buffer_size + difference
            )

    def test_timeout_when_server_not_running(self) -> None:
        channel = "t_cto"
        with RPCServer(channel, timeout=1.0):
            client = RPCClient(channel, timeout=0.1)
            with pytest.raises(RPCTimeoutError):
                client.call("add", a=1, b=2)
