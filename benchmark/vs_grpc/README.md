# SHM-RPC vs gRPC Benchmark

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
- Run the benchmarks

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
Server successfully decommissioned.
      Completed in 5.59 s

[2/3] Running gRPC (UDS) benchmark...
      Completed in 27.21 s

[3/3] Running gRPC (TCP) benchmark...
      Completed in 33.71 s

======================================================================
Testing MEDIUM messages (10000 bytes)
======================================================================

[1/3] Running SHM-RPC benchmark...
Server successfully decommissioned.
      Completed in 7.60 s

[2/3] Running gRPC (UDS) benchmark...
      Completed in 37.20 s

[3/3] Running gRPC (TCP) benchmark...
      Completed in 35.37 s

======================================================================
Testing LARGE messages (500000 bytes)
======================================================================

[1/3] Running SHM-RPC benchmark...
Server successfully decommissioned.
      Completed in 46.61 s

[2/3] Running gRPC (UDS) benchmark...
      Completed in 1m 43.11s

[3/3] Running gRPC (TCP) benchmark...
      Completed in 1m 31.73s

======================================================================
Testing BIG messages (2000000 bytes)
======================================================================

[1/3] Running SHM-RPC benchmark...
Server successfully decommissioned.
      Completed in 3m 15.27s

[2/3] Running gRPC (UDS) benchmark...
      Completed in 7m 10.13s

[3/3] Running gRPC (TCP) benchmark...
      Completed in 4m 56.81s


======================================================================
OVERALL SUMMARY
======================================================================

Small (100 bytes):
  SHM-RPC:    111.83 μs/call
  gRPC (UDS): 544.16 μs/call
  gRPC (TCP): 674.17 μs/call

Medium (10000 bytes):
  SHM-RPC:    152.05 μs/call
  gRPC (UDS): 744.07 μs/call
  gRPC (TCP): 707.48 μs/call

Large (500000 bytes):
  SHM-RPC:    932.24 μs/call
  gRPC (UDS): 2062.30 μs/call
  gRPC (TCP): 1834.59 μs/call

Big (2000000 bytes):
  SHM-RPC:    3905.34 μs/call
  gRPC (UDS): 8602.62 μs/call
  gRPC (TCP): 5936.11 μs/call

======================================================================

Final cleanup...
Done!

=======================================================================
Benchmark complete!
=======================================================================
```


