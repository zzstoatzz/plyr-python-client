# audio tools

monorepo for audio-related python packages.

## packages

| package | description |
|---------|-------------|
| [dac](./packages/digital-audio-claudespace) | programmatic music synthesis via ffmpeg |
| [plyrfm](./packages/plyrfm) | SDK + CLI for [plyr.fm](https://plyr.fm) |
| [plyrfm-mcp](./packages/plyrfm-mcp) | MCP server for LLM clients |

## license

see [LICENSE](./LICENSE).

## interfaces and compatibility

See [when to use MCP, CLI, SDK or HTTP](docs/interfaces.md) and the generated
[capability table](docs/surfaces.md). Run `just check-interfaces` before a commit;
CI also checks the current backend contract. Use `just eval-mcp --json` to audit
an isolated Pi session against the local server.
