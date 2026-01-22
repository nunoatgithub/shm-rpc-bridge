import multiprocessing
import os
import sys

import pytest

# Set log level BEFORE importing shm_rpc_bridge.
# This ensures spawned processes will also use this level
# It's a good idea to leave a production level as default and change it only when developing.
# Otherwise, too much logging may force over-determinism, reducing the actual test coverage.
os.environ["SHM_RPC_BRIDGE_LOG_LEVEL"] = "ERROR"

from shm_rpc_bridge import RPCServer
from shm_rpc_bridge.transport.transport_chooser import SharedMemoryTransport
from shm_rpc_bridge.transport.transport_posix import SharedMemoryTransportPosix

_TEST_CHANNEL = "t"

linux = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux-only test")
macos = pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only test")
posix_only = pytest.mark.skipif(
    SharedMemoryTransport != SharedMemoryTransportPosix, reason="posix-only test"
)


def pytest_configure(config):
    multiprocessing.set_start_method("spawn", force=True)


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
    _server = RPCServer(name=_TEST_CHANNEL, buffer_size=buffer_size, timeout=timeout)
    yield _server
    _server.close()


@pytest.fixture(autouse=True)
def cleanup_test_resources(request):
    SharedMemoryTransport.delete_resources()
    yield
    SharedMemoryTransport.delete_resources()
