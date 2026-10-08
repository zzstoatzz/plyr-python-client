# plyr-python-client

monorepo for audio-related python packages.

## packages

- **dac** (`packages/digital-audio-claudespace`) - programmatic music synthesis via ffmpeg
- **plyrfm** (`packages/plyrfm`) - SDK + CLI for plyr.fm
- **plyrfm-mcp** (`packages/plyrfm-mcp`) - MCP server for LLM clients

## architecture: MCP vs CLI

the MCP server is **read-only** by design:
- browse public tracks
- search tracks, artists, albums, tags
- view liked tracks (with auth)

the CLI handles **mutations**:
- upload tracks
- delete tracks
- like/unlike tracks
- download tracks

use the `/cli` skill to guide users through mutations.

## dev rules

- use `uv` for everything - no pip
- run `uv run ruff check --fix` before commits
- prefer lowercase aesthetics
