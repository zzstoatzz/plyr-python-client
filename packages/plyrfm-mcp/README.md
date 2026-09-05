# plyrfm-mcp

Read-only audio discovery and library inspection for [plyr.fm](https://plyr.fm).
Search or browse tags, inspect selected tracks and playlists, and return listening
links. This MCP cannot play audio in a browser or change a library.

```bash
claude mcp add --transport http plyr-fm https://plyrfm.fastmcp.app/mcp
# or local stdio
claude mcp add plyr-fm -- uvx --prerelease=allow plyrfm-mcp
```

Public discovery needs no token. For private reads, configure `PLYR_TOKEN` locally
or `x-plyr-token` on HTTP requests. Create a token at
[settings](https://plyr.fm/settings#developer); never paste it into chat.
HTTP callers never inherit the server operator's credentials.

Start with `search`, then `get_track` using a returned ID or AT-URI. Search is
lexical/fuzzy; inspect metadata and tags before describing a result. `r2_url` is
an audio URL and `https://plyr.fm/track/{id}` is a listening page. Neither proves
playback happened. Inspect visibility and gating before offering access.

Discover the current tool schemas when connecting. Library reads include
`my_tracks`, `liked_tracks`, `list_playlists`, and owner-only `list_revisions`.
Playlist tools also inspect ordered tracks, public artist playlists and
recommendations. `plyr://me` exposes the caller's identity;
`plyr://interfaces` explains which interface fits each task.

Use the CLI or SDK for authorized changes. See the
[interface guide](../../docs/interfaces.md), generated
[capability table](../../docs/surfaces.md), and
[public agent guide](https://docs.plyr.fm/developers/agents/).
