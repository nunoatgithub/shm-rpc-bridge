#!/usr/bin/env python3
import cProfile
import os
import pstats
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# disable all bridge logging, keep only errors.
os.environ["SHM_RPC_BRIDGE_LOG_LEVEL"] = "ERROR"

from shm_rpc_bridge import RPCServer


def echo(message: str) -> str:
    return message


def run_server(name: str, buffer_size: int, iterations: int):
    server = RPCServer(name, buffer_size=buffer_size, timeout=10.0)
    server.register("echo", echo)

    # wait until there's a call from the client to start profiling
    while not server._handle_request():
        pass

    profiler = cProfile.Profile()
    count = 0
    profiler.enable()
    while count < iterations:
        server._handle_request()
        count += 1
    profiler.disable()
    server.close()

    profiler.dump_stats("server_profile.prof")
    # Print profiling statistics
    print("\n" + "=" * 80)
    print("SERVER PROFILING STATISTICS")
    print("=" * 80)
    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    stats.sort_stats("cumulative")
    stats.print_stats(20)  # Print top 20 functions by cumulative time
    print("=" * 80)
    print("Server profile saved to server_profile.prof")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python `profiling/echo_server.py` <name> <buffer_size> <iterations>")
        sys.exit(1)
    name = sys.argv[1]
    buffer_size = int(sys.argv[2])
    iterations = int(sys.argv[3])
    run_server(name, buffer_size, iterations)
