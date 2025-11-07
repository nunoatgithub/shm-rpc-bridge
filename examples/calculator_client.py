#!/usr/bin/env python3
"""
Calculator RPC Client Example

This client demonstrates making RPC calls to the calculator server
over shared memory.
"""

import sys

from shm_rpc_bridge import RPCClient
from shm_rpc_bridge.exceptions import RPCError, RPCMethodError, RPCTimeoutError


def print_separator() -> None:
    """Print a visual separator."""
    print("-" * 60)


def demonstrate_calculator(client: RPCClient) -> None:
    """Demonstrate various calculator operations."""

    print_separator()
    print("Calculator RPC Client Demo")
    print_separator()

    # Addition
    print("\n1. Addition:")
    result = client.call("add", a=10, b=5)
    print(f"   10 + 5 = {result}")

    result = client.call("add", a=100.5, b=25.3)
    print(f"   100.5 + 25.3 = {result}")

    # Subtraction
    print("\n2. Subtraction:")
    result = client.call("subtract", a=20, b=8)
    print(f"   20 - 8 = {result}")

    result = client.call("subtract", a=5.5, b=3.2)
    print(f"   5.5 - 3.2 = {result}")

    # Multiplication
    print("\n3. Multiplication:")
    result = client.call("multiply", a=6, b=7)
    print(f"   6 * 7 = {result}")

    result = client.call("multiply", a=2.5, b=4)
    print(f"   2.5 * 4 = {result}")

    # Division
    print("\n4. Division:")
    result = client.call("divide", a=100, b=4)
    print(f"   100 / 4 = {result}")

    result = client.call("divide", a=22, b=7)
    print(f"   22 / 7 = {result}")

    # Power
    print("\n5. Power:")
    result = client.call("power", base=2, exponent=10)
    print(f"   2 ^ 10 = {result}")

    result = client.call("power", base=5, exponent=3)
    print(f"   5 ^ 3 = {result}")

    # Square root
    print("\n6. Square Root:")
    result = client.call("sqrt", x=16)
    print(f"   sqrt(16) = {result}")

    result = client.call("sqrt", x=2)
    print(f"   sqrt(2) = {result}")

    # Error handling - division by zero
    print("\n7. Error Handling - Division by Zero:")
    try:
        result = client.call("divide", a=10, b=0)
        print(f"   10 / 0 = {result}")
    except RPCMethodError as e:
        print(f"   ERROR: {e}")

    # Error handling - square root of negative
    print("\n8. Error Handling - Square Root of Negative:")
    try:
        result = client.call("sqrt", x=-4)
        print(f"   sqrt(-4) = {result}")
    except RPCMethodError as e:
        print(f"   ERROR: {e}")

    print_separator()
    print("Demo completed successfully!")
    print_separator()


def interactive_mode(client: RPCClient) -> None:
    """Run an interactive calculator session."""

    print_separator()
    print("Interactive Calculator Mode")
    print("Available operations: add, subtract, multiply, divide, power, sqrt")
    print("Type 'quit' or 'exit' to exit")
    print_separator()

    while True:
        try:
            # Get operation
            print("\nEnter operation (or 'quit'): ", end="")
            operation = input().strip().lower()

            if operation in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            if operation not in ("add", "subtract", "multiply", "divide", "power", "sqrt"):
                print(f"Unknown operation: {operation}")
                continue

            # Get parameters based on operation
            if operation == "sqrt":
                x = float(input("Enter number: "))
                result = client.call(operation, x=x)
                print(f"Result: {result}")
            elif operation == "power":
                base = float(input("Enter base: "))
                exponent = float(input("Enter exponent: "))
                result = client.call(operation, base=base, exponent=exponent)
                print(f"Result: {result}")
            else:
                a = float(input("Enter first number: "))
                b = float(input("Enter second number: "))
                result = client.call(operation, a=a, b=b)
                print(f"Result: {result}")

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
    """Run the calculator RPC client."""
    channel_name = "calculator_rpc"

    # Check command line arguments
    interactive = "--interactive" in sys.argv or "-i" in sys.argv

    print(f"Connecting to calculator server on channel: {channel_name}")

    try:
        # Create RPC client
        with RPCClient(channel_name, buffer_size=8192, timeout=5.0) as client:
            print("Connected to server!")

            if interactive:
                interactive_mode(client)
            else:
                demonstrate_calculator(client)

    except RPCTimeoutError:
        print("\nERROR: Timeout connecting to server.")
        print("Make sure the calculator server is running!")
        print("Start it with: python examples/calculator_server.py")
        sys.exit(1)
    except RPCError as e:
        print(f"\nRPC Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()

