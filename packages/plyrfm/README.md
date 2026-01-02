# plyrfm

python sdk for [plyr.fm](https://plyr.fm) - music on atproto.

## quickstart

requires `uv`. lists recent tracks:

```bash
uv run --with plyrfm python -c "
from plyrfm import PlyrClient

client = PlyrClient()
for t in client.list_tracks(limit=5):
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
tracks = client.list_tracks()
track = client.get_track(42)

# authenticated operations
client = PlyrClient(token="your_token")
my_tracks = client.my_tracks()
client.upload("song.mp3", "My Song")
client.download(42)
```

## CLI

```bash
# set token once
export PLYR_TOKEN="your_token"

# list public tracks
plyrfm list

# list your tracks
plyrfm my-tracks

# upload
plyrfm upload track.mp3 "Song Title"

# download
plyrfm download 42
```

## auth

get a developer token at [plyr.fm/portal](https://plyr.fm/portal) -> "developer tokens"
