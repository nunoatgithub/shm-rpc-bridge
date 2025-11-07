# SHM-RPC Bridge Benchmarks

This directory contains performance benchmarks comparing the SHM-RPC bridge implementation against baseline direct in-memory function calls.

## Overview

The benchmark script (`benchmark_ipc.py`) measures the performance overhead of using shared memory IPC for RPC communication in two scenarios:

1. **Small Messages**: Simple integer operations (addition)
2. **Large Messages**: Complex nested data structures (~31KB JSON)

Each scenario is tested with three different execution contexts:
- **Direct**: In-process function calls (baseline, no IPC overhead)
- **Threads**: RPC between threads using shared memory
- **Processes**: RPC between processes using shared memory

## Running the Benchmark

### Quick Start

Use the provided script to install dependencies and run the benchmark:

```bash
# From the repository root
./benchmark/run_benchmark.sh
```

This script will:
- Check your Python version
- Install required dependencies (posix-ipc)
- Clean up any leftover resources
- Run the benchmark
- Display results

### Manual Run

Alternatively, you can run it manually:

```bash
# From the repository root
pip install posix-ipc
python benchmark/benchmark_ipc.py
```

The benchmark will:
1. Clean up any leftover shared memory resources
2. Run 100,000 iterations for small messages
3. Run 10,000 iterations for large messages
4. Display detailed performance metrics
5. Clean up all resources when complete

## Configuration

You can adjust the iteration counts by modifying these constants in `benchmark_ipc.py`:

```python
NUM_ITERATIONS = 100_000        # Small message iterations
NUM_ITERATIONS_LARGE = 10_000   # Large message iterations
```

## Metrics Reported

For each benchmark, the following metrics are reported:

- **Total time**: Total execution time
- **Throughput**: Operations per second (ops/s)
- **Avg latency**: Average time per call in microseconds (μs)
- **vs Baseline**: Overhead compared to direct calls (when applicable)

## Example Results

Here's an example run on a typical development machine:

```
=======================================================================
SHM-RPC Bridge Benchmark Runner
=======================================================================

Python version: 3.8.20

Installing dependencies...
---
✓ posix-ipc installed

Cleaning up any leftover shared memory resources...
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
Running benchmark (this may take several minutes)...
=======================================================================

Cleaning up any leftover resources...
======================================================================
RPC Implementation Benchmark
======================================================================
Small message iterations: 100,000
Large message iterations: 10,000

Warming up...
Warm-up complete.

======================================================================
PART 1: Small Message Benchmarks (Simple Integer Operations)
======================================================================

[1/3] Running baseline benchmark (direct calls)...

Benchmark 1: Direct Object Calls (Baseline)
======================================================================
  Total time:       11.91 ms
  Throughput:       8.40 M ops/s
  Avg latency:      0.12 μs/call

[2/3] Running thread benchmark (SHM-RPC between threads)...

Benchmark 2: SHM-RPC Between Threads
======================================================================
  Total time:       6.44 s
  Throughput:       15.52 K ops/s
  Avg latency:      64.42 μs/call
  vs Baseline:      540.93x slower (+53993.3% overhead)

[3/3] Running process benchmark (SHM-RPC between processes)...

Benchmark 3: SHM-RPC Between Processes
======================================================================
  Total time:       6.27 s
  Throughput:       15.94 K ops/s
  Avg latency:      62.74 μs/call
  vs Baseline:      526.77x slower (+52576.9% overhead)

======================================================================
Small Message Summary
======================================================================
  Direct calls:     11.91 ms (baseline)
  Threads:          6.44 s (540.93x)
  Processes:        6.27 s (526.77x)

  Thread vs Process: 1.03x
    → Processes are 1.03x faster


======================================================================
PART 2: Large Message Benchmarks (Complex Data Structures)
======================================================================
Message size: ~31.1 KB (serialized JSON)


[1/3] Running baseline benchmark (direct calls with large data)...

Benchmark 4: Direct Calls (Large Messages Baseline)
======================================================================
  Total time:       3.34 s
  Throughput:       3.00 K ops/s
  Avg latency:      333.59 μs/call

[2/3] Running thread benchmark (SHM-RPC with large messages)...

Benchmark 5: SHM-RPC Threads (Large Messages)
======================================================================
  Total time:       19.19 s
  Throughput:       521.21 ops/s
  Avg latency:      1918.62 μs/call
  vs Baseline:      5.75x slower (+475.1% overhead)

[3/3] Running process benchmark (SHM-RPC with large messages)...

Benchmark 6: SHM-RPC Processes (Large Messages)
======================================================================
  Total time:       19.25 s
  Throughput:       519.47 ops/s
  Avg latency:      1925.02 μs/call
  vs Baseline:      5.77x slower (+477.1% overhead)

======================================================================
Large Message Summary
======================================================================
  Direct calls:     3.34 s (baseline)
  Threads:          19.19 s (5.75x)
  Processes:        19.25 s (5.77x)

  Thread vs Process: 1.00x
    → Threads are 1.00x faster


======================================================================
OVERALL SUMMARY
======================================================================

Small Messages (integers):
  Direct:    11.91 ms
  Threads:   6.44 s (540.9x overhead)
  Processes: 6.27 s (526.8x overhead)

Large Messages (~31.1 KB):
  Direct:    3.34 s
  Threads:   19.19 s (5.8x overhead)
  Processes: 19.25 s (5.8x overhead)

======================================================================

Cleaning up resources...
Cleanup complete.

=======================================================================
Benchmark complete!
=======================================================================
=======================================================================
SHM-RPC Bridge Benchmark Runner
=======================================================================

Python version: 3.8.20

Installing dependencies...
---
✓ posix-ipc installed

Cleaning up any leftover shared memory resources...
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
Running benchmark (this may take several minutes)...
=======================================================================

Cleaning up any leftover resources...
======================================================================
RPC Implementation Benchmark
======================================================================
Small message iterations: 100,000
Large message iterations: 10,000

Warming up...
Warm-up complete.

======================================================================
PART 1: Small Message Benchmarks (Simple Integer Operations)
======================================================================

[1/3] Running baseline benchmark (direct calls)...

Benchmark 1: Direct Object Calls (Baseline)
======================================================================
  Total time:       11.89 ms
  Throughput:       8.41 M ops/s
  Avg latency:      0.12 μs/call

[2/3] Running thread benchmark (SHM-RPC between threads)...

Benchmark 2: SHM-RPC Between Threads
======================================================================
  Total time:       5.98 s
  Throughput:       16.72 K ops/s
  Avg latency:      59.80 μs/call
  vs Baseline:      502.94x slower (+50193.8% overhead)

[3/3] Running process benchmark (SHM-RPC between processes)...

Benchmark 3: SHM-RPC Between Processes
======================================================================
  Total time:       5.44 s
  Throughput:       18.38 K ops/s
  Avg latency:      54.40 μs/call
  vs Baseline:      457.52x slower (+45651.6% overhead)

======================================================================
Small Message Summary
======================================================================
  Direct calls:     11.89 ms (baseline)
  Threads:          5.98 s (502.94x)
  Processes:        5.44 s (457.52x)


======================================================================
PART 2: Large Message Benchmarks (Complex Data Structures)
======================================================================
Message size: ~31.1 KB (serialized JSON)


[1/3] Running baseline benchmark (direct calls with large data)...

Benchmark 4: Direct Calls (Large Messages Baseline)
======================================================================
  Total time:       3.14 s
  Throughput:       3.18 K ops/s
  Avg latency:      314.00 μs/call

[2/3] Running thread benchmark (SHM-RPC with large messages)...

Benchmark 5: SHM-RPC Threads (Large Messages)
======================================================================
  Total time:       19.27 s
  Throughput:       519.02 ops/s
  Avg latency:      1926.69 μs/call
  vs Baseline:      6.14x slower (+513.6% overhead)

[3/3] Running process benchmark (SHM-RPC with large messages)...

Benchmark 6: SHM-RPC Processes (Large Messages)
======================================================================
  Total time:       18.74 s
  Throughput:       533.72 ops/s
  Avg latency:      1873.63 μs/call
  vs Baseline:      5.97x slower (+496.7% overhead)

======================================================================
Large Message Summary
======================================================================
  Direct calls:     3.14 s (baseline)
  Threads:          19.27 s (6.14x)
  Processes:        18.74 s (5.97x)


======================================================================
OVERALL SUMMARY
======================================================================

Small Messages (integers):
  Direct:    11.89 ms
  Threads:   5.98 s (502.9x overhead)
  Processes: 5.44 s (457.5x overhead)

Large Messages (~31.1 KB):
  Direct:    3.14 s
  Threads:   19.27 s (6.1x overhead)
  Processes: 18.74 s (6.0x overhead)

======================================================================

```

## Troubleshooting

### Resource Leaks

If you see warnings about leaked shared memory objects:

```bash
# Clean up manually
python util/cleanup_ipc.py
```

### Performance Variability

Benchmark results can vary based on:
- System load
- CPU frequency scaling
- Memory pressure
- OS scheduler behavior

Run the benchmark multiple times and look at average values for more reliable results.

## Related Files

- `../util/cleanup_ipc.py` - Manual cleanup utility for shared memory resources
- `../examples/` - Example client/server implementations
- `../tests/` - Unit and integration tests

