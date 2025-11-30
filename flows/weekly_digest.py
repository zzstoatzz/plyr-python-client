"""weekly plyr.fm digest flow.

gathers stats from public plyr.fm API via MCP, produces a structured report,
and posts a thread to bluesky with the results.
"""

from __future__ import annotations

from datetime import datetime, timezone

from prefect import flow
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

you have access to two MCP servers:
- plyr.fm: for exploring public tracks and gathering music data
- atproto: for posting threads to bluesky and searching previous posts

your tasks:
1. use the atproto search tool to find your previous digest posts (search for "plyr.fm weekly digest")
   - extract the previous stats if found (total tracks, plays, artists)
2. use plyr.fm list_tracks to get current public tracks (limit 50-100)
3. identify the top 5 tracks by play_count
4. find "rising" tracks - newer uploads or tracks with notable engagement
5. spotlight 1-3 interesting artists based on their catalog
6. analyze track titles/artists to write a brief "vibe summary"
7. note any fun facts (e.g. most common file type, prolific uploaders)
8. post a thread to bluesky with your digest using create_thread

thread format (each post max 300 chars):
- post 1: "🎵 plyr.fm weekly digest - [date]" + stats summary
- post 2: top tracks with play counts
- post 3: rising tracks / artist spotlight
- post 4: vibe summary
- post 5: fun fact (if any)

be creative and engaging! this is a public post.
"""

plyr_mcp = MCPServerStreamableHTTP(url="https://plyrfm.fastmcp.app/mcp/")
atproto_mcp = MCPServerStreamableHTTP(url="https://labour-hamster.fastmcp.app/mcp/")

digest_agent: Agent[None, WeeklyDigest] = Agent(
    model=AnthropicModel("claude-sonnet-4-5-20250929"),
    output_type=WeeklyDigest,
    system_prompt=DIGEST_PROMPT,
    mcp_servers=[plyr_mcp, atproto_mcp],
)


@digest_agent.system_prompt
def add_current_time() -> str:
    """inject current UTC time into system prompt."""
    now = datetime.now(timezone.utc)
    return f"current date/time (UTC): {now.isoformat()}"


# -----------------------------------------------------------------------------
# flow
# -----------------------------------------------------------------------------


@flow(name="plyr-weekly-digest", log_prints=True)
async def weekly_digest_flow() -> WeeklyDigest:
    """gather weekly plyr.fm digest and post to bluesky.

    the agent will:
    1. search bluesky for previous digest posts to get comparison data
    2. gather current stats from plyr.fm
    3. generate the digest
    4. post a thread to bluesky with the results

    returns:
        WeeklyDigest with stats and highlights
    """
    print("🎵 starting plyr.fm weekly digest...")
    print("🤖 agent gathering data and posting to bluesky...")

    result = await digest_agent.run(
        "gather the weekly plyr.fm digest and post it as a thread to bluesky"
    )
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

    print("\n✅ digest posted to bluesky!")

    return digest


if __name__ == "__main__":
    import asyncio

    asyncio.run(weekly_digest_flow())
