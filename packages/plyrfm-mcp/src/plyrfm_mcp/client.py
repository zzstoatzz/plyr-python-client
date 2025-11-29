"""helper for creating plyr clients with per-request credentials."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

from plyrfm import AsyncPlyrClient

logger = logging.getLogger(__name__)


def _get_user_agent() -> str:
    """get user-agent string identifying MCP server."""
    try:
        v = version("plyrfm-mcp")
    except Exception:
        v = "unknown"
    return f"plyrfm-mcp/{v}"


def _get_token_from_context() -> str | None:
    """extract token from fastmcp context if available.

    returns:
        token string or None if not in context
    """
    try:
        from fastmcp.server.dependencies import get_context

        ctx = get_context()
        return ctx.get_state("plyr_token")
    except RuntimeError as e:
        if "No active context found" not in str(e):
            raise
        return None
    except AttributeError as e:
        if "get_state" not in str(e):
            raise
        return None


@asynccontextmanager
async def get_plyr_client(require_auth: bool = False) -> AsyncIterator[AsyncPlyrClient]:
    """get a plyr client using token from context or environment.

    first checks if a token was provided via http headers (stored in fastmcp
    context state by PlyrAuthMiddleware). if found, creates a client with that
    token. otherwise falls back to PLYR_TOKEN environment variable.

    this enables both:
    - multi-tenant http deployments (token per request via headers)
    - traditional stdio deployments (token from environment)

    args:
        require_auth: if True, raises ValueError when no token is available

    yields:
        a configured async plyr client

    raises:
        ValueError: if require_auth=True and no token is available

    example:
        async with get_plyr_client() as client:
            tracks = await client.list_tracks()
    """
    token = _get_token_from_context()

    user_agent = _get_user_agent()

    if token:
        logger.debug("using per-request token from context")
        async with AsyncPlyrClient(token=token, user_agent=user_agent) as client:
            yield client
    else:
        logger.debug("no per-request token, using environment defaults")
        client = AsyncPlyrClient(user_agent=user_agent)

        if require_auth and not client._token:
            msg = (
                "authentication required. "
                "set PLYR_TOKEN env var or pass x-plyr-token header"
            )
            raise ValueError(msg)

        async with client:
            yield client
