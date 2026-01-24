"""
shm-rpc-bridge: RPC bridge using shared memory IPC and POSIX semaphores.
"""

import logging
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


def get_logger() -> logging.Logger:
    """
    Get the library's logger instance.

    The logger inherits configuration from the root logger.
    Configure logging using Python's standard logging API.

    Returns:
        The logger used by shm-rpc-bridge
    """
    return logging.getLogger(__name__)


__all__ = [
    "RPCClient",
    "RPCServer",
    "RPCError",
    "RPCTimeoutError",
    "RPCSerializationError",
    "RPCTransportError",
    "get_logger",
]
