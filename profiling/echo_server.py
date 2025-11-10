#!/usr/bin/env python3
import cProfile
import os
import pstats
import signal
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shm_rpc_bridge import RPCServer

profiler = None
server = None
should_exit = False


def echo(message: str) -> str:
    return message


def sigterm_handler(signum, frame):
    """Handle SIGTERM by printing stats and exiting gracefully."""
    global should_exit, profiler, server
    should_exit = True

    if profiler:
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

    if server:
        server.close()

    sys.exit(0)


def run_server():
    count = 0
    global server, profiler, should_exit
    server = RPCServer("echo_profile", timeout=10.0)
    server.register("echo", echo)

    # wait until there's a call from the client to start profiling
    while not server._handle_request():
        pass

    profiler.enable()
    while not should_exit:
        try:
            server._handle_request()
            if (count := count + 1) == 50_000:
                profiler.disable()
        except Exception:
            # Ignore exceptions and keep running until SIGTERM
            pass


if __name__ == "__main__":
    # Register SIGTERM handler
    signal.signal(signal.SIGTERM, sigterm_handler)

    profiler = cProfile.Profile()
    run_server()
