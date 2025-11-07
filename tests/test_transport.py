"""Tests for the transport module."""

import pytest

from shm_rpc_bridge.exceptions import RPCTimeoutError, RPCTransportError
from shm_rpc_bridge.transport import SharedMemoryTransport


class TestSharedMemoryTransport:
    """Test shared memory transport."""

    def test_create_and_cleanup(self) -> None:
        """Test creating and cleaning up transport."""
        transport = SharedMemoryTransport(
            name="test_create",
            buffer_size=4096,
            create=True,
        )
        transport.cleanup()

    def test_context_manager(self) -> None:
        """Test using transport as context manager."""
        with SharedMemoryTransport(
            name="test_context",
            buffer_size=4096,
            create=True,
        ) as transport:
            assert transport.request_shm is not None

    def test_send_receive_request(self) -> None:
        """Test sending and receiving a request."""
        server_transport = SharedMemoryTransport(
            name="test_request",
            buffer_size=4096,
            create=True,
            timeout=1.0,
        )
        client_transport = SharedMemoryTransport(
            name="test_request",
            buffer_size=4096,
            create=False,
            timeout=1.0,
        )

        try:
            # Client sends request
            test_data = b"Hello, server!"
            client_transport.send_request(test_data)

            # Server receives request
            received = server_transport.receive_request()
            assert received == test_data

        finally:
            client_transport.cleanup()
            server_transport.cleanup()

    def test_send_receive_response(self) -> None:
        """Test sending and receiving a response."""
        server_transport = SharedMemoryTransport(
            name="test_response",
            buffer_size=4096,
            create=True,
            timeout=1.0,
        )
        client_transport = SharedMemoryTransport(
            name="test_response",
            buffer_size=4096,
            create=False,
            timeout=1.0,
        )

        try:
            # Server sends response
            test_data = b"Hello, client!"
            server_transport.send_response(test_data)

            # Client receives response
            received = client_transport.receive_response()
            assert received == test_data

        finally:
            client_transport.cleanup()
            server_transport.cleanup()

    def test_roundtrip(self) -> None:
        """Test full request/response roundtrip."""
        server_transport = SharedMemoryTransport(
            name="test_roundtrip",
            buffer_size=4096,
            create=True,
            timeout=1.0,
        )
        client_transport = SharedMemoryTransport(
            name="test_roundtrip",
            buffer_size=4096,
            create=False,
            timeout=1.0,
        )

        try:
            # Client sends request
            request_data = b"Request data"
            client_transport.send_request(request_data)

            # Server receives and sends response
            received_request = server_transport.receive_request()
            assert received_request == request_data

            response_data = b"Response data"
            server_transport.send_response(response_data)

            # Client receives response
            received_response = client_transport.receive_response()
            assert received_response == response_data

        finally:
            client_transport.cleanup()
            server_transport.cleanup()

    def test_message_too_large(self) -> None:
        """Test error when message is too large."""
        with SharedMemoryTransport(
            name="test_large",
            buffer_size=1024,
            create=True,
        ) as transport:
            large_data = b"x" * 2048
            with pytest.raises(RPCTransportError, match="too large"):
                transport.send_request(large_data)

    def test_timeout(self) -> None:
        """Test timeout when no data available."""
        with SharedMemoryTransport(
            name="test_timeout",
            buffer_size=4096,
            create=True,
            timeout=0.1,
        ) as transport:
            # Try to receive without sending - should timeout
            with pytest.raises(RPCTimeoutError):
                transport.receive_request()

    def test_send_timeout(self) -> None:
        """Test timeout when trying to send without buffer space."""
        with SharedMemoryTransport(
            name="test_send_timeout",
            buffer_size=4096,
            create=True,
            timeout=0.1,
        ) as transport:
            # Send first request (fills the buffer)
            transport.send_request(b"First request")
            # Try to send second request without receiving the first
            # Should timeout waiting for empty slot
            with pytest.raises(RPCTimeoutError):
                transport.send_request(b"Second request")

    def test_sequential_roundtrips(self) -> None:
        """Test multiple sequential request/response roundtrips."""
        server_transport = SharedMemoryTransport(
            name="test_sequential",
            buffer_size=4096,
            create=True,
            timeout=1.0,
        )
        client_transport = SharedMemoryTransport(
            name="test_sequential",
            buffer_size=4096,
            create=False,
            timeout=1.0,
        )

        try:
            # Send multiple request/response pairs
            for i in range(3):
                # Client -> Server
                request = f"Request {i}".encode()
                client_transport.send_request(request)
                received = server_transport.receive_request()
                assert received == request

                # Server -> Client
                response = f"Response {i}".encode()
                server_transport.send_response(response)
                received = client_transport.receive_response()
                assert received == response

        finally:
            client_transport.cleanup()
            server_transport.cleanup()
