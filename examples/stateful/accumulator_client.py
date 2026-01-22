#!/usr/bin/env python3
"""
Accumulator RPC Client Example

This client demonstrates making RPC calls to the accumulator server
over shared memory.
"""
import os
import sys

# disable all bridge logging, keep only errors.
os.environ["SHM_RPC_BRIDGE_LOG_LEVEL"] = "ERROR"

from shm_rpc_bridge import RPCClient
from shm_rpc_bridge.exceptions import RPCError, RPCMethodError, RPCTimeoutError


def print_separator() -> None:
    """Print a visual separator."""
    print("-" * 60)


def demonstrate_accumulator(client: RPCClient) -> None:
    """Demonstrate accumulator operations across multiple clients."""

    print_separator()
    print("Accumulator RPC Client Demo")
    print_separator()

    # We'll simulate two different clients to show independent totals
    clients = ["alice", "bob"]

    # 1) Accumulate for Alice (twice)
    print("\n1. Accumulate for 'alice' (twice):")
    total = client.call("accumulate", client_id=clients[0], val=10)
    print(f"   accumulate(client_id='alice', val=10) -> total = {total}")
    total = client.call("accumulate", client_id=clients[0], val=5)
    print(f"   accumulate(client_id='alice', val=5) -> total = {total}")

    # 2) Accumulate for Bob (twice, independent state)
    print("\n2. Accumulate for 'bob' (twice, independent state):")
    total = client.call("accumulate", client_id=clients[1], val=7.5)
    print(f"   accumulate(client_id='bob', val=7.5) -> total = {total}")
    total = client.call("accumulate", client_id=clients[1], val=2.5)
    print(f"   accumulate(client_id='bob', val=2.5) -> total = {total}")

    # 3) Accumulate again for Alice to verify Bob's state didn't affect Alice
    print("\n3. Accumulate again for 'alice' (state remains isolated):")
    total = client.call("accumulate", client_id=clients[0], val=3)
    print(f"   accumulate(client_id='alice', val=3) -> total = {total}")

    # 4) Clear Alice
    print("\n4. Clear 'alice' total:")
    try:
        client.call("clear", client_id=clients[0])
        print("   clear(client_id='alice') -> done")
    except RPCMethodError as e:
        print(f"   ERROR during clear: {e}")

    # 5) Final accumulations to prove Alice was cleared and Bob retained state
    print("\n5. Final accumulate calls (prove 'alice' cleared, 'bob' retained state):")
    total_alice_after_clear = client.call("accumulate", client_id=clients[0], val=1.25)
    print(f"   accumulate(client_id='alice', val=1.25) -> total = {total_alice_after_clear} (should start fresh)")
    total_bob_after = client.call("accumulate", client_id=clients[1], val=1.0)
    print(f"   accumulate(client_id='bob', val=1.0) -> total = {total_bob_after} (should continue from previous)")

    print_separator()
    print("Demo completed successfully!")
    print_separator()


def interactive_mode(client: RPCClient) -> None:
    """Run an interactive accumulator session."""

    print_separator()
    print("Interactive Accumulator Mode")
    print("Available operations: accumulate, clear")
    print("Type 'quit' or 'exit' to exit")
    print_separator()

    while True:
        try:
            # Get operation
            print("\nEnter operation (accumulate|clear or 'quit'): ", end="")
            operation = input().strip().lower()

            if operation in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            if operation not in ("accumulate", "clear"):
                print(f"Unknown operation: {operation}")
                continue

            if operation == "accumulate":
                client_id = input("Enter client_id: ").strip()
                val_str = input("Enter value to add (float): ").strip()
                val = float(val_str)
                total = client.call("accumulate", client_id=client_id, val=val)
                print(f"Total for '{client_id}' is now: {total}")
            else:  # clear
                client_id = input("Enter client_id to clear: ").strip()
                try:
                    client.call("clear", client_id=client_id)
                    print(f"Cleared total for '{client_id}'.")
                except RPCMethodError as e:
                    print(f"Error clearing '{client_id}': {e}")

        except RPCMethodError as e:
            print(f"Error from server: {e}")
        except ValueError as e:
            print(f"Invalid input: {e}")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


def main() -> None:
    """Run the accumulator RPC client."""
    channel_name = "acc_rpc"

    # Check command line arguments
    interactive = "--interactive" in sys.argv or "-i" in sys.argv

    print(f"Connecting to accumulator server on channel: {channel_name}")

    try:
        # Create RPC client
        with RPCClient(channel_name) as client:
            print("Connected to server!")

            if interactive:
                interactive_mode(client)
            else:
                demonstrate_accumulator(client)

    except RPCTimeoutError:
        print("\nERROR: Timeout connecting to server.")
        print("Make sure the accumulator server is running!")
        print("Start it with: python examples/stateful/accumulator_server.py")
        sys.exit(1)
    except RPCError as e:
        print(f"\nRPC Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
