"""plyr.fm API clients - sync and async."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from plyrfm._internal.config import Settings, get_settings
from plyrfm._internal.types import Track, UploadResult

if TYPE_CHECKING:
    pass


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
    def _headers(self) -> dict[str, str]:
        if not self._token:
            msg = (
                "authentication required. "
                "set PLYR_TOKEN or pass token= to client"
            )
            raise ValueError(msg)
        return {"Authorization": f"Bearer {self._token}"}

    def _url(self, path: str) -> str:
        return f"{self._api_url}{path}"

    def _handle_error_response(self, response: httpx.Response) -> None:
        """handle common error responses."""
        if response.status_code == 403:
            detail = response.json().get("detail", "")
            if "artist_profile_required" in detail:
                msg = "artist profile required - create one at plyr.fm/portal"
                raise ValueError(msg)
            if "scope_upgrade_required" in detail:
                msg = "token needs upgrade - log out, back in, create new token"
                raise ValueError(msg)
        response.raise_for_status()


class PlyrClient(_BaseClient):
    """synchronous client for the plyr.fm API.

    example:
        # uses PLYR_TOKEN from environment
        client = PlyrClient()
        tracks = client.list_tracks()

        # explicit token
        client = PlyrClient(token="your_token")

        # as context manager
        with PlyrClient() as client:
            tracks = client.list_tracks()
    """

    def __init__(
        self,
        *,
        token: str | None = None,
        api_url: str | None = None,
        settings: Settings | None = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(token=token, api_url=api_url, settings=settings)
        self._client = httpx.Client(timeout=timeout)

    def __enter__(self) -> PlyrClient:
        return self

    def __exit__(self, *args: object) -> None:
        self._client.close()

    def close(self) -> None:
        """close the HTTP client."""
        self._client.close()

    # -------------------------------------------------------------------------
    # read operations
    # -------------------------------------------------------------------------

    def list_tracks(self, *, limit: int = 50) -> list[Track]:
        """list your tracks. requires auth."""
        response = self._client.get(
            self._url("/tracks/"),
            headers=self._headers,
            params={"limit": limit},
        )
        response.raise_for_status()
        data = response.json()
        return [Track.from_dict(t) for t in data.get("tracks", [])]

    def get_track(self, track_id: int) -> Track:
        """get a single track by ID. requires auth."""
        response = self._client.get(
            self._url(f"/tracks/{track_id}"),
            headers=self._headers,
        )
        response.raise_for_status()
        return Track.from_dict(response.json())

    def me(self) -> dict[str, str]:
        """get current user info. requires auth."""
        response = self._client.get(
            self._url("/auth/me"),
            headers=self._headers,
        )
        response.raise_for_status()
        return response.json()

    # -------------------------------------------------------------------------
    # write operations
    # -------------------------------------------------------------------------

    def upload(
        self,
        file: Path | str,
        title: str,
        *,
        album: str | None = None,
        timeout: float = 300.0,
    ) -> UploadResult:
        """upload a track. requires auth + artist profile."""
        file = Path(file)
        if not file.exists():
            msg = f"file not found: {file}"
            raise FileNotFoundError(msg)

        with open(file, "rb") as f:
            files = {"file": (file.name, f)}
            data: dict[str, str] = {"title": title}
            if album:
                data["album"] = album

            response = self._client.post(
                self._url("/tracks/"),
                headers=self._headers,
                files=files,
                data=data,
                timeout=timeout,
            )

        self._handle_error_response(response)
        upload_data = response.json()

        if track_id := upload_data.get("track_id"):
            return UploadResult(track_id=track_id, title=title)

        upload_id = upload_data.get("upload_id")
        if not upload_id:
            msg = "unexpected response: no track_id or upload_id"
            raise ValueError(msg)

        return self._poll_upload(upload_id, title, timeout=timeout)

    def _poll_upload(
        self,
        upload_id: str,
        title: str,
        *,
        timeout: float = 300.0,
    ) -> UploadResult:
        with self._client.stream(
            "GET",
            self._url(f"/tracks/uploads/{upload_id}/progress"),
            headers=self._headers,
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

    def delete(self, track_id: int) -> None:
        """delete a track. requires auth + ownership."""
        response = self._client.delete(
            self._url(f"/tracks/{track_id}"),
            headers=self._headers,
        )
        response.raise_for_status()

    def download(
        self,
        track_id: int,
        output: Path | str | None = None,
        *,
        timeout: float = 300.0,
    ) -> Path:
        """download a track. requires auth."""
        track = self.get_track(track_id)

        if output is None:
            safe_title = "".join(
                c if c.isalnum() or c in " -_" else "" for c in track.title
            )
            output = Path(f"{safe_title}.{track.file_type}")
        else:
            output = Path(output)

        response = self._client.get(
            self._url(f"/audio/{track.file_id}"),
            headers=self._headers,
            follow_redirects=True,
            timeout=timeout,
        )
        response.raise_for_status()
        output.write_bytes(response.content)
        return output


class AsyncPlyrClient(_BaseClient):
    """asynchronous client for the plyr.fm API.

    example:
        async with AsyncPlyrClient() as client:
            tracks = await client.list_tracks()

        # or manually
        client = AsyncPlyrClient(token="your_token")
        try:
            tracks = await client.list_tracks()
        finally:
            await client.close()
    """

    def __init__(
        self,
        *,
        token: str | None = None,
        api_url: str | None = None,
        settings: Settings | None = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(token=token, api_url=api_url, settings=settings)
        self._client = httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self) -> AsyncPlyrClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._client.aclose()

    async def close(self) -> None:
        """close the HTTP client."""
        await self._client.aclose()

    # -------------------------------------------------------------------------
    # read operations
    # -------------------------------------------------------------------------

    async def list_tracks(self, *, limit: int = 50) -> list[Track]:
        """list your tracks. requires auth."""
        response = await self._client.get(
            self._url("/tracks/"),
            headers=self._headers,
            params={"limit": limit},
        )
        response.raise_for_status()
        data = response.json()
        return [Track.from_dict(t) for t in data.get("tracks", [])]

    async def get_track(self, track_id: int) -> Track:
        """get a single track by ID. requires auth."""
        response = await self._client.get(
            self._url(f"/tracks/{track_id}"),
            headers=self._headers,
        )
        response.raise_for_status()
        return Track.from_dict(response.json())

    async def me(self) -> dict[str, str]:
        """get current user info. requires auth."""
        response = await self._client.get(
            self._url("/auth/me"),
            headers=self._headers,
        )
        response.raise_for_status()
        return response.json()

    # -------------------------------------------------------------------------
    # write operations
    # -------------------------------------------------------------------------

    async def upload(
        self,
        file: Path | str,
        title: str,
        *,
        album: str | None = None,
        timeout: float = 300.0,
    ) -> UploadResult:
        """upload a track. requires auth + artist profile."""
        file = Path(file)
        if not file.exists():
            msg = f"file not found: {file}"
            raise FileNotFoundError(msg)

        with open(file, "rb") as f:
            files = {"file": (file.name, f)}
            data: dict[str, str] = {"title": title}
            if album:
                data["album"] = album

            response = await self._client.post(
                self._url("/tracks/"),
                headers=self._headers,
                files=files,
                data=data,
                timeout=timeout,
            )

        self._handle_error_response(response)
        upload_data = response.json()

        if track_id := upload_data.get("track_id"):
            return UploadResult(track_id=track_id, title=title)

        upload_id = upload_data.get("upload_id")
        if not upload_id:
            msg = "unexpected response: no track_id or upload_id"
            raise ValueError(msg)

        return await self._poll_upload(upload_id, title, timeout=timeout)

    async def _poll_upload(
        self,
        upload_id: str,
        title: str,
        *,
        timeout: float = 300.0,
    ) -> UploadResult:
        async with self._client.stream(
            "GET",
            self._url(f"/tracks/uploads/{upload_id}/progress"),
            headers=self._headers,
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

    async def delete(self, track_id: int) -> None:
        """delete a track. requires auth + ownership."""
        response = await self._client.delete(
            self._url(f"/tracks/{track_id}"),
            headers=self._headers,
        )
        response.raise_for_status()

    async def download(
        self,
        track_id: int,
        output: Path | str | None = None,
        *,
        timeout: float = 300.0,
    ) -> Path:
        """download a track. requires auth."""
        track = await self.get_track(track_id)

        if output is None:
            safe_title = "".join(
                c if c.isalnum() or c in " -_" else "" for c in track.title
            )
            output = Path(f"{safe_title}.{track.file_type}")
        else:
            output = Path(output)

        response = await self._client.get(
            self._url(f"/audio/{track.file_id}"),
            headers=self._headers,
            follow_redirects=True,
            timeout=timeout,
        )
        response.raise_for_status()
        output.write_bytes(response.content)
        return output
