"""plyr.fm API clients - sync and async."""

from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path

import httpx

from plyrfm._internal.config import Settings, get_settings
from plyrfm._internal.types import (
    ArtistDid,
    ArtistProfile,
    ArtistProfilePatch,
    AudioRevision,
    Playlist,
    PlaylistId,
    PlaylistRecommendations,
    PlaylistWithTracks,
    SearchResponse,
    Tag,
    Track,
    TrackPatch,
    TrackRef,
    TrackUri,
    UploadResult,
    is_at_uri,
)


def _get_user_agent(client_name: str = "plyrfm") -> str:
    try:
        v = version(client_name)
    except Exception:
        v = "unknown"
    return f"{client_name}/{v}"


# ---------------------------------------------------------------------------
# base client
# ---------------------------------------------------------------------------


class _BaseClient:
    """shared client logic."""

    def __init__(
        self,
        *,
        token: str | None = None,
        api_url: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._token = token or self._settings.token
        self._api_url = api_url or self._settings.api_url

    @property
    def _auth_headers(self) -> dict[str, str]:
        if not self._token:
            msg = "authentication required. set PLYR_TOKEN or pass token= to client"
            raise ValueError(msg)
        return {"Authorization": f"Bearer {self._token}"}

    def _url(self, path: str) -> str:
        return f"{self._api_url}{path}"

    def _handle_error_response(self, response: httpx.Response) -> None:
        if response.status_code == 403:
            detail = response.json().get("detail", "")
            if "artist_profile_required" in detail:
                msg = "artist profile required - create one at plyr.fm/portal"
                raise ValueError(msg)
            if "scope_upgrade_required" in detail:
                msg = "token needs upgrade - log out, back in, create new token"
                raise ValueError(msg)
        response.raise_for_status()


# ---------------------------------------------------------------------------
# sync namespaces
# ---------------------------------------------------------------------------


class _SyncNamespace:
    def __init__(self, api: PlyrClient) -> None:
        self._api = api


class TracksNamespace(_SyncNamespace):
    """track operations."""

    def list(self, *, limit: int = 50) -> list[Track]:
        """list public tracks."""
        response = self._api._client.get(
            self._api._url("/tracks/"),
            params={"limit": limit},
        )
        response.raise_for_status()
        data = response.json()
        return [Track.model_validate(t) for t in data.get("tracks", [])]

    def get(self, track: TrackRef) -> Track:
        """get a track by ID or AT-URI."""
        if is_at_uri(track):
            return self.get_by_uri(track)  # type: ignore[arg-type]
        response = self._api._client.get(self._api._url(f"/tracks/{track}"))
        response.raise_for_status()
        return Track.model_validate(response.json())

    def get_by_uri(self, uri: TrackUri) -> Track:
        """get a track by AT-URI."""
        response = self._api._client.get(
            self._api._url("/tracks/by-uri"),
            params={"uri": uri},
        )
        response.raise_for_status()
        return Track.model_validate(response.json())

    def _resolve(self, track: TrackRef) -> Track:
        """resolve a TrackRef to a full Track."""
        return self.get(track)

    def _resolve_id(self, track: TrackRef) -> int:
        """resolve a TrackRef to an integer ID."""
        if is_at_uri(track):
            return self._resolve(track).id
        return track  # type: ignore[return-value]

    def my(self, *, limit: int = 50) -> list[Track]:
        """list your tracks. requires auth."""
        response = self._api._client.get(
            self._api._url("/tracks/me"),
            headers=self._api._auth_headers,
            params={"limit": limit},
        )
        response.raise_for_status()
        data = response.json()
        return [Track.model_validate(t) for t in data.get("tracks", [])]

    def liked(self, *, limit: int = 50) -> list[Track]:
        """list tracks you've liked. requires auth."""
        response = self._api._client.get(
            self._api._url("/tracks/liked"),
            headers=self._api._auth_headers,
            params={"limit": limit},
        )
        response.raise_for_status()
        data = response.json()
        return [Track.model_validate(t) for t in data.get("tracks", [])]

    def like(self, track: TrackRef) -> None:
        """like a track. requires auth."""
        track_id = self._resolve_id(track)
        response = self._api._client.post(
            self._api._url(f"/tracks/{track_id}/like"),
            headers=self._api._auth_headers,
        )
        self._api._handle_error_response(response)

    def unlike(self, track: TrackRef) -> None:
        """unlike a track. requires auth."""
        track_id = self._resolve_id(track)
        response = self._api._client.delete(
            self._api._url(f"/tracks/{track_id}/like"),
            headers=self._api._auth_headers,
        )
        self._api._handle_error_response(response)

    def upload(
        self,
        file: Path | str,
        title: str,
        *,
        album: str | None = None,
        tags: set[str] | None = None,
        unlisted: bool = False,
        timeout: float = 300.0,
    ) -> UploadResult:
        """upload a track. requires auth + artist profile.

        when `unlisted=True`, the track is excluded from public discovery
        feeds (latest, top, for-you) but remains accessible by direct URL.
        """
        file = Path(file)
        if not file.exists():
            msg = f"file not found: {file}"
            raise FileNotFoundError(msg)

        with open(file, "rb") as f:
            files = {"file": (file.name, f)}
            data: dict[str, str] = {"title": title}
            if album:
                data["album"] = album
            if tags:
                data["tags"] = json.dumps(list(tags))
            if unlisted:
                data["unlisted"] = "true"

            response = self._api._client.post(
                self._api._url("/tracks/"),
                headers=self._api._auth_headers,
                files=files,
                data=data,
                timeout=timeout,
            )

        self._api._handle_error_response(response)
        upload_data = response.json()

        if track_id := upload_data.get("track_id"):
            return UploadResult(track_id=track_id, title=title)

        upload_id = upload_data.get("upload_id")
        if not upload_id:
            msg = "unexpected response: no track_id or upload_id"
            raise ValueError(msg)

        return self._poll_upload(upload_id, title, timeout=timeout)

    def replace_audio(
        self,
        track: TrackRef,
        file: Path | str,
        *,
        timeout: float = 300.0,
    ) -> UploadResult:
        """replace the audio file backing an existing track. requires auth + ownership.

        this uploads new audio bytes. the track's stable id / URI / likes / comments
        / plays / album linkage all carry over; only the audio (and derived fields
        like duration / fingerprint / embedding) are replaced. the previous audio
        is preserved as a revision — use `.revisions(track)` to list them or
        `.restore_revision(track, revision_id)` to roll back.
        """
        track_id = self._resolve_id(track)
        file = Path(file)
        if not file.exists():
            msg = f"file not found: {file}"
            raise FileNotFoundError(msg)

        with open(file, "rb") as f:
            files = {"file": (file.name, f)}
            response = self._api._client.put(
                self._api._url(f"/tracks/{track_id}/audio"),
                headers=self._api._auth_headers,
                files=files,
                timeout=timeout,
            )

        self._api._handle_error_response(response)
        upload_data = response.json()

        # resolve title for the result label
        title = upload_data.get("title") or ""
        if not title:
            try:
                title = self.get(track_id).title
            except Exception:
                title = ""

        if (completed_track_id := upload_data.get("track_id")) and upload_data.get(
            "status"
        ) in (None, "completed"):
            return UploadResult(track_id=completed_track_id, title=title)

        upload_id = upload_data.get("upload_id")
        if not upload_id:
            msg = "unexpected response: no upload_id"
            raise ValueError(msg)

        return self._poll_upload(upload_id, title, timeout=timeout)

    def revisions(self, track: TrackRef) -> list[AudioRevision]:
        """list previous audio versions of a track, newest first. requires auth + ownership."""
        track_id = self._resolve_id(track)
        response = self._api._client.get(
            self._api._url(f"/tracks/{track_id}/revisions"),
            headers=self._api._auth_headers,
        )
        self._api._handle_error_response(response)
        data = response.json()
        return [AudioRevision.model_validate(r) for r in data.get("revisions", [])]

    def restore_revision(self, track: TrackRef, revision_id: int) -> AudioRevision:
        """restore a previous audio version (owner only).

        returns the new revision row that captured the just-displaced current audio.
        """
        track_id = self._resolve_id(track)
        response = self._api._client.post(
            self._api._url(f"/tracks/{track_id}/revisions/{revision_id}/restore"),
            headers=self._api._auth_headers,
        )
        self._api._handle_error_response(response)
        return AudioRevision.model_validate(response.json())

    def update(self, track: TrackRef, patch: TrackPatch) -> Track:
        """update track metadata. requires auth + ownership."""
        track_id = self._resolve_id(track)
        data: dict[str, str] = {}
        if patch.title is not None:
            data["title"] = patch.title
        if patch.album is not None:
            data["album"] = patch.album
        if patch.features is not None:
            data["features"] = patch.features
        if patch.tags is not None:
            data["tags"] = json.dumps(patch.tags)

        if patch.image is not None:
            image_path = Path(patch.image)
            if not image_path.exists():
                msg = f"image not found: {image_path}"
                raise FileNotFoundError(msg)
            with open(image_path, "rb") as f:
                files = {"image": (image_path.name, f)}
                response = self._api._client.patch(
                    self._api._url(f"/tracks/{track_id}"),
                    headers=self._api._auth_headers,
                    data=data if data else None,
                    files=files,
                )
        else:
            response = self._api._client.patch(
                self._api._url(f"/tracks/{track_id}"),
                headers=self._api._auth_headers,
                data=data if data else None,
            )

        self._api._handle_error_response(response)
        return Track.model_validate(response.json())

    def _poll_upload(
        self, upload_id: str, title: str, *, timeout: float = 300.0
    ) -> UploadResult:
        with self._api._client.stream(
            "GET",
            self._api._url(f"/tracks/uploads/{upload_id}/progress"),
            headers=self._api._auth_headers,
            timeout=timeout,
        ) as response:
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                data = json.loads(line[6:])
                status = data.get("status")
                if status == "completed":
                    return UploadResult(track_id=data["track_id"], title=title)
                if status == "failed":
                    msg = f"upload failed: {data.get('error', 'unknown')}"
                    raise ValueError(msg)
        msg = "upload stream ended without completion"
        raise ValueError(msg)

    def delete(self, track: TrackRef) -> None:
        """delete a track. requires auth + ownership."""
        track_id = self._resolve_id(track)
        response = self._api._client.delete(
            self._api._url(f"/tracks/{track_id}"),
            headers=self._api._auth_headers,
        )
        response.raise_for_status()

    def download(
        self,
        track: TrackRef,
        output: Path | str | None = None,
        *,
        timeout: float = 300.0,
    ) -> Path:
        """download a track's audio file. requires auth."""
        resolved = self._resolve(track)

        if output is None:
            safe_title = "".join(
                c if c.isalnum() or c in " -_" else "" for c in resolved.title
            )
            output = Path(f"{safe_title}.{resolved.file_type}")
        else:
            output = Path(output)

        response = self._api._client.get(
            self._api._url(f"/audio/{resolved.file_id}"),
            headers=self._api._auth_headers,
            follow_redirects=True,
            timeout=timeout,
        )
        response.raise_for_status()
        output.write_bytes(response.content)
        return output


class PlaylistsNamespace(_SyncNamespace):
    """playlist operations."""

    def list(self) -> list[Playlist]:
        """list your playlists. requires auth."""
        response = self._api._client.get(
            self._api._url("/lists/playlists"),
            headers=self._api._auth_headers,
        )
        response.raise_for_status()
        return [Playlist.model_validate(p) for p in response.json()]

    def get(self, playlist: PlaylistId) -> PlaylistWithTracks:
        """get a playlist with its tracks."""
        response = self._api._client.get(
            self._api._url(f"/lists/playlists/{playlist}"),
        )
        response.raise_for_status()
        return PlaylistWithTracks.model_validate(response.json())

    def by_artist(self, artist: ArtistDid) -> list[Playlist]:
        """list public playlists by an artist."""
        response = self._api._client.get(
            self._api._url(f"/lists/playlists/by-artist/{artist}"),
        )
        response.raise_for_status()
        return [Playlist.model_validate(p) for p in response.json()]

    def create(self, name: str) -> Playlist:
        """create a playlist. requires auth."""
        response = self._api._client.post(
            self._api._url("/lists/playlists"),
            headers=self._api._auth_headers,
            json={"name": name},
        )
        self._api._handle_error_response(response)
        return Playlist.model_validate(response.json())

    def add_track(self, playlist: PlaylistId, track: TrackRef) -> Playlist:
        """add a track to a playlist. requires auth."""
        resolved = self._api.tracks._resolve(track)
        if not resolved.atproto_uri or not resolved.atproto_cid:
            msg = f"track {track} has no ATProto record — cannot add to playlist"
            raise ValueError(msg)
        response = self._api._client.post(
            self._api._url(f"/lists/playlists/{playlist}/tracks"),
            headers=self._api._auth_headers,
            json={
                "track_uri": resolved.atproto_uri,
                "track_cid": resolved.atproto_cid,
            },
        )
        self._api._handle_error_response(response)
        return Playlist.model_validate(response.json())

    def remove_track(self, playlist: PlaylistId, track: TrackRef) -> Playlist:
        """remove a track from a playlist. requires auth."""
        resolved = self._api.tracks._resolve(track)
        if not resolved.atproto_uri:
            msg = f"track {track} has no ATProto record — cannot remove from playlist"
            raise ValueError(msg)
        response = self._api._client.delete(
            self._api._url(
                f"/lists/playlists/{playlist}/tracks/{resolved.atproto_uri}"
            ),
            headers=self._api._auth_headers,
        )
        self._api._handle_error_response(response)
        return Playlist.model_validate(response.json())

    def update(
        self,
        playlist: PlaylistId,
        *,
        name: str | None = None,
        show_on_profile: bool | None = None,
    ) -> Playlist:
        """update playlist metadata. requires auth."""
        data: dict[str, str | bool] = {}
        if name is not None:
            data["name"] = name
        if show_on_profile is not None:
            data["show_on_profile"] = show_on_profile
        response = self._api._client.patch(
            self._api._url(f"/lists/playlists/{playlist}"),
            headers=self._api._auth_headers,
            data=data,
        )
        self._api._handle_error_response(response)
        return Playlist.model_validate(response.json())

    def delete(self, playlist: PlaylistId) -> None:
        """delete a playlist. requires auth."""
        response = self._api._client.delete(
            self._api._url(f"/lists/playlists/{playlist}"),
            headers=self._api._auth_headers,
        )
        response.raise_for_status()

    def recommendations(
        self, playlist: PlaylistId, *, limit: int = 3
    ) -> PlaylistRecommendations:
        """get track recommendations for a playlist. requires auth."""
        response = self._api._client.get(
            self._api._url(f"/lists/playlists/{playlist}/recommendations"),
            headers=self._api._auth_headers,
            params={"limit": limit},
        )
        response.raise_for_status()
        return PlaylistRecommendations.model_validate(response.json())


class TagsNamespace(_SyncNamespace):
    """tag operations."""

    def list(self, *, q: str | None = None, limit: int = 20) -> list[Tag]:
        """list tags with track counts."""
        params: dict[str, str | int] = {"limit": limit}
        if q:
            params["q"] = q
        response = self._api._client.get(self._api._url("/tracks/tags"), params=params)
        response.raise_for_status()
        return [Tag.model_validate(t) for t in response.json()]

    def tracks(self, tag: str, *, limit: int = 50) -> list[Track]:
        """get tracks with a specific tag."""
        response = self._api._client.get(self._api._url(f"/tracks/tags/{tag}"))
        response.raise_for_status()
        data = response.json()
        return [Track.model_validate(t) for t in data.get("tracks", [])]


class ArtistsNamespace(_SyncNamespace):
    """artist operations."""

    def me(self) -> ArtistProfile:
        """get your artist profile. requires auth."""
        response = self._api._client.get(
            self._api._url("/artists/me"),
            headers=self._api._auth_headers,
        )
        response.raise_for_status()
        return ArtistProfile.model_validate(response.json())

    def update(self, patch: ArtistProfilePatch) -> ArtistProfile:
        """update your artist profile. requires auth."""
        data: dict[str, str | bool] = {}
        if patch.bio is not None:
            data["bio"] = patch.bio
        if patch.display_name is not None:
            data["display_name"] = patch.display_name
        if patch.support_url is not None:
            data["support_url"] = patch.support_url
        if patch.show_liked_on_profile is not None:
            data["show_liked_on_profile"] = patch.show_liked_on_profile

        response = self._api._client.put(
            self._api._url("/artists/me"),
            headers=self._api._auth_headers,
            json=data,
        )
        self._api._handle_error_response(response)
        return ArtistProfile.model_validate(response.json())


class DiscoverNamespace(_SyncNamespace):
    """discovery operations."""

    def search(
        self, query: str, *, type: str | None = None, limit: int = 20
    ) -> SearchResponse:
        """search tracks, artists, albums, and tags."""
        params: dict[str, str | int] = {"q": query, "limit": limit}
        if type:
            params["type"] = type
        response = self._api._client.get(self._api._url("/search/"), params=params)
        response.raise_for_status()
        return SearchResponse.model_validate(response.json())

    def top_tracks(self, *, limit: int = 10) -> list[Track]:
        """get top tracks by like count."""
        response = self._api._client.get(
            self._api._url("/tracks/top"),
            params={"limit": limit},
        )
        response.raise_for_status()
        return [Track.model_validate(t) for t in response.json()]


# ---------------------------------------------------------------------------
# async namespaces
# ---------------------------------------------------------------------------


class _AsyncNamespace:
    def __init__(self, api: AsyncPlyrClient) -> None:
        self._api = api


class AsyncTracksNamespace(_AsyncNamespace):
    """track operations (async)."""

    async def list(self, *, limit: int = 50) -> list[Track]:
        response = await self._api._client.get(
            self._api._url("/tracks/"),
            params={"limit": limit},
        )
        response.raise_for_status()
        data = response.json()
        return [Track.model_validate(t) for t in data.get("tracks", [])]

    async def get(self, track: TrackRef) -> Track:
        if is_at_uri(track):
            return await self.get_by_uri(track)  # type: ignore[arg-type]
        response = await self._api._client.get(self._api._url(f"/tracks/{track}"))
        response.raise_for_status()
        return Track.model_validate(response.json())

    async def get_by_uri(self, uri: TrackUri) -> Track:
        response = await self._api._client.get(
            self._api._url("/tracks/by-uri"),
            params={"uri": uri},
        )
        response.raise_for_status()
        return Track.model_validate(response.json())

    async def _resolve(self, track: TrackRef) -> Track:
        return await self.get(track)

    async def _resolve_id(self, track: TrackRef) -> int:
        if is_at_uri(track):
            return (await self._resolve(track)).id
        return track  # type: ignore[return-value]

    async def my(self, *, limit: int = 50) -> list[Track]:
        response = await self._api._client.get(
            self._api._url("/tracks/me"),
            headers=self._api._auth_headers,
            params={"limit": limit},
        )
        response.raise_for_status()
        data = response.json()
        return [Track.model_validate(t) for t in data.get("tracks", [])]

    async def liked(self, *, limit: int = 50) -> list[Track]:
        response = await self._api._client.get(
            self._api._url("/tracks/liked"),
            headers=self._api._auth_headers,
            params={"limit": limit},
        )
        response.raise_for_status()
        data = response.json()
        return [Track.model_validate(t) for t in data.get("tracks", [])]

    async def like(self, track: TrackRef) -> None:
        track_id = await self._resolve_id(track)
        response = await self._api._client.post(
            self._api._url(f"/tracks/{track_id}/like"),
            headers=self._api._auth_headers,
        )
        self._api._handle_error_response(response)

    async def unlike(self, track: TrackRef) -> None:
        track_id = await self._resolve_id(track)
        response = await self._api._client.delete(
            self._api._url(f"/tracks/{track_id}/like"),
            headers=self._api._auth_headers,
        )
        self._api._handle_error_response(response)

    async def upload(
        self,
        file: Path | str,
        title: str,
        *,
        album: str | None = None,
        tags: set[str] | None = None,
        unlisted: bool = False,
        timeout: float = 300.0,
    ) -> UploadResult:
        """upload a track. requires auth + artist profile.

        when `unlisted=True`, the track is excluded from public discovery
        feeds (latest, top, for-you) but remains accessible by direct URL.
        """
        file = Path(file)
        if not file.exists():
            msg = f"file not found: {file}"
            raise FileNotFoundError(msg)

        with open(file, "rb") as f:
            files = {"file": (file.name, f)}
            data: dict[str, str] = {"title": title}
            if album:
                data["album"] = album
            if tags:
                data["tags"] = json.dumps(list(tags))
            if unlisted:
                data["unlisted"] = "true"

            response = await self._api._client.post(
                self._api._url("/tracks/"),
                headers=self._api._auth_headers,
                files=files,
                data=data,
                timeout=timeout,
            )

        self._api._handle_error_response(response)
        upload_data = response.json()

        if track_id := upload_data.get("track_id"):
            return UploadResult(track_id=track_id, title=title)

        upload_id = upload_data.get("upload_id")
        if not upload_id:
            msg = "unexpected response: no track_id or upload_id"
            raise ValueError(msg)

        return await self._poll_upload(upload_id, title, timeout=timeout)

    async def replace_audio(
        self,
        track: TrackRef,
        file: Path | str,
        *,
        timeout: float = 300.0,
    ) -> UploadResult:
        """replace the audio file backing an existing track. requires auth + ownership.

        this uploads new audio bytes. the track's stable id / URI / likes / comments
        / plays / album linkage all carry over; only the audio (and derived fields
        like duration / fingerprint / embedding) are replaced. the previous audio
        is preserved as a revision — use `.revisions(track)` to list them or
        `.restore_revision(track, revision_id)` to roll back.
        """
        track_id = await self._resolve_id(track)
        file = Path(file)
        if not file.exists():
            msg = f"file not found: {file}"
            raise FileNotFoundError(msg)

        with open(file, "rb") as f:
            files = {"file": (file.name, f)}
            response = await self._api._client.put(
                self._api._url(f"/tracks/{track_id}/audio"),
                headers=self._api._auth_headers,
                files=files,
                timeout=timeout,
            )

        self._api._handle_error_response(response)
        upload_data = response.json()

        title = upload_data.get("title") or ""
        if not title:
            try:
                title = (await self.get(track_id)).title
            except Exception:
                title = ""

        if (completed_track_id := upload_data.get("track_id")) and upload_data.get(
            "status"
        ) in (None, "completed"):
            return UploadResult(track_id=completed_track_id, title=title)

        upload_id = upload_data.get("upload_id")
        if not upload_id:
            msg = "unexpected response: no upload_id"
            raise ValueError(msg)

        return await self._poll_upload(upload_id, title, timeout=timeout)

    async def revisions(self, track: TrackRef) -> list[AudioRevision]:
        """list previous audio versions of a track, newest first. requires auth + ownership."""
        track_id = await self._resolve_id(track)
        response = await self._api._client.get(
            self._api._url(f"/tracks/{track_id}/revisions"),
            headers=self._api._auth_headers,
        )
        self._api._handle_error_response(response)
        data = response.json()
        return [AudioRevision.model_validate(r) for r in data.get("revisions", [])]

    async def restore_revision(
        self, track: TrackRef, revision_id: int
    ) -> AudioRevision:
        """restore a previous audio version (owner only).

        returns the new revision row that captured the just-displaced current audio.
        """
        track_id = await self._resolve_id(track)
        response = await self._api._client.post(
            self._api._url(f"/tracks/{track_id}/revisions/{revision_id}/restore"),
            headers=self._api._auth_headers,
        )
        self._api._handle_error_response(response)
        return AudioRevision.model_validate(response.json())

    async def update(self, track: TrackRef, patch: TrackPatch) -> Track:
        track_id = await self._resolve_id(track)
        data: dict[str, str] = {}
        if patch.title is not None:
            data["title"] = patch.title
        if patch.album is not None:
            data["album"] = patch.album
        if patch.features is not None:
            data["features"] = patch.features
        if patch.tags is not None:
            data["tags"] = json.dumps(patch.tags)

        if patch.image is not None:
            image_path = Path(patch.image)
            if not image_path.exists():
                msg = f"image not found: {image_path}"
                raise FileNotFoundError(msg)
            with open(image_path, "rb") as f:
                files = {"image": (image_path.name, f)}
                response = await self._api._client.patch(
                    self._api._url(f"/tracks/{track_id}"),
                    headers=self._api._auth_headers,
                    data=data if data else None,
                    files=files,
                )
        else:
            response = await self._api._client.patch(
                self._api._url(f"/tracks/{track_id}"),
                headers=self._api._auth_headers,
                data=data if data else None,
            )

        self._api._handle_error_response(response)
        return Track.model_validate(response.json())

    async def _poll_upload(
        self, upload_id: str, title: str, *, timeout: float = 300.0
    ) -> UploadResult:
        async with self._api._client.stream(
            "GET",
            self._api._url(f"/tracks/uploads/{upload_id}/progress"),
            headers=self._api._auth_headers,
            timeout=timeout,
        ) as response:
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = json.loads(line[6:])
                status = data.get("status")
                if status == "completed":
                    return UploadResult(track_id=data["track_id"], title=title)
                if status == "failed":
                    msg = f"upload failed: {data.get('error', 'unknown')}"
                    raise ValueError(msg)
        msg = "upload stream ended without completion"
        raise ValueError(msg)

    async def delete(self, track: TrackRef) -> None:
        track_id = await self._resolve_id(track)
        response = await self._api._client.delete(
            self._api._url(f"/tracks/{track_id}"),
            headers=self._api._auth_headers,
        )
        response.raise_for_status()

    async def download(
        self,
        track: TrackRef,
        output: Path | str | None = None,
        *,
        timeout: float = 300.0,
    ) -> Path:
        resolved = await self._resolve(track)

        if output is None:
            safe_title = "".join(
                c if c.isalnum() or c in " -_" else "" for c in resolved.title
            )
            output = Path(f"{safe_title}.{resolved.file_type}")
        else:
            output = Path(output)

        response = await self._api._client.get(
            self._api._url(f"/audio/{resolved.file_id}"),
            headers=self._api._auth_headers,
            follow_redirects=True,
            timeout=timeout,
        )
        response.raise_for_status()
        output.write_bytes(response.content)
        return output


class AsyncPlaylistsNamespace(_AsyncNamespace):
    """playlist operations (async)."""

    async def list(self) -> list[Playlist]:
        response = await self._api._client.get(
            self._api._url("/lists/playlists"),
            headers=self._api._auth_headers,
        )
        response.raise_for_status()
        return [Playlist.model_validate(p) for p in response.json()]

    async def get(self, playlist: PlaylistId) -> PlaylistWithTracks:
        response = await self._api._client.get(
            self._api._url(f"/lists/playlists/{playlist}"),
        )
        response.raise_for_status()
        return PlaylistWithTracks.model_validate(response.json())

    async def by_artist(self, artist: ArtistDid) -> list[Playlist]:
        response = await self._api._client.get(
            self._api._url(f"/lists/playlists/by-artist/{artist}"),
        )
        response.raise_for_status()
        return [Playlist.model_validate(p) for p in response.json()]

    async def create(self, name: str) -> Playlist:
        response = await self._api._client.post(
            self._api._url("/lists/playlists"),
            headers=self._api._auth_headers,
            json={"name": name},
        )
        self._api._handle_error_response(response)
        return Playlist.model_validate(response.json())

    async def add_track(self, playlist: PlaylistId, track: TrackRef) -> Playlist:
        resolved = await self._api.tracks._resolve(track)
        if not resolved.atproto_uri or not resolved.atproto_cid:
            msg = f"track {track} has no ATProto record — cannot add to playlist"
            raise ValueError(msg)
        response = await self._api._client.post(
            self._api._url(f"/lists/playlists/{playlist}/tracks"),
            headers=self._api._auth_headers,
            json={
                "track_uri": resolved.atproto_uri,
                "track_cid": resolved.atproto_cid,
            },
        )
        self._api._handle_error_response(response)
        return Playlist.model_validate(response.json())

    async def remove_track(self, playlist: PlaylistId, track: TrackRef) -> Playlist:
        resolved = await self._api.tracks._resolve(track)
        if not resolved.atproto_uri:
            msg = f"track {track} has no ATProto record — cannot remove from playlist"
            raise ValueError(msg)
        response = await self._api._client.delete(
            self._api._url(
                f"/lists/playlists/{playlist}/tracks/{resolved.atproto_uri}"
            ),
            headers=self._api._auth_headers,
        )
        self._api._handle_error_response(response)
        return Playlist.model_validate(response.json())

    async def update(
        self,
        playlist: PlaylistId,
        *,
        name: str | None = None,
        show_on_profile: bool | None = None,
    ) -> Playlist:
        data: dict[str, str | bool] = {}
        if name is not None:
            data["name"] = name
        if show_on_profile is not None:
            data["show_on_profile"] = show_on_profile
        response = await self._api._client.patch(
            self._api._url(f"/lists/playlists/{playlist}"),
            headers=self._api._auth_headers,
            data=data,
        )
        self._api._handle_error_response(response)
        return Playlist.model_validate(response.json())

    async def delete(self, playlist: PlaylistId) -> None:
        response = await self._api._client.delete(
            self._api._url(f"/lists/playlists/{playlist}"),
            headers=self._api._auth_headers,
        )
        response.raise_for_status()

    async def recommendations(
        self, playlist: PlaylistId, *, limit: int = 3
    ) -> PlaylistRecommendations:
        response = await self._api._client.get(
            self._api._url(f"/lists/playlists/{playlist}/recommendations"),
            headers=self._api._auth_headers,
            params={"limit": limit},
        )
        response.raise_for_status()
        return PlaylistRecommendations.model_validate(response.json())


class AsyncTagsNamespace(_AsyncNamespace):
    """tag operations (async)."""

    async def list(self, *, q: str | None = None, limit: int = 20) -> list[Tag]:
        params: dict[str, str | int] = {"limit": limit}
        if q:
            params["q"] = q
        response = await self._api._client.get(
            self._api._url("/tracks/tags"), params=params
        )
        response.raise_for_status()
        return [Tag.model_validate(t) for t in response.json()]

    async def tracks(self, tag: str, *, limit: int = 50) -> list[Track]:
        response = await self._api._client.get(self._api._url(f"/tracks/tags/{tag}"))
        response.raise_for_status()
        data = response.json()
        return [Track.model_validate(t) for t in data.get("tracks", [])]


class AsyncArtistsNamespace(_AsyncNamespace):
    """artist operations (async)."""

    async def me(self) -> ArtistProfile:
        response = await self._api._client.get(
            self._api._url("/artists/me"),
            headers=self._api._auth_headers,
        )
        response.raise_for_status()
        return ArtistProfile.model_validate(response.json())

    async def update(self, patch: ArtistProfilePatch) -> ArtistProfile:
        data: dict[str, str | bool] = {}
        if patch.bio is not None:
            data["bio"] = patch.bio
        if patch.display_name is not None:
            data["display_name"] = patch.display_name
        if patch.support_url is not None:
            data["support_url"] = patch.support_url
        if patch.show_liked_on_profile is not None:
            data["show_liked_on_profile"] = patch.show_liked_on_profile

        response = await self._api._client.put(
            self._api._url("/artists/me"),
            headers=self._api._auth_headers,
            json=data,
        )
        self._api._handle_error_response(response)
        return ArtistProfile.model_validate(response.json())


class AsyncDiscoverNamespace(_AsyncNamespace):
    """discovery operations (async)."""

    async def search(
        self, query: str, *, type: str | None = None, limit: int = 20
    ) -> SearchResponse:
        params: dict[str, str | int] = {"q": query, "limit": limit}
        if type:
            params["type"] = type
        response = await self._api._client.get(
            self._api._url("/search/"), params=params
        )
        response.raise_for_status()
        return SearchResponse.model_validate(response.json())

    async def top_tracks(self, *, limit: int = 10) -> list[Track]:
        response = await self._api._client.get(
            self._api._url("/tracks/top"),
            params={"limit": limit},
        )
        response.raise_for_status()
        return [Track.model_validate(t) for t in response.json()]


# ---------------------------------------------------------------------------
# public clients
# ---------------------------------------------------------------------------


class PlyrClient(_BaseClient):
    """synchronous client for the plyr.fm API.

    example:
        client = PlyrClient()
        tracks = client.tracks.list()
        track = client.tracks.get(42)
        track = client.tracks.get("at://did:plc:abc/fm.plyr.track/xyz")

        client = PlyrClient(token="your_token")
        client.tracks.like(42)
        client.playlists.create("road trip")
    """

    def __init__(
        self,
        *,
        token: str | None = None,
        api_url: str | None = None,
        settings: Settings | None = None,
        timeout: float = 30.0,
        user_agent: str | None = None,
    ) -> None:
        super().__init__(token=token, api_url=api_url, settings=settings)
        headers = {"User-Agent": user_agent or _get_user_agent()}
        self._client = httpx.Client(timeout=timeout, headers=headers)
        self.tracks = TracksNamespace(self)
        self.playlists = PlaylistsNamespace(self)
        self.tags = TagsNamespace(self)
        self.artists = ArtistsNamespace(self)
        self.discover = DiscoverNamespace(self)

    def __enter__(self) -> PlyrClient:
        return self

    def __exit__(self, *args: object) -> None:
        self._client.close()

    def close(self) -> None:
        self._client.close()

    def me(self) -> dict[str, str]:
        """get current user info. requires auth."""
        response = self._client.get(
            self._url("/auth/me"),
            headers=self._auth_headers,
        )
        response.raise_for_status()
        return response.json()


class AsyncPlyrClient(_BaseClient):
    """asynchronous client for the plyr.fm API.

    example:
        async with AsyncPlyrClient() as client:
            tracks = await client.tracks.list()

        async with AsyncPlyrClient(token="your_token") as client:
            await client.tracks.like(42)
            await client.playlists.create("road trip")
    """

    def __init__(
        self,
        *,
        token: str | None = None,
        api_url: str | None = None,
        settings: Settings | None = None,
        timeout: float = 30.0,
        user_agent: str | None = None,
    ) -> None:
        super().__init__(token=token, api_url=api_url, settings=settings)
        headers = {"User-Agent": user_agent or _get_user_agent()}
        self._client = httpx.AsyncClient(timeout=timeout, headers=headers)
        self.tracks = AsyncTracksNamespace(self)
        self.playlists = AsyncPlaylistsNamespace(self)
        self.tags = AsyncTagsNamespace(self)
        self.artists = AsyncArtistsNamespace(self)
        self.discover = AsyncDiscoverNamespace(self)

    async def __aenter__(self) -> AsyncPlyrClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._client.aclose()

    async def close(self) -> None:
        await self._client.aclose()

    async def me(self) -> dict[str, str]:
        """get current user info. requires auth."""
        response = await self._client.get(
            self._url("/auth/me"),
            headers=self._auth_headers,
        )
        response.raise_for_status()
        return response.json()
