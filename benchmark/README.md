# SHM-RPC Bridge Benchmarks

This directory contains performance benchmarks comparing the SHM-RPC bridge implementation against baseline direct in-memory function calls.

## Overview

The benchmark script (`benchmark_ipc.py`) measures the performance overhead of using shared memory IPC for RPC communication in two scenarios:

1. **Small Messages**: Simple integer operations (addition)
2. **Large Messages**: Complex nested data structures 

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

```
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
  Total time:       16.32 ms
  Throughput:       6.13 M ops/s
  Avg latency:      0.16 μs/call

[2/3] Running thread benchmark (SHM-RPC between threads)...

Benchmark 2: SHM-RPC Between Threads
======================================================================
  Total time:       3.62 s
  Throughput:       27.63 K ops/s
  Avg latency:      36.19 μs/call
  vs Baseline:      221.76x slower (+22076.0% overhead)

[3/3] Running process benchmark (SHM-RPC between processes)...

Benchmark 3: SHM-RPC Between Processes
======================================================================
  Total time:       3.40 s
  Throughput:       29.44 K ops/s
  Avg latency:      33.97 μs/call
  vs Baseline:      208.13x slower (+20713.2% overhead)

======================================================================
Small Message Summary
======================================================================
  Direct calls:     16.32 ms (baseline)
  Threads:          3.62 s (221.76x)
  Processes:        3.40 s (208.13x)


======================================================================
PART 2: Large Message Benchmarks (Complex Data Structures)
======================================================================
Message size: ~313.9 KB (serialized JSON)


[1/3] Running baseline benchmark (direct calls with large data)...

Benchmark 4: Direct Calls (Large Messages Baseline)
======================================================================
  Total time:       32.05 s
  Throughput:       312.06 ops/s
  Avg latency:      3204.56 μs/call

[2/3] Running thread benchmark (SHM-RPC with large messages)...

Benchmark 5: SHM-RPC Threads (Large Messages)
======================================================================
  Total time:       1m 26.29s
  Throughput:       115.89 ops/s
  Avg latency:      8629.03 μs/call
  vs Baseline:      2.69x slower (+169.3% overhead)

[3/3] Running process benchmark (SHM-RPC with large messages)...

Benchmark 6: SHM-RPC Processes (Large Messages)
======================================================================
  Total time:       1m 24.46s
  Throughput:       118.40 ops/s
  Avg latency:      8446.17 μs/call
  vs Baseline:      2.64x slower (+163.6% overhead)

======================================================================
Large Message Summary
======================================================================
  Direct calls:     32.05 s (baseline)
  Threads:          1m 26.29s (2.69x)
  Processes:        1m 24.46s (2.64x)


======================================================================
OVERALL SUMMARY
======================================================================

Small Messages (integers):
  Direct:    16.32 ms
  Threads:   3.62 s (221.8x overhead)
  Processes: 3.40 s (208.1x overhead)

Large Messages (~313.9 KB):
  Direct:    32.05 s
  Threads:   1m 26.29s (2.7x overhead)
  Processes: 1m 24.46s (2.6x overhead)

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

