"""
Typed exceptions shared by the Soroban protocol adapters.

Adapters must never fabricate transaction hashes or market data when an
underlying RPC call fails.  Callers (the API layer, mixins, risk engine)
need one unambiguous signal that a real blockchain interaction did not
succeed, so a failed call raises :class:`AdapterRpcError` instead of
returning a simulated value.
"""


class AdapterRpcError(RuntimeError):
    """A Soroban RPC call to the underlying protocol failed.

    Raised when the RPC transport errors, the contract returns an error,
    or a write call completes without a real transaction hash in the
    response.  ``RuntimeError`` is kept as a base class so existing
    ``except RuntimeError`` call sites that only re-raise still behave
    correctly.
    """
