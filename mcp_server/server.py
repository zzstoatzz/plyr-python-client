"""plyr.fm MCP server implementation using fastmcp."""

from __future__ import annotations

from fastmcp import FastMCP

from mcp_server.client import get_plyr_client
from mcp_server.middleware import PlyrAuthMiddleware
from plyrfm import AsyncPlyrClient, Track

mcp = FastMCP("plyr.fm")

# add middleware for per-request authentication via http headers
mcp.add_middleware(PlyrAuthMiddleware())


# -----------------------------------------------------------------------------
# prompts
# -----------------------------------------------------------------------------


@mcp.prompt("upload_guide")
def upload_guide() -> str:
    """guide for uploading tracks via the plyr CLI."""
    return """\
# uploading tracks to plyr.fm

if you have terminal access, use the plyr CLI:

## setup
1. get a token at https://plyr.fm/portal -> "developer tokens"
2. export PLYR_TOKEN="your_token"

## upload
```bash
# basic upload
plyr upload path/to/track.mp3 "My Song Title"

# with album
plyr upload track.mp3 "My Song" --album "My Album"
```

## other useful commands
```bash
plyr my-tracks          # list your tracks
plyr download 42        # download track by id
plyr delete 42          # delete track by id
```

## notes
- supported formats: mp3, wav, flac, aac, ogg
- requires an artist profile (create at plyr.fm/portal)
- tracks are processed async - may take a moment to appear
"""


@mcp.prompt("download_guide")
def download_guide() -> str:
    """guide for downloading tracks via the plyr CLI or SDK."""
    return """\
# downloading tracks from plyr.fm

## CLI usage

```bash
# setup
export PLYR_TOKEN="your_token"

# download a single track by ID
plyr download 42

# download to a specific file
plyr download 42 --output ~/Music/song.mp3
```

## python SDK usage

```python
from plyrfm import PlyrClient

client = PlyrClient(token="your_token")

# download a single track
path = client.download(track_id=42)
print(f"saved to: {path}")

# download to specific location
path = client.download(track_id=42, output="~/Music/song.mp3")
```

## async SDK usage

```python
from plyrfm import AsyncPlyrClient

async with AsyncPlyrClient(token="your_token") as client:
    path = await client.download(track_id=42)
    print(f"saved to: {path}")
```

## notes
- requires authentication (PLYR_TOKEN env var or token= parameter)
- file is saved with original format (mp3, flac, etc.)
- default filename is based on track title
"""


# -----------------------------------------------------------------------------
# tools
# -----------------------------------------------------------------------------


@mcp.tool
async def list_tracks(limit: int = 20) -> list[dict]:
    """list public tracks on plyr.fm. no auth required.

    args:
        limit: max tracks to return (default 20)

    returns:
        list of track metadata dicts
    """
    async with get_plyr_client() as client:
        tracks = await client.list_tracks(limit=limit)
        return [_track_to_dict(t) for t in tracks]


@mcp.tool
async def get_track(track_id: int) -> dict:
    """get a single track by ID. no auth required.

    args:
        track_id: the track's ID

    returns:
        track metadata dict
    """
    async with get_plyr_client() as client:
        track = await client.get_track(track_id)
        return _track_to_dict(track)


@mcp.tool
async def my_tracks(limit: int = 20) -> list[dict]:
    """list your own tracks. requires auth (PLYR_TOKEN or x-plyr-token header).

    args:
        limit: max tracks to return (default 20)

    returns:
        list of track metadata dicts
    """
    async with get_plyr_client(require_auth=True) as client:
        tracks = await client.my_tracks(limit=limit)
        return [_track_to_dict(t) for t in tracks]


@mcp.tool
async def delete_track(track_id: int) -> dict:
    """delete a track. requires auth (PLYR_TOKEN or x-plyr-token header) and ownership.

    args:
        track_id: the track's ID

    returns:
        confirmation dict
    """
    async with get_plyr_client(require_auth=True) as client:
        await client.delete(track_id)
        return {"deleted": track_id}


@mcp.tool
async def whoami() -> dict:
    """get current authenticated user info. requires auth (PLYR_TOKEN or x-plyr-token header).

    returns:
        dict with did and handle
    """
    async with get_plyr_client(require_auth=True) as client:
        return await client.me()


# -----------------------------------------------------------------------------
# resources
# -----------------------------------------------------------------------------


@mcp.resource("plyr://tracks")
async def tracks_resource() -> str:
    """list of recent public tracks."""
    async with AsyncPlyrClient() as client:
        tracks = await client.list_tracks(limit=10)
        lines = ["# recent tracks on plyr.fm\n"]
        for t in tracks:
            lines.append(f"- [{t.id}] {t.title} by {t.artist} ({t.play_count} plays)")
        return "\n".join(lines)


@mcp.resource("plyr://tracks/{track_id}")
async def track_resource(track_id: int) -> str:
    """get track details by ID."""
    async with AsyncPlyrClient() as client:
        t = await client.get_track(track_id)
        album_info = f" from album '{t.album.title}'" if t.album else ""
        return f"""\
# {t.title}

artist: {t.artist} (@{t.artist_handle})
plays: {t.play_count}
likes: {t.like_count}{album_info}
"""


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------


def _track_to_dict(track: Track) -> dict:
    """convert Track to a serializable dict."""
    return {
        "id": track.id,
        "title": track.title,
        "artist": track.artist,
        "artist_handle": track.artist_handle,
        "play_count": track.play_count,
        "like_count": track.like_count,
        "album": track.album.title if track.album else None,
        "image_url": track.image_url,
    }


# -----------------------------------------------------------------------------
# entrypoint
# -----------------------------------------------------------------------------


def main() -> None:
    """run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
