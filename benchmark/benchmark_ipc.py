#!/usr/bin/env python3
"""
Benchmark script comparing different IPC implementations.

Compares performance of 1 million RPC calls across three implementations:
1. Direct object calls (in-process, baseline)
2. SHM-RPC between threads
3. SHM-RPC between processes
"""

import multiprocessing
import os
import sys
import threading
import time

# Add parent directory to path to import cleanup utility
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shm_rpc_bridge import RPCClient, RPCServer


# Cleanup helper
def cleanup_channel(channel: str) -> None:
    """Clean up shared memory resources for a channel."""
    import posix_ipc
    from multiprocessing import shared_memory

    # Clean up multiprocessing.shared_memory objects
    for resource_type in ['request', 'response']:
        shm_name = f"{channel}_{resource_type}"
        try:
            # Try to open and unlink the shared memory
            shm = shared_memory.SharedMemory(name=shm_name, create=False)
            shm.close()
            shm.unlink()
        except FileNotFoundError:
            pass
        except Exception:
            pass

    # Clean up POSIX semaphores
    for sem_type in ['req_empty', 'req_full', 'resp_empty', 'resp_full']:
        try:
            posix_ipc.unlink_semaphore(f"/{channel}_{sem_type}")
        except:
            pass


# Number of iterations for the benchmark
NUM_ITERATIONS = 100_000
NUM_ITERATIONS_LARGE = 10_000  # Fewer iterations for large messages


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


def create_large_message(size: str = "small") -> dict:
    """
    Create a large, complex nested data structure.

    Args:
        size: "small" (1KB), "medium" (10KB), or "large" (100KB)
    """
    if size == "small":
        items = 10
    elif size == "medium":
        items = 100
    else:  # large
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


# ==============================================================================
# Benchmark 1: Direct Object Calls (Baseline)
# ==============================================================================

def benchmark_direct_calls() -> float:
    """Benchmark direct object method calls (no IPC)."""
    service = CalculatorService()

    start = time.perf_counter()
    for i in range(NUM_ITERATIONS):
        result = service.add(i, i + 1)
    end = time.perf_counter()

    return end - start


# ==============================================================================
# Benchmark 2: SHM-RPC Between Threads
# ==============================================================================

def run_server_thread(channel: str, ready_event: threading.Event, server_holder: list) -> None:
    """Run RPC server in a thread."""
    server = RPCServer(channel, timeout=10.0)
    server_holder.append(server)  # Store reference so we can stop it

    service = CalculatorService()
    server.register("add", service.add)

    # Give server a moment to fully initialize
    time.sleep(0.1)

    # Signal that server is ready
    ready_event.set()

    # Start server (will run until stop() is called)
    try:
        server.start()
    except Exception:
        pass
    finally:
        server.close()


def benchmark_threads() -> float:
    """Benchmark RPC calls between threads using shared memory."""
    channel = "bench_threads"
    ready_event = threading.Event()
    server_holder: list = []  # To hold server reference

    # Clean up any leftover resources first
    cleanup_channel(channel)

    # Start server thread (NOT daemon - we want to properly stop it)
    server_thread = threading.Thread(
        target=run_server_thread,
        args=(channel, ready_event, server_holder),
        daemon=False,
    )
    server_thread.start()

    # Wait for server to be ready
    ready_event.wait(timeout=5.0)

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

        # Stop server properly
        if server_holder:
            server_holder[0].stop()

        # Wait for thread to actually finish
        server_thread.join(timeout=5.0)

        # Clean up shared memory resources
        cleanup_channel(channel)

# ==============================================================================
# Benchmark 3: SHM-RPC Between Processes
# ==============================================================================

def run_server_process(channel: str, ready_queue: multiprocessing.Queue) -> None:  # type: ignore
    """Run RPC server in a separate process."""
    server = RPCServer(channel, timeout=10.0)
    service = CalculatorService()
    server.register("add", service.add)

    # Signal that server is ready
    ready_queue.put("ready")

    # Start server (will run until terminated)
    try:
        server.start()
    finally:
        server.close()


def benchmark_processes() -> float:
    """Benchmark RPC calls between processes using shared memory."""
    channel = "bench_processes"
    ready_queue: multiprocessing.Queue = multiprocessing.Queue()  # type: ignore

    # Clean up any leftover resources first
    cleanup_channel(channel)

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
        cleanup_channel(channel)
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

        # Clean up shared memory resources
        cleanup_channel(channel)


# ==============================================================================
# Benchmark 4: Large Messages - Direct Calls
# ==============================================================================

def benchmark_large_direct(message_size: str = "medium") -> float:
    """Benchmark direct calls with large messages."""
    service = DataService()
    large_msg = create_large_message(message_size)

    start = time.perf_counter()
    for _ in range(NUM_ITERATIONS_LARGE):
        result = service.process_data(large_msg)
    end = time.perf_counter()

    return end - start


# ==============================================================================
# Benchmark 5: Large Messages - Threads
# ==============================================================================

def run_data_server_thread(channel: str, ready_event: threading.Event, server_holder: list) -> None:
    """Run data processing server in a thread."""
    server = RPCServer(channel, timeout=10.0)
    server_holder.append(server)

    service = DataService()
    server.register("process_data", service.process_data)

    time.sleep(0.1)
    ready_event.set()

    try:
        server.start()
    except Exception:
        pass
    finally:
        server.close()


def benchmark_large_threads(message_size: str = "medium") -> float:
    """Benchmark RPC with large messages between threads."""
    channel = "bench_large_threads"
    ready_event = threading.Event()
    server_holder: list = []

    cleanup_channel(channel)

    server_thread = threading.Thread(
        target=run_data_server_thread,
        args=(channel, ready_event, server_holder),
        daemon=False,
    )
    server_thread.start()
    ready_event.wait(timeout=5.0)

    client = None
    large_msg = create_large_message(message_size)

    try:
        client = RPCClient(channel, timeout=10.0)

        start = time.perf_counter()
        for _ in range(NUM_ITERATIONS_LARGE):
            result = client.call("process_data", data=large_msg)
        end = time.perf_counter()

        return end - start
    finally:
        if client:
            try:
                client.close()
            except:
                pass

        if server_holder:
            server_holder[0].stop()

        server_thread.join(timeout=5.0)

        # Clean up shared memory resources
        cleanup_channel(channel)


# ==============================================================================
# Benchmark 6: Large Messages - Processes
# ==============================================================================

def run_data_server_process(channel: str, ready_queue: multiprocessing.Queue) -> None:  # type: ignore
    """Run data processing server in a separate process."""
    server = RPCServer(channel, timeout=10.0)
    service = DataService()
    server.register("process_data", service.process_data)

    ready_queue.put("ready")

    try:
        server.start()
    finally:
        server.close()


def benchmark_large_processes(message_size: str = "medium") -> float:
    """Benchmark RPC with large messages between processes."""
    channel = "bench_large_processes"
    ready_queue: multiprocessing.Queue = multiprocessing.Queue()  # type: ignore

    cleanup_channel(channel)

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
        cleanup_channel(channel)
        raise RuntimeError(f"Server failed to start: {e}")

    client = None
    large_msg = create_large_message(message_size)

    try:
        client = RPCClient(channel, timeout=10.0)

        start = time.perf_counter()
        for _ in range(NUM_ITERATIONS_LARGE):
            result = client.call("process_data", data=large_msg)
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

        # Clean up shared memory resources
        cleanup_channel(channel)


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


def print_results(name: str, duration: float, baseline: float = None, iterations: int = NUM_ITERATIONS) -> None:  # type: ignore
    """Print benchmark results."""
    ops_per_sec = iterations / duration
    latency_us = (duration / iterations) * 1_000_000

    print(f"\n{name}")
    print("=" * 70)
    print(f"  Total time:       {format_time(duration)}")
    print(f"  Throughput:       {format_throughput(ops_per_sec)}")
    print(f"  Avg latency:      {latency_us:.2f} μs/call")

    if baseline:
        overhead = ((duration / baseline) - 1) * 100
        slowdown = duration / baseline
        print(f"  vs Baseline:      {slowdown:.2f}x slower ({overhead:+.1f}% overhead)")


# ==============================================================================
# Main Benchmark
# ==============================================================================

def main() -> None:
    """Run all benchmarks."""
    # Clean up any leftover resources from previous runs
    print("Cleaning up any leftover resources...")
    cleanup_channel("bench_threads")
    cleanup_channel("bench_processes")
    cleanup_channel("bench_large_threads")
    cleanup_channel("bench_large_processes")

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
    print("\n[1/3] Running baseline benchmark (direct calls)...")
    direct_time = benchmark_direct_calls()
    print_results("Benchmark 1: Direct Object Calls (Baseline)", direct_time)

    # Benchmark 2: Threads
    print("\n[2/3] Running thread benchmark (SHM-RPC between threads)...")
    try:
        thread_time = benchmark_threads()
        print_results("Benchmark 2: SHM-RPC Between Threads", thread_time, direct_time)
    except Exception as e:
        print(f"\n✗ Thread benchmark failed: {e}")
        thread_time = None

    # Benchmark 3: Processes
    print("\n[3/3] Running process benchmark (SHM-RPC between processes)...")
    try:
        process_time = benchmark_processes()
        print_results("Benchmark 3: SHM-RPC Between Processes", process_time, direct_time)
    except Exception as e:
        print(f"\n✗ Process benchmark failed: {e}")
        process_time = None

    # Summary for small messages
    print("\n" + "=" * 70)
    print("Small Message Summary")
    print("=" * 70)
    print(f"  Direct calls:     {format_time(direct_time)} (baseline)")
    if thread_time:
        print(f"  Threads:          {format_time(thread_time)} ({thread_time/direct_time:.2f}x)")
    if process_time:
        print(f"  Processes:        {format_time(process_time)} ({process_time/direct_time:.2f}x)")

    # Comparison
    if thread_time and process_time:
        print(f"\n  Thread vs Process: {thread_time/process_time:.2f}x")
        if thread_time < process_time:
            print(f"    → Threads are {process_time/thread_time:.2f}x faster")
        else:
            print(f"    → Processes are {thread_time/process_time:.2f}x faster")

    # ===========================================================================
    # PART 2: Large Messages (complex nested structures)
    # ===========================================================================

    print("\n\n" + "=" * 70)
    print("PART 2: Large Message Benchmarks (Complex Data Structures)")
    print("=" * 70)

    # Test with medium-sized messages (~10KB JSON)
    message_size = "medium"
    sample_msg = create_large_message(message_size)
    import json
    msg_size_kb = len(json.dumps(sample_msg)) / 1024
    print(f"Message size: ~{msg_size_kb:.1f} KB (serialized JSON)")
    print()

    # Benchmark 4: Large direct calls (baseline)
    print("\n[1/3] Running baseline benchmark (direct calls with large data)...")
    large_direct_time = benchmark_large_direct(message_size)
    print_results("Benchmark 4: Direct Calls (Large Messages Baseline)", large_direct_time,
                  iterations=NUM_ITERATIONS_LARGE)

    # Benchmark 5: Large threads
    print("\n[2/3] Running thread benchmark (SHM-RPC with large messages)...")
    try:
        large_thread_time = benchmark_large_threads(message_size)
        print_results("Benchmark 5: SHM-RPC Threads (Large Messages)",
                      large_thread_time, large_direct_time, NUM_ITERATIONS_LARGE)
    except Exception as e:
        print(f"\n✗ Thread benchmark failed: {e}")
        large_thread_time = None

    # Benchmark 6: Large processes
    print("\n[3/3] Running process benchmark (SHM-RPC with large messages)...")
    try:
        large_process_time = benchmark_large_processes(message_size)
        print_results("Benchmark 6: SHM-RPC Processes (Large Messages)",
                      large_process_time, large_direct_time, NUM_ITERATIONS_LARGE)
    except Exception as e:
        print(f"\n✗ Process benchmark failed: {e}")
        large_process_time = None

    # Summary for large messages
    print("\n" + "=" * 70)
    print("Large Message Summary")
    print("=" * 70)
    print(f"  Direct calls:     {format_time(large_direct_time)} (baseline)")
    if large_thread_time:
        print(f"  Threads:          {format_time(large_thread_time)} ({large_thread_time/large_direct_time:.2f}x)")
    if large_process_time:
        print(f"  Processes:        {format_time(large_process_time)} ({large_process_time/large_direct_time:.2f}x)")

    # Comparison
    if large_thread_time and large_process_time:
        print(f"\n  Thread vs Process: {large_thread_time/large_process_time:.2f}x")
        if large_thread_time < large_process_time:
            print(f"    → Threads are {large_process_time/large_thread_time:.2f}x faster")
        else:
            print(f"    → Processes are {large_thread_time/large_process_time:.2f}x faster")

    # ===========================================================================
    # Final Summary
    # ===========================================================================

    print("\n\n" + "=" * 70)
    print("OVERALL SUMMARY")
    print("=" * 70)
    print("\nSmall Messages (integers):")
    print(f"  Direct:    {format_time(direct_time)}")
    if thread_time:
        print(f"  Threads:   {format_time(thread_time)} ({thread_time/direct_time:.1f}x overhead)")
    if process_time:
        print(f"  Processes: {format_time(process_time)} ({process_time/direct_time:.1f}x overhead)")

    print(f"\nLarge Messages (~{msg_size_kb:.1f} KB):")
    print(f"  Direct:    {format_time(large_direct_time)}")
    if large_thread_time:
        print(f"  Threads:   {format_time(large_thread_time)} ({large_thread_time/large_direct_time:.1f}x overhead)")
    if large_process_time:
        print(f"  Processes: {format_time(large_process_time)} ({large_process_time/large_direct_time:.1f}x overhead)")

    print("\n" + "=" * 70)

    # Final cleanup
    print("\nCleaning up resources...")
    cleanup_channel("bench_threads")
    cleanup_channel("bench_processes")
    cleanup_channel("bench_large_threads")
    cleanup_channel("bench_large_processes")
    print("Cleanup complete.")


if __name__ == "__main__":
    main()

