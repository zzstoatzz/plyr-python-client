"""weekly plyr.fm digest flow.

gathers stats from public plyr.fm API via MCP, produces a structured report,
and posts a thread to bluesky with the results.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from atproto import Client, models
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


class ThreadContent(BaseModel):
    """the bluesky thread content to post."""

    posts: list[str] = Field(
        description="list of post texts (max 300 chars each). "
        "post 1: header + stats, post 2: top tracks, post 3: rising/spotlight, "
        "post 4: vibe summary, post 5: fun fact (optional)"
    )


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
    thread: ThreadContent = Field(
        description="the bluesky thread content ready to post"
    )


# -----------------------------------------------------------------------------
# bluesky posting
# -----------------------------------------------------------------------------


def post_thread(posts: list[str], max_retries: int = 3) -> str:
    """post a thread to bluesky.

    args:
        posts: list of post texts (max 300 chars each). first post is thread root,
               subsequent posts reply to the previous one.
        max_retries: number of retries for transient failures.

    returns:
        URL of the thread root post.
    """
    handle = os.environ.get("BSKY_HANDLE")
    password = os.environ.get("BSKY_PASSWORD")
    if not handle or not password:
        raise ValueError("BSKY_HANDLE and BSKY_PASSWORD env vars required")

    for attempt in range(max_retries):
        try:
            client = Client()
            client.login(handle, password)

            post_uris = []
            root_uri = None
            parent_uri = None

            for i, text in enumerate(posts):
                if len(text) > 300:
                    text = text[:297] + "..."

                if i == 0:
                    response = client.send_post(text=text)
                    root_uri = response.uri
                    parent_uri = root_uri
                    post_uris.append(root_uri)
                    time.sleep(1)  # longer delay for API stability
                else:
                    parent_post = client.app.bsky.feed.get_posts(
                        params={"uris": [parent_uri]}
                    )
                    if not parent_post.posts:
                        raise ValueError(f"could not find parent post {parent_uri}")

                    parent_cid = parent_post.posts[0].cid
                    parent_ref = models.ComAtprotoRepoStrongRef.Main(
                        uri=parent_uri, cid=parent_cid
                    )

                    root_post = client.app.bsky.feed.get_posts(
                        params={"uris": [root_uri]}
                    )
                    root_cid = root_post.posts[0].cid
                    root_ref = models.ComAtprotoRepoStrongRef.Main(
                        uri=root_uri, cid=root_cid
                    )

                    reply_ref = models.AppBskyFeedPost.ReplyRef(
                        parent=parent_ref, root=root_ref
                    )
                    response = client.send_post(text=text, reply_to=reply_ref)
                    parent_uri = response.uri
                    post_uris.append(response.uri)

                    if i < len(posts) - 1:
                        time.sleep(1)

            rkey = root_uri.split("/")[-1] if root_uri else ""
            return f"https://bsky.app/profile/{handle}/post/{rkey}"

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"attempt {attempt + 1} failed: {e}, retrying...")
                time.sleep(2**attempt)  # exponential backoff
            else:
                raise


# -----------------------------------------------------------------------------
# agent setup
# -----------------------------------------------------------------------------

DIGEST_PROMPT = """\
you are a music curator analyzing plyr.fm, a community music platform on bluesky.

your tasks:
1. use plyr.fm list_tracks to get current public tracks (limit 50-100)
2. identify the top 5 tracks by play_count
3. find "rising" tracks - newer uploads or tracks with notable engagement
4. spotlight 1-3 interesting artists based on their catalog
5. analyze track titles/artists to write a brief "vibe summary"
6. note any fun facts (e.g. most common file type, prolific uploaders)

return the structured digest with thread content ready to post.

thread format (each post max 300 chars):
- post 1: "🎵 plyr.fm weekly digest - [date]" + stats summary
- post 2: top tracks with play counts
- post 3: rising tracks / artist spotlight
- post 4: vibe summary
- post 5: fun fact (if any)

be creative and engaging! this will be posted publicly.
"""

plyr_mcp = MCPServerStreamableHTTP(url="https://plyrfm.fastmcp.app/mcp/")

digest_agent: Agent[None, WeeklyDigest] = Agent(
    model=AnthropicModel("claude-sonnet-4-5-20250929"),
    output_type=WeeklyDigest,
    system_prompt=DIGEST_PROMPT,
    mcp_servers=[plyr_mcp],
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

    the agent gathers data and returns structured output including thread content,
    then we deterministically post the thread.

    returns:
        WeeklyDigest with stats and highlights
    """
    print("🎵 starting plyr.fm weekly digest...")
    print("🤖 agent gathering data...")

    result = await digest_agent.run("gather the weekly plyr.fm digest")
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

    # post the thread
    print("\n📤 posting thread to bluesky...")
    thread_url = post_thread(digest.thread.posts)
    print(f"✅ thread posted: {thread_url}")

    return digest


if __name__ == "__main__":
    import asyncio

    asyncio.run(weekly_digest_flow())
