# plyrfm

python sdk for [plyr.fm](https://plyr.fm) - music on atproto.

## quickstart

requires `uv`. lists recent tracks:

```bash
uv run --with plyrfm python -c "
from plyrfm import PlyrClient

client = PlyrClient()
for t in client.tracks.list(limit=5):
    print(f'{t.id}: {t.title} by {t.artist}')
"
```

## install

```bash
uv add plyrfm
```

## usage

```python
from plyrfm import PlyrClient

# public operations (no auth needed)
client = PlyrClient()
tracks = client.tracks.list()
track = client.tracks.get(42)

# authenticated operations
client = PlyrClient(token="your_token")
my_tracks = client.tracks.my()
client.tracks.upload("song.mp3", "My Song")
client.tracks.download(42)
```

## CLI

```bash
# set token once
export PLYR_TOKEN="your_token"

# list public tracks
plyrfm tracks list

# list your tracks
plyrfm tracks my

# upload
plyrfm tracks upload track.mp3 "Song Title"

# download
plyrfm tracks download 42
```

## auth

get a developer token at [plyr.fm/settings#developer](https://plyr.fm/settings#developer)

See [interface choices](../../docs/interfaces.md) and the generated
[capability table](../../docs/surfaces.md). Downloads use the artist-policy
endpoint; streaming access alone does not imply download permission.
