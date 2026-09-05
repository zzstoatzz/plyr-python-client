"""The real SDK, CLI and MCP must send the same reads and preserve results."""

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from fastmcp import Client
from plyrfm import AsyncPlyrClient, PlyrClient
from plyrfm._internal.config import get_settings
from plyrfm.cli import app
from plyrfm_mcp.server import mcp

TRACK = {
    "id": 42,
    "title": "test ambient",
    "file_id": "audio",
    "visibility": "private",
    "gated": True,
    "r2_url": None,
}
PLAYLIST = {
    "id": "test-playlist",
    "name": "test collection",
    "owner_did": "did:plc:test",
    "owner_handle": "test.example",
    "tracks": [TRACK],
}
SEARCH = {
    "results": [
        {
            "type": "track",
            "id": 42,
            "title": "test ambient",
            "artist_handle": "test.example",
            "artist_display_name": "test",
            "relevance": 1,
        }
    ],
    "counts": {"tracks": 1},
}
CASES = [
    (
        "tracks.list",
        "list_tracks",
        {"limit": 1},
        [],
        {"limit": 1},
        "/tracks/",
        {"limit": "1"},
        {"tracks": [TRACK, TRACK]},
        ["tracks", "list", "--limit", "1"],
    ),
    (
        "tracks.get",
        "get_track",
        {"track_id": 42},
        [42],
        {},
        "/tracks/42",
        {},
        TRACK,
        ["tracks", "get", "42"],
    ),
    (
        "tracks.my",
        "my_tracks",
        {"limit": 1},
        [],
        {"limit": 1},
        "/tracks/me",
        {"limit": "1"},
        {"tracks": [TRACK, TRACK]},
        ["tracks", "my", "--limit", "1"],
    ),
    (
        "tracks.liked",
        "liked_tracks",
        {"limit": 1},
        [],
        {"limit": 1},
        "/tracks/liked",
        {},
        {"tracks": [TRACK, TRACK]},
        ["tracks", "liked", "--limit", "1"],
    ),
    (
        "tracks.revisions",
        "list_revisions",
        {"track_id": 42},
        [42],
        {},
        "/tracks/42/revisions",
        {},
        {"revisions": []},
        ["tracks", "revisions", "42"],
    ),
    (
        "discover.search",
        "search",
        {"query": "ambient", "type": "tracks", "limit": 1},
        ["ambient"],
        {"type": "tracks", "limit": 1},
        "/search/",
        {"q": "ambient", "type": "tracks", "limit": "1"},
        SEARCH,
        ["discover", "search", "ambient", "--type", "tracks", "--limit", "1"],
    ),
    (
        "discover.top_tracks",
        "top_tracks",
        {"limit": 1},
        [],
        {"limit": 1},
        "/tracks/top",
        {"limit": "1"},
        [TRACK],
        ["discover", "top", "--limit", "1"],
    ),
    (
        "tags.list",
        "list_tags",
        {"q": "am", "limit": 1},
        [],
        {"q": "am", "limit": 1},
        "/tracks/tags",
        {"q": "am", "limit": "1"},
        [{"name": "ambient", "track_count": 2}],
        ["tags", "list", "--q", "am", "--limit", "1"],
    ),
    (
        "tags.tracks",
        "tracks_by_tag",
        {"tag": "ambient", "limit": 1},
        ["ambient"],
        {"limit": 1},
        "/tracks/tags/ambient",
        {},
        {"tracks": [TRACK, TRACK]},
        ["tags", "get", "ambient", "--limit", "1"],
    ),
    (
        "playlists.list",
        "list_playlists",
        {},
        [],
        {},
        "/lists/playlists",
        {},
        [PLAYLIST],
        ["playlists", "list"],
    ),
    (
        "playlists.get",
        "get_playlist",
        {"playlist_id": "test-playlist"},
        ["test-playlist"],
        {},
        "/lists/playlists/test-playlist",
        {},
        PLAYLIST,
        ["playlists", "get", "test-playlist"],
    ),
    (
        "playlists.by_artist",
        "playlists_by_artist",
        {"artist_did": "did:plc:test"},
        ["did:plc:test"],
        {},
        "/lists/playlists/by-artist/did:plc:test",
        {},
        [PLAYLIST],
        None,
    ),
    (
        "playlists.recommendations",
        "playlist_recommendations",
        {"playlist_id": "test-playlist", "limit": 1},
        ["test-playlist"],
        {"limit": 1},
        "/lists/playlists/test-playlist/recommendations",
        {"limit": "1"},
        {"tracks": [], "available": False},
        None,
    ),
]


def serialized(value: object) -> object:
    if isinstance(value, list):
        return [serialized(item) for item in value]
    return value.model_dump(mode="json", by_alias=True)


@pytest.mark.parametrize(
    "operation,tool,tool_args,args,kwargs,path,query,response,cli",
    CASES,
    ids=[c[0] for c in CASES],
)
async def test_same_reads(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    tool: str,
    tool_args: dict[str, object],
    args: list[object],
    kwargs: dict[str, object],
    path: str,
    query: dict[str, str],
    response: object,
    cli: list[str] | None,
) -> None:
    calls: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.method == "GET"
        assert request.url.path == path
        assert dict(request.url.params) == query
        assert request.headers["authorization"] == "Bearer test-token"
        return httpx.Response(200, json=response)

    for cls in [httpx.Client, httpx.AsyncClient]:
        original = cls.__init__

        def initialize(
            self: object,
            *args: object,
            _original: Callable[..., None] = original,
            **kwargs: object,
        ) -> None:
            kwargs["transport"] = httpx.MockTransport(respond)
            _original(self, *args, **kwargs)

        monkeypatch.setattr(cls, "__init__", initialize)
    monkeypatch.setenv("PLYR_TOKEN", "test-token")
    get_settings.cache_clear()
    namespace, name = operation.split(".")
    try:
        with PlyrClient() as sync:
            expected = serialized(
                getattr(getattr(sync, namespace), name)(*args, **kwargs)
            )
        async with AsyncPlyrClient() as async_client:
            actual = serialized(
                await getattr(getattr(async_client, namespace), name)(*args, **kwargs)
            )
        assert actual == expected
        async with Client(mcp) as client:
            result = await client.call_tool(tool, tool_args)
        actual = result.structured_content
        if isinstance(actual, dict) and set(actual) == {"result"}:
            actual = actual["result"]
        assert actual == expected
        if kwargs.get("limit") == 1 and isinstance(expected, list):
            assert len(expected) <= 1
        if cli:
            command, bound, _ = app.parse_args(cli)
            command(*bound.args, **bound.kwargs)
        assert len(calls) == (4 if cli else 3)
    finally:
        get_settings.cache_clear()


def test_every_tool_has_behavioral_parity_case() -> None:
    rows = json.loads(
        (Path(__file__).resolve().parents[1] / "contracts/surfaces.json").read_text()
    )
    assert {row["mcp"] for row in rows if row["mcp"]} == {case[1] for case in CASES}


@pytest.mark.parametrize(
    "arguments",
    [
        {"query": "x"},
        {"query": "ambient", "limit": 0},
        {"query": "ambient", "limit": 51},
    ],
)
async def test_search_rejects_invalid_inputs(arguments: dict[str, object]) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("search", arguments, raise_on_error=False)
    assert result.is_error
