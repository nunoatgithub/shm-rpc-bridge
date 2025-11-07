# SHM-RPC Bridge Benchmarks

This directory contains performance benchmarks comparing the SHM-RPC bridge implementation against baseline direct function calls.

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
  Total time:       10.14 ms
  Throughput:       9.86 M ops/s
  Avg latency:      0.10 μs/call

[2/3] Running thread benchmark (SHM-RPC between threads)...

Benchmark 2: SHM-RPC Between Threads
======================================================================
  Total time:       13.15 s
  Throughput:       7.61 K ops/s
  Avg latency:      131.48 μs/call
  vs Baseline:      1296.40x slower (+129540.0% overhead)

[3/3] Running process benchmark (SHM-RPC between processes)...

Benchmark 3: SHM-RPC Between Processes
======================================================================
  Total time:       13.72 s
  Throughput:       7.29 K ops/s
  Avg latency:      137.19 μs/call
  vs Baseline:      1352.66x slower (+135166.5% overhead)

======================================================================
Small Message Summary
======================================================================
  Direct calls:     10.14 ms (baseline)
  Threads:          13.15 s (1296.40x)
  Processes:        13.72 s (1352.66x)

  Thread vs Process: 0.96x
    → Threads are 1.04x faster

======================================================================
PART 2: Large Message Benchmarks (Complex Data Structures)
======================================================================
Message size: ~31.1 KB (serialized JSON)

[1/3] Running baseline benchmark (direct calls with large data)...

Benchmark 4: Direct Calls (Large Messages Baseline)
======================================================================
  Total time:       3.03 s
  Throughput:       3.30 K ops/s
  Avg latency:      302.91 μs/call

[2/3] Running thread benchmark (SHM-RPC with large messages)...

Benchmark 5: SHM-RPC Threads (Large Messages)
======================================================================
  Total time:       19.58 s
  Throughput:       510.65 ops/s
  Avg latency:      1958.28 μs/call
  vs Baseline:      6.46x slower (+546.5% overhead)

[3/3] Running process benchmark (SHM-RPC with large messages)...

Benchmark 6: SHM-RPC Processes (Large Messages)
======================================================================
  Total time:       18.12 s
  Throughput:       551.98 ops/s
  Avg latency:      1811.67 μs/call
  vs Baseline:      5.98x slower (+498.1% overhead)

======================================================================
Large Message Summary
======================================================================
  Direct calls:     3.03 s (baseline)
  Threads:          19.58 s (6.46x)
  Processes:        18.12 s (5.98x)

  Thread vs Process: 1.08x
    → Processes are 1.08x faster

======================================================================
OVERALL SUMMARY
======================================================================

Small Messages (integers):
  Direct:    10.14 ms
  Threads:   13.15 s (1296.4x overhead)
  Processes: 13.72 s (1352.7x overhead)

Large Messages (~31.1 KB):
  Direct:    3.03 s
  Threads:   19.58 s (6.5x overhead)
  Processes: 18.12 s (6.0x overhead)

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

