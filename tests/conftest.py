import os

import pytest

from shm_rpc_bridge import RPCServer
from shm_rpc_bridge.transport import SharedMemoryTransport


@pytest.fixture
def buffer_size():
    return 4096


@pytest.fixture
def timeout(request):
    """Timeout fixture that supports indirect parametrization."""
    return getattr(request, "param", None)


@pytest.fixture
def server_transport(buffer_size, timeout):
    transport = SharedMemoryTransport.create(
        name="test_channel", buffer_size=buffer_size, timeout=timeout
    )
    yield transport
    transport.close()


@pytest.fixture
def client_transport(buffer_size, timeout):
    transport = SharedMemoryTransport.open(
        name="test_channel", buffer_size=buffer_size, timeout=timeout
    )
    yield transport
    transport.close()


@pytest.fixture
def server(buffer_size, timeout):
    server = RPCServer(name="test_server", buffer_size=buffer_size, timeout=timeout)
    yield server
    server.close()


@pytest.fixture(autouse=True)
def cleanup_test_resources(request):
    # skip automatic cleanup when test is marked with `@pytest.mark.no_cleanup`
    if request.node.get_closest_marker("no_cleanup"):
        yield
        return
    _cleanup_test_ipc()
    yield
    _cleanup_test_ipc()


def _cleanup_test_ipc() -> None:
    shm_prefix = "test"
    sem_prefix = "sem.test"
    shm_dir = "/dev/shm"
    if os.path.exists(shm_dir):
        for filename in os.listdir(shm_dir):
            if filename.startswith(shm_prefix) or filename.startswith(sem_prefix):
                try:
                    os.unlink(os.path.join(shm_dir, filename))
                except Exception:
                    pass
