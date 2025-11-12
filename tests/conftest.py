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
    """Best-effort removal of leftover test IPC objects.

    Removes candidate shared memory and semaphore files on Linux and attempts
    POSIX unlink via libc on macOS; failures are ignored.
    """
    import platform
    import ctypes

    shm_prefix = "test"
    sem_prefix = "sem.test"
    # primary target on Linux
    shm_dir = "/dev/shm"
    # additional dirs to probe (macOS often doesn't expose /dev/shm)
    probe_dirs = [shm_dir, "/var/run", "/private/var/run", "/var/tmp", "/tmp"]

    is_darwin = platform.system() == "Darwin"
    libc = None
    if is_darwin:
        try:
            libc = ctypes.CDLL("libc.dylib")
        except Exception:
            libc = None

    for d in probe_dirs:
        if not os.path.exists(d):
            continue
        for filename in os.listdir(d):
            if filename.startswith(shm_prefix) or filename.startswith(sem_prefix):
                path = os.path.join(d, filename)
                try:
                    os.unlink(path)
                except Exception:
                    pass
                # on macOS try POSIX unlink for named objects as a fallback
                if is_darwin and libc is not None:
                    try:
                        # try both with and without leading slash
                        candidate_names = [filename]
                        if not filename.startswith("/"):
                            candidate_names.insert(0, "/" + filename)
                        for name in candidate_names:
                            bname = name.encode()
                            if filename.startswith(sem_prefix):
                                try:
                                    libc.sem_unlink(bname)
                                except Exception:
                                    pass
                            else:
                                try:
                                    libc.shm_unlink(bname)
                                except Exception:
                                    pass
                    except Exception:
                        pass
