# plyrfm-mcp

MCP server for [plyr.fm](https://plyr.fm) - expose your music library to LLM clients.

## quickstart

use the hosted server with claude code:

```bash
claude mcp add-json plyr-fm '{"type": "http", "url": "https://plyrfm.fastmcp.app/mcp", "headers": {"x-plyr-token": "YOUR_TOKEN"}}'
```

or run locally via uvx:

```bash
PLYR_TOKEN="your_token" uvx plyrfm-mcp
```

## install

```bash
uv add plyrfm-mcp
```

## tools

this server is **read-only** by design. use the `plyrfm` CLI for mutations (upload, delete, like, unlike).

**public (no auth):**
- `list_tracks` - list public tracks
- `get_track` - get a single track by ID
- `search` - search tracks, artists, albums, tags
- `top_tracks` - get top tracks by likes
- `list_tags` - list all tags with track counts
- `tracks_by_tag` - get tracks with a specific tag

**authenticated:**
- `my_tracks` - list your tracks
- `liked_tracks` - list your liked tracks

## auth

get a developer token at [plyr.fm/portal](https://plyr.fm/portal) -> "developer tokens"
