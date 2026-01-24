#!/usr/bin/env python3
"""
Accumulator RPC Server Example

This server demonstrates how to implement a stateful service
that can be called remotely via RPC over shared memory.
"""

from __future__ import annotations

from shm_rpc_bridge import RPCServer

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
    channel_name = "acc_rpc"

    print("Starting Accumulator RPC Server...")
    print(f"Channel: {channel_name}")

    # Create accumulator instance
    acc = Accumulator()

    # Create RPC server
    server = RPCServer(channel_name)

    # Register methods
    server.register("accumulate", acc.accumulate)
    server.register("clear", acc.clear)

    # Start serving requests
    print("Server ready! Waiting for requests...")
    print("Press Ctrl+C to stop.")
    server.start()

if __name__ == "__main__":
    main()

