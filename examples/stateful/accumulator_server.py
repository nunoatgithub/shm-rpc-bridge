#!/usr/bin/env python3
"""
Accumulator RPC Server Example

This server demonstrates how to implement a stateful service
that can be called remotely via RPC over shared memory.
"""

from __future__ import annotations
import logging

from shm_rpc_bridge import RPCServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Accumulator:
    """A simple accumulator service with a table of accumulated values per client."""

    totals: dict[str, float] = {}

    def accumulate(self, client_id: str, val: float) -> float:
        self.totals[client_id] = self.totals.get(client_id, 0.0) + val
        return self.totals[client_id]

    def clear(self, client_id: str) -> None:
        del self.totals[client_id]

def main() -> None:
    """Run the accumulator RPC server."""
    channel_name = "accumulator_rpc"

    logger.info("Starting Accumulator RPC Server...")
    logger.info(f"Channel: {channel_name}")

    # Create accumulator instance
    acc = Accumulator()

    # Create RPC server
    server = RPCServer(channel_name)

    # Register methods
    server.register("accumulate", acc.accumulate)
    server.register("clear", acc.clear)

    # Start serving requests
    logger.info("Server ready! Waiting for requests...")
    logger.info("Press Ctrl+C to stop.")
    server.start()

if __name__ == "__main__":
    main()

