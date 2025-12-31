"""type definitions for plyrfm."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class TrackPatch(BaseModel):
    """fields that can be updated on a track."""

    title: str | None = None
    album: str | None = None
    features: str | None = None
    tags: list[str] | None = None
    image: Path | str | None = None

    model_config = {"extra": "forbid"}


@dataclass
class Artist:
    """artist profile."""

    did: str
    handle: str
    display_name: str | None = None
    avatar_url: str | None = None


@dataclass
class Album:
    """album metadata."""

    id: UUID
    title: str
    slug: str
    description: str | None = None
    image_url: str | None = None


@dataclass
class Track:
    """track metadata."""

    id: int
    title: str
    file_id: str
    file_type: str
    artist: str  # display name or handle
    artist_handle: str
    play_count: int = 0
    like_count: int = 0
    album: Album | None = None
    image_url: str | None = None
    audio_url: str | None = None
    created_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Track:
        """create track from API response dict."""
        album_data = data.get("album")
        album = None
        if isinstance(album_data, dict):
            album = Album(
                id=UUID(album_data["id"]),
                title=album_data["title"],
                slug=album_data["slug"],
                description=album_data.get("description"),
                image_url=album_data.get("image_url"),
            )

        created_at = None
        if created_str := data.get("created_at"):
            created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))

        return cls(
            id=data["id"],
            title=data["title"],
            file_id=data["file_id"],
            file_type=data.get("file_type", "mp3"),
            artist=data.get("artist", ""),
            artist_handle=data.get("artist_handle", ""),
            play_count=data.get("play_count", 0),
            like_count=data.get("like_count", 0),
            album=album,
            image_url=data.get("image_url"),
            audio_url=data.get("r2_url"),
            created_at=created_at,
        )


@dataclass
class UploadResult:
    """result of a track upload."""

    track_id: int
    title: str
