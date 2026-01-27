"""
shm-rpc-bridge: RPC bridge using shared memory IPC and POSIX semaphores.
"""

from importlib.metadata import version

__version__ = version("shm-rpc-bridge")

from shm_rpc_bridge.client import RPCClient
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
    "RPCError",
    "RPCTimeoutError",
    "RPCSerializationError",
    "RPCTransportError",
]
