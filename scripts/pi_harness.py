"""Run Pi with only plyr.fm MCP tools in an isolated agent session."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Existing dotenv file with PLYR_TOKEN / PLYR_API_URL",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit Pi's JSON event stream for a tool-call audit",
    )
    parser.add_argument("--model", default="openai-codex/gpt-5.6-luna")
    parser.add_argument("--scenario", default="discovery")
    parser.add_argument(
        "--url", help="Evaluate a hosted MCP instead of the local checkout"
    )
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    scenarios = json.loads((project / "evals/scenarios.json").read_text())
    if args.scenario not in scenarios:
        parser.error(f"Unknown scenario: {args.scenario}")
    prompt = args.prompt or scenarios[args.scenario]["prompt"]
    agent_dir = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi/agent"))
    adapter = agent_dir / "npm/node_modules/pi-mcp-adapter/index.ts"
    if not adapter.is_file():
        parser.error("Install the adapter first: pi install npm:pi-mcp-adapter")
    command = ["run", "--directory", str(project)]
    if args.env_file is not None:
        command.extend(["--env-file", str(args.env_file.resolve())])
    command.append("plyrfm-mcp")
    config = {
        "mcpServers": {
            "plyrfm-mcp": {"command": "uv", "args": command, "lifecycle": "eager"}
        }
    }
    if args.scenario == "anonymous-library":
        config["mcpServers"]["plyrfm-mcp"]["env"] = {"PLYR_TOKEN": ""}
    if args.url:
        config = {"mcpServers": {"plyrfm-mcp": {"url": args.url, "lifecycle": "eager"}}}
    with tempfile.TemporaryDirectory(prefix="plyr-pi-") as directory:
        extension = Path(directory) / "plyr.ts"
        extension.write_text(
            f"import {{ createMcpAdapter }} from {json.dumps(str(adapter))};\n"
            f"export default createMcpAdapter({{ config: {json.dumps(config)} }});\n"
        )
        pi_args = [
            "pi",
            "--model",
            args.model,
            "--no-session",
            "--no-extensions",
            "--extension",
            str(extension),
            "--no-context-files",
            "--no-skills",
            "--no-prompt-templates",
            "--no-builtin-tools",
            "--tools",
            "mcp",
            "--print",
        ]
        if args.json:
            pi_args.extend(["--mode", "json"])
        pi_args.append(prompt)
        subprocess.run(pi_args, cwd=directory, check=True, timeout=args.timeout)


if __name__ == "__main__":
    main()
