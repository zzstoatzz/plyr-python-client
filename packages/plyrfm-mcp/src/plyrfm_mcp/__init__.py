"""plyrfm-mcp - MCP server for plyr.fm."""

from plyrfm_mcp.client import get_plyr_client
from plyrfm_mcp.server import mcp

__all__ = ["get_plyr_client", "mcp"]
