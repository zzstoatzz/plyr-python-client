# plyrfm

python sdk for [plyr.fm](https://plyr.fm) - music streaming on AT Protocol

## installation

```bash
uv add plyrfm
# or
pip install plyrfm
```

## authentication

some operations (listing public tracks, getting a track by ID) work without auth.

for authenticated operations (upload, download, delete, my-tracks):

1. go to [plyr.fm/portal](https://plyr.fm/portal) -> "your data" -> "developer tokens"
2. create a token (you'll authorize via your PDS)
3. set it in your environment:

```bash
export PLYR_TOKEN="your_token_here"
```

## quick start

### CLI

```bash
# public (no auth required)
plyr list                        # list all tracks

# authenticated (requires PLYR_TOKEN)
plyr my-tracks                   # list your tracks
plyr upload track.mp3 "My Song"  # upload
plyr download 42 -o song.mp3     # download
plyr delete 42 -y                # delete
plyr me                          # check auth
```

### sync client

```python
from plyrfm import PlyrClient

# public operations (no auth)
client = PlyrClient()
tracks = client.list_tracks()
track = client.get_track(42)

# authenticated operations
client = PlyrClient(token="your_token")  # or set PLYR_TOKEN
my_tracks = client.my_tracks()
result = client.upload("song.mp3", "My Song")
client.delete(result.track_id)
```

### async client

```python
import asyncio
from plyrfm import AsyncPlyrClient

async def main():
    # public (no auth)
    async with AsyncPlyrClient() as client:
        tracks = await client.list_tracks()

    # authenticated
    async with AsyncPlyrClient(token="your_token") as client:
        await client.upload("song.mp3", "My Song")

asyncio.run(main())
```

### explicit configuration

```python
from plyrfm import PlyrClient

# pass token directly
client = PlyrClient(token="your_token")

# use staging API
client = PlyrClient(api_url="https://api-stg.plyr.fm")

# both
client = PlyrClient(
    token="your_token",
    api_url="https://api-stg.plyr.fm",
)
```

## API reference

| method | auth | description |
|--------|------|-------------|
| `list_tracks(limit=50)` | no | list all public tracks |
| `get_track(track_id)` | no | get track by ID |
| `my_tracks(limit=50)` | yes | list your tracks (with liked state) |
| `upload(file, title, album=None)` | yes | upload a track |
| `download(track_id, output=None)` | yes | download track audio |
| `delete(track_id)` | yes | delete a track |
| `me()` | yes | get current user info |

## environment variables

| variable | default | description |
|----------|---------|-------------|
| `PLYR_TOKEN` | - | developer token (for authenticated operations) |
| `PLYR_API_URL` | `https://api.plyr.fm` | API base URL |

## requirements

- python 3.10+
- developer token from plyr.fm

## license

MIT
