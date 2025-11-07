# SHM-RPC vs gRPC Benchmark

This benchmark compares the performance of the SHM-RPC bridge library against standard gRPC using different transport methods for inter-process communication.

## Overview

The benchmark measures the latency and throughput of simple string echo operations across different message sizes and transport methods:

**Message Sizes:**
- **Small**: 15 bytes
- **Medium**: 1KB (1,000 bytes)
- **Big**: 10KB (10,000 bytes)
- **Large**: 60KB (60,000 bytes)

**Transport Methods:**
- **SHM-RPC**: Shared memory with POSIX semaphores
- **gRPC (UDS)**: gRPC over Unix domain sockets
- **gRPC (TCP)**: gRPC over TCP/IP on localhost

All implementations use **process-to-process** communication.

## Running the Benchmark

### Quick Start

Use the provided script to install all dependencies and run the benchmark:

```bash
# From the repository root
./benchmark/vs_grpc/run_benchmark.sh
```

This script will:
- Check your Python version
- Install required dependencies (posix-ipc, grpcio, grpcio-tools)
- Generate gRPC code from the proto file
- Clean up any leftover resources (shared memory, Unix sockets)
- Run the benchmark
- Display results

### Manual Setup

Alternatively, you can set it up manually:

#### Install Dependencies

```bash
pip install posix-ipc grpcio grpcio-tools
```

#### Generate gRPC Code

```bash
cd benchmark/vs_grpc
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. echo.proto
cd ../..
```

#### Run the Benchmark

```bash
# From the repository root
python benchmark/vs_grpc/benchmark_vs_grpc.py
```

The benchmark will:
1. Clean up any leftover resources (shared memory, Unix sockets)
2. Test each message size with 100,000 iterations
3. Run warmup iterations before each test
4. Test all three transport methods for each message size
5. Display detailed performance metrics
6. Clean up all resources when complete

## What It Tests

### SHM-RPC Bridge
- Transport: Shared memory with POSIX semaphores
- Serialization: JSON
- Connection: Named shared memory segments
- Processes: Separate client and server processes

### gRPC (Unix Domain Sockets)
- Transport: Unix domain sockets (UDS)
- Serialization: Protocol Buffers
- Connection: Unix socket file (`/tmp/grpc_benchmark.sock`)
- Processes: Separate client and server processes

### gRPC (TCP/IP)
- Transport: TCP/IP on localhost
- Serialization: Protocol Buffers
- Connection: TCP socket on port 50051
- Processes: Separate client and server processes

## Metrics Reported

For each message size, the following metrics are displayed:

- **Total time**: Time to complete all iterations
- **Throughput**: Operations per second
- **Avg latency**: Average time per call in microseconds
- **Comparison**: Which implementation is faster and by how much

## Files

- `benchmark_vs_grpc.py` - Main benchmark script
- `echo.proto` - gRPC service definition
- `echo_pb2.py` - Generated protobuf message classes
- `echo_pb2_grpc.py` - Generated gRPC service stubs

## Troubleshooting

### Shared Memory Leaks

If you see resource leak warnings:

```bash
# Clean up from repository root
python util/cleanup_ipc.py
```

### Socket Permission Errors

If you get permission errors with the Unix socket:

```bash
# Clean up the socket manually
rm -f /tmp/grpc_benchmark.sock
```

### Import Errors

Make sure you're running from the repository root so Python can find the `shm_rpc_bridge` module:

```bash
# Wrong (from vs_grpc directory)
python benchmark_vs_grpc.py

# Correct (from repository root)
python benchmark/vs_grpc/benchmark_vs_grpc.py
```

## Example Benchmark Results

```
=======================================================================
SHM-RPC vs gRPC Benchmark Runner
=======================================================================

Python version: 3.8.20

Installing dependencies...
---
Installing posix-ipc...
✓ posix-ipc installed
Installing grpcio...
✓ grpcio and grpcio-tools installed

Generating gRPC code from proto file...
✓ gRPC code generated

Cleaning up any leftover shared memory and socket resources...
POSIX IPC Cleanup Utility
============================================================

Cleaning up shared memory segments...

Cleaning up semaphores...

============================================================
Summary:
  Shared memory segments: 0 removed, 0 failed
  Semaphores: 0 removed, 0 failed
  Total: 0 removed, 0 failed
✓ Cleanup complete

=======================================================================
Running SHM-RPC vs gRPC benchmark...
This will take several minutes
=======================================================================

======================================================================
SHM-RPC Bridge vs gRPC Benchmark
======================================================================
Iterations per test: 100,000
Communication: Process-to-Process

Cleaning up any leftover resources...
Cleanup complete.


======================================================================
Testing SMALL messages (15 bytes)
======================================================================

[1/3] Running SHM-RPC benchmark...
      Completed in 5.51 s

[2/3] Running gRPC (UDS) benchmark...
      Completed in 31.96 s

[3/3] Running gRPC (TCP) benchmark...
      Completed in 34.22 s

======================================================================
SMALL MESSAGE (15 bytes)
======================================================================

SHM-RPC Bridge:
  Total time:    5.51 s
  Throughput:    18.16 K ops/s
  Avg latency:   55.07 μs/call

gRPC (Unix Domain Sockets):
  Total time:    31.96 s
  Throughput:    3.13 K ops/s
  Avg latency:   319.60 μs/call

gRPC (TCP/IP localhost):
  Total time:    34.22 s
  Throughput:    2.92 K ops/s
  Avg latency:   342.16 μs/call

Fastest: SHM-RPC

======================================================================
Testing MEDIUM messages (1000 bytes)
======================================================================

[1/3] Running SHM-RPC benchmark...
      Completed in 6.98 s

[2/3] Running gRPC (UDS) benchmark...
      Completed in 32.31 s

[3/3] Running gRPC (TCP) benchmark...
      Completed in 36.42 s

======================================================================
MEDIUM MESSAGE (1000 bytes)
======================================================================

SHM-RPC Bridge:
  Total time:    6.98 s
  Throughput:    14.33 K ops/s
  Avg latency:   69.76 μs/call

gRPC (Unix Domain Sockets):
  Total time:    32.31 s
  Throughput:    3.09 K ops/s
  Avg latency:   323.15 μs/call

gRPC (TCP/IP localhost):
  Total time:    36.42 s
  Throughput:    2.75 K ops/s
  Avg latency:   364.21 μs/call

Fastest: SHM-RPC

======================================================================
Testing BIG messages (10000 bytes)
======================================================================

[1/3] Running SHM-RPC benchmark...
      Completed in 19.41 s

[2/3] Running gRPC (UDS) benchmark...
      Completed in 36.81 s

[3/3] Running gRPC (TCP) benchmark...
      Completed in 37.57 s

======================================================================
BIG MESSAGE (10000 bytes)
======================================================================

SHM-RPC Bridge:
  Total time:    19.41 s
  Throughput:    5.15 K ops/s
  Avg latency:   194.14 μs/call

gRPC (Unix Domain Sockets):
  Total time:    36.81 s
  Throughput:    2.72 K ops/s
  Avg latency:   368.13 μs/call

gRPC (TCP/IP localhost):
  Total time:    37.57 s
  Throughput:    2.66 K ops/s
  Avg latency:   375.72 μs/call

Fastest: SHM-RPC

======================================================================
Testing LARGE messages (60000 bytes)
======================================================================

[1/3] Running SHM-RPC benchmark...
      Completed in 1m 26.86s

[2/3] Running gRPC (UDS) benchmark...
      Completed in 47.77 s

[3/3] Running gRPC (TCP) benchmark...
      Completed in 51.18 s

======================================================================
LARGE MESSAGE (60000 bytes)
======================================================================

SHM-RPC Bridge:
  Total time:    1m 26.86s
  Throughput:    1.15 K ops/s
  Avg latency:   868.65 μs/call

gRPC (Unix Domain Sockets):
  Total time:    47.77 s
  Throughput:    2.09 K ops/s
  Avg latency:   477.71 μs/call

gRPC (TCP/IP localhost):
  Total time:    51.18 s
  Throughput:    1.95 K ops/s
  Avg latency:   511.81 μs/call

Fastest: gRPC-UDS


======================================================================
OVERALL SUMMARY
======================================================================

Small (15 bytes):
  SHM-RPC:    55.07 μs/call
  gRPC (UDS): 319.60 μs/call
  gRPC (TCP): 342.16 μs/call

Medium (1000 bytes):
  SHM-RPC:    69.76 μs/call
  gRPC (UDS): 323.15 μs/call
  gRPC (TCP): 364.21 μs/call

Big (10000 bytes):
  SHM-RPC:    194.14 μs/call
  gRPC (UDS): 368.13 μs/call
  gRPC (TCP): 375.72 μs/call

Large (60000 bytes):
  SHM-RPC:    868.65 μs/call
  gRPC (UDS): 477.71 μs/call
  gRPC (TCP): 511.81 μs/call

======================================================================
```


