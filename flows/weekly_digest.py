"""weekly plyr.fm digest flow.

gathers stats from public plyr.fm API via MCP, produces a structured report.
first run establishes baseline; subsequent runs compare to previous week.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from prefect import flow
from prefect.variables import Variable
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.anthropic import AnthropicModel

# -----------------------------------------------------------------------------
# output types
# -----------------------------------------------------------------------------


class TrackHighlight(BaseModel):
    """a notable track to feature in the digest."""

    track_id: int
    title: str
    artist: str
    artist_handle: str
    play_count: int
    reason: str = Field(
        description="why this track is notable (e.g. 'most played', 'new artist')"
    )


class ArtistSpotlight(BaseModel):
    """an artist worth highlighting."""

    handle: str
    display_name: str | None
    track_count: int
    total_plays: int
    reason: str = Field(description="why spotlight this artist")


class WeeklyStats(BaseModel):
    """aggregate stats for the week."""

    total_tracks: int
    total_plays: int
    unique_artists: int
    new_tracks_this_period: int = Field(
        description="tracks created in the observation period"
    )
    top_file_types: dict[str, int] = Field(description="count of tracks by file type")


class WeeklyDigest(BaseModel):
    """structured output for the weekly plyr.fm digest."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    period_start: datetime | None = Field(
        default=None, description="start of observation period (None for baseline)"
    )
    period_end: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    stats: WeeklyStats
    top_tracks: list[TrackHighlight] = Field(description="top 5 tracks by play count")
    rising_tracks: list[TrackHighlight] = Field(
        description="tracks gaining momentum (new or fast-growing)"
    )
    artist_spotlights: list[ArtistSpotlight] = Field(
        default_factory=list, description="1-3 artists to highlight"
    )
    vibe_summary: str = Field(
        description="2-3 sentence summary of the week's musical vibe/themes"
    )
    fun_fact: str | None = Field(
        default=None, description="an interesting observation from the data"
    )


# -----------------------------------------------------------------------------
# agent setup
# -----------------------------------------------------------------------------

DIGEST_PROMPT = """\
you are a music curator analyzing plyr.fm, a community music platform on bluesky.

use the plyr.fm MCP tools to explore public tracks and gather data for a weekly digest.

your tasks:
1. list all public tracks (use list_tracks with a reasonable limit like 50-100)
2. identify the top 5 tracks by play_count
3. find "rising" tracks - newer uploads or tracks with notable engagement
4. spotlight 1-3 interesting artists based on their catalog
5. analyze track titles/artists to write a brief "vibe summary"
6. note any fun facts (e.g. most common file type, prolific uploaders)

be creative with your vibe summary - look for themes, genres hinted at in titles,
interesting artist names, etc.

this is a baseline run, so period_start should be None.
"""


def create_digest_agent() -> Agent[None, WeeklyDigest]:
    """create agent with plyr.fm MCP for gathering digest data."""
    plyr_mcp = MCPServerStreamableHTTP(url="https://plyrfm.fastmcp.app/mcp/")

    return Agent(
        model=AnthropicModel("claude-sonnet-4-5-20250929"),
        output_type=WeeklyDigest,
        system_prompt=DIGEST_PROMPT,
        mcp_servers=[plyr_mcp],
    )


# -----------------------------------------------------------------------------
# flow
# -----------------------------------------------------------------------------


VARIABLE_NAME = "plyr_weekly_digest"


@flow(name="plyr-weekly-digest", log_prints=True)
async def weekly_digest_flow() -> WeeklyDigest:
    """gather weekly plyr.fm digest.

    reads previous digest from prefect variable for comparison.
    stores new digest back to the same variable.

    returns:
        WeeklyDigest with stats and highlights
    """
    print("🎵 starting plyr.fm weekly digest...")

    agent = create_digest_agent()

    # load previous digest from prefect variable (use sync API for compatibility)
    previous_data = Variable.get(VARIABLE_NAME, default=None)
    if previous_data and isinstance(previous_data, dict):
        previous = WeeklyDigest.model_validate(previous_data)
        context = f"""
        this is a comparison run. previous digest from {previous.generated_at}:
        - total tracks: {previous.stats.total_tracks}
        - total plays: {previous.stats.total_plays}
        - unique artists: {previous.stats.unique_artists}

        set period_start to {previous.generated_at} and compare current stats.
        highlight tracks that gained the most plays since then.
        """
        print(f"📊 comparing to previous digest from {previous.generated_at}")
    else:
        context = """
        this is a baseline run - first digest, no previous data to compare.
        gather current stats and identify standout tracks/artists.
        set period_start to None.
        """
        print("📊 baseline run - establishing initial stats")

    # run agent
    print("🤖 agent exploring plyr.fm...")
    result = await agent.run(context)
    digest = result.output

    # log summary
    print("\n📈 stats:")
    print(f"   tracks: {digest.stats.total_tracks}")
    print(f"   plays: {digest.stats.total_plays}")
    print(f"   artists: {digest.stats.unique_artists}")

    print("\n🏆 top tracks:")
    for t in digest.top_tracks[:3]:
        print(f"   - {t.title} by {t.artist} ({t.play_count} plays)")

    print(f"\n🎤 vibe: {digest.vibe_summary}")

    if digest.fun_fact:
        print(f"\n💡 fun fact: {digest.fun_fact}")

    # save digest to prefect variable (use sync API for compatibility)
    digest_json = digest.model_dump_json()
    digest_value = json.loads(digest_json)
    print(f"\n📝 digest JSON length: {len(digest_json)} chars")
    try:
        result = Variable.set(
            name=VARIABLE_NAME,
            value=digest_value,
            overwrite=True,
        )
        print(f"💾 saved to prefect variable '{VARIABLE_NAME}' (result: {result})")
    except Exception as e:
        print(f"❌ failed to save variable: {e}")

    return digest


if __name__ == "__main__":
    import asyncio

    asyncio.run(weekly_digest_flow())
