# plan: SDK namespace restructure + playlist support

**date**: 2026-04-13
**issue**: #26

## goal

restructure the SDK and CLI from flat methods/commands to noun-first namespaces. add playlist support as part of this restructure. the canonical shape is resource-first, with consistent verbs inside each namespace.

## design

### CLI: `plyrfm <resource> <verb> [args] [flags]`

```
plyrfm tracks list [--limit N]
plyrfm tracks get <ref>
plyrfm tracks upload <file> <title> [--album NAME] [-t TAG ...]
plyrfm tracks update <ref> [--title TEXT] [--tags TAG,TAG,...]
plyrfm tracks delete <ref> [--yes]
plyrfm tracks download <ref> [--output FILE]
plyrfm tracks like <ref>
plyrfm tracks unlike <ref>

plyrfm playlists list
plyrfm playlists get <id>
plyrfm playlists create <name>
plyrfm playlists update <id> [--name NAME] [--show-on-profile / --no-show-on-profile]
plyrfm playlists delete <id> [--yes]
plyrfm playlists add-track <id> <track>
plyrfm playlists remove-track <id> <track>

plyrfm tags list [--limit N]
plyrfm tags get <name> [--limit N]

plyrfm artists get [<handle>]
plyrfm artists me
plyrfm artists update [--bio TEXT] [--display-name NAME] [--support-url URL]

plyrfm discover search <query> [--limit N]
plyrfm discover top [--limit N]
plyrfm discover liked [--limit N]

plyrfm me
```

`<ref>` = track ID (int) or AT-URI (at://...) everywhere.

### SDK: `client.<namespace>.<verb>(...)`

```python
client.tracks.list(limit=50)
client.tracks.get(ref)
client.tracks.get_by_uri(uri)
client.tracks.upload(file, title, ...)
client.tracks.update(ref, patch)
client.tracks.delete(ref)
client.tracks.download(ref, output)
client.tracks.like(ref)
client.tracks.unlike(ref)
client.tracks.liked(limit=50)

client.playlists.list()
client.playlists.get(id)
client.playlists.by_artist(did)
client.playlists.create(name)
client.playlists.update(id, name=..., show_on_profile=...)
client.playlists.delete(id)
client.playlists.add_track(id, track_ref)
client.playlists.remove_track(id, track_ref)
client.playlists.recommendations(id, limit=3)

client.tags.list(q=..., limit=20)
client.tags.tracks(name, limit=50)

client.artists.me()
client.artists.get_profile()
client.artists.update_profile(patch)

client.discover.search(query, type=..., limit=20)
client.discover.top_tracks(limit=10)

client.me()
```

### MCP: unchanged — flat tool names are appropriate for MCP protocol

## not doing

- playlist cover upload, reorder, get-by-uri
- album support (separate issue #25)
- for-you, now-playing, etc. (separate issue #29)

## phases

### phase 1: SDK namespace restructure

move all existing flat methods into namespace classes. the client object
creates namespace instances that hold a back-reference to the parent client
for HTTP access and auth.

**files**:
- `packages/plyrfm/src/plyrfm/client.py` — PlyrClient/AsyncPlyrClient become thin shells with namespace properties + `me()`
- new namespace classes in client.py (keep in one file for now — split later if needed)

### phase 2: playlist namespace

add `PlaylistsNamespace` / `AsyncPlaylistsNamespace` with all playlist methods.

### phase 3: CLI restructure

rewrite CLI with noun-first subcommand routing. `plyrfm <resource> <verb>`.

### phase 4: update tests + exports

update client parity test, exports, MCP server imports.

## testing

- client parity test: verify sync/async namespace methods match
- `uv run ruff check` on all packages
- `uv run pytest` passes
- `plyrfm --help` shows new structure
