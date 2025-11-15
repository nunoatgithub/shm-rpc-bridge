import sys

import pytest

from shm_rpc_bridge import RPCServer
from shm_rpc_bridge._internal.transport_chooser import SharedMemoryTransport

_TEST_CHANNEL = "t"

linux = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux-only test")
macos = pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only test")


@pytest.fixture
def buffer_size():
    return 4096


@pytest.fixture
def timeout(request):
    """Timeout fixture that supports indirect parametrization."""
    return getattr(request, "param", 1.0)


@pytest.fixture
def server_transport(buffer_size, timeout):
    transport = SharedMemoryTransport.create(
        name=_TEST_CHANNEL, buffer_size=buffer_size, timeout=timeout
    )
    yield transport
    transport.close()


@pytest.fixture
def client_transport(buffer_size, timeout):
    transport = SharedMemoryTransport.open(
        name=_TEST_CHANNEL, buffer_size=buffer_size, timeout=timeout
    )
    yield transport
    transport.close()


@pytest.fixture
def server(buffer_size, timeout):
    server = RPCServer(name=_TEST_CHANNEL, buffer_size=buffer_size, timeout=timeout)
    yield server
    server.close()


@pytest.fixture(autouse=True)
def cleanup_test_resources(request):
    SharedMemoryTransport.delete_resources()
    yield
    SharedMemoryTransport.delete_resources()
