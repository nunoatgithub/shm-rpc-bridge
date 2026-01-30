# Transport Layer Benchmarks

This directory contains performance benchmarks comparing SharedMemoryTransportPosix against other byte-level IPC transport implementations.

## Overview

The benchmark script (`transport_benchmark.py`) measures the performance of direct transport layer communication between processes, comparing:

1. **SharedMemoryTransportPosix**: Shared memory with POSIX semaphores (one of the transports used by shm-rpc-bridge)
2. **ZeroMQ IPC**: ZeroMQ REQ/REP sockets over Unix domain sockets

The benchmark uses raw byte arrays of increasing sizes to test pure transport performance without RPC serialization overhead.

## Running the Benchmark

### Quick Start

Use the provided script to install dependencies and run the benchmark:

```bash
# From the repository root
./benchmark/transport/run_benchmark.sh
```

This script will:
- Check your Python version
- Install required dependencies (posix-ipc, pyzmq)
- Run the benchmark

### Manual Run

Alternatively, you can run it manually:

```bash
# From the repository root
pip install posix-ipc pyzmq
python benchmark/transport/transport_benchmark.py
```

The benchmark will:
1. Clean up any leftover resources
2. Run 50,000 iterations for each message size
3. Display detailed performance metrics for both transports

## Configuration

You can adjust the benchmark parameters by modifying these constants in `transport_benchmark.py`:

```python
NUM_ITERATIONS = 50_000  # Number of send/receive operations per test

MESSAGE_SIZES = {
    "small": 100,          # 100 bytes
    "medium": 10_000,      # 10KB
    "large": 500_000,      # 500KB
    "big": 2_000_000,      # 2MB
}

BUFFER_SIZE = 2_500_000   # 2.5MB buffer
TIMEOUT = 10.0            # 10 seconds timeout
```

## Metrics Reported

For each transport and message size, the following metrics are reported:

- **Total time**: Total execution time for all iterations
- **Throughput**: Operations per second (ops/s)
- **Avg latency**: Average round-trip time per call in microseconds (μs)

## Example Results
```
=======================================================================
Running benchmark (this may take several minutes)...
=======================================================================

======================================================================
Transport Layer Benchmark
======================================================================
Iterations per test: 50,000
Communication: Process-to-Process (raw byte arrays)

Cleaning up any leftover resources...
Cleanup complete.


======================================================================
Testing SMALL messages (100 bytes)
======================================================================

[1/2] Running SHM POSIX benchmark...
      Completed in 4.03 s

[2/2] Running ZeroMQ IPC benchmark...
      Completed in 13.78 s

======================================================================
Testing MEDIUM messages (10000 bytes)
======================================================================

[1/2] Running SHM POSIX benchmark...
      Completed in 4.58 s

[2/2] Running ZeroMQ IPC benchmark...
      Completed in 14.08 s

======================================================================
Testing LARGE messages (500000 bytes)
======================================================================

[1/2] Running SHM POSIX benchmark...
      Completed in 9.53 s

[2/2] Running ZeroMQ IPC benchmark...
      Completed in 37.95 s

======================================================================
Testing BIG messages (2000000 bytes)
======================================================================

[1/2] Running SHM POSIX benchmark...
      Completed in 39.08 s

[2/2] Running ZeroMQ IPC benchmark...
      Completed in 2m 7.89s


======================================================================
OVERALL SUMMARY
======================================================================

Small (100 bytes):
  SHM POSIX:   80.68 μs/call
 ZeroMQ IPC:  275.65 μs/call (241.7% slower)

Medium (10000 bytes):
  SHM POSIX:   91.58 μs/call
 ZeroMQ IPC:  281.64 μs/call (207.5% slower)

Large (500000 bytes):
  SHM POSIX:   190.64 μs/call
 ZeroMQ IPC:  758.95 μs/call (298.1% slower)

Big (2000000 bytes):
  SHM POSIX:   781.57 μs/call
 ZeroMQ IPC:  2557.78 μs/call (227.3% slower)

======================================================================

Final cleanup...
Done!

=======================================================================
Benchmark complete!
=======================================================================
```
