"""Exercise storage consent and ownership metadata over real local HTTP."""

import json
import threading
from collections.abc import Iterator
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Queue

import pytest
from fastmcp import Client
from plyrfm import AsyncPlyrClient, PlyrClient
from plyrfm._internal.config import get_settings
from plyrfm._internal.types import AudioRevision
from plyrfm.cli import app
from plyrfm_mcp.server import mcp

AUDIO_SPACE = "at://did:plc:artist/space/example.audio/playback/did:plc:artist/example.track/audio"
TRACK = {
    "id": 42,
    "title": "protected audio",
    "file_id": "audio",
    "audio_storage": "r2_private",
    "pds_blob_cid": None,
    "audio_space": AUDIO_SPACE,
}


@pytest.fixture
def api() -> Iterator[tuple[str, Queue[dict[str, bytes]]]]:
    uploads: Queue[dict[str, bytes]] = Queue()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def answer(self, body: dict[str, object]) -> None:
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self) -> None:
            assert self.path == "/tracks/"
            assert self.headers["authorization"] == "Bearer test-token"
            data = self.rfile.read(int(self.headers["Content-Length"]))
            message = BytesParser(policy=default).parsebytes(
                f"Content-Type: {self.headers['Content-Type']}\r\n\r\n".encode() + data
            )
            uploads.put(
                {
                    part.get_param(
                        "name", header="content-disposition"
                    ): part.get_payload(decode=True)
                    for part in message.iter_parts()
                }
            )
            self.answer({"track_id": 42})

        def do_GET(self) -> None:
            assert self.path == "/tracks/42"
            self.answer(TRACK)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", uploads
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize("surface", ["sync", "async", "cli"])
@pytest.mark.parametrize("accepted", [False, True])
async def test_upload_requires_explicit_storage_consent(
    api: tuple[str, Queue[dict[str, bytes]]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
    accepted: bool,
) -> None:
    url, uploads = api
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"test audio")
    if surface == "sync":
        with PlyrClient(api_url=url, token="test-token") as client:
            result = client.tracks.upload(audio, "audio", accept_plyr_storage=accepted)
            assert result.track_id == 42
    elif surface == "async":
        async with AsyncPlyrClient(api_url=url, token="test-token") as client:
            result = await client.tracks.upload(
                audio, "audio", accept_plyr_storage=accepted
            )
            assert result.track_id == 42
    else:
        monkeypatch.setenv("PLYR_API_URL", url)
        monkeypatch.setenv("PLYR_TOKEN", "test-token")
        get_settings.cache_clear()
        try:
            args = ["tracks", "upload", str(audio), "audio"]
            if accepted:
                args.append("--accept-plyr-storage")
            command, bound, _ = app.parse_args(args)
            command(*bound.args, **bound.kwargs)
        finally:
            get_settings.cache_clear()
    payload = uploads.get(timeout=2)
    assert payload["file"] == b"test audio"
    assert payload.get("accept_plyr_storage") == (b"true" if accepted else None)


async def test_space_ownership_survives_sdk_and_mcp_reads(
    api: tuple[str, Queue[dict[str, bytes]]], monkeypatch: pytest.MonkeyPatch
) -> None:
    url, _ = api
    with PlyrClient(api_url=url) as client:
        assert client.tracks.get(42).audio_space == AUDIO_SPACE
    async with AsyncPlyrClient(api_url=url) as client:
        track = await client.tracks.get(42)
        assert track.audio_space == AUDIO_SPACE
        assert track.pds_blob_cid is None
    monkeypatch.setenv("PLYR_API_URL", url)
    get_settings.cache_clear()
    try:
        async with Client(mcp) as client:
            result = await client.call_tool("get_track", {"track_id": 42})
        assert result.data.audio_space == AUDIO_SPACE
        assert result.data.pds_blob_cid is None
    finally:
        get_settings.cache_clear()


def test_revision_retains_protected_source_uri() -> None:
    revision = AudioRevision.model_validate(
        {
            "id": 1,
            "track_id": 42,
            "created_at": "2026-10-28T00:00:00Z",
            "file_type": "mp3",
            "audio_storage": "r2_private",
            "was_gated": True,
            "audio_space": AUDIO_SPACE,
        }
    )
    assert revision.model_dump()["audio_space"] == AUDIO_SPACE
