# SHM-RPC vs gRPC Benchmark

This benchmark compares the performance of the SHM-RPC bridge library against standard gRPC using different transport methods for inter-process communication.

## Overview

The benchmark measures the latency and throughput of simple string echo operations across different message sizes and transport methods:

**Message Sizes:**
- **Small**: 100 bytes
- **Medium**: 10 KB
- **Big**: 500 KB
- **Large**: 2 MB

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
- Install required dependencies (posix-ipc, orjson, grpcio, grpcio-tools)
- Generate gRPC code from the proto file
- Clean up any leftover resources (shared memory, Unix sockets)
- Run the benchmark
- Display results

### Manual Setup

Alternatively, you can set it up manually:

#### Install Dependencies

```bash
pip install posix-ipc orjson grpcio grpcio-tools
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
/home/nuno/dev/tools/miniconda3/envs/shm-rpc-bridge/lib/python3.8/site-packages/grpc_tools/protoc.py:25: DeprecationWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html
  import pkg_resources
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
Iterations per test: 50,000
Communication: Process-to-Process

Cleaning up any leftover resources...
Cleanup complete.


======================================================================
Testing SMALL messages (100 bytes)
======================================================================

[1/3] Running SHM-RPC benchmark...
      Completed in 1.61 s

[2/3] Running gRPC (UDS) benchmark...
      Completed in 16.17 s

[3/3] Running gRPC (TCP) benchmark...
      Completed in 17.20 s

======================================================================
Testing MEDIUM messages (10000 bytes)
======================================================================

[1/3] Running SHM-RPC benchmark...
      Completed in 2.60 s

[2/3] Running gRPC (UDS) benchmark...
      Completed in 17.38 s

[3/3] Running gRPC (TCP) benchmark...
      Completed in 18.48 s

======================================================================
Testing LARGE messages (500000 bytes)
======================================================================

[1/3] Running SHM-RPC benchmark...
      Completed in 45.11 s

[2/3] Running gRPC (UDS) benchmark...
      Completed in 1m 26.56s

[3/3] Running gRPC (TCP) benchmark...
      Completed in 1m 34.48s

======================================================================
Testing BIG messages (2000000 bytes)
======================================================================

[1/3] Running SHM-RPC benchmark...
      Completed in 3m 2.48s

[2/3] Running gRPC (UDS) benchmark...
      Completed in 4m 24.44s

[3/3] Running gRPC (TCP) benchmark...
      Completed in 4m 39.83s


======================================================================
OVERALL SUMMARY
======================================================================

Small (100 bytes):
  SHM-RPC:    32.26 μs/call
  gRPC (UDS): 323.38 μs/call
  gRPC (TCP): 343.91 μs/call

Medium (10000 bytes):
  SHM-RPC:    51.99 μs/call
  gRPC (UDS): 347.60 μs/call
  gRPC (TCP): 369.58 μs/call

Large (500000 bytes):
  SHM-RPC:    902.19 μs/call
  gRPC (UDS): 1731.23 μs/call
  gRPC (TCP): 1889.54 μs/call

Big (2000000 bytes):
  SHM-RPC:    3649.69 μs/call
  gRPC (UDS): 5288.85 μs/call
  gRPC (TCP): 5596.50 μs/call

======================================================================

```


