"""
shm-rpc-bridge: RPC bridge using shared memory IPC and POSIX semaphores.
"""

__version__ = "0.1.0"

from shm_rpc_bridge.client import RPCClient
from shm_rpc_bridge.data import (
    RPCCodec,
    RPCRequest,
    RPCResponse,
)
from shm_rpc_bridge.exceptions import (
    RPCError,
    RPCSerializationError,
    RPCTimeoutError,
    RPCTransportError,
)
from shm_rpc_bridge.server import RPCServer

__all__ = [
    "RPCClient",
    "RPCServer",
    "RPCCodec",
    "RPCRequest",
    "RPCResponse",
    "RPCError",
    "RPCTimeoutError",
    "RPCSerializationError",
    "RPCTransportError",
]
