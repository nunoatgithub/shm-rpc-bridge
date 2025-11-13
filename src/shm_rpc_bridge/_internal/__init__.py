# Import guard: allow imports from within the package, block external usage.

from __future__ import annotations

import inspect
import os

__all__: list[str] = []  # Nothing publicly exported.

_ALLOWED_ENV_VALUES = {"1", "true", "yes", "on"}


def _env_allows() -> bool:
    val = os.environ.get("SHM_RPC_BRIDGE_ALLOW_INTERNALS")
    return val is not None and val.lower() in _ALLOWED_ENV_VALUES


def _line_imports_internal(line: str) -> bool:
    # Detect any form of importing the private package or its submodules.
    # We are only interested in lines that actually reference shm_rpc_bridge._internal.
    return "shm_rpc_bridge._internal" in line


def _is_allowed_import() -> bool:
    if _env_allows():
        return True

    # Scan all frames to find the frame whose line is importing _internal.*
    for frame_info in inspect.stack():
        module_name = frame_info.frame.f_globals.get("__name__", "")
        ctx = frame_info.code_context
        if not ctx:
            continue
        line = ctx[0].strip()

        if not _line_imports_internal(line):
            continue  # Not the import line we care about.

        # Allow imports from other modules inside the package, but deny imports
        # directly from `_internal` modules; internals should use relative imports.
        is_within_package = module_name.startswith("shm_rpc_bridge.")
        is_internal_submodule = module_name.startswith("shm_rpc_bridge._internal")
        if is_within_package and not is_internal_submodule:
            return True

        # External (or direct _internal) import -> deny.
        return False

    # If we cannot identify the importing frame, deny by default.
    return False


if not _is_allowed_import():
    raise ImportError("Private API: do not import 'shm_rpc_bridge._internal.*' directly.")
