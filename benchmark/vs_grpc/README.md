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
======================================================================
SHM-RPC Bridge vs gRPC Benchmark
======================================================================
Iterations per test: 100,000
Communication: Process-to-Process

Cleaning up any leftover resources...
Cleanup complete.

======================================================================
Testing TINY messages (2 bytes)
======================================================================

[1/2] Running SHM-RPC benchmark...
      Completed in 11.37 s

[2/2] Running gRPC benchmark...
      Completed in 53.44 s

======================================================================
TINY MESSAGE (2 bytes)
======================================================================

SHM-RPC Bridge:
  Total time:    11.37 s
  Throughput:    8.80 K ops/s
  Avg latency:   113.66 μs/call

gRPC (Unix Domain Sockets):
  Total time:    53.44 s
  Throughput:    1.87 K ops/s
  Avg latency:   534.43 μs/call

Comparison:
  SHM-RPC is 4.70x faster than gRPC
  SHM-RPC latency is 4.70x lower

======================================================================
Testing SMALL messages (13 bytes)
======================================================================

[1/2] Running SHM-RPC benchmark...
      Completed in 13.67 s

[2/2] Running gRPC benchmark...
      Completed in 1m 2.58s

======================================================================
SMALL MESSAGE (13 bytes)
======================================================================

SHM-RPC Bridge:
  Total time:    13.67 s
  Throughput:    7.31 K ops/s
  Avg latency:   136.72 μs/call

gRPC (Unix Domain Sockets):
  Total time:    1m 2.58s
  Throughput:    1.60 K ops/s
  Avg latency:   625.77 μs/call

Comparison:
  SHM-RPC is 4.58x faster than gRPC
  SHM-RPC latency is 4.58x lower

======================================================================
Testing MEDIUM messages (100 bytes)
======================================================================

[1/2] Running SHM-RPC benchmark...
      Completed in 14.42 s

[2/2] Running gRPC benchmark...
      Completed in 1m 3.32s

======================================================================
MEDIUM MESSAGE (100 bytes)
======================================================================

SHM-RPC Bridge:
  Total time:    14.42 s
  Throughput:    6.93 K ops/s
  Avg latency:   144.22 μs/call

gRPC (Unix Domain Sockets):
  Total time:    1m 3.32s
  Throughput:    1.58 K ops/s
  Avg latency:   633.24 μs/call

Comparison:
  SHM-RPC is 4.39x faster than gRPC
  SHM-RPC latency is 4.39x lower

======================================================================
Testing LARGE messages (1000 bytes)
======================================================================

[1/2] Running SHM-RPC benchmark...
      Completed in 19.04 s

[2/2] Running gRPC benchmark...
      Completed in 1m 8.02s

======================================================================
LARGE MESSAGE (1000 bytes)
======================================================================

SHM-RPC Bridge:
  Total time:    19.04 s
  Throughput:    5.25 K ops/s
  Avg latency:   190.39 μs/call

gRPC (Unix Domain Sockets):
  Total time:    1m 8.02s
  Throughput:    1.47 K ops/s
  Avg latency:   680.25 μs/call

Comparison:
  SHM-RPC is 3.57x faster than gRPC
  SHM-RPC latency is 3.57x lower

======================================================================
OVERALL SUMMARY
======================================================================

Tiny (2 bytes):
  SHM-RPC:  113.66 μs/call
  gRPC:     534.43 μs/call
  Winner:   SHM-RPC (4.70x faster)

Small (13 bytes):
  SHM-RPC:  136.72 μs/call
  gRPC:     625.77 μs/call
  Winner:   SHM-RPC (4.58x faster)

Medium (100 bytes):
  SHM-RPC:  144.22 μs/call
  gRPC:     633.24 μs/call
  Winner:   SHM-RPC (4.39x faster)

Large (1000 bytes):
  SHM-RPC:  190.39 μs/call
  gRPC:     680.25 μs/call
  Winner:   SHM-RPC (3.57x faster)

======================================================================
```

**Why SHM-RPC Outperforms gRPC:**
1. **No socket overhead**: Direct shared memory access vs Unix socket syscalls
2. **Simpler protocol**: Less protocol overhead compared to HTTP/2-based gRPC
3. **Zero-copy I/O**: Memoryview allows direct memory access
4. **Optimized for local IPC**: Designed specifically for same-host communication


