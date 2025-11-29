"""tests for MCP server header-based authentication."""

from unittest.mock import AsyncMock, MagicMock, patch

from mcp_server.client import get_plyr_client
from mcp_server.middleware import PlyrAuthMiddleware


async def test_middleware_extracts_token_from_headers():
    """middleware extracts plyr token from x-plyr-token header."""
    middleware = PlyrAuthMiddleware()

    mock_fastmcp_ctx = MagicMock()
    mock_context = MagicMock()
    mock_context.fastmcp_context = mock_fastmcp_ctx

    mock_call_next = AsyncMock(return_value="result")

    with patch(
        "mcp_server.middleware.get_http_headers"
    ) as mock_get_http_headers:
        mock_get_http_headers.return_value = {
            "x-plyr-token": "test-token-12345",
        }

        result = await middleware.on_call_tool(mock_context, mock_call_next)

    # verify token was stored in context
    mock_fastmcp_ctx.set_state.assert_called_once_with(
        "plyr_token", "test-token-12345"
    )

    # verify call_next was called
    mock_call_next.assert_called_once_with(mock_context)
    assert result == "result"


async def test_middleware_handles_missing_headers():
    """middleware handles missing headers gracefully."""
    middleware = PlyrAuthMiddleware()

    mock_fastmcp_ctx = MagicMock()
    mock_context = MagicMock()
    mock_context.fastmcp_context = mock_fastmcp_ctx
    mock_call_next = AsyncMock(return_value="result")

    with patch(
        "mcp_server.middleware.get_http_headers"
    ) as mock_get_http_headers:
        # no plyr-specific headers
        mock_get_http_headers.return_value = {}

        result = await middleware.on_call_tool(mock_context, mock_call_next)

    # should not set token in context
    mock_fastmcp_ctx.set_state.assert_not_called()
    assert result == "result"


async def test_middleware_handles_stdio_mode():
    """middleware handles stdio mode (no http headers available)."""
    middleware = PlyrAuthMiddleware()

    mock_fastmcp_ctx = MagicMock()
    mock_context = MagicMock()
    mock_context.fastmcp_context = mock_fastmcp_ctx
    mock_call_next = AsyncMock(return_value="result")

    with patch(
        "mcp_server.middleware.get_http_headers"
    ) as mock_get_http_headers:
        # simulate stdio mode where get_http_headers returns empty dict
        mock_get_http_headers.return_value = {}

        result = await middleware.on_call_tool(mock_context, mock_call_next)

    # should not crash, just skip token extraction
    mock_fastmcp_ctx.set_state.assert_not_called()
    assert result == "result"


async def test_get_plyr_client_with_context_token():
    """get_plyr_client uses token from context when available."""
    mock_context = MagicMock()
    mock_context.get_state.return_value = "test-token-from-context"

    with (
        patch(
            "fastmcp.server.dependencies.get_context",
            return_value=mock_context,
        ),
        patch(
            "mcp_server.client.AsyncPlyrClient"
        ) as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        async with get_plyr_client() as client:
            assert client is mock_client

        # verify AsyncPlyrClient was called with token from context
        mock_client_cls.assert_called_once_with(token="test-token-from-context")


async def test_get_plyr_client_fallback_to_environment():
    """get_plyr_client falls back to environment when no context token."""
    with (
        patch(
            "fastmcp.server.dependencies.get_context",
            side_effect=RuntimeError("No active context found."),
        ),
        patch(
            "mcp_server.client.AsyncPlyrClient"
        ) as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client._token = "env-token"  # simulate env token
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        async with get_plyr_client() as client:
            assert client is mock_client

        # verify AsyncPlyrClient was called without explicit token (uses env)
        mock_client_cls.assert_called_once_with()


async def test_get_plyr_client_fallback_when_no_token_in_context():
    """get_plyr_client falls back when context exists but has no token."""
    mock_context = MagicMock()
    mock_context.get_state.return_value = None  # no token in state

    with (
        patch(
            "fastmcp.server.dependencies.get_context",
            return_value=mock_context,
        ),
        patch(
            "mcp_server.client.AsyncPlyrClient"
        ) as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client._token = "env-token"
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        async with get_plyr_client() as client:
            assert client is mock_client

        # verify AsyncPlyrClient was called without explicit token
        mock_client_cls.assert_called_once_with()


async def test_get_plyr_client_require_auth_raises_when_no_token():
    """get_plyr_client raises ValueError when require_auth=True but no token."""
    mock_context = MagicMock()
    mock_context.get_state.return_value = None  # no token in state

    with (
        patch(
            "fastmcp.server.dependencies.get_context",
            return_value=mock_context,
        ),
        patch(
            "mcp_server.client.AsyncPlyrClient"
        ) as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client._token = None  # no env token either
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        try:
            async with get_plyr_client(require_auth=True):
                pass
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "authentication required" in str(e)
