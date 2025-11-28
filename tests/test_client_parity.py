"""test that PlyrClient and AsyncPlyrClient have the same public methods."""

import inspect

from plyrfm import AsyncPlyrClient, PlyrClient


def get_public_methods(cls: type) -> set[str]:
    """get public method names (excluding dunder and private)."""
    return {
        name
        for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction)
        if not name.startswith("_")
    }


def test_clients_have_same_methods():
    """sync and async clients should expose the same public API."""
    sync_methods = get_public_methods(PlyrClient)
    async_methods = get_public_methods(AsyncPlyrClient)

    assert sync_methods == async_methods, (
        f"method mismatch:\n"
        f"  only in sync: {sync_methods - async_methods}\n"
        f"  only in async: {async_methods - sync_methods}"
    )


def test_methods_have_same_signatures():
    """sync and async methods should have the same parameter signatures."""
    sync_methods = get_public_methods(PlyrClient)

    for method_name in sync_methods:
        sync_method = getattr(PlyrClient, method_name)
        async_method = getattr(AsyncPlyrClient, method_name)

        sync_sig = inspect.signature(sync_method)
        async_sig = inspect.signature(async_method)

        # compare parameter names and defaults (ignore self)
        sync_params = list(sync_sig.parameters.items())[1:]  # skip self
        async_params = list(async_sig.parameters.items())[1:]

        assert len(sync_params) == len(async_params), (
            f"{method_name}: different param count"
        )

        for (sync_name, sync_param), (async_name, async_param) in zip(
            sync_params, async_params, strict=True
        ):
            assert sync_name == async_name, (
                f"{method_name}: param name mismatch {sync_name} vs {async_name}"
            )
            assert sync_param.default == async_param.default, (
                f"{method_name}.{sync_name}: default mismatch"
            )
            assert sync_param.annotation == async_param.annotation, (
                f"{method_name}.{sync_name}: annotation mismatch"
            )
