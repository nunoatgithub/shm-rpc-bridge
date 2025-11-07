# SHM-RPC vs gRPC Benchmark

This benchmark compares the performance of the SHM-RPC bridge library against standard gRPC using Unix domain sockets for inter-process communication.

## Overview

The benchmark measures the latency and throughput of simple string echo operations across different message sizes:
- **Small**: 15 bytes
- **Medium**: 1KB (1,000 bytes)
- **Big**: 10KB (10,000 bytes)
- **Large**: 60KB (60,000 bytes)

Both implementations use **process-to-process** communication (no threading comparison).

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
4. Display detailed performance metrics
5. Clean up all resources when complete

### SHM-RPC Bridge
- Transport: Shared memory with POSIX semaphores
- Serialization: JSON
- Connection: Named shared memory segments
- Processes: Separate client and server processes

### gRPC
- Transport: Unix domain sockets (UDS)
- Serialization: Protocol Buffers
- Connection: Unix socket file (`/tmp/grpc_benchmark.sock`)
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

Here's an example run on a typical development machine:

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

[1/2] Running SHM-RPC benchmark...
      Completed in 5.58 s

[2/2] Running gRPC benchmark...
      Completed in 31.90 s

======================================================================
SMALL MESSAGE (15 bytes)
======================================================================

SHM-RPC Bridge:
  Total time:    5.58 s
  Throughput:    17.93 K ops/s
  Avg latency:   55.76 μs/call

gRPC (Unix Domain Sockets):
  Total time:    31.90 s
  Throughput:    3.14 K ops/s
  Avg latency:   318.96 μs/call

Comparison:
  SHM-RPC is 5.72x faster than gRPC

======================================================================
Testing MEDIUM messages (1000 bytes)
======================================================================

[1/2] Running SHM-RPC benchmark...
      Completed in 7.04 s

[2/2] Running gRPC benchmark...
      Completed in 32.82 s

======================================================================
MEDIUM MESSAGE (1000 bytes)
======================================================================

SHM-RPC Bridge:
  Total time:    7.04 s
  Throughput:    14.21 K ops/s
  Avg latency:   70.36 μs/call

gRPC (Unix Domain Sockets):
  Total time:    32.82 s
  Throughput:    3.05 K ops/s
  Avg latency:   328.17 μs/call

Comparison:
  SHM-RPC is 4.66x faster than gRPC

======================================================================
Testing BIG messages (10000 bytes)
======================================================================

[1/2] Running SHM-RPC benchmark...
      Completed in 18.19 s

[2/2] Running gRPC benchmark...
      Completed in 35.29 s

======================================================================
BIG MESSAGE (10000 bytes)
======================================================================

SHM-RPC Bridge:
  Total time:    18.19 s
  Throughput:    5.50 K ops/s
  Avg latency:   181.93 μs/call

gRPC (Unix Domain Sockets):
  Total time:    35.29 s
  Throughput:    2.83 K ops/s
  Avg latency:   352.89 μs/call

Comparison:
  SHM-RPC is 1.94x faster than gRPC

======================================================================
Testing LARGE messages (60000 bytes)
======================================================================

[1/2] Running SHM-RPC benchmark...
      Completed in 1m 25.86s

[2/2] Running gRPC benchmark...
      Completed in 49.26 s

======================================================================
LARGE MESSAGE (60000 bytes)
======================================================================

SHM-RPC Bridge:
  Total time:    1m 25.86s
  Throughput:    1.16 K ops/s
  Avg latency:   858.64 μs/call

gRPC (Unix Domain Sockets):
  Total time:    49.26 s
  Throughput:    2.03 K ops/s
  Avg latency:   492.63 μs/call

Comparison:
  gRPC is 1.74x faster than SHM-RPC


======================================================================
OVERALL SUMMARY
======================================================================

Small (15 bytes):
  SHM-RPC:  55.76 μs/call
  gRPC:     318.96 μs/call
  Winner:   SHM-RPC (5.72x faster)

Medium (1000 bytes):
  SHM-RPC:  70.36 μs/call
  gRPC:     328.17 μs/call
  Winner:   SHM-RPC (4.66x faster)

Big (10000 bytes):
  SHM-RPC:  181.93 μs/call
  gRPC:     352.89 μs/call
  Winner:   SHM-RPC (1.94x faster)

Large (60000 bytes):
  SHM-RPC:  858.64 μs/call
  gRPC:     492.63 μs/call
  Winner:   gRPC (1.74x faster)

======================================================================
```

**Why SHM-RPC Outperforms gRPC:**
1. **No socket overhead**: Direct shared memory access vs Unix socket syscalls
2. **Simpler protocol**: Less protocol overhead compared to HTTP/2-based gRPC
3. **Zero-copy I/O**: Memoryview allows direct memory access
4. **Optimized for local IPC**: Designed specifically for same-host communication


