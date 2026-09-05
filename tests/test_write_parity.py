"""Compare sync/async writes at the HTTP boundary; no real account is used."""

import inspect
import json
from collections.abc import Callable
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

import httpx
import pytest
from plyrfm import AsyncPlyrClient, PlyrClient, TrackPatch
from plyrfm._internal.config import get_settings
from plyrfm._internal.types import ArtistProfilePatch
from plyrfm.cli import app, artists_update, tracks_update

TRACK = {
    "id": 42,
    "title": "test",
    "file_id": "file",
    "atproto_record_uri": "at://did:plc:test/fm.plyr.track/test",
    "atproto_record_cid": "test-cid",
}
PLAYLIST = {
    "id": "playlist",
    "name": "test",
    "owner_did": "did:plc:test",
    "owner_handle": "test.example",
}
REVISION = {
    "id": 1,
    "track_id": 42,
    "created_at": "2026-09-05T00:00:00Z",
    "file_type": "mp3",
    "audio_storage": "r2",
    "was_gated": False,
}
CASES = [
    ("tracks.like", [42], {}, "POST", "/tracks/42/like", {}),
    ("tracks.unlike", [42], {}, "DELETE", "/tracks/42/like", {}),
    ("tracks.delete", [42], {}, "DELETE", "/tracks/42", {}),
    (
        "tracks.update",
        [42, TrackPatch(title="new", description="", tags=["ambient"], unlisted=True)],
        {},
        "PATCH",
        "/tracks/42",
        TRACK,
    ),
    (
        "tracks.restore_revision",
        [42, 1],
        {},
        "POST",
        "/tracks/42/revisions/1/restore",
        REVISION,
    ),
    (
        "tracks.upload",
        ["AUDIO", "test"],
        {"tags": {"ambient"}, "description": "notes"},
        "POST",
        "/tracks/",
        {"track_id": 42},
    ),
    (
        "tracks.replace_audio",
        [42, "AUDIO"],
        {},
        "PUT",
        "/tracks/42/audio",
        {"track_id": 42},
    ),
    ("playlists.create", ["test"], {}, "POST", "/lists/playlists", PLAYLIST),
    (
        "playlists.add_track",
        ["playlist", 42],
        {},
        "POST",
        "/lists/playlists/playlist/tracks",
        PLAYLIST,
    ),
    (
        "playlists.remove_track",
        ["playlist", 42],
        {},
        "DELETE",
        "/lists/playlists/playlist/tracks/at://did:plc:test/fm.plyr.track/test",
        PLAYLIST,
    ),
    (
        "playlists.update",
        ["playlist"],
        {"name": "new", "show_on_profile": True},
        "PATCH",
        "/lists/playlists/playlist",
        PLAYLIST,
    ),
    ("playlists.delete", ["playlist"], {}, "DELETE", "/lists/playlists/playlist", {}),
    (
        "artists.update",
        [ArtistProfilePatch(bio="test", show_liked_on_profile=True)],
        {},
        "PUT",
        "/artists/me",
        {"did": "did:plc:test", "handle": "test.example"},
    ),
]


COMMANDS = {
    "tracks.like": ["tracks", "like", "42"],
    "tracks.unlike": ["tracks", "unlike", "42"],
    "tracks.delete": ["tracks", "delete", "42", "--yes"],
    "tracks.update": [
        "tracks",
        "update",
        "42",
        "--title",
        "new",
        "--description",
        "",
        "--tags",
        "ambient",
        "--unlisted",
    ],
    "tracks.restore_revision": ["tracks", "restore-revision", "42", "1", "--yes"],
    "tracks.upload": [
        "tracks",
        "upload",
        "AUDIO",
        "test",
        "--tag",
        "ambient",
        "--description",
        "notes",
    ],
    "tracks.replace_audio": ["tracks", "replace-audio", "42", "AUDIO"],
    "playlists.create": ["playlists", "create", "test"],
    "playlists.add_track": ["playlists", "add-track", "playlist", "42"],
    "playlists.remove_track": ["playlists", "remove-track", "playlist", "42"],
    "playlists.update": [
        "playlists",
        "update",
        "playlist",
        "--name",
        "new",
        "--show-on-profile",
    ],
    "playlists.delete": ["playlists", "delete", "playlist", "--yes"],
    "artists.update": ["artists", "update", "--bio", "test", "--show-liked-on-profile"],
}


def body(request: httpx.Request) -> object:
    content_type = request.headers.get("content-type", "")
    if "multipart/" in content_type:
        message = BytesParser(policy=default).parsebytes(
            f"Content-Type: {content_type}\r\n\r\n".encode() + request.content
        )
        return [
            (
                part.get_param("name", header="content-disposition"),
                part.get_payload(decode=True),
            )
            for part in message.iter_parts()
        ]
    return request.content


@pytest.mark.parametrize(
    "operation,args,kwargs,method,path,response", CASES, ids=[case[0] for case in CASES]
)
async def test_same_writes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    operation: str,
    args: list[object],
    kwargs: dict[str, object],
    method: str,
    path: str,
    response: object,
) -> None:
    audio = tmp_path / "test.mp3"
    audio.write_bytes(b"test audio")
    args = [audio if arg == "AUDIO" else arg for arg in args]
    requests: list[tuple[str, str, object]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-token"
        requests.append((request.method, request.url.path, body(request)))
        if request.method == "GET" and request.url.path == "/tracks/42":
            return httpx.Response(200, json=TRACK)
        assert (request.method, request.url.path) == (method, path)
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
    namespace, name = operation.split(".")
    with PlyrClient(token="test-token") as sync:
        expected = getattr(getattr(sync, namespace), name)(*args, **kwargs)
    expected_requests = requests.copy()
    requests.clear()
    async with AsyncPlyrClient(token="test-token") as asynchronous:
        actual = await getattr(getattr(asynchronous, namespace), name)(*args, **kwargs)
    assert actual == expected
    assert requests == expected_requests
    requests.clear()
    monkeypatch.setenv("PLYR_TOKEN", "test-token")
    get_settings.cache_clear()
    try:
        tokens = [
            str(audio) if token == "AUDIO" else token for token in COMMANDS[operation]
        ]
        command, bound, _ = app.parse_args(tokens)
        command(*bound.args, **bound.kwargs)
        assert [r for r in requests if r[0] != "GET"] == [
            r for r in expected_requests if r[0] != "GET"
        ]
    finally:
        get_settings.cache_clear()


def test_all_write_operations_have_cases() -> None:
    rows = json.loads(
        (Path(__file__).resolve().parents[1] / "contracts/surfaces.json").read_text()
    )
    expected = {row["sdk"] for row in rows if row["effect"] == "write"}
    assert expected == {case[0] for case in CASES} | {"tracks.download"}


def test_cli_exposes_track_patch_fields() -> None:
    assert set(TrackPatch.model_fields) <= set(
        inspect.signature(tracks_update).parameters
    )


def test_cli_exposes_artist_patch_fields() -> None:
    assert set(ArtistProfilePatch.model_fields) <= set(
        inspect.signature(artists_update).parameters
    )
