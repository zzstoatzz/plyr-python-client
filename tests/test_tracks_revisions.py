"""tests for track audio replace + revisions + restore."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from plyrfm import AudioRevision, PlyrClient, UploadResult

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


SSE_COMPLETED = (
    b"data: " + json.dumps({"status": "completed", "track_id": 42}).encode() + b"\n\n"
)


def _make_client(handler) -> PlyrClient:
    """build a PlyrClient whose internal httpx.Client is swapped for a
    MockTransport driven by the supplied handler."""
    transport = httpx.MockTransport(handler)
    client = PlyrClient(token="test-token", api_url="https://api.test")
    # swap the internal client for one using our mock transport
    client._client.close()
    client._client = httpx.Client(transport=transport, headers=client._client.headers)
    return client


# ---------------------------------------------------------------------------
# replace_audio
# ---------------------------------------------------------------------------


def test_replace_audio_polls_sse_and_returns_upload_result(tmp_path: Path) -> None:
    audio = tmp_path / "new.mp3"
    audio.write_bytes(b"\x00\x01\x02\x03")  # not real audio, just bytes

    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.method == "PUT" and request.url.path == "/tracks/42/audio":
            assert request.headers.get("authorization") == "Bearer test-token"
            return httpx.Response(
                202,
                json={"upload_id": "u-abc", "status": "pending", "title": "my song"},
            )
        if request.url.path == "/tracks/uploads/u-abc/progress":
            return httpx.Response(
                200,
                content=SSE_COMPLETED,
                headers={"content-type": "text/event-stream"},
            )
        raise AssertionError(f"unexpected: {request.method} {request.url}")

    client = _make_client(handler)
    result = client.tracks.replace_audio(42, audio)

    assert isinstance(result, UploadResult)
    assert result.track_id == 42
    assert result.title == "my song"
    assert calls == [
        "PUT /tracks/42/audio",
        "GET /tracks/uploads/u-abc/progress",
    ]


def test_replace_audio_immediate_completion(tmp_path: Path) -> None:
    """if the endpoint happens to return a completed status synchronously,
    we should skip the SSE poll."""
    audio = tmp_path / "new.mp3"
    audio.write_bytes(b"\x00")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        assert request.url.path == "/tracks/7/audio"
        return httpx.Response(
            200,
            json={"track_id": 7, "title": "x", "status": "completed"},
        )

    client = _make_client(handler)
    result = client.tracks.replace_audio(7, audio)
    assert result.track_id == 7
    assert result.title == "x"


def test_replace_audio_missing_file_raises(tmp_path: Path) -> None:
    client = _make_client(lambda r: httpx.Response(500))
    with pytest.raises(FileNotFoundError):
        client.tracks.replace_audio(1, tmp_path / "nope.mp3")


# ---------------------------------------------------------------------------
# revisions
# ---------------------------------------------------------------------------


def test_revisions_returns_list_newest_first() -> None:
    payload = {
        "track_id": 42,
        "revisions": [
            {
                "id": 9,
                "track_id": 42,
                "created_at": "2026-04-21T10:00:00Z",
                "file_type": "mp3",
                "original_file_type": None,
                "audio_storage": "both",
                "duration": 180,
                "was_gated": False,
            },
            {
                "id": 7,
                "track_id": 42,
                "created_at": "2026-04-20T13:48:26Z",
                "file_type": "wav",
                "original_file_type": None,
                "audio_storage": "r2",
                "duration": 2,
                "was_gated": False,
            },
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/tracks/42/revisions"
        assert request.headers.get("authorization") == "Bearer test-token"
        return httpx.Response(200, json=payload)

    client = _make_client(handler)
    revs = client.tracks.revisions(42)

    assert len(revs) == 2
    assert all(isinstance(r, AudioRevision) for r in revs)
    assert [r.id for r in revs] == [9, 7]  # server order preserved
    assert revs[0].file_type == "mp3"
    assert revs[1].audio_storage == "r2"
    assert revs[0].duration == 180


def test_revisions_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"track_id": 1, "revisions": []})

    client = _make_client(handler)
    assert client.tracks.revisions(1) == []


# ---------------------------------------------------------------------------
# restore_revision
# ---------------------------------------------------------------------------


def test_restore_revision_parses_audio_revision() -> None:
    payload = {
        "id": 12,
        "track_id": 42,
        "created_at": "2026-04-22T11:22:33Z",
        "file_type": "mp3",
        "original_file_type": "mp3",
        "audio_storage": "both",
        "duration": 240,
        "was_gated": False,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/tracks/42/revisions/7/restore"
        assert request.headers.get("authorization") == "Bearer test-token"
        return httpx.Response(200, json=payload)

    client = _make_client(handler)
    new_rev = client.tracks.restore_revision(42, 7)

    assert isinstance(new_rev, AudioRevision)
    assert new_rev.id == 12
    assert new_rev.track_id == 42
    assert new_rev.file_type == "mp3"
    assert new_rev.audio_storage == "both"
