import multiprocessing
import os
import sys

import pytest

# Set log level and format via environment variables.
# Spawned processes inherit OS environment, so when they import shm_rpc_bridge,
# the library will read these env vars and configure logging accordingly.
os.environ["SHM_RPC_BRIDGE_LOG_LEVEL"] = "DEBUG"
os.environ["SHM_RPC_BRIDGE_LOG_FORMAT"] = (
    "%(asctime)s - %(process)s - %(name)s - %(levelname)s: %(message)s"
)

from shm_rpc_bridge import RPCServer, get_logger
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


@pytest.fixture(autouse=True)
def flush_logs_after_test(request):
    """Flush logs after each test to ensure spawned process logs are captured."""
    yield
    import logging

    # Flush all handlers to ensure logs from spawned processes are written
    for handler in logging.getLogger().handlers:
        handler.flush()

    logger = get_logger()
    for handler in logger.handlers:
        handler.flush()

    sys.stdout.flush()
    sys.stderr.flush()
