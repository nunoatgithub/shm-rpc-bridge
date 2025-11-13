# SHM-RPC Bridge

A simple Python library for RPC inter-process communication using shared memory and POSIX semaphores.

Note: I used it as a testbed for comparing communication alternatives when splitting a python monolithic process into multiple processes.

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Installation

### From Source

```bash
# Clone and enter repo
git clone https://github.com/nunoatgithub/shm-rpc-bridge.git
cd shm-rpc-bridge

# Option A: pip editable install (simple)
pip install -e .

# Option B: create a conda env from `environment.yml` (calls pip install)
conda env create -f `environment.yml` -n shm-rpc-bridge
conda activate shm-rpc-bridge
```

### Requirements

- Python 3.8 or higher
- Linux/Unix with POSIX shared memory support
- `posix-ipc` library (installed automatically)
- `orjson` library (installed automatically)

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

1. **POSIX Shared Memory Buffers**: Two buffers (request/response) for bidirectional communication
2. **POSIX Semaphores**: Producer-consumer pattern for synchronization
3. **JSON Serialization**: Simple, flexible message encoding

## Benchmarks

Some benchmarks are included to help understand performance characteristics.

### IPC Implementation Benchmark

Comparison of direct in-memory calls vs this library :

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
- **Accumulator Service**: A stateful accumulator that maintains a running total per client

## Development

### Running Tests, Linting and Type Checking

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
ruff format src tests

# Lint code
ruff check src tests

# Type checking
mypy src

# All of the above in one go, for versions 3.8+ (provided they are installed in the system)
tox
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
- **Buffer size**: Messages must fit in configured buffer
- **No encryption**: Data in shared memory is not encrypted (same-host trust model)
- **Single channel**: Each client-server pair uses one channel (no connection pooling)
- **No threading**: The server registers signal handlers that automate the deletion of resources on SIGTERM and SIGINT. 
Due to Python's known limitation about registering signal handlers in threads, the server cannot be spawned in threads, only processes.
- **Synchronous only**: Can't leverage async I/O

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

