# SHM-RPC Bridge Benchmarks

This directory contains performance benchmarks comparing the SHM-RPC bridge implementation against baseline direct in-memory function calls.

## Overview

The benchmark script (`benchmark_ipc.py`) measures the performance overhead of using shared memory IPC for RPC communication in two scenarios:

1. **Small Messages**: Simple integer operations (addition)
2. **Large Messages**: Complex nested data structures 

Each scenario is tested with two execution contexts:
- **Direct**: In-process function calls (baseline, no IPC overhead)
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
- Install required dependencies (posix-ipc, orjson)
- Run the benchmark

### Manual Run

Alternatively, you can run it manually:

```bash
# From the repository root
pip install posix-ipc orjson
python benchmark/benchmark_ipc.py
```

The benchmark will:
1. Clean up any leftover shared memory resources
2. Run NUM_ITERATIONS iterations for small messages
3. Run NUM_ITERATIONS_LARGE iterations for large messages
4. Display detailed performance metrics

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

[1/2] Running baseline benchmark (direct calls)...

Benchmark 1: Direct Object Calls (Baseline)
======================================================================
  Total time:       10.82 ms
  Throughput:       9.24 M ops/s
  Avg latency:      0.11 μs/call

[2/2] Running SHM-RPC benchmark (SHM-RPC between processes)...

Benchmark 2: SHM-RPC Between Processes
======================================================================
  Total time:       10.36 s
  Throughput:       9.65 K ops/s
  Avg latency:      103.59 μs/call

======================================================================
Small Message Summary
======================================================================
  Direct calls:     10.82 ms (baseline)
       SHM-RPC:     10.36 s (957.20x)


======================================================================
PART 2: Large Message Benchmarks (Complex Data Structures)
======================================================================
Message size: ~313.9 KB (serialized JSON)


[1/2] Running baseline benchmark (direct calls with large data)...

Benchmark 3: Direct Calls (Large Messages Baseline)
======================================================================
  Total time:       30.17 s
  Throughput:       331.50 ops/s
  Avg latency:      3016.56 μs/call

[2/2] Running SHM-RPC benchmark (SHM-RPC with large messages)...

Benchmark 4: SHM-RPC Processes (Large Messages)
======================================================================
  Total time:       1m 18.28s
  Throughput:       127.75 ops/s
  Avg latency:      7828.09 μs/call

======================================================================
Large Message Summary
======================================================================
  Direct calls:     30.17 s (baseline)
       SHM-RPC:     1m 18.28s (2.60x)


======================================================================
OVERALL SUMMARY
======================================================================

Small Messages (integers):
  Direct:    10.82 ms
 SHM-RPC:    10.36 s (957.2x overhead)

Large Messages (~313.9 KB):
  Direct:    30.17 s
 SHM-RPC:    1m 18.28s (2.6x overhead)

======================================================================

Cleaning up resources...
Cleanup complete.

=======================================================================
Benchmark complete!
=======================================================================
```
## Troubleshooting

### Resource Leaks

If you see warnings about leaked shared memory objects:

```bash
# Clean up manually
python util/cleanup_ipc.py
```
