#!/usr/bin/env python3
import cProfile
import os
import pstats
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shm_rpc_bridge import RPCServer

profiler = None

def echo(message: str) -> str:
    return message

def run_server():
    call_count = 0
    server = RPCServer("echo_profile", timeout=10.0)
    server.register("echo", echo)

    profiler.enable()
    while call_count < 50_000:
        server._handle_request()
        call_count += 1
    profiler.disable()
    server.close()


if __name__ == "__main__":
    profiler = cProfile.Profile()
    run_server()
    profiler.dump_stats("server_profile.prof")

    # Print profiling statistics
    print("\n" + "="*80)
    print("SERVER PROFILING STATISTICS")
    print("="*80)
    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Print top 20 functions by cumulative time
    print("\nTop 20 functions by total time:")
    stats.sort_stats('tottime')
    stats.print_stats(20)
    print("="*80)
    print("Server profile saved to server_profile.prof")

