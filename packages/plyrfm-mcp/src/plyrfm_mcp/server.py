"""plyr.fm MCP server implementation using fastmcp."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from plyrfm import AudioRevision, Playlist, PlaylistWithTracks, Track
from plyrfm._internal.types import PlaylistRecommendations, SearchResponse, Tag
from pydantic import Field

from plyrfm_mcp.client import get_plyr_client

mcp = FastMCP(
    "plyr.fm",
    instructions="""Discover audio with search or exact tags, then inspect a selected track.
Search is lexical/fuzzy: a title match does not establish how audio sounds.
Share https://plyr.fm/track/{id}; r2_url is an audio URL, not proof of playback.
This server is read-only and cannot control the browser player. Use the CLI,
SDK, or HTTP API for user-authorized changes. Read back state after a write.
Library reads need PLYR_TOKEN (stdio) or x-plyr-token (HTTP); never put tokens
in tool arguments. Read plyr://interfaces for interface selection guidance.""",
)


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
- they need a developer token (plyr.fm/settings#developer)

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
Consult https://docs.plyr.fm/artists/ for current upload formats and limits.

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
- downloads follow the artist's policy; some require authentication
- use search or my_tracks to find track IDs; do not treat streaming access as download permission
"""


# -----------------------------------------------------------------------------
# track tools
# -----------------------------------------------------------------------------


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def list_tracks(limit: Annotated[int, Field(ge=1, le=100)] = 20) -> list[Track]:
    """list public tracks on plyr.fm. no auth required."""
    async with get_plyr_client() as client:
        return await client.tracks.list(limit=limit)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def get_track(
    track_id: Annotated[int, Field(gt=0)]
    | Annotated[str, Field(pattern=r"^at://[^/]+/[^/]+/[^/]+$")],
) -> Track:
    """Inspect a track by numeric ID or AT-URI, including access fields and audio URL.

    Public metadata needs no token; private access uses the caller's token.
    Return https://plyr.fm/track/{id} for listening; this does not start playback."""
    async with get_plyr_client() as client:
        return await client.tracks.get(track_id)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def my_tracks(limit: Annotated[int, Field(ge=1, le=100)] = 20) -> list[Track]:
    """list your own tracks. requires auth (PLYR_TOKEN or x-plyr-token header)."""
    async with get_plyr_client(require_auth=True) as client:
        return await client.tracks.my(limit=limit)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def search(
    query: Annotated[str, Field(min_length=2, max_length=100)],
    type: str | None = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 20,
) -> SearchResponse:
    """Find candidates using lexical/fuzzy matching; inspect selected tracks with get_track.

    Counts describe returned results, not catalog totals. Narrow the query for more
    useful matches; there is no offset and titles are not evidence of sound.

    args:
        query: search query (2-100 chars)
        type: filter by type (tracks, artists, albums, tags, playlists - comma-separated)
        limit: max results per type (1-50)
    """
    async with get_plyr_client() as client:
        return await client.discover.search(query, type=type, limit=limit)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def top_tracks(limit: Annotated[int, Field(ge=1, le=100)] = 10) -> list[Track]:
    """get top tracks by like count. no auth required."""
    async with get_plyr_client() as client:
        return await client.discover.top_tracks(limit=limit)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def list_tags(
    q: str | None = None, limit: Annotated[int, Field(ge=1, le=100)] = 20
) -> list[Tag]:
    """list tags with track counts. no auth required.

    args:
        q: optional prefix search query
        limit: max results (1-100)
    """
    async with get_plyr_client() as client:
        return await client.tags.list(q=q, limit=limit)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def tracks_by_tag(
    tag: str, limit: Annotated[int, Field(ge=1, le=100)] = 50
) -> list[Track]:
    """get tracks with a specific tag. no auth required."""
    async with get_plyr_client() as client:
        return await client.tags.tracks(tag, limit=limit)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def liked_tracks(limit: Annotated[int, Field(ge=1, le=100)] = 20) -> list[Track]:
    """list your liked tracks. requires auth."""
    async with get_plyr_client(require_auth=True) as client:
        return await client.tracks.liked(limit=limit)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def list_revisions(track_id: int) -> list[AudioRevision]:
    """list previous audio versions of a track (newest first). requires auth + ownership.

    args:
        track_id: plyr.fm track ID
    """
    async with get_plyr_client(require_auth=True) as client:
        return await client.tracks.revisions(track_id)


# -----------------------------------------------------------------------------
# playlist tools (read-only)
# -----------------------------------------------------------------------------


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def list_playlists() -> list[Playlist]:
    """list your playlists. requires auth."""
    async with get_plyr_client(require_auth=True) as client:
        return await client.playlists.list()


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def get_playlist(playlist_id: str) -> PlaylistWithTracks:
    """Inspect a playlist and its ordered tracks. Public playlists need no token;
    private playlists require the owner's token."""
    async with get_plyr_client() as client:
        return await client.playlists.get(playlist_id)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def playlists_by_artist(artist_did: str) -> list[Playlist]:
    """list public playlists by an artist. no auth required.

    args:
        artist_did: ATProto DID of the artist (did:plc:... or did:web:...)
    """
    async with get_plyr_client() as client:
        return await client.playlists.by_artist(artist_did)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def playlist_recommendations(
    playlist_id: str, limit: Annotated[int, Field(ge=1, le=10)] = 3
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


@mcp.resource("plyr://interfaces")
def interfaces_resource() -> str:
    """Choose an interface and understand verification boundaries."""
    return """Use MCP for conversational discovery and library inspection.
Use the CLI for terminal workflows and authorized uploads or edits.
Use the Python SDK for typed, composable sync/async applications.
Use HTTP for other languages, exact schemas, pagination, or API-only features.
All share the same backend; MCP deliberately exposes reads only.
Start: https://plyr.fm/llms.txt
API schema: https://api.plyr.fm/openapi.json
Guide: https://docs.plyr.fm/developers/agents/
A search hit is a summary. Track detail establishes metadata, not playback.
Preserve visibility and gating; do not invent missing duration or sound.
"""


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
