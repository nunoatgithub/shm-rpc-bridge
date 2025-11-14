from __future__ import annotations

import os

from shm_rpc_bridge.exceptions import RPCTransportError

from .transport_posix import SharedMemoryTransportPosix

try:
    from .transport_futex import SharedMemoryTransportFutex  # type: ignore[import]
except Exception:  # pragma: no cover - optional dependency / platform-specific
    SharedMemoryTransportFutex = None  # type: ignore[assignment,misc]


if os.name == "posix":
    sysname = os.uname().sysname.lower()
    SharedMemoryTransport = SharedMemoryTransportPosix
    if sysname == "linux" and SharedMemoryTransportFutex is not None:
        SharedMemoryTransport = SharedMemoryTransportFutex  # type: ignore[assignment,misc]
else:
    raise RPCTransportError(f"No transport support yet for OS [{os.name}, {os.uname().sysname}]")
