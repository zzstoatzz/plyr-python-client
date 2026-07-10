"""type definitions for plyrfm."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal, TypeAlias
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# identifier types
# ---------------------------------------------------------------------------

TrackId: TypeAlias = Annotated[int, Field(description="plyr.fm track ID")]
TrackUri: TypeAlias = Annotated[
    str, Field(description="AT-URI (at://did/collection/rkey)")
]
TrackRef: TypeAlias = TrackId | TrackUri

PlaylistId: TypeAlias = Annotated[str, Field(description="plyr.fm playlist ID (UUID)")]

ArtistDid: TypeAlias = Annotated[
    str, Field(description="ATProto DID (did:plc:... or did:web:...)")
]
ArtistHandle: TypeAlias = Annotated[str, Field(description="ATProto handle")]
ArtistRef: TypeAlias = ArtistDid | ArtistHandle


def is_at_uri(ref: int | str) -> bool:
    """check if a reference is an AT-URI."""
    return isinstance(ref, str) and ref.startswith("at://")


# ---------------------------------------------------------------------------
# patch types
# ---------------------------------------------------------------------------


class TrackPatch(BaseModel):
    """fields that can be updated on a track."""

    title: str | None = None
    album: str | None = None
    features: str | None = None
    tags: list[str] | None = None
    image: Path | str | None = None
    unlisted: bool | None = None
    # liner notes / show notes. "" clears the existing description.
    description: str | None = None

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# artist types
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# album types
# ---------------------------------------------------------------------------


class Album(BaseModel):
    """album metadata."""

    id: UUID
    title: str
    slug: str
    description: str | None = None
    image_url: str | None = None


# ---------------------------------------------------------------------------
# track types
# ---------------------------------------------------------------------------


class Track(BaseModel):
    """track metadata."""

    id: int
    title: str
    description: str | None = None  # liner notes / show notes
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
    unlisted: bool = False
    visibility: str = "public"  # public | unlisted | supporters | private
    support_gate: dict[str, Any] | None = None  # supporter gating config
    gated: bool = False  # gated AND the viewer lacks access
    audio_storage: str = "r2"  # "r2" | "pds" | "both"
    pds_blob_cid: str | None = None  # CID when audio lives on the user's PDS
    original_file_id: str | None = None  # pre-transcode source hash
    original_file_type: str | None = None  # pre-transcode source extension
    atproto_uri: str | None = Field(default=None, alias="atproto_record_uri")
    atproto_cid: str | None = Field(default=None, alias="atproto_record_cid")

    model_config = {"populate_by_name": True}


class UploadResult(BaseModel):
    """result of a track upload."""

    track_id: int
    title: str


class AudioRevision(BaseModel):
    """a previous audio version of a track."""

    id: int
    track_id: int
    created_at: datetime
    file_type: str
    original_file_type: str | None = None
    audio_storage: str  # "r2" | "pds" | "both"
    duration: int | None = None
    was_gated: bool


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


# ---------------------------------------------------------------------------
# tag types
# ---------------------------------------------------------------------------


class Tag(BaseModel):
    """tag with track count."""

    name: str
    track_count: int


# ---------------------------------------------------------------------------
# playlist types
# ---------------------------------------------------------------------------


class Playlist(BaseModel):
    """playlist metadata."""

    id: str
    name: str
    owner_did: str
    owner_handle: str
    track_count: int = 0
    image_url: str | None = None
    show_on_profile: bool = False
    atproto_record_uri: str | None = None
    created_at: datetime | None = None


class PlaylistWithTracks(Playlist):
    """playlist with its tracks."""

    tracks: list[Track] = Field(default_factory=list)


class RecommendedTrack(BaseModel):
    """track recommendation for a playlist."""

    id: int
    title: str
    artist_handle: str
    artist_display_name: str
    image_url: str | None = None


class PlaylistRecommendations(BaseModel):
    """playlist track recommendations."""

    tracks: list[RecommendedTrack]
    available: bool
