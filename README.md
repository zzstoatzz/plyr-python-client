# plyr-python-client

python packages for [plyr.fm](https://plyr.fm).

## packages

| package | description | install |
|---------|-------------|---------|
| [plyrfm](./packages/plyrfm) | SDK + CLI | `uv add plyrfm` |
| [plyrfm-mcp](./packages/plyrfm-mcp) | MCP server for LLM clients | `uv add plyrfm-mcp` |

## quick start

### SDK

```python
from plyrfm import PlyrClient

client = PlyrClient()
tracks = client.list_tracks()

# authenticated
client = PlyrClient(token="your_token")
client.upload("song.mp3", "My Song")
```

### CLI

```bash
export PLYR_TOKEN="your_token"
plyrfm list
plyrfm upload track.mp3 "Song Title"
```

### MCP server

use the hosted server with claude code:

```bash
claude mcp add-json plyr-fm '{"type": "http", "url": "https://plyrfm.fastmcp.app/mcp", "headers": {"x-plyr-token": "YOUR_TOKEN"}}'
```

or run your own server locally:

```bash
PLYR_TOKEN="your_token" uvx plyrfm-mcp
```

## auth

get a developer token at [plyr.fm/portal](https://plyr.fm/portal) -> "developer tokens"

## license

see [LICENSE](./LICENSE).