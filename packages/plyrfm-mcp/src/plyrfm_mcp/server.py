"""plyr.fm MCP server implementation using fastmcp."""

from __future__ import annotations

from fastmcp import FastMCP
from plyrfm import Playlist, PlaylistWithTracks, Track
from plyrfm._internal.types import PlaylistRecommendations, SearchResponse, Tag

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
plyrfm tracks upload path/to/track.mp3 "Song Title"

# upload with album
plyrfm tracks upload track.mp3 "Song Title" --album "Album Name"

# upload with tags (can use -t multiple times)
plyrfm tracks upload track.mp3 "Song Title" -t electronic -t ambient
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
plyrfm tracks download 42

# download to specific path
plyrfm tracks download 42 --output ~/Music/song.mp3
```

## SDK usage (if user is writing python code)

```python
from plyrfm import PlyrClient

client = PlyrClient(token="their_token")
path = client.tracks.download(42)
path = client.tracks.download(42, output="~/Music/song.mp3")
```

## notes
- download requires authentication
- use the my_tracks tool to help user find their track IDs
"""


# -----------------------------------------------------------------------------
# track tools
# -----------------------------------------------------------------------------


@mcp.tool
@filterable
async def list_tracks(limit: int = 20) -> list[Track]:
    """list public tracks on plyr.fm. no auth required."""
    async with get_plyr_client() as client:
        return await client.tracks.list(limit=limit)


@mcp.tool
async def get_track(track_id: int) -> Track:
    """get a single track by ID. no auth required."""
    async with get_plyr_client() as client:
        return await client.tracks.get(track_id)


@mcp.tool
@filterable
async def my_tracks(limit: int = 20) -> list[Track]:
    """list your own tracks. requires auth (PLYR_TOKEN or x-plyr-token header)."""
    async with get_plyr_client(require_auth=True) as client:
        return await client.tracks.my(limit=limit)


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
        return await client.discover.search(query, type=type, limit=limit)


@mcp.tool
@filterable
async def top_tracks(limit: int = 10) -> list[Track]:
    """get top tracks by like count. no auth required."""
    async with get_plyr_client() as client:
        return await client.discover.top_tracks(limit=limit)


@mcp.tool
@filterable
async def list_tags(q: str | None = None, limit: int = 20) -> list[Tag]:
    """list tags with track counts. no auth required.

    args:
        q: optional prefix search query
        limit: max results (1-100)
    """
    async with get_plyr_client() as client:
        return await client.tags.list(q=q, limit=limit)


@mcp.tool
@filterable
async def tracks_by_tag(tag: str, limit: int = 50) -> list[Track]:
    """get tracks with a specific tag. no auth required."""
    async with get_plyr_client() as client:
        return await client.tags.tracks(tag, limit=limit)


@mcp.tool
@filterable
async def liked_tracks(limit: int = 20) -> list[Track]:
    """list your liked tracks. requires auth."""
    async with get_plyr_client(require_auth=True) as client:
        return await client.tracks.liked(limit=limit)


# -----------------------------------------------------------------------------
# playlist tools (read-only)
# -----------------------------------------------------------------------------


@mcp.tool
@filterable
async def list_playlists() -> list[Playlist]:
    """list your playlists. requires auth."""
    async with get_plyr_client(require_auth=True) as client:
        return await client.playlists.list()


@mcp.tool
async def get_playlist(playlist_id: str) -> PlaylistWithTracks:
    """get a playlist with its tracks. no auth required."""
    async with get_plyr_client() as client:
        return await client.playlists.get(playlist_id)


@mcp.tool
@filterable
async def playlists_by_artist(artist_did: str) -> list[Playlist]:
    """list public playlists by an artist. no auth required.

    args:
        artist_did: ATProto DID of the artist (did:plc:... or did:web:...)
    """
    async with get_plyr_client() as client:
        return await client.playlists.by_artist(artist_did)


@mcp.tool
async def playlist_recommendations(
    playlist_id: str, limit: int = 3
) -> PlaylistRecommendations:
    """get track recommendations for a playlist. requires auth.

    args:
        playlist_id: playlist ID (UUID)
        limit: max recommendations (1-10, default 3)
    """
    async with get_plyr_client(require_auth=True) as client:
        return await client.playlists.recommendations(playlist_id, limit=limit)


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
