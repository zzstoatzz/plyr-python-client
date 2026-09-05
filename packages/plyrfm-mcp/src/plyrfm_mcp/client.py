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
        auth_setup = "set PLYR_TOKEN in the local stdio server's environment"
    else:
        token = request.headers.get("x-plyr-token") or None
        auth_setup = "configure the x-plyr-token header on this hosted HTTP connection"
    if require_auth and not token:
        raise ValueError(
            f"authentication required: {auth_setup}. "
            "Create a token at https://plyr.fm/settings#developer. Never paste it in chat."
        )
    settings = settings.model_copy(update={"token": token})
    async with AsyncPlyrClient(
        settings=settings, user_agent=f"plyrfm-mcp/{version('plyrfm-mcp')}"
    ) as client:
        yield client
