#!/usr/bin/env python3
"""
Benchmark script comparing orjson vs cysimdjson performance.

This script benchmarks the serialization and deserialization performance
of two JSON libraries:
- orjson: Fast, correct JSON library for Python
- cysimdjson: Python bindings for simdjson (requires exporting to dict)

The benchmarks test various data sizes to understand performance characteristics.

Requirements:
    pip install orjson cysimdjson

Usage:
    python benchmark_json_libs.py
"""

import time
from typing import Any, Callable

import orjson

try:
    import cysimdjson
except ImportError:
    print("Error: cysimdjson is not installed. Install it with: pip install cysimdjson")
    exit(1)


# ==============================================================================
# Test Data Creation
# ==============================================================================


def create_small_data() -> dict[str, Any]:
    """Create a small JSON data structure (~0.1 KB)."""
    return {
        "id": 123,
        "name": "John Doe",
        "email": "john@example.com",
        "active": True,
        "score": 95.5,
    }


def create_medium_data() -> dict[str, Any]:
    """Create a medium JSON data structure (~10 KB)."""
    return {
        "users": [
            {
                "id": i,
                "username": f"user_{i}",
                "email": f"user_{i}@example.com",
                "profile": {
                    "first_name": f"First{i}",
                    "last_name": f"Last{i}",
                    "age": 20 + (i % 50),
                    "city": ["New York", "London", "Tokyo", "Paris"][i % 4],
                },
                "preferences": {
                    "theme": "dark" if i % 2 == 0 else "light",
                    "notifications": i % 3 == 0,
                    "language": ["en", "es", "fr", "de"][i % 4],
                },
                "tags": [f"tag_{j}" for j in range(5)],
            }
            for i in range(100)
        ],
        "metadata": {
            "total": 100,
            "created_at": "2025-01-01T00:00:00Z",
            "version": "1.0",
        },
    }


def create_large_data() -> dict[str, Any]:
    """Create a large JSON data structure (~200 KB)."""
    return {
        "items_count": 1000,
        "items": [
            {
                "id": i,
                "name": f"item_{i}",
                "description": f"This is item number {i} with some descriptive text that makes it larger",
                "properties": {
                    "color": ["red", "green", "blue", "yellow", "purple"][i % 5],
                    "size": ["small", "medium", "large", "xlarge"][i % 4],
                    "price": i * 1.99,
                    "in_stock": i % 2 == 0,
                    "category": ["electronics", "clothing", "food", "toys", "books"][i % 5],
                    "weight": i * 0.5,
                    "dimensions": {
                        "length": i * 0.1,
                        "width": i * 0.2,
                        "height": i * 0.15,
                    },
                },
                "tags": [f"tag_{j}" for j in range(10)],
                "metadata": {
                    "created": "2025-01-01",
                    "updated": "2025-11-10",
                    "version": 1,
                    "author": f"author_{i % 10}",
                },
                "reviews": [
                    {
                        "rating": (j % 5) + 1,
                        "comment": f"Review {j} for item {i}",
                        "helpful": j % 3 == 0,
                    }
                    for j in range(3)
                ],
            }
            for i in range(1000)
        ],
        "summary": {
            "total_items": 1000,
            "total_value": sum(i * 1.99 for i in range(1000)),
            "categories": ["electronics", "clothing", "food", "toys", "books"],
            "avg_price": 999.5,
        },
    }


# ==============================================================================
# Benchmark Functions
# ==============================================================================


def benchmark_serialization(
    lib_name: str,
    serialize_fn: Callable[[Any], bytes],
    data: Any,
    iterations: int,
) -> tuple[float, int]:
    """
    Benchmark serialization performance.
    
    Returns:
        Tuple of (total_time_seconds, serialized_size_bytes)
    """
    # Warm-up
    for _ in range(100):
        _ = serialize_fn(data)
    
    # Actual benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        serialized = serialize_fn(data)
    end = time.perf_counter()
    
    # Get size
    size = len(serialize_fn(data))
    
    return end - start, size


def benchmark_deserialization(
    lib_name: str,
    serialize_fn: Callable[[Any], bytes],
    deserialize_fn: Callable[[bytes], Any],
    data: Any,
    iterations: int,
    convert_to_dict: bool = False,
) -> float:
    """
    Benchmark deserialization performance.
    
    Args:
        lib_name: Name of the library being tested
        serialize_fn: Function to serialize data
        deserialize_fn: Function to deserialize data
        data: Data to serialize/deserialize
        iterations: Number of iterations
        convert_to_dict: Whether to convert result to dict (for cysimdjson)
    
    Returns:
        Total time in seconds
    """
    # Serialize once
    serialized = serialize_fn(data)
    
    # Warm-up
    for _ in range(100):
        result = deserialize_fn(serialized)
        if convert_to_dict:
            # For cysimdjson, we need to export to dict to get actual Python objects
            _ = result.export()
    
    # Actual benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        result = deserialize_fn(serialized)
        if convert_to_dict:
            # For cysimdjson, we need to export to dict to get actual Python objects
            _ = result.export()
    end = time.perf_counter()
    
    return end - start


def benchmark_roundtrip(
    lib_name: str,
    serialize_fn: Callable[[Any], bytes],
    deserialize_fn: Callable[[bytes], Any],
    data: Any,
    iterations: int,
    convert_to_dict: bool = False,
) -> float:
    """
    Benchmark full serialization + deserialization roundtrip.
    
    Returns:
        Total time in seconds
    """
    # Warm-up
    for _ in range(100):
        serialized = serialize_fn(data)
        result = deserialize_fn(serialized)
        if convert_to_dict:
            _ = result.export()
    
    # Actual benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        serialized = serialize_fn(data)
        result = deserialize_fn(serialized)
        if convert_to_dict:
            _ = result.export()
    end = time.perf_counter()
    
    return end - start


# ==============================================================================
# Results Display
# ==============================================================================


def format_time(seconds: float) -> str:
    """Format time in a human-readable way."""
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.2f} μs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    else:
        return f"{seconds:.2f} s"


def format_throughput(ops_per_sec: float) -> str:
    """Format throughput in a human-readable way."""
    if ops_per_sec >= 1_000_000:
        return f"{ops_per_sec / 1_000_000:.2f} M ops/s"
    elif ops_per_sec >= 1_000:
        return f"{ops_per_sec / 1_000:.2f} K ops/s"
    else:
        return f"{ops_per_sec:.2f} ops/s"


def format_size(size_bytes: int) -> str:
    """Format size in a human-readable way."""
    if size_bytes >= 1_048_576:  # 1 MB
        return f"{size_bytes / 1_048_576:.2f} MB"
    elif size_bytes >= 1_024:  # 1 KB
        return f"{size_bytes / 1_024:.2f} KB"
    else:
        return f"{size_bytes} B"


def print_benchmark_result(
    name: str,
    orjson_time: float,
    cysimdjson_time: float,
    iterations: int,
    size: int = None,
) -> None:
    """Print benchmark results comparing two libraries."""
    print(f"\n{name}")
    print("=" * 80)
    
    if size:
        print(f"  Data size:        {format_size(size)}")
    
    # orjson results
    orjson_ops = iterations / orjson_time
    orjson_latency = (orjson_time / iterations) * 1_000_000
    print(f"\n  orjson:")
    print(f"    Total time:     {format_time(orjson_time)}")
    print(f"    Throughput:     {format_throughput(orjson_ops)}")
    print(f"    Avg latency:    {orjson_latency:.2f} μs/op")
    
    # cysimdjson results
    cysimdjson_ops = iterations / cysimdjson_time
    cysimdjson_latency = (cysimdjson_time / iterations) * 1_000_000
    print(f"\n  cysimdjson (with dict export):")
    print(f"    Total time:     {format_time(cysimdjson_time)}")
    print(f"    Throughput:     {format_throughput(cysimdjson_ops)}")
    print(f"    Avg latency:    {cysimdjson_latency:.2f} μs/op")
    
    # Comparison
    speedup = orjson_time / cysimdjson_time
    if speedup > 1:
        print(f"\n  Winner:           cysimdjson is {speedup:.2f}x faster")
    elif speedup < 1:
        print(f"\n  Winner:           orjson is {1/speedup:.2f}x faster")
    else:
        print(f"\n  Result:           Both libraries are equally fast")


# ==============================================================================
# Main Benchmark
# ==============================================================================


def main() -> None:
    """Run all benchmarks."""
    print("=" * 80)
    print("JSON Libraries Benchmark: orjson vs cysimdjson")
    print("=" * 80)
    print("\nNote: cysimdjson benchmarks include the cost of exporting to dict")
    print("      (as required for practical use in Python)\n")
    
    # Initialize parsers
    parser = cysimdjson.JSONParser()
    
    # Define serialization/deserialization functions
    orjson_serialize = lambda data: orjson.dumps(data)
    orjson_deserialize = lambda data: orjson.loads(data)
    
    cysimdjson_serialize = lambda data: orjson.dumps(data)  # Use orjson for serialization
    cysimdjson_deserialize = lambda data: parser.parse(data)
    
    # Test data
    test_cases = [
        ("Small Data (~0.1 KB)", create_small_data(), 100_000),
        ("Medium Data (~10 KB)", create_medium_data(), 10_000),
        ("Large Data (~200 KB)", create_large_data(), 1_000),
    ]
    
    for test_name, test_data, iterations in test_cases:
        print("\n" + "=" * 80)
        print(f"Test: {test_name}")
        print("=" * 80)
        print(f"Iterations: {iterations:,}")
        
        # Serialization benchmark
        print(f"\n[1/3] Benchmarking serialization...")
        orjson_ser_time, data_size = benchmark_serialization(
            "orjson", orjson_serialize, test_data, iterations
        )
        cysimdjson_ser_time, _ = benchmark_serialization(
            "cysimdjson", cysimdjson_serialize, test_data, iterations
        )
        print_benchmark_result(
            f"Serialization - {test_name}",
            orjson_ser_time,
            cysimdjson_ser_time,
            iterations,
            data_size,
        )
        
        # Deserialization benchmark
        print(f"\n[2/3] Benchmarking deserialization...")
        orjson_deser_time = benchmark_deserialization(
            "orjson",
            orjson_serialize,
            orjson_deserialize,
            test_data,
            iterations,
            convert_to_dict=False,
        )
        cysimdjson_deser_time = benchmark_deserialization(
            "cysimdjson",
            cysimdjson_serialize,
            cysimdjson_deserialize,
            test_data,
            iterations,
            convert_to_dict=True,  # cysimdjson needs dict export
        )
        print_benchmark_result(
            f"Deserialization - {test_name}",
            orjson_deser_time,
            cysimdjson_deser_time,
            iterations,
            data_size,
        )
        
        # Roundtrip benchmark
        print(f"\n[3/3] Benchmarking roundtrip (serialize + deserialize)...")
        orjson_roundtrip_time = benchmark_roundtrip(
            "orjson",
            orjson_serialize,
            orjson_deserialize,
            test_data,
            iterations,
            convert_to_dict=False,
        )
        cysimdjson_roundtrip_time = benchmark_roundtrip(
            "cysimdjson",
            cysimdjson_serialize,
            cysimdjson_deserialize,
            test_data,
            iterations,
            convert_to_dict=True,  # cysimdjson needs dict export
        )
        print_benchmark_result(
            f"Roundtrip - {test_name}",
            orjson_roundtrip_time,
            cysimdjson_roundtrip_time,
            iterations,
            data_size,
        )
    
    # Final summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\nKey Observations:")
    print("  • orjson uses native serialization/deserialization")
    print("  • cysimdjson benchmarks include dict export overhead")
    print("  • cysimdjson may show advantages in pure parsing speed")
    print("  • orjson provides a complete solution with fast serialization")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
