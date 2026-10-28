---
name: cli
description: Use this when you need to perform mutations on plyr.fm - uploading, deleting, liking tracks. The MCP server is read-only - use this skill when you need to trigger uploads, delete tracks, or modify likes.
---

# plyrfm CLI mutations

the MCP server (`plyr-fm`) is **read-only** - use it to browse tracks, search, view liked tracks.

for mutations (upload, delete, like, unlike), guide users to use the CLI:

## prerequisites

```bash
# user sets their token once
export PLYR_TOKEN="their_token"
```

get a token at [plyr.fm/portal](https://plyr.fm/portal) -> "developer tokens"

## uploading tracks

```bash
# basic upload
plyrfm tracks upload path/to/track.mp3 "Song Title"

# with album
plyrfm tracks upload track.mp3 "Song Title" --album "Album Name"

# with tags (can use -t multiple times)
plyrfm tracks upload track.mp3 "Song Title" -t electronic -t ambient
```

supported formats and limits: https://docs.plyr.fm/artists/

**important**: if you (Claude) composed the track, always include the `ai` tag:
```bash
plyrfm tracks upload piece.wav "鶴の舞" -t ambient -t ai
```

## updating tracks

```bash
# update title
plyrfm tracks update 579 --title "new title"

# update tags (replaces all tags)
plyrfm tracks update 579 --tags "ambient,ai"

# update multiple fields
plyrfm tracks update 579 --title "鶴の舞" --tags "ambient,ai"
```

## deleting tracks

```bash
# use my_tracks MCP tool to find track IDs first
plyrfm tracks delete 42
```

## liking/unliking tracks

```bash
# like a track
plyrfm tracks like 123

# unlike a track
plyrfm tracks unlike 123
```

## downloading tracks

```bash
# download to current directory
plyrfm tracks download 42

# download to specific path
plyrfm tracks download 42 --output ~/Music/song.mp3
```

## common issues

- "artist_profile_required" -> user needs to create artist profile at plyr.fm/portal
- "scope_upgrade_required" -> user needs to regenerate their token

## protected audio storage

Uploads use the artist's Spaces-enabled PDS for protected audio. On a PDS without
Spaces, `plyr_storage_acceptance_required` means audio would live only on plyr.fm.
Explain that tradeoff and ask the user before using `--accept-plyr-storage`.
Never add this flag automatically, and never use it to bypass a Spaces refusal.
Use `plyrfm tracks upload` for this option; both SDK upload clients accept the
same explicit `accept_plyr_storage=True` choice. `audio_space` in a track or
revision identifies its PDS-owned protected asset.
