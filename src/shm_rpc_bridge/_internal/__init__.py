# Import guard: allow imports from within the package or test code, block others.
import inspect
import os


def _is_allowed_import() -> bool:
    if os.environ.get("SHM_RPC_BRIDGE_ALLOW_INTERNALS") == "1":
        return True
    for frame in inspect.stack():
        mod = frame.frame.f_globals.get("__name__", "")
        filename = frame.filename.replace("\\", "/")
        if mod.startswith("shm_rpc_bridge"):
            return True  # internal usage
        if "/tests/" in filename or filename.endswith("/tests/__init__.py"):
            return True  # test usage
    return False


if not _is_allowed_import():
    raise ImportError("Private API: do not import 'shm_rpc_bridge._internal.*' directly.")
