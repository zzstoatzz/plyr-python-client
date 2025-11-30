"""weekly plyr.fm digest flow.

gathers stats from public plyr.fm API via MCP, produces a structured report,
and posts a thread to bluesky with the results. uses previous digest as baseline.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone

from atproto import Client, models
from prefect import flow
from prefect.variables import Variable
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.anthropic import AnthropicModel

LATEST_DIGEST_VAR = "plyr-digest-latest-url"

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
    reason: str = Field(description="why this track is notable - be specific")


class ArtistSpotlight(BaseModel):
    """an artist worth highlighting."""

    handle: str
    display_name: str | None
    track_count: int
    total_plays: int
    reason: str = Field(description="why spotlight this artist - be specific")


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
        description="list of post texts (max 300 chars each). keep it tight and factual."
    )


class WeeklyDigest(BaseModel):
    """structured output for the weekly plyr.fm digest."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    period_start: datetime | None = Field(
        default=None, description="start of observation period"
    )
    period_end: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    stats: WeeklyStats
    top_tracks: list[TrackHighlight] = Field(description="top 5 tracks by play count")
    rising_tracks: list[TrackHighlight] = Field(
        description="tracks gaining momentum - new uploads or notable engagement"
    )
    artist_spotlights: list[ArtistSpotlight] = Field(
        default_factory=list, description="1-2 artists to highlight"
    )
    vibe_summary: str = Field(description="1 sentence summary of the week's themes")
    fun_fact: str | None = Field(
        default=None, description="one interesting observation from the data"
    )
    thread: ThreadContent = Field(description="the bluesky thread content to post")


class PreviousDigest(BaseModel):
    """parsed stats from a previous digest post."""

    total_tracks: int | None = None
    total_plays: int | None = None
    unique_artists: int | None = None
    top_track: str | None = None
    post_date: str | None = None


# -----------------------------------------------------------------------------
# bluesky helpers
# -----------------------------------------------------------------------------


def get_bsky_client() -> Client:
    """get authenticated bluesky client."""
    handle = os.environ.get("BSKY_HANDLE")
    password = os.environ.get("BSKY_PASSWORD")
    if not handle or not password:
        raise ValueError("BSKY_HANDLE and BSKY_PASSWORD env vars required")
    client = Client()
    client.login(handle, password)
    return client


async def get_previous_digest() -> PreviousDigest | None:
    """fetch previous digest using URL stored in prefect variable."""
    try:
        url = await Variable.aget(LATEST_DIGEST_VAR)
        if not url:
            return None

        # extract post rkey from URL: https://bsky.app/profile/handle/post/RKEY
        parts = url.split("/")
        if len(parts) < 2:
            return None

        handle = parts[-3] if len(parts) >= 3 else os.environ.get("BSKY_HANDLE", "")
        rkey = parts[-1]

        # fetch the post
        client = get_bsky_client()
        # construct AT URI from URL
        # need to resolve handle to DID first
        profile = client.get_profile(actor=handle)
        at_uri = f"at://{profile.did}/app.bsky.feed.post/{rkey}"

        posts = client.app.bsky.feed.get_posts(params={"uris": [at_uri]})
        if not posts.posts:
            return None

        post = posts.posts[0]
        return _parse_digest_post(post.record.text, post.record.created_at)

    except Exception as e:
        print(f"failed to fetch previous digest: {e}")
        return None


def _parse_digest_post(text: str, created_at: str) -> PreviousDigest:
    """extract stats from a digest post."""
    result = PreviousDigest(post_date=created_at[:10] if created_at else None)

    # look for patterns like "57 tracks" or "tracks: 57"
    tracks_match = re.search(r"(\d+)\s*tracks", text, re.IGNORECASE)
    if tracks_match:
        result.total_tracks = int(tracks_match.group(1))

    # look for patterns like "1776 plays" or "plays: 1776"
    plays_match = re.search(r"(\d+)\s*plays", text, re.IGNORECASE)
    if plays_match:
        result.total_plays = int(plays_match.group(1))

    # look for patterns like "24 artists"
    artists_match = re.search(r"(\d+)\s*artists", text, re.IGNORECASE)
    if artists_match:
        result.unique_artists = int(artists_match.group(1))

    return result


def post_thread(posts: list[str], max_retries: int = 3) -> str:
    """post a thread to bluesky with retry logic."""
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
                    time.sleep(1)
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
                time.sleep(2**attempt)
            else:
                raise


# -----------------------------------------------------------------------------
# agent setup
# -----------------------------------------------------------------------------

DIGEST_PROMPT = """\
you are analyzing plyr.fm, a music platform on bluesky.

tasks:
1. use list_tracks (limit 100) to get current public tracks
2. identify top 5 tracks by play_count
3. find rising tracks - recently uploaded or gaining plays
4. spotlight 1-2 interesting artists
5. note one fun fact from the data

style guidelines:
- be direct and factual. no hype, no superlatives
- focus on what changed since last week (if previous stats provided)
- keep posts SHORT. aim for 200 chars, max 280
- use numbers: "+3 new tracks" not "several new tracks"
- if one artist dominates, acknowledge it once and move on to what else is interesting

thread format (4-5 posts, each under 280 chars):
- post 1: "plyr.fm digest [date]" + key stats + delta from last week if available
- post 2: top 3 tracks with play counts
- post 3: what's new/rising this week
- post 4: one interesting observation

avoid: excessive emojis, "crushing it", "vibes", "eclectic", filler words
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

    fetches previous digest for comparison, generates new digest with deltas,
    posts the thread, then saves the URL for next time.
    """
    print("fetching previous digest for comparison...")
    previous = await get_previous_digest()

    if previous and previous.total_tracks:
        print(f"found previous digest from {previous.post_date}:")
        print(f"  tracks: {previous.total_tracks}, plays: {previous.total_plays}")
        context = (
            f"previous digest ({previous.post_date}): "
            f"{previous.total_tracks} tracks, {previous.total_plays} plays, "
            f"{previous.unique_artists} artists. "
            "compare current stats to these and report deltas."
        )
    else:
        print("no previous digest found, this will be the baseline")
        context = "this is the first digest, no previous data to compare."

    print("gathering current data...")
    result = await digest_agent.run(f"generate plyr.fm digest. {context}")
    digest = result.output

    print(
        f"\nstats: {digest.stats.total_tracks} tracks, {digest.stats.total_plays} plays"
    )
    print(f"top track: {digest.top_tracks[0].title} by {digest.top_tracks[0].artist}")

    print("\nposting thread...")
    thread_url = post_thread(digest.thread.posts)
    print(f"posted: {thread_url}")

    # save URL for next run
    await Variable.aset(LATEST_DIGEST_VAR, thread_url, overwrite=True)
    print(f"saved {LATEST_DIGEST_VAR} = {thread_url}")

    return digest


if __name__ == "__main__":
    import asyncio

    asyncio.run(weekly_digest_flow())
