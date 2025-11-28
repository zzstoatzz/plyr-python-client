# plyrfm

python sdk for [plyr.fm](https://plyr.fm) - music streaming on AT Protocol

## installation

```bash
uv add plyrfm
# or
pip install plyrfm
```

## authentication

all operations require a developer token:

1. go to [plyr.fm/portal](https://plyr.fm/portal) -> "your data" -> "developer tokens"
2. create a token (you'll authorize via your PDS)
3. set it in your environment:

```bash
export PLYR_TOKEN="your_token_here"
```

## quick start

### CLI

```bash
# list your tracks
plyr list

# upload a track
plyr upload track.mp3 "My Song" --album "My Album"

# download a track
plyr download 42 -o song.mp3

# delete a track
plyr delete 42 -y

# check auth
plyr me
```

### sync client

```python
from plyrfm import PlyrClient

# uses PLYR_TOKEN from environment
with PlyrClient() as client:
    # list tracks
    tracks = client.list_tracks()
    for track in tracks:
        print(f"{track.id}: {track.title}")

    # upload
    result = client.upload("song.mp3", "My Song", album="My Album")
    print(f"uploaded track {result.track_id}")

    # download
    path = client.download(42, output="song.mp3")
    print(f"saved to {path}")

    # delete
    client.delete(42)
```

### async client

```python
import asyncio
from plyrfm import AsyncPlyrClient

async def main():
    async with AsyncPlyrClient() as client:
        tracks = await client.list_tracks()
        for track in tracks:
            print(f"{track.id}: {track.title}")

        # upload concurrently
        results = await asyncio.gather(
            client.upload("song1.mp3", "Song 1"),
            client.upload("song2.mp3", "Song 2"),
        )

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

### `PlyrClient` / `AsyncPlyrClient`

| method | auth required | description |
|--------|---------------|-------------|
| `list_tracks(limit=50)` | yes | list your tracks |
| `get_track(track_id)` | yes | get track by ID |
| `upload(file, title, album=None)` | yes + artist profile | upload a track |
| `download(track_id, output=None)` | yes | download track audio |
| `delete(track_id)` | yes + ownership | delete a track |
| `me()` | yes | get current user info |

### types

```python
@dataclass
class Track:
    id: int
    title: str
    file_id: str
    file_type: str
    artist: str
    artist_handle: str
    play_count: int
    like_count: int
    album: Album | None
    image_url: str | None
    created_at: datetime | None

@dataclass
class Album:
    id: int
    title: str
    slug: str

@dataclass
class UploadResult:
    track_id: int
    title: str
```

## environment variables

| variable | default | description |
|----------|---------|-------------|
| `PLYR_TOKEN` | - | developer token (required) |
| `PLYR_API_URL` | `https://api.plyr.fm` | API base URL |

## requirements

- python 3.10+
- developer token from plyr.fm

## license

MIT
