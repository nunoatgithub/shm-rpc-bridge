# Utilities
## cleanup_ipc.py
Cleans up leftover POSIX IPC resources (shared memory and semaphores).
### Usage
```bash
# List resources
python util/cleanup_ipc.py --list
# Clean up all resources
python util/cleanup_ipc.py
# Dry-run
python util/cleanup_ipc.py --dry-run
# Clean specific prefix only
python util/cleanup_ipc.py --prefix calculator_rpc
```
Use this when servers/clients crash and leave resources behind.
