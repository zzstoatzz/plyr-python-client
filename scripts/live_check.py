"""Read-only deployed HTTP/SDK/MCP consistency check; never mutates a library."""

import argparse
import asyncio

import httpx
from fastmcp import Client
from plyrfm import AsyncPlyrClient
from plyrfm_mcp.server import mcp


async def run(url: str | None) -> None:
    async with (
        AsyncPlyrClient() as sdk,
        Client(url or mcp) as tools,
        httpx.AsyncClient() as http,
    ):
        query = {"query": "ambient", "type": "tracks", "limit": 2}
        result = await tools.call_tool("search", query)
        search = await sdk.discover.search("ambient", type="tracks", limit=2)
        assert result.structured_content == search.model_dump(
            mode="json", by_alias=True
        )
        selected = next(row for row in search.results if row.type == "track")
        track = await sdk.tracks.get(selected.id)
        detail = await tools.call_tool("get_track", {"track_id": selected.id})
        assert detail.structured_content == track.model_dump(mode="json", by_alias=True)
        response = await http.get(f"{sdk._api_url}/tracks/{selected.id}")
        response.raise_for_status()
        raw = response.json()
        assert raw["id"] == track.id
        assert raw["r2_url"] == track.audio_url
        assert raw["gated"] == track.gated
        assert raw["visibility"] == track.visibility
        print(
            f"PASS HTTP/SDK/MCP search, identity, audio URL and access fields (track {track.id})"
        )
        definitions = {tool.name: tool for tool in await tools.list_tools()}
        schema = definitions["search"].input_schema
        assert schema["properties"]["query"].get("minLength") == 2, (
            "deployed search schema is stale"
        )
        assert schema["properties"]["limit"].get("maximum") == 50, (
            "deployed limit schema is stale"
        )
        print("PASS deployed input constraints")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Hosted MCP; omit to evaluate the local checkout")
    args = parser.parse_args()
    asyncio.run(run(args.url))


if __name__ == "__main__":
    main()
