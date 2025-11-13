#!/usr/bin/env python3
"""
Calculator RPC Server Example

This server implements a calculator with basic arithmetic operations
that can be called remotely via RPC over shared memory.
"""

import logging

from shm_rpc_bridge import RPCServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Calculator:
    """A simple calculator with arithmetic operations."""

    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        result = a + b
        logger.info(f"add({a}, {b}) = {result}")
        return result

    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        result = a - b
        logger.info(f"subtract({a}, {b}) = {result}")
        return result

    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        result = a * b
        logger.info(f"multiply({a}, {b}) = {result}")
        return result

    def divide(self, a: float, b: float) -> float:
        """Divide a by b."""
        if b == 0:
            logger.error(f"divide({a}, {b}) - Division by zero!")
            raise ValueError("Cannot divide by zero")
        result = a / b
        logger.info(f"divide({a}, {b}) = {result}")
        return result

    def power(self, base: float, exponent: float) -> float:
        """Raise base to the power of exponent."""
        result = base ** exponent
        logger.info(f"power({base}, {exponent}) = {result}")
        return result

    def sqrt(self, x: float) -> float:
        """Calculate the square root of x."""
        if x < 0:
            logger.error(f"sqrt({x}) - Cannot calculate square root of negative number!")
            raise ValueError("Cannot calculate square root of negative number")
        result = x ** 0.5
        logger.info(f"sqrt({x}) = {result}")
        return result


def main() -> None:
    """Run the calculator RPC server."""
    channel_name = "calculator_rpc"

    logger.info("Starting Calculator RPC Server...")
    logger.info(f"Channel: {channel_name}")

    # Create calculator instance
    calc = Calculator()

    # Create RPC server
    server = RPCServer(channel_name)

    # Register calculator methods
    server.register("add", calc.add)
    server.register("subtract", calc.subtract)
    server.register("multiply", calc.multiply)
    server.register("divide", calc.divide)
    server.register("power", calc.power)
    server.register("sqrt", calc.sqrt)

    # Start serving requests
    logger.info("Server ready! Waiting for requests...")
    logger.info("Press Ctrl+C to stop.")
    server.start()

if __name__ == "__main__":
    main()

