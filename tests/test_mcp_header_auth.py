"""Exercise real MCP calls with only the HTTP boundary replaced."""

from collections.abc import Iterator
from contextvars import ContextVar

import httpx
import pytest
from fastmcp import Client
from plyrfm._internal.config import get_settings
from plyrfm_mcp.server import mcp
from starlette.requests import Request


@pytest.fixture
def requests(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[httpx.Request]]:
    recorded: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        if request.url.path == "/auth/me":
            return httpx.Response(
                200, json={"did": "did:plc:test", "handle": "test.example"}
            )
        return httpx.Response(200, json={"tracks": []})

    original = httpx.AsyncClient.__init__

    def initialize(self: httpx.AsyncClient, *args: object, **kwargs: object) -> None:
        kwargs["transport"] = httpx.MockTransport(respond)
        original(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", initialize)
    monkeypatch.setenv("PLYR_TOKEN", "server-token-must-not-leak")
    get_settings.cache_clear()
    yield recorded
    get_settings.cache_clear()


def http_request(monkeypatch: pytest.MonkeyPatch, token: str | None) -> None:
    headers = [(b"x-plyr-token", token.encode())] if token else []
    request = Request({"type": "http", "headers": headers})
    monkeypatch.setattr(
        "fastmcp.server.dependencies._current_http_request",
        ContextVar("test_request", default=request),
    )


async def test_http_call_uses_current_header_and_never_server_token(
    monkeypatch: pytest.MonkeyPatch, requests: list[httpx.Request]
) -> None:
    async with Client(mcp) as client:
        for token in ["caller-a", "caller-b"]:
            http_request(monkeypatch, token)
            await client.call_tool("my_tracks", {})
            assert requests[-1].headers["authorization"] == f"Bearer {token}"
        http_request(monkeypatch, None)
        result = await client.call_tool("my_tracks", {}, raise_on_error=False)
        assert result.is_error
        assert len(requests) == 2
        await client.call_tool("list_tracks", {})
        assert "authorization" not in requests[-1].headers


async def test_stdio_uses_local_credentials(requests: list[httpx.Request]) -> None:
    async with Client(mcp) as client:
        await client.call_tool("my_tracks", {})
    assert requests[-1].headers["authorization"] == "Bearer server-token-must-not-leak"


async def test_identity_resource_uses_http_credentials(
    monkeypatch: pytest.MonkeyPatch, requests: list[httpx.Request]
) -> None:
    http_request(monkeypatch, "resource-caller")
    async with Client(mcp) as client:
        await client.read_resource("plyr://me")
    assert requests[-1].headers["authorization"] == "Bearer resource-caller"
