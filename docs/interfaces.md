# choose an interface

Use the surface that fits how you work. They share one API and the same SDK models;
they have deliberately different jobs.

| use case | start here | why |
| --- | --- | --- |
| ask an assistant to find audio or inspect a library | hosted MCP, `https://plyrfm.fastmcp.app/mcp` | bounded read tools, input constraints, explicit access and playback limits |
| run those tools locally with your own environment | `uvx --prerelease=allow plyrfm-mcp` | same MCP, local stdio credentials and API URL |
| work in a terminal, upload, edit, or manage tracks | `uvx plyrfm --help` | readable output and explicit commands; no agent required |
| compose an application or repeatable Python workflow | `PlyrClient` / `AsyncPlyrClient` | typed results, full control over composition, sync and async parity |
| use another language, inspect precise schemas, or use API-only features | `https://api.plyr.fm/openapi.json` | complete HTTP surface, including features not yet wrapped by the SDK |

The CLI also supports public reads. The MCP intentionally exposes no write tools
and cannot control the web player. A token grants access; it does not authorize
an assistant to change a user's library. After an authorized write through the
CLI, SDK or API, read the affected resource again before claiming success.

The [capability table](surfaces.md) is generated from the reviewed operation
inventory. A blank mapping is never implicit: every omitted CLI or MCP operation
has a reason. API-only features include browser sessions, live player/queue state,
radio, jams, and features not represented in the SDK namespaces.

## credentials

Create a developer token at https://plyr.fm/settings#developer. Keep it in local
configuration, never in a tool argument or chat. CLI/SDK/local MCP read
`PLYR_TOKEN`; `PLYR_API_URL` selects the backend. Hosted MCP accepts
`x-plyr-token` on each request and never falls back to the server operator's token.
Public reads may use the caller's token for private/gated access, but that does
not make every resource accessible.

## parity that stays checked

`just check-interfaces` is the pre-commit gate and runs in CI. It checks:

- every public sync/async SDK operation has the same signature and an inventory entry;
- every MCP tool and mapped CLI command exists, and every MCP tool has a behavioral case;
- real sync SDK, async SDK, MCP calls and CLI argument parsing send matching HTTP
  reads and preserve response aliases, access fields, filters and result limits;
- sync SDK, async SDK and CLI mutation payloads agree against synthetic HTTP responses (including uploads, edits and playlist operations);
- HTTP request paths and query fields exist in the reviewed API schema;
- generated capability documentation matches the inventory and Python SDK examples bind to real method signatures;
- anonymous HTTP callers cannot inherit server credentials or another caller's identity.

CI also checks the SDK against the current backend source schema. The backend
repository runs the reciprocal check for every PR and main push. Response, input
and parameter changes require reviewing the SDK models and mappings, updating
`contracts/http.json`, and copying that reviewed snapshot to
`plyr.fm/docs/internal/contracts/client-api.json`. These checks export schemas
without starting services or connecting to databases.

Add a supported operation to `contracts/surfaces.json`, implement its mappings or
state why a surface omits it, add a real boundary test, and run `just surfaces`.
Extending the HTTP wrapper style requires extending the AST request checker; it
is a guard for these wrappers, not a proof of arbitrary Python behavior.

Run `uv run python scripts/live_check.py --url https://plyrfm.fastmcp.app/mcp`
to compare live results and detect a stale deployment.

Offline checks are repeatable merge gates. Live checks catch deployed-version
drift; Pi evaluations measure what an agent accomplishes. Neither replaces the other.

## agent evaluations

Install Pi and `pi install npm:pi-mcp-adapter`, then use its existing provider
credentials. The harness disables shell/file tools, other extensions, context
files and saved sessions so the result measures this MCP.

```bash
just eval-mcp --scenario discovery --json
just eval-mcp --scenario handoff --json
just eval-mcp --scenario anonymous-library --json
just eval-mcp --scenario discovery --url https://plyrfm.fastmcp.app/mcp --json
```

Pass `--model provider/model` to compare models. Scenarios and human review
rubrics live in `evals/scenarios.json`; the JSON event stream records tool
arguments, results, model and usage for inspection. Keep transcripts local.
An agent process exiting successfully is not a passing evaluation: review the
rubric against tool evidence and the final response.

For a read-only authenticated trial, configure `PLYR_TOKEN` via an existing
`.env`, then use `--env-file /path/to/.env --scenario authenticated-library`.
Use a test account for private reads. Do not use real likes, uploads or deletions
as connectivity probes.

## publishing access

uploads without a publishing override use the artist's Portal defaults (or the
album's saved settings). the resolved policy is saved on the track; later Portal
changes affect future uploads, not the existing catalog.

```python
from plyrfm import PlyrClient, PublishingDefaults, PublishingPolicy

client = PlyrClient(token="your_token")
client.tracks.upload(
    "song.wav",
    "My Song",
    publishing=PublishingDefaults(access=PublishingPolicy(downloads="off")),
)
```

the equivalent CLI override is:

```sh
plyrfm tracks upload song.wav "My Song" --publishing '{"access":{"listening":"public","downloads":"off","visibility":"public"},"attach_rights":false}'
```

listening, original-file downloads, discovery, and optional rights metadata are
separate choices. downloads off still permits playback when listening is public.
it does not prevent recording playback or revoke copies already distributed.

the old upload/update `unlisted` argument and CLI flags are removed. for a new
unlisted upload, set `access.visibility` to `unlisted` in the publishing override.
use Portal to change access on existing tracks; metadata updates do not change it.
private Space access still requires a compatible PDS and its native authorization.
