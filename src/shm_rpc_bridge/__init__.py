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

import logging
import os

logger = logging.getLogger("shm_rpc_bridge")
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - %(process)s - %(threadName)s - %(name)s - %(levelname)s : %(message)s"
    )
)
logger.addHandler(handler)
_log_level = os.environ.get("SHM_RPC_BRIDGE_LOG_LEVEL", "WARNING").upper()
logger.setLevel(getattr(logging, _log_level, logging.WARNING))
logger.propagate = False  # Prevent propagation to root logger to avoid duplicate logs
