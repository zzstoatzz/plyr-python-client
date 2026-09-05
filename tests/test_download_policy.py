"""Downloads must use the policy endpoint and never send tokens to the CDN."""

from pathlib import Path

import httpx
import pytest
from plyrfm import AsyncPlyrClient, PlyrClient


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("allowed", [False, True])
async def test_download_policy_and_redirect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, asynchronous: bool, allowed: bool
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.host == "cdn.example":
            assert "authorization" not in request.headers
            return httpx.Response(200, content=b"audio")
        assert request.headers["authorization"] == "Bearer test-token"
        if request.url.path == "/tracks/42":
            return httpx.Response(
                200, json={"id": 42, "title": "test", "file_id": "file"}
            )
        assert request.url.path == "/audio/file/download"
        if not allowed:
            return httpx.Response(
                403, json={"detail": "the artist has disabled downloads"}
            )
        return httpx.Response(307, headers={"location": "https://cdn.example/file"})

    cls = httpx.AsyncClient if asynchronous else httpx.Client
    original = cls.__init__

    def initialize(self: object, *args: object, **kwargs: object) -> None:
        kwargs["transport"] = httpx.MockTransport(respond)
        original(self, *args, **kwargs)

    monkeypatch.setattr(cls, "__init__", initialize)
    output = tmp_path / "test.mp3"
    try:
        if asynchronous:
            async with AsyncPlyrClient(token="test-token") as client:
                await client.tracks.download(42, output)
        else:
            with PlyrClient(token="test-token") as client:
                client.tracks.download(42, output)
    except httpx.HTTPStatusError as exc:
        assert not allowed
        assert exc.response.status_code == 403
        assert not output.exists()
    else:
        assert allowed
        assert output.read_bytes() == b"audio"
