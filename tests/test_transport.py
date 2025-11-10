import multiprocessing
import threading
import time

import pytest

from shm_rpc_bridge.exceptions import RPCTimeoutError, RPCTransportError
from shm_rpc_bridge.transport import SharedMemoryTransport


class TestSharedMemoryTransport:

    @staticmethod
    def _assert_client_ipc_initialized(transport: SharedMemoryTransport, name: str, buffer_size: int) -> None:
        assert transport.name == name
        assert transport.buffer_size == buffer_size
        assert transport.create is False
        assert transport.request_shm is not None
        assert transport.response_shm is not None
        assert transport.request_mmap is not None
        assert transport.response_mmap is not None
        assert transport.request_empty_sem is not None
        assert transport.request_full_sem is not None
        assert transport.response_empty_sem is not None
        assert transport.response_full_sem is not None

    @staticmethod
    def _assert_server_ipc_initialized(transport: SharedMemoryTransport, name: str, buffer_size: int) -> None:
        assert transport.name == name
        assert transport.buffer_size == buffer_size
        assert transport.create is True
        assert transport.request_shm is not None
        assert transport.response_shm is not None
        assert transport.request_mmap is not None
        assert transport.response_mmap is not None
        assert transport.request_empty_sem is not None
        assert transport.request_full_sem is not None
        assert transport.response_empty_sem is not None
        assert transport.response_full_sem is not None

    @staticmethod
    def _assert_ipc_resources_cleaned_up(transport: SharedMemoryTransport) -> None:
        assert transport.request_shm is None
        assert transport.response_shm is None
        assert transport.request_mmap is None
        assert transport.response_mmap is None
        assert transport.request_empty_sem is None
        assert transport.request_full_sem is None
        assert transport.response_empty_sem is None
        assert transport.response_full_sem is None

    def test_create_and_cleanup(self, buffer_size) -> None:
        transport = SharedMemoryTransport.create(name="test_create", buffer_size=buffer_size)
        self._assert_server_ipc_initialized(transport=transport, name="test_create", buffer_size=buffer_size)
        transport.cleanup()
        self._assert_ipc_resources_cleaned_up(transport)

    def test_create_and_cleanup_with_context_manager(self, buffer_size) -> None:
        with SharedMemoryTransport.create(name="test_context", buffer_size=buffer_size) as transport:
            self._assert_server_ipc_initialized(transport=transport, name="test_context", buffer_size=buffer_size)
        self._assert_ipc_resources_cleaned_up(transport)

    def test_open_and_cleanup(self, buffer_size) -> None:

        def create_transport_and_wait(name: str, ev: multiprocessing.Event, q: multiprocessing.Queue) -> None:
            with SharedMemoryTransport.create(name=name, buffer_size=buffer_size) as server_transport:
                ev.set()
                ev.wait()  # wait for client signal to exit
                try:
                    self._assert_server_ipc_initialized(transport=server_transport, name="test_open",
                                                        buffer_size=buffer_size)
                    q.put(None)
                except AssertionError as e:
                    q.put(str(e))

        event = multiprocessing.Event()
        queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=create_transport_and_wait,
            args=("test_open", event, queue)
        )
        process.start()
        # Wait for server side
        event.wait()

        # Open the transport (client side) and close it, with no exceptions and no impact on the ability
        # of the next client to do the same

        client_transport = SharedMemoryTransport.open(name="test_open", buffer_size=buffer_size)
        client_transport.cleanup()

        client_transport = SharedMemoryTransport.open(name="test_open", buffer_size=buffer_size)
        client_transport.cleanup()

        # Signal server to exit
        event.set()
        process.join()
        server_result = queue.get()
        assert server_result is None, f"Assertion failed in server: {server_result}"

    def test_send_receive(self, server_transport, client_transport) -> None:
        request_data = b"Request data"
        client_transport.send_request(request_data)
        received_request = server_transport.receive_request()
        assert received_request == request_data

        response_data = b"Response data"
        server_transport.send_response(response_data)
        received_response = client_transport.receive_response()
        assert received_response == response_data

    def test_conversation(self, server_transport, client_transport) -> None:
        # Send multiple request/response pairs
        for i in range(3):
            request = f"Request {i}".encode()
            client_transport.send_request(request)
            received = server_transport.receive_request()
            assert received == request
            # Server -> Client
            response = f"Response {i}".encode()
            server_transport.send_response(response)
            received = client_transport.receive_response()
            assert received == response

    def test_message_too_large(self, buffer_size, server_transport, client_transport) -> None:
        large_data = b"x" * (buffer_size + 1)
        with pytest.raises(RPCTransportError, match="too large"):
            client_transport.send_request(large_data)
        with pytest.raises(RPCTransportError, match="too large"):
            server_transport.send_response(large_data)

    @pytest.mark.parametrize('timeout', [0.1], indirect=True)
    def test_timeout(self, server_transport, client_transport) -> None:
        """Test timeout when no data available."""
        with pytest.raises(RPCTimeoutError):
            server_transport.receive_request()
        with pytest.raises(RPCTimeoutError):
            client_transport.receive_response()

    @pytest.mark.parametrize('timeout', [1], indirect=True)
    def test_cleanup_doesnt_break_acquire(self, server_transport, timeout) -> None:
        """
        Test that cleanup does not create an SBT exception due to unlinking an ongoing acquired sem
        """
        receive_started = threading.Event()
        receive_finished = threading.Event()

        cleanup_interrupts_timeout = True

        def blocking_receive():
            nonlocal cleanup_interrupts_timeout
            receive_started.set()
            try:
                server_transport.receive_request()
            except RPCTimeoutError:
                cleanup_interrupts_timeout = False
            except Exception:
                pass
            receive_finished.set()

        receive_thread = threading.Thread(target=blocking_receive)
        receive_thread.start()
        receive_started.wait(0.1)

        time.sleep(0.1)

        server_transport.cleanup()
        receive_finished.wait(2.0)

        assert not cleanup_interrupts_timeout


