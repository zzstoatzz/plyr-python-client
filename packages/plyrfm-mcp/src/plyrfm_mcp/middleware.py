"""middleware for plyr.fm MCP server."""

from __future__ import annotations

import logging
from typing import Any

import mcp_types as mt
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext

logger = logging.getLogger(__name__)


class PlyrAuthMiddleware(Middleware):
    """extract plyr credentials from http headers with fallback to environment.

    enables multi-tenant deployments where each request can carry
    its own plyr token via a custom http header. if headers are not
    present (e.g., in stdio transport), falls back to PLYR_TOKEN env var.

    headers expected:
        - x-plyr-token: plyr API token

    the extracted credentials are stored in the fastmcp context state and can be
    accessed using `get_plyr_token()` from the client module.
    """

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, Any],
    ) -> Any:
        """extract credentials from headers on each tool call."""
        fastmcp_ctx = context.fastmcp_context

        if fastmcp_ctx:
            # extract from http headers if available
            # get_http_headers() returns empty dict when not in http transport
            headers = get_http_headers(include_all=True)
            token = headers.get("x-plyr-token")

            if token:
                logger.debug("extracted plyr token from http headers")
                fastmcp_ctx.set_state("plyr_token", token)

        return await call_next(context)
