#!/usr/bin/env python3
import cProfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shm_rpc_bridge import RPCClient


def run_client():
    client = RPCClient("echo_profile", timeout=10.0)
    message = "x" * 2_000_000
    profiler = cProfile.Profile()
    profiler.enable()

    for i in range(50_000):
        client.call("echo", message=message)

    profiler.disable()
    profiler.dump_stats("client_profile.prof")
    print("Client profile saved to client_profile.prof")
    client.close()


if __name__ == "__main__":
    run_client()

