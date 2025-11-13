import multiprocessing
import os
import signal
import time

import pytest

from shm_rpc_bridge import RPCTransportError
from shm_rpc_bridge._internal.transport import SharedMemoryTransport
from shm_rpc_bridge.server import RPCServer


class TestRPCServer:
    def test_create_and_close(self):
        server = RPCServer("test_init", 100, 1.0)
        assert server.transport.name == "test_init"
        assert server.transport.buffer_size == 100
        assert server.transport.timeout == 1.0
        assert server._status() == RPCServer.Status.INITIALIZED
        server.close()
        assert server.transport is None
        assert server._status() == RPCServer.Status.CLOSED
        # make sure close is idempotent
        server.close()

        # default constructor, using context manager protocol
        with RPCServer("test_init_default") as server:
            assert server.transport.name == "test_init_default"
            assert server.transport.buffer_size == SharedMemoryTransport.DEFAULT_BUFFER_SIZE
            assert server.transport.timeout == SharedMemoryTransport.DEFAULT_TIMEOUT

    def test_create_twice_fails(self, server):
        with pytest.raises(RPCTransportError):
            RPCServer(server.transport.name)
        # but leaves the original untouched
        assert server._status() == RPCServer.Status.INITIALIZED

    def test_register_method(self, server) -> None:
        def test_func(x: int) -> int:
            return x * 2

        assert len(server.methods) == 1
        server.register("test", test_func)
        assert len(server.methods) == 2
        assert "test" in server.methods
        assert server.methods["test"] == test_func

    def test_register_decorator(self, server) -> None:
        @server.register_function
        def multiply(x: int, y: int) -> int:
            return x * y

        assert "multiply" in server.methods


class TestAutoCleanupBeforeStart:
    """Tests resource management before server starts"""

    def test_no_auto_cleanup_on_normal_termination_before_server_start(self) -> None:
        server_name = "test_exit_ok"

        process_started = multiprocessing.Event()
        can_exit = multiprocessing.Event()

        def _create_rpc_server(
            started: multiprocessing.Event, can_exit: multiprocessing.Event
        ) -> None:
            _ = RPCServer(server_name)  # assigning to prevent premature gc
            started.set()
            # block until clean exit signal
            can_exit.wait()

        process = multiprocessing.Process(
            target=_create_rpc_server, args=(process_started, can_exit)
        )
        process.start()
        process_started.wait(2.0)

        can_exit.set()
        process.join(2.0)
        with pytest.raises(AssertionError):
            RPCServer._assert_no_resources_left_behind(server_name)

    def test_auto_cleanup_on_sigterm_before_server_start(self) -> None:
        server_name = "test_sigterm_ok"

        process_started = multiprocessing.Event()
        can_exit = multiprocessing.Event()

        def _create_rpc_server(
            started: multiprocessing.Event, can_exit: multiprocessing.Event
        ) -> None:
            RPCServer(server_name)
            started.set()
            # block indefinitely
            can_exit.wait()

        process = multiprocessing.Process(
            target=_create_rpc_server, args=(process_started, can_exit)
        )
        process.start()
        process_started.wait(2.0)

        os.kill(process.pid, signal.SIGTERM)
        can_exit.set()
        process.join(2.0)
        RPCServer._assert_no_resources_left_behind(server_name)

    def test_auto_cleanup_on_sigint_before_server_start(self) -> None:
        server_name = "test_sigint_ok"

        process_started = multiprocessing.Event()
        can_exit = multiprocessing.Event()

        def _create_rpc_server(
            started: multiprocessing.Event, can_exit: multiprocessing.Event
        ) -> None:
            RPCServer(server_name)
            started.set()
            can_exit.wait()

        process = multiprocessing.Process(
            target=_create_rpc_server, args=(process_started, can_exit)
        )
        process.start()
        process_started.wait(2.0)

        time.sleep(0.1)

        os.kill(process.pid, signal.SIGINT)
        can_exit.set()
        process.join(2.0)
        RPCServer._assert_no_resources_left_behind(server_name)


class TestAutoCleanupAfterStart:
    """Tests resource management after server starts"""

    def test_auto_cleanup_on_sigterm_after_server_start(self) -> None:
        server_name = "test_sigterm_after_start_ok"

        process_started = multiprocessing.Event()

        def _create_rpc_server(started: multiprocessing.Event) -> None:
            server = RPCServer(server_name)
            started.set()
            server.start()

        process = multiprocessing.Process(target=_create_rpc_server, args=(process_started,))
        process.start()
        process_started.wait(2.0)

        time.sleep(0.1)

        os.kill(process.pid, signal.SIGTERM)
        process.join(2.0)
        RPCServer._assert_no_resources_left_behind(server_name)

    def test_auto_cleanup_on_sigint_after_server_start(self) -> None:
        server_name = "test_sigint_after_start_ok"

        process_started = multiprocessing.Event()

        def _create_rpc_server(started: multiprocessing.Event) -> None:
            server = RPCServer(server_name)
            started.set()
            server.start()

        process = multiprocessing.Process(target=_create_rpc_server, args=(process_started,))
        process.start()
        process_started.wait(2.0)

        time.sleep(0.1)

        os.kill(process.pid, signal.SIGINT)
        process.join(2.0)
        RPCServer._assert_no_resources_left_behind(server_name)
