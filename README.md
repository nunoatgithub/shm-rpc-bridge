# SHM-RPC Bridge

A simple Python library for RPC inter-process communication using shared memory and POSIX semaphores.
Used as a testbed for comparing communication alternatives when splitting a python monolithic process into multiple processes.

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Installation

### From Source

```bash
git clone https://github.com/yourusername/shm-rpc-bridge.git
cd shm-rpc-bridge
pip install -e .
```

### Requirements

- Python 3.8 or higher
- Linux/Unix with POSIX shared memory support
- `posix-ipc` library (installed automatically)

## Quick Start

### Server Example

```python
from shm_rpc_bridge import RPCServer

# Create server
server = RPCServer("my_service")

# Register methods
def add(a: int, b: int) -> int:
    return a + b

def greet(name: str) -> str:
    return f"Hello, {name}!"

server.register("add", add)
server.register("greet", greet)

# Start serving (blocks until stopped)
server.start()
```

### Client Example

```python
from shm_rpc_bridge import RPCClient

# Connect to server
with RPCClient("my_service") as client:
    # Make RPC calls
    result = client.call("add", a=5, b=3)
    print(f"5 + 3 = {result}")  # Output: 5 + 3 = 8
    
    greeting = client.call("greet", name="Alice")
    print(greeting)  # Output: Hello, Alice!
```

## How It Works

### Architecture

```
┌─────────────┐                                  ┌─────────────┐
│   Client    │                                  │   Server    │
│  Process    │                                  │  Process    │
└──────┬──────┘                                  └──────┬──────┘
       │                                                │
       │  1. Serialize request (JSON)                   │
       │  2. Write to shared memory                     │
       │  3. Signal with semaphore                      │
       ├────────────────────────────────────────────────┤
       │           Shared Memory Region                 │
       │    ┌────────────────────────────────-─┐        │
       │    │  Request Buffer   (Client→Server)│        │
       │    │  Response Buffer  (Server→Client)│        │
       │    └─────────────────────────────────-┘        │
       ├────────────────────────────────────────────────┤
       │                                                │
       │              4. Read from shared memory        │
       │              5. Deserialize & execute          │
       │              6. Serialize result               │
       │              7. Write response                 │
       │              8. Signal completion              │
       ├────────────────────────────────────────────────┤
       │  9. Read response                              │
       │ 10. Deserialize result                         │
       └────────────────────────────────────────────────┘
```

### Key Components

1. **Shared Memory Buffers**: Two buffers (request/response) for bidirectional communication
2. **POSIX Semaphores**: Producer-consumer pattern for synchronization
3. **JSON Serialization**: Simple, flexible message encoding

## Benchmarks

Comprehensive benchmarks are included to help understand performance characteristics.

### IPC Implementation Benchmark

Comparison of direct in-memory calls vs thread-based or process-based use of this library :

```bash
./benchmark/run_benchmark.sh
```

📊 [Full benchmark details →](benchmark/)

### vs gRPC Benchmark

Comparison of this library with gRPC (Unix domain sockets and TCP/IP):

```bash
./benchmark/vs_grpc/run_benchmark.sh
```

📊 [Full benchmark details →](benchmark/vs_grpc/)

## API Reference

### Server API

```python
class RPCServer:
    def __init__(
        self,
        name: str,
        buffer_size: int = SharedMemoryTransport.DEFAULT_BUFFER_SIZE,
        timeout: float | None = None
    )
    
    def register(self, name: str, func: Callable) -> None:
        """Register a method for RPC calls."""
    
    def register_function(self, func: Callable) -> Callable:
        """Decorator to register a method."""
    
    def start(self) -> None:
        """Start the server (blocking)."""
    
    def stop(self) -> None:
        """Stop the server."""
    
    def close(self) -> None:
        """Clean up resources."""
```

### Client API

```python
class RPCClient:
    def __init__(
        self,
        name: str,
        buffer_size: int = SharedMemoryTransport.DEFAULT_BUFFER_SIZE,
        timeout: float | None = 5.0
    )
    
    def call(self, method: str, **params) -> Any:
        """Make an RPC call to the server."""
    
    def close(self) -> None:
        """Clean up resources."""
```

### Exceptions

```python
class RPCError(Exception):
    """Base exception for RPC errors."""

class RPCTimeoutError(RPCError):
    """Raised when an operation times out."""

class RPCMethodError(RPCError):
    """Raised when a remote method call fails."""

class RPCTransportError(RPCError):
    """Raised when transport layer fails."""

class RPCSerializationError(RPCError):
    """Raised when serialization/deserialization fails."""
```

## Examples

Complete working examples are provided in the [`examples/`](examples/) directory:

- **Calculator Service**: A simple calculator with add, subtract, multiply, divide operations
  - [`calculator_server.py`](examples/calculator_server.py) - Server implementation
  - [`calculator_client.py`](examples/calculator_client.py) - Client with interactive mode

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=shm_rpc_bridge --cov-report=term-missing

# Run tests across all Python versions
tox
```

### Linting and Type Checking

```bash
# Format code
ruff format src tests

# Lint code
ruff check src tests

# Type checking
mypy src
```

## Architecture Details

### Memory Layout

Each RPC channel creates two shared memory regions:

```
Request Buffer (Client → Server):
┌────────────────────────────────────────┐
│ Size (4 bytes) │ JSON Message (N bytes)│
└────────────────────────────────────────┘

Response Buffer (Server → Client):
┌────────────────────────────────────────┐
│ Size (4 bytes) │ JSON Message (N bytes)│
└────────────────────────────────────────┘
```

### Synchronization

Four POSIX semaphores per channel:
- `request_empty`: Counts empty slots in request buffer
- `request_full`: Counts full slots in request buffer
- `response_empty`: Counts empty slots in response buffer
- `response_full`: Counts full slots in response buffer

## Limitations

- **Same-host only**: Shared memory requires processes on the same machine
- **POSIX systems**: Requires POSIX semaphore support (Linux, macOS, BSD)
- **Buffer size**: Messages must fit in configured buffer (default 3MB)
- **No encryption**: Data in shared memory is not encrypted (same-host trust model)
- **Single channel**: Each client-server pair uses one channel (no connection pooling)

## Troubleshooting

### "Cannot find shared memory"

Server must be started before clients connect. Ensure server is running:

```bash
ps aux | grep your_server_script
```

### "Message too large"

Increase buffer size when creating client/server:

### Resource leaks

Run the cleanup utility:

```bash
python util/cleanup_ipc.py
```

