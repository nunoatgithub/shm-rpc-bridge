#!/usr/bin/env python3
import cProfile
import os
import pstats
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shm_rpc_bridge import RPCClient


def run_client():
    client = RPCClient("echo_profile", timeout=10.0)
    message = "x" * 2_000_000
    profiler = cProfile.Profile()

    # issue first call as a signal to the server to start profiling
    client.call("echo", message=message)

    profiler.enable()
    for i in range(50_000):
        client.call("echo", message=message)
    profiler.disable()
    profiler.dump_stats("client_profile.prof")

    # Print profiling statistics
    print("\n" + "=" * 80)
    print("CLIENT PROFILING STATISTICS")
    print("=" * 80)
    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    stats.sort_stats("cumulative")
    stats.print_stats(20)  # Print top 20 functions by cumulative time
    print("=" * 80)
    print("Client profile saved to client_profile.prof")

    client.close()


if __name__ == "__main__":
    run_client()
