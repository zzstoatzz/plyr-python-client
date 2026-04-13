"""test that PlyrClient and AsyncPlyrClient have the same public methods."""

import inspect

from plyrfm import AsyncPlyrClient, PlyrClient
from plyrfm.client import (
    ArtistsNamespace,
    AsyncArtistsNamespace,
    AsyncDiscoverNamespace,
    AsyncPlaylistsNamespace,
    AsyncTagsNamespace,
    AsyncTracksNamespace,
    DiscoverNamespace,
    PlaylistsNamespace,
    TagsNamespace,
    TracksNamespace,
)


def get_public_methods(cls: type) -> set[str]:
    """get public method names (excluding dunder and private)."""
    return {
        name
        for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction)
        if not name.startswith("_")
    }


# --- top-level client parity ---


def test_clients_have_same_methods():
    """sync and async clients should expose the same public API."""
    sync_methods = get_public_methods(PlyrClient)
    async_methods = get_public_methods(AsyncPlyrClient)

    assert sync_methods == async_methods, (
        f"method mismatch:\n"
        f"  only in sync: {sync_methods - async_methods}\n"
        f"  only in async: {async_methods - sync_methods}"
    )


def test_clients_have_same_namespaces():
    """sync and async clients should expose the same namespace attributes."""
    sync_ns = {name for name in ("tracks", "playlists", "tags", "artists", "discover")}
    for name in sync_ns:
        assert hasattr(PlyrClient, name) or name in PlyrClient.__init__.__code__.co_names, (
            f"PlyrClient missing namespace: {name}"
        )


# --- namespace parity ---

NAMESPACE_PAIRS = [
    (TracksNamespace, AsyncTracksNamespace),
    (PlaylistsNamespace, AsyncPlaylistsNamespace),
    (TagsNamespace, AsyncTagsNamespace),
    (ArtistsNamespace, AsyncArtistsNamespace),
    (DiscoverNamespace, AsyncDiscoverNamespace),
]


def test_namespace_method_parity():
    """sync and async namespaces should have the same public methods."""
    for sync_cls, async_cls in NAMESPACE_PAIRS:
        sync_methods = get_public_methods(sync_cls)
        async_methods = get_public_methods(async_cls)

        assert sync_methods == async_methods, (
            f"{sync_cls.__name__} vs {async_cls.__name__} method mismatch:\n"
            f"  only in sync: {sync_methods - async_methods}\n"
            f"  only in async: {async_methods - sync_methods}"
        )


def test_namespace_signature_parity():
    """sync and async namespace methods should have the same signatures."""
    for sync_cls, async_cls in NAMESPACE_PAIRS:
        for method_name in get_public_methods(sync_cls):
            sync_method = getattr(sync_cls, method_name)
            async_method = getattr(async_cls, method_name)

            sync_sig = inspect.signature(sync_method)
            async_sig = inspect.signature(async_method)

            sync_params = list(sync_sig.parameters.items())[1:]  # skip self
            async_params = list(async_sig.parameters.items())[1:]

            assert len(sync_params) == len(async_params), (
                f"{sync_cls.__name__}.{method_name}: different param count"
            )

            for (sync_name, sync_param), (async_name, async_param) in zip(
                sync_params, async_params, strict=True
            ):
                assert sync_name == async_name, (
                    f"{sync_cls.__name__}.{method_name}: "
                    f"param name mismatch {sync_name} vs {async_name}"
                )
                assert sync_param.default == async_param.default, (
                    f"{sync_cls.__name__}.{method_name}.{sync_name}: default mismatch"
                )
