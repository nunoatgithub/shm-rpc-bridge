#!/usr/bin/env python3
import cProfile
import sys
import os

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
    print(f"\nServer profile saved to server_profile.prof")

