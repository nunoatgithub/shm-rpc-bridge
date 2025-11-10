#!/usr/bin/env python3
"""
Cleanup utility for POSIX IPC resources.

This script removes all shared memory segments and semaphores created by
the shm-rpc-bridge library that may have been left behind due to crashes
or improper shutdown.

Usage:
    python util/cleanup_ipc.py [--dry-run] [--prefix PREFIX]

Options:
    --dry-run       Show what would be deleted without actually deleting
    --prefix        Only delete resources with this prefix (default: all)
    -h, --help      Show this help message
"""

import argparse
import os
import sys

try:
    import posix_ipc
except ImportError:
    print("ERROR: posix_ipc module not found. Install it with: pip install posix-ipc")
    sys.exit(1)


def list_shared_memory():
    """
    List all POSIX shared memory segments (excluding semaphores).

    Returns:
        List of shared memory segment names
    """
    shm_list = []
    shm_dir = "/dev/shm"

    if os.path.exists(shm_dir):
        try:
            for name in os.listdir(shm_dir):
                # Skip directories, semaphores (sem. prefix), and non-IPC files
                path = os.path.join(shm_dir, name)
                if os.path.isfile(path) and not name.startswith("sem."):
                    # POSIX shared memory names start with /
                    shm_list.append(f"/{name}")
        except PermissionError:
            print(f"WARNING: Permission denied accessing {shm_dir}")

    return shm_list


def list_semaphores():
    """
    List all POSIX semaphores.

    Returns:
        List of semaphore names
    """
    sem_list = []
    sem_dir = "/dev/shm"

    if os.path.exists(sem_dir):
        try:
            for name in os.listdir(sem_dir):
                path = os.path.join(sem_dir, name)
                # Semaphores are also in /dev/shm but have different characteristics
                if os.path.isfile(path) and name.startswith("sem."):
                    # Extract the actual semaphore name (remove sem. prefix)
                    sem_name = f"/{name[4:]}"
                    sem_list.append(sem_name)
        except PermissionError:
            print(f"WARNING: Permission denied accessing {sem_dir}")

    return sem_list


def cleanup_shared_memory(prefix=None, dry_run=False):
    """
    Remove shared memory segments.

    Args:
        prefix: Only remove segments with this prefix
        dry_run: If True, only print what would be removed

    Returns:
        Tuple of (removed_count, failed_count)
    """
    shm_list = list_shared_memory()
    removed = 0
    failed = 0

    for shm_name in shm_list:
        # Filter by prefix if specified
        if prefix and not shm_name[1:].startswith(prefix):
            continue

        if dry_run:
            print(f"[DRY-RUN] Would remove shared memory: {shm_name}")
            removed += 1
        else:
            try:
                posix_ipc.unlink_shared_memory(shm_name)
                print(f"✓ Removed shared memory: {shm_name}")
                removed += 1
            except posix_ipc.ExistentialError:
                # Already deleted or doesn't exist
                pass
            except Exception as e:
                print(f"✗ Failed to remove shared memory {shm_name}: {e}")
                failed += 1

    return removed, failed


def cleanup_semaphores(prefix=None, dry_run=False):
    """
    Remove POSIX semaphores.

    Args:
        prefix: Only remove semaphores with this prefix
        dry_run: If True, only print what would be removed

    Returns:
        Tuple of (removed_count, failed_count)
    """
    sem_list = list_semaphores()
    removed = 0
    failed = 0

    for sem_name in sem_list:
        # Filter by prefix if specified
        if prefix and not sem_name[1:].startswith(prefix):
            continue

        if dry_run:
            print(f"[DRY-RUN] Would remove semaphore: {sem_name}")
            removed += 1
        else:
            try:
                posix_ipc.unlink_semaphore(sem_name)
                print(f"✓ Removed semaphore: {sem_name}")
                removed += 1
            except posix_ipc.ExistentialError:
                # Already deleted or doesn't exist
                pass
            except Exception as e:
                print(f"✗ Failed to remove semaphore {sem_name}: {e}")
                failed += 1

    return removed, failed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cleanup POSIX IPC resources (shared memory and semaphores)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default=None,
        help="Only delete resources with this prefix (e.g., 'calculator_rpc')",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Just list resources without deleting",
    )

    args = parser.parse_args()

    # List mode
    if args.list:
        print("=== POSIX IPC Resources in /dev/shm ===")
        print()
        print("Shared Memory Segments (data buffers):")
        shm_list = list_shared_memory()
        if shm_list:
            filtered_shm = [shm for shm in shm_list if not args.prefix or shm[1:].startswith(args.prefix)]
            if filtered_shm:
                for shm in filtered_shm:
                    print(f"  {shm}")
            else:
                print("  (none matching filter)")
        else:
            print("  (none found)")

        print()
        print("POSIX Semaphores (synchronization primitives):")
        sem_list = list_semaphores()
        if sem_list:
            filtered_sem = [sem for sem in sem_list if not args.prefix or sem[1:].startswith(args.prefix)]
            if filtered_sem:
                for sem in filtered_sem:
                    print(f"  {sem}")
            else:
                print("  (none matching filter)")
        else:
            print("  (none found)")

        print()
        print(f"Note: Both are stored as files in /dev/shm/")
        print(f"      Semaphores have 'sem.' prefix, shared memory segments don't.")

        return 0

    # Cleanup mode
    print("POSIX IPC Cleanup Utility")
    print("=" * 60)

    if args.dry_run:
        print("DRY RUN MODE - Nothing will be deleted")
        print("=" * 60)

    if args.prefix:
        print(f"Filtering resources with prefix: {args.prefix}")
        print("=" * 60)

    # Clean up shared memory
    print("\nCleaning up shared memory segments...")
    shm_removed, shm_failed = cleanup_shared_memory(args.prefix, args.dry_run)

    # Clean up semaphores
    print("\nCleaning up semaphores...")
    sem_removed, sem_failed = cleanup_semaphores(args.prefix, args.dry_run)

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Shared memory segments: {shm_removed} removed, {shm_failed} failed")
    print(f"  Semaphores: {sem_removed} removed, {sem_failed} failed")
    print(f"  Total: {shm_removed + sem_removed} removed, {shm_failed + sem_failed} failed")

    if args.dry_run:
        print("\n(This was a dry run - nothing was actually deleted)")

    return 0 if (shm_failed + sem_failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

