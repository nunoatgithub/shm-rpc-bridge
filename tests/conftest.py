import os

import posix_ipc
import pytest

from shm_rpc_bridge.transport import SharedMemoryTransport


@pytest.fixture
def buffer_size():
    return 4096

@pytest.fixture
def timeout(request):
    """Timeout fixture that supports indirect parametrization."""
    return getattr(request, 'param', None)

@pytest.fixture
def server_transport(buffer_size, timeout):
    transport = SharedMemoryTransport.create(name="test_channel", buffer_size=buffer_size, timeout=timeout)
    yield transport
    transport.cleanup()

@pytest.fixture
def client_transport(buffer_size, timeout):
    transport = SharedMemoryTransport.open(name="test_channel", buffer_size=buffer_size, timeout=timeout)
    yield transport
    transport.cleanup()

@pytest.fixture(autouse=True)
def cleanup_test_resources():
    _cleanup_test_ipc()
    yield
    _cleanup_test_ipc()


def _cleanup_test_ipc() -> None:
    prefix = "test"
    # Clean up shared memory segments in /dev/shm
    shm_dir = "/dev/shm"
    if os.path.exists(shm_dir):
        for filename in os.listdir(shm_dir):
            if filename.startswith(prefix):
                try:
                    os.unlink(os.path.join(shm_dir, filename))
                except Exception:
                    pass

    # Clean up semaphores
    # Semaphores follow pattern: /{name}_{suffix}
    # We scan /dev/shm for shared memory names and derive semaphore names from them
    common_suffixes = ["_req_empty", "_req_full", "_resp_empty", "_resp_full"]

    # Extract base names from shared memory segments
    base_names = set()
    if os.path.exists(shm_dir):
        for filename in os.listdir(shm_dir):
            if filename.startswith(prefix):
                # Remove _request or _response suffix to get base name
                for shm_suffix in ["_request", "_response"]:
                    if filename.endswith(shm_suffix):
                        base_name = filename[:-len(shm_suffix)]
                        base_names.add(base_name)
                        break

    # Clean up semaphores for discovered base names
    for base_name in base_names:
        for suffix in common_suffixes:
            try:
                posix_ipc.unlink_semaphore(f"/{base_name}{suffix}")
            except Exception:
                pass
