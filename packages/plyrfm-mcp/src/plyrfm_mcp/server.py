"""plyr.fm MCP server implementation using fastmcp."""

from __future__ import annotations

from fastmcp import FastMCP
from plyrfm import Track
from plyrfm._internal.types import SearchResponse, Tag

from plyrfm_mcp.client import get_plyr_client
from plyrfm_mcp.filterable import filterable
from plyrfm_mcp.middleware import PlyrAuthMiddleware

mcp = FastMCP("plyr.fm")

# add middleware for per-request authentication via http headers
mcp.add_middleware(PlyrAuthMiddleware())


# -----------------------------------------------------------------------------
# prompts
# -----------------------------------------------------------------------------


@mcp.prompt("upload_guide")
def upload_guide() -> str:
    """instructions for helping users upload tracks via CLI."""
    return """\
# helping users upload tracks to plyr.fm

when a user wants to upload music, guide them through these steps:

## prerequisites
- they need an account at plyr.fm
- they need an artist profile (created at plyr.fm/portal)
- they need a developer token (plyr.fm/portal -> "developer tokens")

## CLI commands to suggest

```bash
# set token (user does this once)
export PLYR_TOKEN="their_token"

# upload a track
plyrfm upload path/to/track.mp3 "Song Title"

# upload with album
plyrfm upload track.mp3 "Song Title" --album "Album Name"

# upload with tags (can use -t multiple times)
plyrfm upload track.mp3 "Song Title" -t electronic -t ambient

# upload with album and tags
plyrfm upload track.mp3 "Song Title" --album "Album Name" -t ai -t podcast
```

## supported formats
mp3, wav, m4a

## tags
tags help users filter and discover tracks. common tags:
- genre tags: electronic, ambient, hip-hop, etc.
- content tags: ai (for AI-generated content), podcast, remix

## common issues
- "artist_profile_required" -> user needs to create artist profile at plyr.fm/portal
- "scope_upgrade_required" -> user needs to regenerate their token
"""


@mcp.prompt("download_guide")
def download_guide() -> str:
    """instructions for helping users download tracks via CLI or SDK."""
    return """\
# helping users download tracks from plyr.fm

when a user wants to download their music, guide them through these options:

## CLI usage

```bash
# user sets their token once
export PLYR_TOKEN="their_token"

# download by track ID
plyrfm download 42

# download to specific path
plyrfm download 42 --output ~/Music/song.mp3
```

## SDK usage (if user is writing python code)

```python
from plyrfm import PlyrClient

# user provides their token
client = PlyrClient(token="their_token")

# download returns the saved path
path = client.download(track_id=42)
path = client.download(track_id=42, output="~/Music/song.mp3")
```

## notes
- download requires authentication
- use the my_tracks tool to help user find their track IDs
"""


# -----------------------------------------------------------------------------
# tools
# -----------------------------------------------------------------------------


@mcp.tool
@filterable
async def list_tracks(limit: int = 20) -> list[Track]:
    """list public tracks on plyr.fm. no auth required."""
    async with get_plyr_client() as client:
        return await client.list_tracks(limit=limit)


@mcp.tool
async def get_track(track_id: int) -> Track:
    """get a single track by ID. no auth required."""
    async with get_plyr_client() as client:
        return await client.get_track(track_id)


@mcp.tool
@filterable
async def my_tracks(limit: int = 20) -> list[Track]:
    """list your own tracks. requires auth (PLYR_TOKEN or x-plyr-token header)."""
    async with get_plyr_client(require_auth=True) as client:
        return await client.my_tracks(limit=limit)


@mcp.tool
async def search(
    query: str, type: str | None = None, limit: int = 20
) -> SearchResponse:
    """search tracks, artists, albums, and tags. no auth required.

    args:
        query: search query (2-100 chars)
        type: filter by type (tracks, artists, albums, tags - comma-separated)
        limit: max results per type (1-50)
    """
    async with get_plyr_client() as client:
        return await client.search(query, type=type, limit=limit)


@mcp.tool
@filterable
async def top_tracks(limit: int = 10) -> list[Track]:
    """get top tracks by like count. no auth required."""
    async with get_plyr_client() as client:
        return await client.top_tracks(limit=limit)


@mcp.tool
@filterable
async def list_tags(q: str | None = None, limit: int = 20) -> list[Tag]:
    """list tags with track counts. no auth required.

    args:
        q: optional prefix search query
        limit: max results (1-100)
    """
    async with get_plyr_client() as client:
        return await client.list_tags(q=q, limit=limit)


@mcp.tool
@filterable
async def tracks_by_tag(tag: str, limit: int = 50) -> list[Track]:
    """get tracks with a specific tag. no auth required."""
    async with get_plyr_client() as client:
        return await client.tracks_by_tag(tag, limit=limit)


@mcp.tool
@filterable
async def liked_tracks(limit: int = 20) -> list[Track]:
    """list your liked tracks. requires auth."""
    async with get_plyr_client(require_auth=True) as client:
        return await client.liked_tracks(limit=limit)


# -----------------------------------------------------------------------------
# resources
# -----------------------------------------------------------------------------


@mcp.resource("plyr://me")
async def me_resource() -> str:
    """current authenticated user identity."""
    try:
        async with get_plyr_client(require_auth=True) as client:
            info = await client.me()
            return f"authenticated as {info.get('handle', 'unknown')} ({info.get('did', 'unknown')})"
    except ValueError:
        return "not authenticated - set PLYR_TOKEN or pass x-plyr-token header"


# -----------------------------------------------------------------------------
# entrypoint
# -----------------------------------------------------------------------------


def main() -> None:
    """run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
