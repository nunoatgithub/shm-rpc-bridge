"""
Data module for RPC communication.

Contains serialization/deserialization (serdes), message definitions, and protocol handling.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from shm_rpc_bridge.exceptions import RPCSerializationError

# ==============================================================================
# Message Definitions
# ==============================================================================


@dataclass
class RPCRequest:
    """Represents an RPC request."""

    request_id: str
    method: str
    params: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "method": self.method,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RPCRequest:
        return cls(
            request_id=data["request_id"],
            method=data["method"],
            params=data["params"],
        )


@dataclass
class RPCResponse:
    """Represents an RPC response."""

    request_id: str
    result: Any | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "result": self.result,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RPCResponse:
        return cls(
            request_id=data["request_id"],
            result=data.get("result"),
            error=data.get("error"),
        )


# ==============================================================================
# Serdes (Serialization/Deserialization)
# ==============================================================================


class Serdes(ABC):
    """Abstract interface for serialization/deserialization."""

    @abstractmethod
    def serialize(self, data: Any) -> bytes:
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        pass


class JSONSerdes(Serdes):
    """JSON-based serdes implementation."""

    def serialize(self, data: Any) -> bytes:
        try:
            return json.dumps(data).encode("utf-8")
        except (TypeError, ValueError) as e:
            raise RPCSerializationError(f"Failed to serialize data: {e}") from e

    def deserialize(self, data: bytes) -> Any:
        try:
            return json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise RPCSerializationError(f"Failed to deserialize data: {e}") from e


# ==============================================================================
# Codec (Encode/Decode)
# ==============================================================================


class RPCCodec:
    """Codec for encoding/decoding RPC messages using JSON."""

    def __init__(self) -> None:
        self._serdes = JSONSerdes()

    def encode_request(self, request: RPCRequest) -> bytes:
        return self._serdes.serialize(request.to_dict())

    def decode_request(self, data: bytes) -> RPCRequest:
        return RPCRequest.from_dict(self._serdes.deserialize(data))

    def encode_response(self, response: RPCResponse) -> bytes:
        return self._serdes.serialize(response.to_dict())

    def decode_response(self, data: bytes) -> RPCResponse:
        return RPCResponse.from_dict(self._serdes.deserialize(data))
