import pytest

from shm_rpc_bridge.data import JSONSerdes, RPCCodec, RPCRequest, RPCResponse, Serdes
from shm_rpc_bridge.exceptions import RPCSerializationError


class TestRPCRequest:
    """Test RPC request."""

    def test_to_dict(self) -> None:
        """Test converting request to dictionary."""
        request = RPCRequest(
            request_id="123",
            method="test_method",
            params={"arg1": "value1", "arg2": 42},
        )
        result = request.to_dict()
        assert result == {
            "request_id": "123",
            "method": "test_method",
            "params": {"arg1": "value1", "arg2": 42},
        }

    def test_from_dict(self) -> None:
        """Test creating request from dictionary."""
        data = {
            "request_id": "123",
            "method": "test_method",
            "params": {"arg1": "value1"},
        }
        request = RPCRequest.from_dict(data)
        assert request.request_id == "123"
        assert request.method == "test_method"
        assert request.params == {"arg1": "value1"}

    def test_roundtrip(self) -> None:
        """Test to_dict -> from_dict roundtrip."""
        original = RPCRequest(
            request_id="abc-123",
            method="calculate",
            params={"op": "add", "a": 10, "b": 20},
        )
        data = original.to_dict()
        restored = RPCRequest.from_dict(data)
        assert restored.request_id == original.request_id
        assert restored.method == original.method
        assert restored.params == original.params


class TestRPCResponse:
    """Test RPC response."""

    def test_to_dict_with_result(self) -> None:
        """Test converting successful response to dictionary."""
        response = RPCResponse(request_id="123", result={"answer": 42})
        result = response.to_dict()
        assert result == {
            "request_id": "123",
            "result": {"answer": 42},
            "error": None,
        }

    def test_to_dict_with_error(self) -> None:
        """Test converting error response to dictionary."""
        response = RPCResponse(request_id="123", error="Something went wrong")
        result = response.to_dict()
        assert result == {
            "request_id": "123",
            "result": None,
            "error": "Something went wrong",
        }

    def test_from_dict(self) -> None:
        """Test creating response from dictionary."""
        data = {
            "request_id": "123",
            "result": 42,
            "error": None,
        }
        response = RPCResponse.from_dict(data)
        assert response.request_id == "123"
        assert response.result == 42
        assert response.error is None

    def test_roundtrip_success(self) -> None:
        """Test to_dict -> from_dict roundtrip for success response."""
        original = RPCResponse(request_id="test-456", result=[1, 2, 3])
        data = original.to_dict()
        restored = RPCResponse.from_dict(data)
        assert restored.request_id == original.request_id
        assert restored.result == original.result
        assert restored.error is None

    def test_roundtrip_error(self) -> None:
        """Test to_dict -> from_dict roundtrip for error response."""
        original = RPCResponse(request_id="test-789", error="Failed")
        data = original.to_dict()
        restored = RPCResponse.from_dict(data)
        assert restored.request_id == original.request_id
        assert restored.result is None
        assert restored.error == original.error


class TestJSONSerdes:
    """Test JSON serdes."""

    def test_serialize_dict(self) -> None:
        """Test serializing a dictionary."""
        serdes = JSONSerdes()
        data = {"key": "value", "number": 42}
        result = serdes.serialize(data)
        assert isinstance(result, bytes)
        assert b"key" in result
        assert b"value" in result

    def test_deserialize_dict(self) -> None:
        """Test deserializing a dictionary."""
        serdes = JSONSerdes()
        data = b'{"key": "value", "number": 42}'
        result = serdes.deserialize(data)
        assert result == {"key": "value", "number": 42}

    def test_roundtrip(self) -> None:
        """Test serialize/deserialize roundtrip."""
        serdes = JSONSerdes()
        original = {"method": "test", "params": {"a": 1, "b": "two"}}
        serialized = serdes.serialize(original)
        deserialized = serdes.deserialize(serialized)
        assert deserialized == original

    def test_serialize_error(self) -> None:
        """Test serialization error handling."""
        serdes = JSONSerdes()
        # Object with circular reference
        obj = {}  # type: ignore
        obj["self"] = obj
        with pytest.raises(RPCSerializationError):
            serdes.serialize(obj)

    def test_deserialize_error(self) -> None:
        """Test deserialization error handling."""
        serdes = JSONSerdes()
        with pytest.raises(RPCSerializationError):
            serdes.deserialize(b"not valid json")

    def test_interface_compliance(self) -> None:
        """Test that JSONSerdes implements Serdes."""
        serdes = JSONSerdes()
        assert isinstance(serdes, Serdes)


class TestRPCCodec:
    """Test RPC codec."""

    def test_encode_decode_request(self) -> None:
        """Test encoding and decoding a request."""
        codec = RPCCodec()
        request = RPCRequest(
            request_id="test-123",
            method="calculate",
            params={"op": "add", "a": 1, "b": 2},
        )
        encoded = codec.encode_request(request)
        decoded = codec.decode_request(encoded)
        assert decoded.request_id == request.request_id
        assert decoded.method == request.method
        assert decoded.params == request.params

    def test_encode_decode_response(self) -> None:
        """Test encoding and decoding a response."""
        codec = RPCCodec()
        response = RPCResponse(request_id="test-123", result={"sum": 3})
        encoded = codec.encode_response(response)
        decoded = codec.decode_response(encoded)
        assert decoded.request_id == response.request_id
        assert decoded.result == response.result
        assert decoded.error is None
