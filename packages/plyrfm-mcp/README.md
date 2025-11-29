# plyrfm-mcp

MCP server for [plyr.fm](https://plyr.fm) - expose your music library to LLM clients.

## install

```bash
pip install plyrfm-mcp
# or
uv add plyrfm-mcp
```

## usage with claude code

```bash
claude mcp add-json plyr-fm '{"type": "http", "url": "https://plyrfm.fastmcp.app/mcp", "headers": {"x-plyr-token": "YOUR_TOKEN"}}'
```

or run locally:

```bash
export PLYR_TOKEN="your_token"
plyrfm-mcp
```

## tools

- `list_tracks` - list public tracks (supports `_filter` for jmespath filtering)
- `get_track` - get a single track by ID
- `my_tracks` - list your tracks (supports `_filter`)
- `delete_track` - delete a track
- `whoami` - get current user info

## filtering

tools that return lists support a `_filter` parameter for jmespath expressions:

```
# select specific fields
list_tracks(_filter="[*].{id: id, title: title}")

# filter by condition
list_tracks(_filter="[?play_count > `50`]")

# extract values
list_tracks(_filter="[*].title")
```

## auth

get a developer token at [plyr.fm/portal](https://plyr.fm/portal) -> "developer tokens"
