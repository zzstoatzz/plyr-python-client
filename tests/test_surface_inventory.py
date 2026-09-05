"""New operations must be classified, mapped and documented across surfaces."""

import inspect
import json
from pathlib import Path

from fastmcp import Client
from plyrfm import AsyncPlyrClient, PlyrClient
from plyrfm.cli import app
from plyrfm_mcp.server import mcp

ROOT = Path(__file__).resolve().parents[1]
OPERATIONS = json.loads((ROOT / "contracts/surfaces.json").read_text())


def methods(client: PlyrClient | AsyncPlyrClient) -> set[str]:
    names = {"me"}
    for namespace, obj in vars(client).items():
        if namespace.startswith("_"):
            continue
        names.update(
            f"{namespace}.{name}"
            for name, _ in inspect.getmembers(obj, inspect.ismethod)
            if not name.startswith("_")
        )
    return names


async def test_inventory_covers_real_surfaces() -> None:
    expected = {row["sdk"] for row in OPERATIONS}
    assert len(expected) == len(OPERATIONS), "duplicate operation"
    with PlyrClient() as sync:
        assert methods(sync) == expected
    async with AsyncPlyrClient() as async_client:
        assert methods(async_client) == expected
    async with Client(mcp) as client:
        tools = await client.list_tools()
    assert {tool.name for tool in tools} == {r["mcp"] for r in OPERATIONS if r["mcp"]}
    for row in OPERATIONS:
        for surface in ["cli", "mcp"]:
            assert bool(row[surface]) != bool(row[f"{surface}_note"]), row
        if row["cli"]:
            command = app
            for part in row["cli"].split():
                command = command[part]
            assert command.default_command is not None, row
    for tool in tools:
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False


async def test_sync_async_full_signatures() -> None:
    with PlyrClient() as sync:
        async with AsyncPlyrClient() as async_client:
            for row in OPERATIONS:
                left, right = sync, async_client
                for name in row["sdk"].split("."):
                    left, right = getattr(left, name), getattr(right, name)
                assert inspect.signature(left) == inspect.signature(right), row["sdk"]
