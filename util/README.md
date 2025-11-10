# Utilities

## cleanup_ipc.py

Cleans up leftover POSIX IPC resources (shared memory and semaphores) from `/dev/shm/`.

### What It Does

On Linux, both POSIX shared memory and semaphores are stored as files in `/dev/shm/`:
- **Shared Memory Segments**: Regular files (e.g., `test_sequential_request`)
- **POSIX Semaphores**: Files with `sem.` prefix (e.g., `sem.test_sequential_req_full`)

This utility lists and removes these resources when they're left behind after crashes.

### Usage

```bash
# List all IPC resources
python util/cleanup_ipc.py --list

# Clean up all resources (with confirmation)
python util/cleanup_ipc.py

# Preview what would be deleted without actually deleting
python util/cleanup_ipc.py --dry-run

# Clean only resources matching a specific prefix
python util/cleanup_ipc.py --prefix calculator_rpc
python util/cleanup_ipc.py --list --prefix test_sequential
```

### When to Use

Use this utility when:
- Tests crash or are interrupted before cleanup
- Server/client processes terminate unexpectedly
- You see "file exists" errors when creating new IPC resources
- You want to verify what IPC resources are currently in use
