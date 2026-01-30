#!/usr/bin/env python3
"""
Compares performance of raw transport layer byte array communication between processes:
1. SharedMemoryTransportPosix (POSIX shared memory + semaphores)
2. ZeroMQ IPC (ZeroMQ over Unix domain sockets)
"""

from __future__ import annotations

import os

# Allow access to internal APIs for benchmarking
os.environ["SHM_RPC_BRIDGE_ALLOW_INTERNALS"] = "true"

import logging
import multiprocessing
import time

import zmq

from shm_rpc_bridge.transport.transport_posix import SharedMemoryTransportPosix


# Benchmark configuration
NUM_ITERATIONS = 50_000  # Number of send/receive operations to make
MESSAGE_SIZES = {
    "small": 100,                    # 100 bytes
    "medium": 10_000,                # 10KB
    "large": 500_000,                # 500KB
    "big": 2_000_000,                # 2MB
}

BUFFER_SIZE = 2_500_000  # 2.5MB buffer to accommodate all message sizes
TIMEOUT = 10.0  # 10 seconds timeout


# ==============================================================================
# Cleanup Helper
# ==============================================================================

def cleanup_posix_resources(name: str) -> None:
    try:
        SharedMemoryTransportPosix.delete_resources()
    except Exception:
        pass


def cleanup_zmq_socket(socket_path: str) -> None:
    try:
        if os.path.exists(socket_path):
            os.unlink(socket_path)
    except Exception:
        pass


# ==============================================================================
# 1. SharedMemoryTransportPosix
# ==============================================================================

def run_posix_server(name: str) -> None:

    transport = SharedMemoryTransportPosix.create(
        name=name,
        buffer_size=BUFFER_SIZE,
        timeout=TIMEOUT,
    )

    try:
        # Echo back received messages
        while True:
            data = transport.receive_request()
            transport.send_response(data)
    except KeyboardInterrupt:
        pass
    finally:
        transport.close()


def benchmark_posix(name: str, message_size: int) -> float:
    """Benchmark POSIX IPC transport."""

    # Start server process
    server_process = multiprocessing.Process(
        target=run_posix_server,
        args=(name,),
    )
    server_process.start()

    try:
        # Create client transport
        transport = SharedMemoryTransportPosix.open(
            name=name,
            buffer_size=BUFFER_SIZE,
            timeout=TIMEOUT,
            wait_for_creation=5.0,
        )

        # Create test message
        message = b"A" * message_size

        # Warm-up
        for _ in range(100):
            transport.send_request(message)
            _ = transport.receive_response()

        # Benchmark
        start = time.perf_counter()
        for _ in range(NUM_ITERATIONS):
            transport.send_request(message)
            _ = transport.receive_response()
        end = time.perf_counter()

        transport.close()
        return end - start

    finally:
        # Stop server
        server_process.terminate()
        server_process.join(timeout=2.0)
        if server_process.is_alive():
            server_process.kill()
            server_process.join()


# ==============================================================================
# ZeroMQ IPC Implementation
# ==============================================================================

def run_zmq_server(socket_path: str, server_ready: multiprocessing.Event) -> None:  # type: ignore
    """Run ZeroMQ IPC server in a separate process."""
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"ipc://{socket_path}")

    server_ready.set()

    try:
        # Echo back received messages
        while True:
            message = socket.recv()
            socket.send(message)
    except KeyboardInterrupt:
        pass
    finally:
        socket.close()
        context.term()


def benchmark_zmq(socket_path: str, message_size: int) -> float:
    """Benchmark ZeroMQ IPC transport."""
    server_ready: multiprocessing.Event = multiprocessing.Event()  # type: ignore

    # Clean up socket if it exists
    cleanup_zmq_socket(socket_path)

    # Start server process
    server_process = multiprocessing.Process(
        target=run_zmq_server,
        args=(socket_path, server_ready),
    )
    server_process.start()

    # Wait for server to be ready
    try:
        server_ready.wait(timeout=5.0)
    except Exception as e:
        server_process.terminate()
        server_process.join()
        raise RuntimeError(f"ZeroMQ server failed to start: {e}")

    # Give server a moment to fully initialize
    time.sleep(0.1)

    try:
        # Create client socket
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect(f"ipc://{socket_path}")

        # Create test message
        message = b"A" * message_size

        # Warm-up
        for _ in range(100):
            socket.send(message)
            _ = socket.recv()

        # Benchmark
        start = time.perf_counter()
        for _ in range(NUM_ITERATIONS):
            socket.send(message)
            _ = socket.recv()
        end = time.perf_counter()

        socket.close()
        context.term()
        return end - start

    finally:
        # Stop server
        server_process.terminate()
        server_process.join(timeout=2.0)
        if server_process.is_alive():
            server_process.kill()
            server_process.join()

        # Clean up socket
        cleanup_zmq_socket(socket_path)


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

# ==============================================================================
# Main Benchmark
# ==============================================================================

def main() -> None:
    """Run the benchmark suite."""

    print("=" * 70)
    print("Transport Layer Benchmark")
    print("=" * 70)
    print(f"Iterations per test: {NUM_ITERATIONS:,}")
    print(f"Communication: Process-to-Process (raw byte arrays)")
    print()

    # Paths for temporary resources
    posix_channel_name = "t_bench"
    zmq_socket_path = "/tmp/zt_bench.sock"

    # Initial cleanup
    print("Cleaning up any leftover resources...")
    cleanup_posix_resources(posix_channel_name)
    cleanup_zmq_socket(zmq_socket_path)
    print("Cleanup complete.\n")

    results = {}

    # Run benchmarks for each message size
    for size_name, message_size in MESSAGE_SIZES.items():
        print(f"\n{'='*70}")
        print(f"Testing {size_name.upper()} messages ({message_size} bytes)")
        print(f"{'='*70}")

        # Benchmark POSIX IPC
        print(f"\n[1/2] Running SHM POSIX benchmark...")
        try:
            posix_time = benchmark_posix(posix_channel_name, message_size)
            print(f"      Completed in {format_time(posix_time)}")
        except Exception as e:
            print(f"✗ SHM POSIX benchmark failed: {e}")
            posix_time = None

        # Small delay between benchmarks
        time.sleep(0.5)

        # Benchmark ZeroMQ IPC
        print(f"\n[2/2] Running ZeroMQ IPC benchmark...")
        try:
            zmq_time = benchmark_zmq(zmq_socket_path, message_size)
            print(f"      Completed in {format_time(zmq_time)}")
        except Exception as e:
            print(f"✗ ZeroMQ IPC benchmark failed: {e}")
            zmq_time = None

        results[size_name] = {
            "size": message_size,
            "posix_time": posix_time,
            "zmq_time": zmq_time,
        }

        # Cleanup between tests
        cleanup_posix_resources(posix_channel_name)
        cleanup_zmq_socket(zmq_socket_path)
        time.sleep(0.2)

    # Overall summary
    print("\n\n" + "=" * 70)
    print("OVERALL SUMMARY")
    print("=" * 70)

    for size_name, data in results.items():
        msg_size = data["size"]
        print(f"\n{size_name.capitalize()} ({msg_size} bytes):")

        if data["posix_time"]:
            posix_lat = (data["posix_time"] / NUM_ITERATIONS) * 1_000_000
            print(f"  SHM POSIX:   {posix_lat:.2f} μs/call")

        if data["zmq_time"]:
            zmq_lat = (data["zmq_time"] / NUM_ITERATIONS) * 1_000_000
            percent_change = ((zmq_lat - posix_lat) / posix_lat) * 100
            label = "faster" if percent_change < 0 else "slower"
            diff_msg = f"({abs(percent_change):.1f}% {label})"
            print(f" ZeroMQ IPC:  {zmq_lat:.2f} μs/call {diff_msg}")

    print("\n" + "=" * 70)

    # Final cleanup
    print("\nFinal cleanup...")
    cleanup_posix_resources(posix_channel_name)
    cleanup_zmq_socket(zmq_socket_path)
    print("Done!")


if __name__ == "__main__":
    # Ensure we're using 'spawn' method for multiprocessing
    # This is more similar to how processes would be used in production
    multiprocessing.set_start_method('spawn', force=True)
    main()
