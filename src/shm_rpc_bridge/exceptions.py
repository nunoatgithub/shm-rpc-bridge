"""
Custom exceptions for the shm-rpc-bridge library.
"""


class RPCError(Exception):
    """Base exception for all RPC-related errors."""

    pass


class RPCTimeoutError(RPCError):
    """Raised when an RPC operation times out."""

    pass


class RPCSerializationError(RPCError):
    """Raised when serialization or deserialization fails."""

    pass


class RPCTransportError(RPCError):
    """Raised when transport layer encounters an error."""

    pass


class RPCMethodError(RPCError):
    """Raised when a remote method call fails."""

    pass
