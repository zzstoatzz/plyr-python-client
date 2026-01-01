# audio tools

monorepo for audio-related python packages.

## packages

| package | description |
|---------|-------------|
| [dac](./packages/digital-audio-claudespace) | programmatic music synthesis via ffmpeg |
| [plyrfm](./packages/plyrfm) | SDK + CLI for [plyr.fm](https://plyr.fm) |
| [plyrfm-mcp](./packages/plyrfm-mcp) | MCP server for LLM clients |

install from git:
```bash
uv add dac@git+https://github.com/zzstoatzz/plyr-python-client#subdirectory=packages/digital-audio-claudespace
uv add plyrfm@git+https://github.com/zzstoatzz/plyr-python-client#subdirectory=packages/plyrfm
```

## dac (digital audio claudespace)

compose music programmatically using sine waves, samples, and effects:

```python
from dac import Sine, Sample, mix, Tempo
from dac.compose import Voice, Phrase, DrumKit

tempo = Tempo(bpm=90)

# melodic phrase
melody = Phrase(["C4", "E4", "G4", "C5"])
tracks = melody.render(start_beat=1, tempo=tempo)

# add drums
kit = DrumKit(kick=DrumSound(...), snare=DrumSound(...))
tracks.append(kit.render_kick(1, tempo))

mix(tracks, "output.wav", duration=10)
```

see [dac README](./packages/digital-audio-claudespace/README.md) for details.

## plyrfm

<details>
<summary>SDK + CLI for plyr.fm</summary>

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

or run locally:

```bash
PLYR_TOKEN="your_token" uvx plyrfm-mcp
```

get a developer token at [plyr.fm/portal](https://plyr.fm/portal) -> "developer tokens"

</details>

## license

see [LICENSE](./LICENSE).
