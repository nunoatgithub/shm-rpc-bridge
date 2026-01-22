# SHM-RPC Bridge

A simple Python library for RPC inter-process communication using shared memory and POSIX semaphores.

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Installation

```bash
pip install shm-rpc-bridge
```

### From Source

```bash
# Clone and enter repo
git clone https://github.com/nunoatgithub/shm-rpc-bridge.git
cd shm-rpc-bridge

# Option A: pip editable install (simple)
pip install -e .

# Option B: create a conda env from `environment.yml` (calls pip install)
conda env create -f environment.yml
conda activate shm-rpc-bridge
```

#### Futexes on Linux

On Linux, instead of POSIX semaphores, futexes can be used. However, they offer no measurable benefit to this library in
terms of performance or stability and may actually be less stable. Use with caution; the code base toggles to this mode
automatically when constructed with

```bash
USE_FUTEX=1 pip install -e .
```

### Requirements

- Python 3.8 or higher
- Linux/MacOS/BSD with POSIX shared memory and semaphore support
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
3. **JSON Serialization**: Given the generic nature of the RPC contract proposed by this API, json (with orjson) is the
   absolute best possible. I tested most of the alternatives (e.g.protobuf, capnproto, cysimdjson), but the presence
   of generic blobs in the request and response always forces a generic form of serialization before serializing the root 
   object, so unless you use json for the entire structure, it's always json + other proto on top => slower. 
   If you consider other more specialized RPC contracts, a fork from this repo with a quicker data layer would 
   certainly make sense. 
4. **Using only the transport layer**: Given the limitations of json as a serialization mechanism in python, it is
   possible to bypass the RPC layer and directly use the byte-based transport layer underneath it !
   This gives you a safe byte-based shared memory pipe API between two processes !

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
            timeout: float = SharedMemoryTransport.DEFAULT_TIMEOUT,
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
            timeout: float = SharedMemoryTransport.DEFAULT_TIMEOUT,
            wait_for_server: float = 0
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

### Direct usage of the Transport API
See the definition in *shm_rpc_bridge.transport.transport.py*.

Use the *client.py* and *server.py* as inspiration for how to use it. The tests can help too.

## Examples

Complete working examples are provided in the [`examples/`](examples/) directory:

- **Calculator Service**: A simple calculator with add, subtract, multiply, divide operations
- **Accumulator Service**: A stateful accumulator that maintains a running total per client

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
  Due to Python's known limitation about registering signal handlers in threads, the server cannot be spawned in
  threads, only processes.
- **Synchronous only**: Can't leverage async I/O

## Troubleshooting

### "Cannot find shared memory"

Server must be started before clients connect. Ensure server is running:

### "Message too large"

Increase buffer size when creating client/server:

### Resource leaks

Run the [cleanup](util/README.md) utility.

## Logging

The library uses Python's standard `logging` module. Logs by default at WARNING level.

To change logging level :
```bash
export SHM_RPC_BRIDGE_LOG_LEVEL=DEBUG
```
To change more things than just the level :
```python
import logging

import shm_rpc_bridge
# now override, AFTER import

# Enable debug logging
logging.getLogger("shm_rpc_bridge").setLevel(logging.DEBUG)

# Or configure with a handler for file output
handler = logging.FileHandler("shm_rpc_bridge.log")
handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(process)d - %(name)s - %(levelname)s : %(message)s"
))
logging.getLogger("shm_rpc_bridge").addHandler(handler)
```

## Development

### Install development dependencies
```bash
pip install -e ".[dev]"
```

### Other Dependencies

In addition to Python dependencies, workflow validation requires `act`, a tool to run GitHub Actions locally. 
This is is NOT a Python package and cannot be installed via `pip` or listed in `pyproject.toml`. Each developer must install it separately on their system.

See https://nektosact.com/installation/

### Multi-OS Testing and CI

The project supports Python versions 3.8 through 3.13 on Linux and macOS. The Linux implementation has two transport variants: POSIX-based and futex-based.

#### Automated CI

**Workflow:** `.github/workflows/ci.yml`

The CI runs automatically on every push to `master` and tests all Python versions (3.8-3.13) on both `ubuntu-latest` and `macos-latest`.

**Jobs:**
- `test`: Runs pytest across all OS/Python combinations
- `lint`: Runs ruff linting once (Python 3.8, Linux only)
- `type-check`: Runs mypy type checking once (Python 3.8, Linux only)

#### Testing on Branches (Manual Trigger)

For feature branch development, you can manually trigger CI with filters:

1. Push your branch: `git push origin my-feature`
2. Go to GitHub → Actions → "CI" → "Run workflow"
3. Select your branch from dropdown
4. Choose filters:
   - **OS**: `all`, `ubuntu-latest`, or `macos-latest`
   - **Python version**: `all` or specific version (3.8-3.13)
   - **Debug**: Enable SSH access via tmate for interactive debugging
5. Click "Run workflow"

This allows you to:
- Test support for a different operating system than yours
- Test specific OS/Python combinations without running the full matrix
- Debug issues interactively by SSH-ing into the runner

**Tip:** Use `git commit --amend` + `git push --force` to iterate on your branch without polluting commit history.

#### Why Not Docker for macOS?

macOS cannot legally or technically be containerized on non-Apple hardware due to licensing restrictions. The only way to validate macOS support is:

1. **CI with macOS runners** (GitHub Actions runs on actual Apple hardware)
2. **Local macOS machine** (your own Mac or cloud macOS VM)

#### Development Workflow for macOS Support

Since you can't run macOS in Docker on Linux:

1. **Develop locally** on Linux, run Linux tests (both POSIX and futex variants if desired)
2. **Push to a branch** and manually trigger CI with macOS filter
3. **Check GitHub Actions** for macOS job results
4. **Iterate** based on macOS logs if issues arise

The CI tests both Linux transport variants (POSIX and futex) as well as the macOS POSIX implementation.

#### Quick Reference

| Task                         | Command                                           |
|------------------------------|---------------------------------------------------|
| Run all tests locally        | `pytest`                                          |
| Test single Python version   | `tox -e py38` (or py39, py310, etc.)              |
| Lint code                    | `tox -e lint`                                     |
| Type check                   | `tox -e type`                                     |
| Format code                  | `tox -e format`                                   |
| Validate CI workflows        | `tox -e workflow`                               |
| Run full test matrix locally | `tox`                                             |
| Test on macOS (from Linux)   | Push branch → manually trigger CI with macOS filter |
| Test on Linux (from macOS)   | Push branch → manually trigger CI with Linux filter |

**For detailed CI usage, debugging tips, and workflow examples, see** [`.github/workflows/README.md`](.github/workflows/README.md)

