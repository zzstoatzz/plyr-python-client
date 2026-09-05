"""Create a client with credentials belonging only to the current caller."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastmcp.server.dependencies import get_http_request
from plyrfm import AsyncPlyrClient
from plyrfm._internal.config import get_settings


@asynccontextmanager
async def get_plyr_client(require_auth: bool = False) -> AsyncIterator[AsyncPlyrClient]:
    """HTTP uses request headers; stdio uses the local environment."""
    settings = get_settings()
    try:
        request = get_http_request()
    except RuntimeError as exc:
        if str(exc) != "No active HTTP request found.":
            raise
        token = settings.token
    else:
        token = request.headers.get("x-plyr-token") or None
    if require_auth and not token:
        raise ValueError(
            "authentication required: configure PLYR_TOKEN for stdio or "
            "x-plyr-token for HTTP. Create a token at https://plyr.fm/settings#developer"
        )
    settings = settings.model_copy(update={"token": token})
    async with AsyncPlyrClient(
        settings=settings, user_agent=f"plyrfm-mcp/{version('plyrfm-mcp')}"
    ) as client:
        yield client
