#!/usr/bin/env python3
"""
Benchmark comparing SHM-RPC Bridge vs gRPC with Unix Domain Sockets.

Compares performance of lightweight string message RPC calls between processes:
1. SHM-RPC Bridge (shared memory + POSIX semaphores)
2. gRPC over Unix Domain Sockets

Both implementations use process-to-process communication.
"""

from __future__ import annotations

import multiprocessing
import os
import sys
import time
from concurrent import futures
from pathlib import Path

import grpc

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shm_rpc_bridge import RPCClient, RPCServer

# Import generated gRPC code
import echo_pb2
import echo_pb2_grpc

# Benchmark configuration
NUM_ITERATIONS = 100_000  # Number of RPC calls to make
MESSAGE_SIZES = {
    "small": "A" * 15,                               # 15 bytes
    "medium": "B" * 1000,                            # 1KB
    "big": "C" * 10_000,                             # 10KB
    "large": "D" * 60_000,                           # 60KB
}


# ==============================================================================
# Cleanup Helper
# ==============================================================================

def cleanup_shm_resources(channel: str) -> None:
    """Clean up shared memory resources for a channel."""
    import posix_ipc
    from multiprocessing import shared_memory

    # Clean up multiprocessing.shared_memory objects
    for resource_type in ['request', 'response']:
        shm_name = f"{channel}_{resource_type}"
        try:
            shm = shared_memory.SharedMemory(name=shm_name, create=False)
            shm.close()
            shm.unlink()
        except (FileNotFoundError, Exception):
            pass

    # Clean up POSIX semaphores
    for sem_type in ['req_empty', 'req_full', 'resp_empty', 'resp_full']:
        try:
            posix_ipc.unlink_semaphore(f"/{channel}_{sem_type}")
        except Exception:
            pass


def cleanup_uds_socket(socket_path: str) -> None:
    """Clean up Unix domain socket file."""
    try:
        if os.path.exists(socket_path):
            os.unlink(socket_path)
    except Exception:
        pass


# ==============================================================================
# gRPC Implementation
# ==============================================================================

class EchoServicer(echo_pb2_grpc.EchoServiceServicer):
    """gRPC echo service implementation."""

    def Echo(self, request, context):
        return echo_pb2.EchoResponse(message=request.message)


def run_grpc_server(socket_path: str, ready_queue: multiprocessing.Queue) -> None:  # type: ignore
    """Run gRPC server in a separate process."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    echo_pb2_grpc.add_EchoServiceServicer_to_server(EchoServicer(), server)

    # Use Unix domain socket
    server.add_insecure_port(f'unix://{socket_path}')
    server.start()

    ready_queue.put("ready")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)


def benchmark_grpc(message: str, socket_path: str) -> float:
    """Benchmark gRPC over Unix domain sockets."""
    ready_queue: multiprocessing.Queue = multiprocessing.Queue()  # type: ignore

    # Clean up socket if it exists
    cleanup_uds_socket(socket_path)

    # Start server process
    server_process = multiprocessing.Process(
        target=run_grpc_server,
        args=(socket_path, ready_queue),
    )
    server_process.start()

    # Wait for server to be ready
    try:
        ready_queue.get(timeout=5.0)
    except Exception as e:
        server_process.terminate()
        server_process.join()
        raise RuntimeError(f"gRPC server failed to start: {e}")

    # Give server a moment to fully initialize
    time.sleep(0.1)

    try:
        # Create client channel
        channel = grpc.insecure_channel(f'unix://{socket_path}')
        stub = echo_pb2_grpc.EchoServiceStub(channel)

        # Warm-up
        for _ in range(100):
            stub.Echo(echo_pb2.EchoRequest(message=message))

        # Benchmark
        start = time.perf_counter()
        for _ in range(NUM_ITERATIONS):
            response = stub.Echo(echo_pb2.EchoRequest(message=message))
        end = time.perf_counter()

        channel.close()
        return end - start

    finally:
        # Stop server
        server_process.terminate()
        server_process.join(timeout=2.0)
        if server_process.is_alive():
            server_process.kill()
            server_process.join()

        # Clean up socket
        cleanup_uds_socket(socket_path)


# ==============================================================================
# SHM-RPC Implementation
# ==============================================================================

def run_shm_rpc_server(channel: str, ready_queue: multiprocessing.Queue) -> None:  # type: ignore
    """Run SHM-RPC server in a separate process."""
    server = RPCServer(channel, timeout=10.0)

    # Register echo method
    def echo(message: str) -> str:
        return message

    server.register("echo", echo)
    ready_queue.put("ready")

    try:
        server.start()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()


def benchmark_shm_rpc(message: str, channel: str) -> float:
    """Benchmark SHM-RPC bridge."""
    ready_queue: multiprocessing.Queue = multiprocessing.Queue()  # type: ignore

    # Clean up any leftover resources
    cleanup_shm_resources(channel)

    # Start server process
    server_process = multiprocessing.Process(
        target=run_shm_rpc_server,
        args=(channel, ready_queue),
    )
    server_process.start()

    # Wait for server to be ready
    try:
        ready_queue.get(timeout=5.0)
    except Exception as e:
        server_process.terminate()
        server_process.join()
        cleanup_shm_resources(channel)
        raise RuntimeError(f"SHM-RPC server failed to start: {e}")

    # Give server a moment to fully initialize
    time.sleep(0.1)

    try:
        # Create client
        client = RPCClient(channel, timeout=10.0)

        # Warm-up
        for _ in range(100):
            client.call("echo", message=message)

        # Benchmark
        start = time.perf_counter()
        for _ in range(NUM_ITERATIONS):
            result = client.call("echo", message=message)
        end = time.perf_counter()

        client.close()
        return end - start

    finally:
        # Stop server
        server_process.terminate()
        server_process.join(timeout=2.0)
        if server_process.is_alive():
            server_process.kill()
            server_process.join()

        # Clean up resources
        cleanup_shm_resources(channel)


# ==============================================================================
# Results Display
# ==============================================================================

def format_time(seconds: float) -> str:
    """Format time in a human-readable way."""
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.2f} μs"
    elif seconds < 1:
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


def print_comparison(size_name: str, message: str, shm_time: float, grpc_time: float) -> None:
    """Print comparison results for a specific message size."""
    msg_size = len(message.encode('utf-8'))

    shm_throughput = NUM_ITERATIONS / shm_time
    grpc_throughput = NUM_ITERATIONS / grpc_time

    shm_latency_us = (shm_time / NUM_ITERATIONS) * 1_000_000
    grpc_latency_us = (grpc_time / NUM_ITERATIONS) * 1_000_000

    speedup = shm_time / grpc_time

    print(f"\n{'='*70}")
    print(f"{size_name.upper()} MESSAGE ({msg_size} bytes)")
    print(f"{'='*70}")

    print(f"\nSHM-RPC Bridge:")
    print(f"  Total time:    {format_time(shm_time)}")
    print(f"  Throughput:    {format_throughput(shm_throughput)}")
    print(f"  Avg latency:   {shm_latency_us:.2f} μs/call")

    print(f"\ngRPC (Unix Domain Sockets):")
    print(f"  Total time:    {format_time(grpc_time)}")
    print(f"  Throughput:    {format_throughput(grpc_throughput)}")
    print(f"  Avg latency:   {grpc_latency_us:.2f} μs/call")

    print(f"\nComparison:")
    if speedup > 1:
        print(f"  gRPC is {speedup:.2f}x faster than SHM-RPC")
    else:
        print(f"  SHM-RPC is {1/speedup:.2f}x faster than gRPC")

# ==============================================================================
# Main Benchmark
# ==============================================================================

def main() -> None:
    """Run the benchmark suite."""
    print("="*70)
    print("SHM-RPC Bridge vs gRPC Benchmark")
    print("="*70)
    print(f"Iterations per test: {NUM_ITERATIONS:,}")
    print(f"Communication: Process-to-Process")
    print()

    # Paths for temporary resources
    socket_path = "/tmp/grpc_benchmark.sock"
    shm_channel = "shm_benchmark"

    # Initial cleanup
    print("Cleaning up any leftover resources...")
    cleanup_uds_socket(socket_path)
    cleanup_shm_resources(shm_channel)
    print("Cleanup complete.\n")

    results = {}

    # Run benchmarks for each message size
    for size_name, message in MESSAGE_SIZES.items():
        print(f"\n{'='*70}")
        print(f"Testing {size_name.upper()} messages ({len(message.encode('utf-8'))} bytes)")
        print(f"{'='*70}")

        # Benchmark SHM-RPC
        print(f"\n[1/2] Running SHM-RPC benchmark...")
        try:
            shm_time = benchmark_shm_rpc(message, shm_channel)
            print(f"      Completed in {format_time(shm_time)}")
        except Exception as e:
            print(f"✗ SHM-RPC benchmark failed: {e}")
            shm_time = None

        # Small delay between benchmarks
        time.sleep(0.5)

        # Benchmark gRPC
        print(f"\n[2/2] Running gRPC benchmark...")
        try:
            grpc_time = benchmark_grpc(message, socket_path)
            print(f"      Completed in {format_time(grpc_time)}")
        except Exception as e:
            print(f"✗ gRPC benchmark failed: {e}")
            grpc_time = None

        if shm_time and grpc_time:
            results[size_name] = {
                'message': message,
                'shm_time': shm_time,
                'grpc_time': grpc_time,
            }
            print_comparison(size_name, message, shm_time, grpc_time)

        # Cleanup between tests
        cleanup_shm_resources(shm_channel)
        cleanup_uds_socket(socket_path)
        time.sleep(0.2)

    # Overall summary
    print("\n\n" + "="*70)
    print("OVERALL SUMMARY")
    print("="*70)

    for size_name, data in results.items():
        msg_size = len(data['message'].encode('utf-8'))
        shm_lat = (data['shm_time'] / NUM_ITERATIONS) * 1_000_000
        grpc_lat = (data['grpc_time'] / NUM_ITERATIONS) * 1_000_000
        speedup = data['shm_time'] / data['grpc_time']

        winner = "gRPC" if speedup > 1 else "SHM-RPC"
        ratio = speedup if speedup > 1 else 1/speedup

        print(f"\n{size_name.capitalize()} ({msg_size} bytes):")
        print(f"  SHM-RPC:  {shm_lat:.2f} μs/call")
        print(f"  gRPC:     {grpc_lat:.2f} μs/call")
        print(f"  Winner:   {winner} ({ratio:.2f}x faster)")

    print("\n" + "="*70)

    # Final cleanup
    print("\nFinal cleanup...")
    cleanup_uds_socket(socket_path)
    cleanup_shm_resources(shm_channel)
    print("Done!")


if __name__ == "__main__":
    # Ensure we're using 'spawn' method for multiprocessing
    # This is more similar to how processes would be used in production
    multiprocessing.set_start_method('spawn', force=True)
    main()

