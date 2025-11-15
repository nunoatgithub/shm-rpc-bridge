import multiprocessing
import threading
import time

import posix_ipc
import pytest

# -------------------------------------------------------------------------------------
# overriding two fixture definitions here to force SharedMemoryTransportPosix usage
# -------------------------------------------------------------------------------------
from conftest import _TEST_CHANNEL

from shm_rpc_bridge._internal.transport_posix import SharedMemoryTransportPosix
from shm_rpc_bridge.exceptions import RPCTimeoutError, RPCTransportError


@pytest.fixture
def server_transport(buffer_size, timeout):
    transport = SharedMemoryTransportPosix.create(
        name=_TEST_CHANNEL, buffer_size=buffer_size, timeout=timeout
    )
    yield transport
    transport.close()


@pytest.fixture
def client_transport(buffer_size, timeout):
    transport = SharedMemoryTransportPosix.open(
        name=_TEST_CHANNEL, buffer_size=buffer_size, timeout=timeout
    )
    yield transport
    transport.close()


# -------------------------------------------------------------------------------------


class TestSharedMemoryTransportPosix:
    @staticmethod
    def _assert_client_ipc_initialized(
        transport: SharedMemoryTransportPosix, name: str, buffer_size: int
    ) -> None:
        assert transport.name == name
        assert transport.buffer_size == buffer_size
        assert transport.owner is False
        assert transport.request_shm is not None
        assert transport.response_shm is not None
        assert transport.request_mmap is not None
        assert transport.response_mmap is not None
        assert transport.request_empty_sem is not None
        assert transport.request_full_sem is not None
        assert transport.response_empty_sem is not None
        assert transport.response_full_sem is not None

    @staticmethod
    def _assert_server_ipc_initialized(
        transport: SharedMemoryTransportPosix, name: str, buffer_size: int
    ) -> None:
        assert transport.name == name
        assert transport.buffer_size == buffer_size
        assert transport.owner is True
        assert transport.request_shm is not None
        assert transport.response_shm is not None
        assert transport.request_mmap is not None
        assert transport.response_mmap is not None
        assert transport.request_empty_sem is not None
        assert transport.request_full_sem is not None
        assert transport.response_empty_sem is not None
        assert transport.response_full_sem is not None

    @staticmethod
    def _assert_ipc_resources_cleaned_up(transport: SharedMemoryTransportPosix) -> None:
        assert transport.request_shm is None
        assert transport.response_shm is None
        assert transport.request_mmap is None
        assert transport.response_mmap is None
        assert transport.request_empty_sem is None
        assert transport.request_full_sem is None
        assert transport.response_empty_sem is None
        assert transport.response_full_sem is None
        SharedMemoryTransportPosix.assert_no_resources_left_behind(transport.name)

    def test_create_and_close(self, buffer_size) -> None:
        transport = SharedMemoryTransportPosix.create(
            name="t_cre", buffer_size=buffer_size, timeout=1.1
        )
        self._assert_server_ipc_initialized(
            transport=transport, name="t_cre", buffer_size=buffer_size
        )
        assert transport.timeout == 1.1
        transport.close()
        self._assert_ipc_resources_cleaned_up(transport)

        # and repeat but with default constructor
        transport = SharedMemoryTransportPosix.create(name="t_cre_d")
        self._assert_server_ipc_initialized(
            transport=transport,
            name="t_cre_d",
            buffer_size=SharedMemoryTransportPosix.DEFAULT_BUFFER_SIZE,
        )
        assert transport.timeout == SharedMemoryTransportPosix.DEFAULT_TIMEOUT
        transport.close()
        self._assert_ipc_resources_cleaned_up(transport)

    def test_create_and_close_with_context_manager(self, buffer_size) -> None:
        with SharedMemoryTransportPosix.create(name="t_ctx", buffer_size=buffer_size) as transport:
            self._assert_server_ipc_initialized(
                transport=transport, name="t_ctx", buffer_size=buffer_size
            )
        self._assert_ipc_resources_cleaned_up(transport)

    def test_create_twice_fails(self, server_transport):
        with pytest.raises(RPCTransportError):
            SharedMemoryTransportPosix.create(server_transport.name)
        # but leaves the original untouched
        self._assert_server_ipc_initialized(
            transport=server_transport,
            name=server_transport.name,
            buffer_size=server_transport.buffer_size,
        )

    def test_partial_creation_rolls_back_automatically(self):
        # simulating a situation where the last allocated resource during creation already existed
        transport_name = "t_part"
        sem_name = SharedMemoryTransportPosix._get_response_semaphore_names(transport_name)[1]
        preexisting_semaphore = None
        try:
            preexisting_semaphore = posix_ipc.Semaphore(
                sem_name,
                flags=posix_ipc.O_CREX,
                initial_value=0,
            )
            with pytest.raises(RPCTransportError):
                # tries to create the semaphore "sem.t_part_resp_full", which already exists
                SharedMemoryTransportPosix.create(transport_name)
            # check rollback
            SharedMemoryTransportPosix.assert_no_resources_left_behind(transport_name, sem_name)
        finally:
            if preexisting_semaphore is not None:
                posix_ipc.unlink_semaphore(sem_name)

    @staticmethod
    def _create_transport_and_wait(
        name: str,
        buffer_size: int,
        ready_event: multiprocessing.Event,
        shutdown_event: multiprocessing.Event,
        q: multiprocessing.Queue
    ) -> None:
        with SharedMemoryTransportPosix.create(
            name=name, buffer_size=buffer_size
        ) as server_transport:
            ready_event.set()  # signal server is ready
            shutdown_event.wait()  # wait for client signal to exit
            try:
                TestSharedMemoryTransportPosix._assert_server_ipc_initialized(
                    transport=server_transport, name="t_open", buffer_size=buffer_size
                )
                q.put(None)
            except AssertionError as e:
                q.put(str(e))

    def test_open_and_close(self, buffer_size) -> None:
        ready_event = multiprocessing.Event()
        shutdown_event = multiprocessing.Event()
        queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=TestSharedMemoryTransportPosix._create_transport_and_wait,
            args=("t_open", buffer_size, ready_event, shutdown_event, queue),
        )
        process.start()
        # Wait for server side
        ready_event.wait()

        # Open the transport (client side) and close it, with no exceptions and no impact on the
        # ability of the next client to do the same

        client_transport = SharedMemoryTransportPosix.open(name="t_open", buffer_size=buffer_size)
        client_transport.close()

        client_transport = SharedMemoryTransportPosix.open(name="t_open", buffer_size=buffer_size)
        client_transport.close()

        # Signal server to exit
        shutdown_event.set()
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

    @pytest.mark.parametrize("timeout", [0.1], indirect=True)
    def test_timeout(self, server_transport, client_transport) -> None:
        """Test timeout when no data available."""
        with pytest.raises(RPCTimeoutError):
            server_transport.receive_request()
        with pytest.raises(RPCTimeoutError):
            client_transport.receive_response()

    @pytest.mark.parametrize("timeout", [1], indirect=True)
    def test_close_doesnt_break_acquire(self, server_transport, timeout) -> None:
        """
        Test that close does not create an SBT exception due to unlinking an ongoing acquired sem
        """
        receive_started = threading.Event()
        receive_finished = threading.Event()

        close_interrupts_timeout = True

        def blocking_receive():
            nonlocal close_interrupts_timeout
            receive_started.set()
            try:
                server_transport.receive_request()
            except RPCTimeoutError:
                close_interrupts_timeout = False
            except Exception:
                pass
            receive_finished.set()

        receive_thread = threading.Thread(target=blocking_receive)
        receive_thread.start()
        receive_started.wait(0.1)

        time.sleep(0.1)

        server_transport.close()
        receive_finished.wait(2.0)

        assert not close_interrupts_timeout
