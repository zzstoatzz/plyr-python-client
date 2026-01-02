"""type definitions for plyrfm."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TrackPatch(BaseModel):
    """fields that can be updated on a track."""

    title: str | None = None
    album: str | None = None
    features: str | None = None
    tags: list[str] | None = None
    image: Path | str | None = None

    model_config = {"extra": "forbid"}


class Artist(BaseModel):
    """artist profile (minimal, from track context)."""

    did: str
    handle: str
    display_name: str | None = None
    avatar_url: str | None = None


class ArtistProfile(BaseModel):
    """full artist profile."""

    did: str
    handle: str
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    support_url: str | None = None
    show_liked_on_profile: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ArtistProfilePatch(BaseModel):
    """fields that can be updated on an artist profile."""

    bio: str | None = None
    display_name: str | None = None
    support_url: str | None = None
    show_liked_on_profile: bool | None = None

    model_config = {"extra": "forbid"}


class Album(BaseModel):
    """album metadata."""

    id: UUID
    title: str
    slug: str
    description: str | None = None
    image_url: str | None = None


class Track(BaseModel):
    """track metadata."""

    id: int
    title: str
    file_id: str
    file_type: str = "mp3"
    artist: str = ""  # display name or handle
    artist_handle: str = ""
    play_count: int = 0
    like_count: int = 0
    album: Album | None = None
    image_url: str | None = None
    audio_url: str | None = Field(default=None, alias="r2_url")
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None

    model_config = {"populate_by_name": True}


class UploadResult(BaseModel):
    """result of a track upload."""

    track_id: int
    title: str


# --- search types ---


class TrackSearchResult(BaseModel):
    """track search result."""

    type: Literal["track"] = "track"
    id: int
    title: str
    artist_handle: str
    artist_display_name: str
    image_url: str | None = None
    relevance: float


class ArtistSearchResult(BaseModel):
    """artist search result."""

    type: Literal["artist"] = "artist"
    did: str
    handle: str
    display_name: str
    avatar_url: str | None = None
    relevance: float


class AlbumSearchResult(BaseModel):
    """album search result."""

    type: Literal["album"] = "album"
    id: str
    title: str
    slug: str
    artist_handle: str
    artist_display_name: str
    image_url: str | None = None
    relevance: float


class TagSearchResult(BaseModel):
    """tag search result."""

    type: Literal["tag"] = "tag"
    id: int
    name: str
    track_count: int
    relevance: float


class PlaylistSearchResult(BaseModel):
    """playlist search result."""

    type: Literal["playlist"] = "playlist"
    id: str
    name: str
    owner_handle: str
    owner_display_name: str
    image_url: str | None = None
    track_count: int
    relevance: float


SearchResult = Annotated[
    TrackSearchResult
    | ArtistSearchResult
    | AlbumSearchResult
    | TagSearchResult
    | PlaylistSearchResult,
    Field(discriminator="type"),
]


class SearchResponse(BaseModel):
    """unified search response."""

    results: list[SearchResult]
    counts: dict[str, int]


# --- tag types ---


class Tag(BaseModel):
    """tag with track count."""

    name: str
    track_count: int
