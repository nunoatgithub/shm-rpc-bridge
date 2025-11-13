#!/usr/bin/env python3
"""
Benchmark script comparing different IPC implementations.

Compares performance of RPC calls across two implementations:
1. Direct object calls (in-process, baseline)
2. SHM-RPC between processes
"""
import json
import multiprocessing
import time
import logging

from shm_rpc_bridge import RPCClient, RPCServer
from shm_rpc_bridge.transport import SharedMemoryTransport


# Cleanup helper
def ensure_clean_slate(channel: str) -> None:
    SharedMemoryTransport.Cleanup.delete_resources_with_prefix(channel)


# ==============================================================================
# Service Implementation (same for all benchmarks)
# ==============================================================================

class CalculatorService:
    """Simple calculator service for benchmarking."""

    def add(self, a: int, b: int) -> int:
        return a + b


class DataService:
    """Service that handles large, complex data structures."""

    def process_data(self, data: dict) -> dict:
        """Process a complex data structure and return a modified version."""
        # Simulate some processing
        result = {
            "status": "processed",
            "input_size": len(str(data)),
            "data": data,
            "metadata": {
                "timestamp": time.time(),
                "items_count": data.get("items_count", 0),
            }
        }
        return result


# Create large message once and reuse it across all benchmarks
def _create_large_message() -> dict:
    """Create a large, complex nested data structure."""
    items = 1000

    return {
        "items_count": items,
        "items": [
            {
                "id": i,
                "name": f"item_{i}",
                "description": f"This is item number {i} with some descriptive text",
                "properties": {
                    "color": ["red", "green", "blue"][i % 3],
                    "size": ["small", "medium", "large"][i % 3],
                    "price": i * 1.99,
                    "in_stock": i % 2 == 0,
                },
                "tags": [f"tag_{j}" for j in range(5)],
                "metadata": {
                    "created": "2025-01-01",
                    "updated": "2025-11-07",
                    "version": 1,
                }
            }
            for i in range(items)
        ],
        "summary": {
            "total_items": items,
            "total_value": sum(i * 1.99 for i in range(items)),
            "categories": ["electronics", "clothing", "food", "toys"],
        }
    }


# Number of iterations for the benchmark
NUM_ITERATIONS = 100_000
NUM_ITERATIONS_LARGE = 10_000  # Fewer iterations for large messages
LARGE_MESSAGE = _create_large_message()  # Large message for benchmarking
LARGE_MESSAGE_SERIALIZED_SIZE = len(json.dumps(LARGE_MESSAGE))

# ==============================================================================
# Benchmark 1: Direct Object Calls (Baseline)
# ==============================================================================

def benchmark_direct_calls() -> float:
    """Benchmark direct object method calls (no IPC)."""
    service = CalculatorService()

    start = time.perf_counter()
    for i in range(NUM_ITERATIONS):
        _ = service.add(i, i + 1)
    end = time.perf_counter()

    return end - start


# ==============================================================================
# Benchmark 2: SHM-RPC Between Processes
# ==============================================================================

def run_server_process(channel: str, ready_queue: multiprocessing.Queue) -> None:  # type: ignore
    """Run RPC server in a separate process."""
    server = RPCServer(channel, timeout=10.0)
    service = CalculatorService()
    server.register("add", service.add)

    # Signal that server is ready
    ready_queue.put("ready")
    # Start server (will run until terminated)
    server.start()


def benchmark_processes() -> float:
    """Benchmark RPC calls between processes using shared memory."""
    channel = "bench_small"
    ready_queue: multiprocessing.Queue = multiprocessing.Queue()  # type: ignore

    # Clean up any leftover resources first
    ensure_clean_slate(channel)

    # Start server process
    server_process = multiprocessing.Process(
        target=run_server_process,
        args=(channel, ready_queue),
    )
    server_process.start()

    # Wait for server to be ready
    try:
        ready_queue.get(timeout=5.0)
    except Exception as e:
        server_process.terminate()
        server_process.join()
        ensure_clean_slate(channel)
        raise RuntimeError(f"Server failed to start: {e}")

    client = None
    try:
        # Create client
        client = RPCClient(channel, timeout=10.0)

        # Benchmark
        start = time.perf_counter()
        for i in range(NUM_ITERATIONS):
            result = client.call("add", a=i, b=i + 1)
        end = time.perf_counter()

        return end - start
    finally:
        # Clean up client
        if client:
            try:
                client.close()
            except:
                pass

        # Stop server
        server_process.terminate()
        server_process.join(timeout=5.0)


# ==============================================================================
# Benchmark 3: Large Messages - Direct Calls
# ==============================================================================

def benchmark_large_direct(message_size: str = "large") -> float:
    """Benchmark direct calls with large messages."""
    service = DataService()

    start = time.perf_counter()
    for _ in range(NUM_ITERATIONS_LARGE):
        result = service.process_data(LARGE_MESSAGE)
    end = time.perf_counter()

    return end - start


# ==============================================================================
# Benchmark 4: Large Messages - SHM-RPC Between Processes
# ==============================================================================

def run_data_server_process(channel: str,
                            ready_queue: multiprocessing.Queue) -> None:  # type: ignore
    """Run data processing server in a separate process."""
    server = RPCServer(channel, buffer_size=LARGE_MESSAGE_SERIALIZED_SIZE, timeout=10.0)
    service = DataService()
    server.register("process_data", service.process_data)

    ready_queue.put("ready")

    try:
        server.start()
    finally:
        server.close()


def benchmark_large_processes(message_size: str = "large") -> float:
    """Benchmark RPC with large messages between processes."""
    channel = "bench_large"
    ready_queue: multiprocessing.Queue = multiprocessing.Queue()  # type: ignore

    ensure_clean_slate(channel)

    server_process = multiprocessing.Process(
        target=run_data_server_process,
        args=(channel, ready_queue),
    )
    server_process.start()

    try:
        ready_queue.get(timeout=5.0)
    except Exception as e:
        server_process.terminate()
        server_process.join()
        ensure_clean_slate(channel)
        raise RuntimeError(f"Server failed to start: {e}")

    client = None

    try:
        client = RPCClient(channel, buffer_size=LARGE_MESSAGE_SERIALIZED_SIZE, timeout=10.0)

        start = time.perf_counter()
        for _ in range(NUM_ITERATIONS_LARGE):
            result = client.call("process_data", data=LARGE_MESSAGE)
        end = time.perf_counter()

        return end - start
    finally:
        if client:
            try:
                client.close()
            except:
                pass

        server_process.terminate()
        server_process.join(timeout=5.0)


# ==============================================================================
# Results Display
# ==============================================================================

def format_time(seconds: float) -> str:
    """Format time in a human-readable way."""
    if seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    elif seconds < 60:
        return f"{seconds:.2f} s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.2f}s"


def format_throughput(ops_per_sec: float) -> str:
    """Format throughput in a human-readable way."""
    if ops_per_sec >= 1_000_000:
        return f"{ops_per_sec / 1_000_000:.2f} M ops/s"
    elif ops_per_sec >= 1_000:
        return f"{ops_per_sec / 1_000:.2f} K ops/s"
    else:
        return f"{ops_per_sec:.2f} ops/s"


def print_results(name: str, duration: float, baseline: float = None,
                  iterations: int = NUM_ITERATIONS) -> None:  # type: ignore
    """Print benchmark results."""
    ops_per_sec = iterations / duration
    latency_us = (duration / iterations) * 1_000_000

    print(f"\n{name}")
    print("=" * 70)
    print(f"  Total time:       {format_time(duration)}")
    print(f"  Throughput:       {format_throughput(ops_per_sec)}")
    print(f"  Avg latency:      {latency_us:.2f} μs/call")

# ==============================================================================
# Main Benchmark
# ==============================================================================

def main() -> None:
    """Run all benchmarks."""

    logging.getLogger("shm_rpc_bridge").setLevel(logging.ERROR)

    print("Cleaning up any leftover resources...")
    ensure_clean_slate("bench_small")
    ensure_clean_slate("bench_large")

    print("=" * 70)
    print("RPC Implementation Benchmark")
    print("=" * 70)
    print(f"Small message iterations: {NUM_ITERATIONS:,}")
    print(f"Large message iterations: {NUM_ITERATIONS_LARGE:,}")
    print()

    # Warm-up (helps stabilize timing)
    print("Warming up...")
    service = CalculatorService()
    for i in range(1000):
        _ = service.add(i, i + 1)
    print("Warm-up complete.")

    # ===========================================================================
    # PART 1: Small Messages (simple integers)
    # ===========================================================================

    print("\n" + "=" * 70)
    print("PART 1: Small Message Benchmarks (Simple Integer Operations)")
    print("=" * 70)

    # Benchmark 1: Direct calls (baseline)
    print("\n[1/2] Running baseline benchmark (direct calls)...")
    direct_time = benchmark_direct_calls()
    print_results("Benchmark 1: Direct Object Calls (Baseline)", direct_time)

    # Benchmark 2: Processes
    print("\n[2/2] Running SHM-RPC benchmark (SHM-RPC between processes)...")
    try:
        process_time = benchmark_processes()
        print_results("Benchmark 2: SHM-RPC Between Processes", process_time, direct_time)
    except Exception as e:
        print(f"\n✗ SHM-RPC benchmark failed: {e}")
        process_time = None

    # Summary for small messages
    print("\n" + "=" * 70)
    print("Small Message Summary")
    print("=" * 70)
    print(f"  Direct calls:     {format_time(direct_time)} (baseline)")
    if process_time:
        print(
            f"       SHM-RPC:     {format_time(process_time)} ({process_time / direct_time:.2f}x)")

    # ===========================================================================
    # PART 2: Large Messages (complex nested structures)
    # ===========================================================================

    print("\n\n" + "=" * 70)
    print("PART 2: Large Message Benchmarks (Complex Data Structures)")
    print("=" * 70)

    msg_size_kb = LARGE_MESSAGE_SERIALIZED_SIZE / 1024
    print(f"Message size: ~{msg_size_kb:.1f} KB (serialized JSON)")
    print()

    # Benchmark 3: Large direct calls (baseline)
    print("\n[1/2] Running baseline benchmark (direct calls with large data)...")
    large_direct_time = benchmark_large_direct()
    print_results("Benchmark 3: Direct Calls (Large Messages Baseline)", large_direct_time,
                  iterations=NUM_ITERATIONS_LARGE)

    # Benchmark 4: Large processes
    print("\n[2/2] Running SHM-RPC benchmark (SHM-RPC with large messages)...")
    try:
        large_process_time = benchmark_large_processes()
        print_results("Benchmark 4: SHM-RPC Processes (Large Messages)",
                      large_process_time, large_direct_time, NUM_ITERATIONS_LARGE)
    except Exception as e:
        print(f"\n✗ SHM-RPC benchmark failed: {e}")
        large_process_time = None

    # Summary for large messages
    print("\n" + "=" * 70)
    print("Large Message Summary")
    print("=" * 70)
    print(f"  Direct calls:     {format_time(large_direct_time)} (baseline)")
    if large_process_time:
        print(
            f"       SHM-RPC:     {format_time(large_process_time)} ("
            f"{large_process_time / large_direct_time:.2f}x)")

    # ===========================================================================
    # Final Summary
    # ===========================================================================

    print("\n\n" + "=" * 70)
    print("OVERALL SUMMARY")
    print("=" * 70)
    print("\nSmall Messages (integers):")
    print(f"  Direct:    {format_time(direct_time)}")
    if process_time:
        print(
            f" SHM-RPC:    {format_time(process_time)} ({process_time / direct_time:.1f}x "
            f"overhead)")

    print(f"\nLarge Messages (~{msg_size_kb:.1f} KB):")
    print(f"  Direct:    {format_time(large_direct_time)}")
    if large_process_time:
        print(
            f" SHM-RPC:    {format_time(large_process_time)} ("
            f"{large_process_time / large_direct_time:.1f}x overhead)")

    print("\n" + "=" * 70)

    # Final cleanup
    print("\nCleaning up resources...")
    ensure_clean_slate("bench_small")
    ensure_clean_slate("bench_large")
    print("Cleanup complete.")


if __name__ == "__main__":
    # Ensure we're using 'spawn' method for multiprocessing
    # This is more similar to how processes would be used in production
    multiprocessing.set_start_method('spawn', force=True)
    main()
