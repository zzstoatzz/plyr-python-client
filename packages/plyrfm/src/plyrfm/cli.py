"""plyr.fm CLI powered by cyclopts."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import cyclopts
import httpx
from rich.console import Console
from rich.table import Table

from plyrfm._internal.types import ArtistProfilePatch, TrackPatch, TrackRef, is_at_uri
from plyrfm.client import PlyrClient

console = Console()

app = cyclopts.App(
    name="plyrfm",
    help="plyr.fm CLI — audio streaming on AT Protocol.",
    help_flags=["--help", "-h"],
    version_flags=[],
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _error(msg: str) -> None:
    console.print(f"[red]error:[/] {msg}")
    sys.exit(1)


def _get_client(require_auth: bool = False) -> PlyrClient:
    client = PlyrClient()
    if require_auth and not client._token:
        _error(
            "authentication required. "
            "set PLYR_TOKEN or create a token at plyr.fm/portal"
        )
    return client


def _parse_track_ref(value: str) -> TrackRef:
    """parse a string as a TrackRef (int ID or AT-URI)."""
    if is_at_uri(value):
        return value
    try:
        return int(value)
    except ValueError:
        _error(f"invalid track reference: {value} (expected integer ID or at:// URI)")
        raise  # unreachable


def _handle_http_error(e: httpx.HTTPStatusError, resource: str = "resource") -> None:
    if e.response.status_code == 404:
        _error(f"{resource} not found")
    if e.response.status_code == 401:
        _error("invalid or expired token")
    if e.response.status_code == 403:
        _error("permission denied")
    raise e


# ---------------------------------------------------------------------------
# tracks
# ---------------------------------------------------------------------------

tracks_app = cyclopts.App(name="tracks", help="manage tracks.")
app.command(tracks_app)


@tracks_app.command(name="list")
def tracks_list(
    *,
    limit: Annotated[int, cyclopts.Parameter("--limit", help="max tracks")] = 20,
) -> None:
    """list public tracks."""
    client = _get_client()
    tracks = client.tracks.list(limit=limit)

    if not tracks:
        console.print("no tracks found")
        return

    table = Table(title="tracks")
    table.add_column("ID", style="cyan")
    table.add_column("title")
    table.add_column("artist")
    table.add_column("plays", justify="right")

    for t in tracks:
        table.add_row(str(t.id), t.title, t.artist, str(t.play_count))

    console.print(table)


@tracks_app.command(name="get")
def tracks_get(ref: str) -> None:
    """get a track by ID or AT-URI."""
    client = _get_client()
    track_ref = _parse_track_ref(ref)

    try:
        track = client.tracks.get(track_ref)
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "track")

    console.print(f"[bold]{track.title}[/] by {track.artist}")
    console.print(
        f"[dim]id:[/] {track.id}  [dim]plays:[/] {track.play_count}  [dim]likes:[/] {track.like_count}"
    )
    if track.album:
        console.print(f"[dim]album:[/] {track.album.title}")
    if track.tags:
        console.print(f"[dim]tags:[/] {', '.join(track.tags)}")
    if track.atproto_uri:
        console.print(f"[dim]uri:[/] {track.atproto_uri}")


@tracks_app.command(name="upload")
def tracks_upload(
    file: str,
    title: str,
    *,
    album: Annotated[
        str | None, cyclopts.Parameter("--album", help="album name")
    ] = None,
    tag: Annotated[
        list[str] | None,
        cyclopts.Parameter("--tag", alias="-t", help="tag (repeatable)"),
    ] = None,
    unlisted: Annotated[
        bool,
        cyclopts.Parameter(
            "--unlisted",
            help="exclude from public discovery feeds (latest, top, for-you); accessible by direct URL",
            negative=(),
        ),
    ] = False,
) -> None:
    """upload a track."""
    client = _get_client(require_auth=True)
    path = Path(file)
    if not path.exists():
        _error(f"file not found: {file}")

    tags = set(tag) if tag else None
    with console.status("uploading..."):
        try:
            result = client.tracks.upload(
                path, title, album=album, tags=tags, unlisted=unlisted
            )
        except ValueError as e:
            _error(str(e))
        except httpx.HTTPStatusError as e:
            _handle_http_error(e, "track")

    console.print(f"[green]uploaded:[/] track {result.track_id}")


@tracks_app.command(name="update")
def tracks_update(
    ref: str,
    *,
    title: Annotated[str | None, cyclopts.Parameter("--title")] = None,
    album: Annotated[str | None, cyclopts.Parameter("--album")] = None,
    tags: Annotated[
        str | None, cyclopts.Parameter("--tags", help="comma-separated tags")
    ] = None,
) -> None:
    """update track metadata."""
    client = _get_client(require_auth=True)
    track_ref = _parse_track_ref(ref)
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    patch = TrackPatch(title=title, album=album, tags=tag_list)

    try:
        track = client.tracks.update(track_ref, patch)
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "track")

    console.print(f"[green]updated:[/] {track.title}")
    if track.tags:
        console.print(f"[dim]tags:[/] {', '.join(track.tags)}")


@tracks_app.command(name="delete")
def tracks_delete(
    ref: str,
    *,
    yes: Annotated[
        bool, cyclopts.Parameter("--yes", alias="-y", help="skip confirmation")
    ] = False,
) -> None:
    """delete a track."""
    client = _get_client(require_auth=True)
    track_ref = _parse_track_ref(ref)

    try:
        track = client.tracks.get(track_ref)
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "track")

    if not yes:
        console.print(f"delete '{track.title}'? [y/N] ", end="")
        if input().lower() != "y":
            console.print("cancelled")
            return

    try:
        client.tracks.delete(track.id)
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "track")

    console.print(f"[green]deleted:[/] {track.title}")


@tracks_app.command(name="download")
def tracks_download(
    ref: str,
    *,
    output: Annotated[
        str | None, cyclopts.Parameter("--output", alias="-o", help="output path")
    ] = None,
) -> None:
    """download a track."""
    client = _get_client(require_auth=True)
    track_ref = _parse_track_ref(ref)

    with console.status("downloading..."):
        try:
            out_path = Path(output) if output else None
            result = client.tracks.download(track_ref, out_path)
        except httpx.HTTPStatusError as e:
            _handle_http_error(e, "track")

    size_mb = result.stat().st_size / 1024 / 1024
    console.print(f"[green]saved:[/] {result} ({size_mb:.1f} MB)")


@tracks_app.command(name="replace-audio")
def tracks_replace_audio(ref: str, file: str) -> None:
    """replace the audio file backing an existing track.

    the track's id / URI / likes / plays / metadata all carry over;
    only the audio bytes are replaced. previous audio is preserved as a revision.
    """
    client = _get_client(require_auth=True)
    track_ref = _parse_track_ref(ref)
    path = Path(file)
    if not path.exists():
        _error(f"file not found: {file}")

    with console.status("replacing audio..."):
        try:
            result = client.tracks.replace_audio(track_ref, path)
        except ValueError as e:
            _error(str(e))
        except httpx.HTTPStatusError as e:
            _handle_http_error(e, "track")

    console.print(f"[green]replaced audio:[/] track {result.track_id}")


@tracks_app.command(name="revisions")
def tracks_revisions(ref: str) -> None:
    """list previous audio versions of a track (newest first)."""
    client = _get_client(require_auth=True)
    track_ref = _parse_track_ref(ref)

    try:
        revisions = client.tracks.revisions(track_ref)
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "track")

    if not revisions:
        console.print("no revisions found")
        return

    table = Table(title=f"audio revisions for track {ref}")
    table.add_column("ID", style="cyan")
    table.add_column("created_at")
    table.add_column("format")
    table.add_column("duration", justify="right")
    table.add_column("storage")

    for r in revisions:
        duration = f"{r.duration}s" if r.duration is not None else "-"
        table.add_row(
            str(r.id),
            r.created_at.isoformat(),
            r.file_type,
            duration,
            r.audio_storage,
        )

    console.print(table)


@tracks_app.command(name="restore-revision")
def tracks_restore_revision(
    ref: str,
    revision_id: int,
    *,
    yes: Annotated[
        bool, cyclopts.Parameter("--yes", alias="-y", help="skip confirmation")
    ] = False,
) -> None:
    """restore a previous audio version of a track."""
    client = _get_client(require_auth=True)
    track_ref = _parse_track_ref(ref)

    if not yes:
        console.print(
            f"restore revision {revision_id} on track {ref}? "
            f"(current audio will be preserved as a new revision) [y/N] ",
            end="",
        )
        if input().lower() != "y":
            console.print("cancelled")
            return

    try:
        new_rev = client.tracks.restore_revision(track_ref, revision_id)
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "track or revision")

    console.print(
        f"[green]restored[/] revision {revision_id}; "
        f"previous audio saved as revision {new_rev.id}"
    )


@tracks_app.command(name="like")
def tracks_like(ref: str) -> None:
    """like a track."""
    client = _get_client(require_auth=True)
    track_ref = _parse_track_ref(ref)

    try:
        client.tracks.like(track_ref)
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "track")

    console.print(f"[green]liked[/] track {ref}")


@tracks_app.command(name="unlike")
def tracks_unlike(ref: str) -> None:
    """unlike a track."""
    client = _get_client(require_auth=True)
    track_ref = _parse_track_ref(ref)

    try:
        client.tracks.unlike(track_ref)
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "track")

    console.print(f"[dim]unliked[/] track {ref}")


@tracks_app.command(name="my")
def tracks_my(
    *,
    limit: Annotated[int, cyclopts.Parameter("--limit")] = 20,
) -> None:
    """list your tracks."""
    client = _get_client(require_auth=True)

    try:
        tracks = client.tracks.my(limit=limit)
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "tracks")

    if not tracks:
        console.print("no tracks found")
        return

    table = Table(title="your tracks")
    table.add_column("ID", style="cyan")
    table.add_column("title")
    table.add_column("album")
    table.add_column("plays", justify="right")

    for t in tracks:
        album_name = t.album.title if t.album else "-"
        table.add_row(str(t.id), t.title, album_name, str(t.play_count))

    console.print(table)


@tracks_app.command(name="liked")
def tracks_liked(
    *,
    limit: Annotated[int, cyclopts.Parameter("--limit")] = 20,
) -> None:
    """list tracks you've liked."""
    client = _get_client(require_auth=True)

    try:
        tracks = client.tracks.liked(limit=limit)
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "tracks")

    if not tracks:
        console.print("no liked tracks")
        return

    table = Table(title="liked tracks")
    table.add_column("ID", style="cyan")
    table.add_column("title")
    table.add_column("artist")

    for t in tracks:
        table.add_row(str(t.id), t.title, t.artist)

    console.print(table)


# ---------------------------------------------------------------------------
# playlists
# ---------------------------------------------------------------------------

playlists_app = cyclopts.App(name="playlists", help="manage playlists.")
app.command(playlists_app)


@playlists_app.command(name="list")
def playlists_list() -> None:
    """list your playlists."""
    client = _get_client(require_auth=True)

    try:
        playlists = client.playlists.list()
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "playlists")

    if not playlists:
        console.print("no playlists found")
        return

    table = Table(title="your playlists")
    table.add_column("ID", style="cyan")
    table.add_column("name")
    table.add_column("tracks", justify="right")
    table.add_column("profile", justify="center")

    for p in playlists:
        table.add_row(
            p.id, p.name, str(p.track_count), "yes" if p.show_on_profile else "-"
        )

    console.print(table)


@playlists_app.command(name="get")
def playlists_get(playlist_id: str) -> None:
    """show a playlist with its tracks."""
    client = _get_client()

    try:
        playlist = client.playlists.get(playlist_id)
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "playlist")

    console.print(f"[bold]{playlist.name}[/] by @{playlist.owner_handle}")
    console.print(f"[dim]{playlist.track_count} tracks[/]")

    if not playlist.tracks:
        console.print("  (empty)")
        return

    table = Table()
    table.add_column("#", style="dim")
    table.add_column("ID", style="cyan")
    table.add_column("title")
    table.add_column("artist")

    for i, t in enumerate(playlist.tracks, 1):
        table.add_row(str(i), str(t.id), t.title, t.artist)

    console.print(table)


@playlists_app.command(name="create")
def playlists_create(name: str) -> None:
    """create a playlist."""
    client = _get_client(require_auth=True)

    try:
        playlist = client.playlists.create(name)
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "playlist")

    console.print(f"[green]created:[/] {playlist.name} ({playlist.id})")


@playlists_app.command(name="add-track")
def playlists_add_track(playlist_id: str, track: str) -> None:
    """add a track to a playlist."""
    client = _get_client(require_auth=True)
    track_ref = _parse_track_ref(track)

    with console.status("adding track..."):
        try:
            playlist = client.playlists.add_track(playlist_id, track_ref)
        except ValueError as e:
            _error(str(e))
        except httpx.HTTPStatusError as e:
            _handle_http_error(e, "playlist or track")

    console.print(
        f"[green]added[/] track to {playlist.name} ({playlist.track_count} tracks)"
    )


@playlists_app.command(name="remove-track")
def playlists_remove_track(playlist_id: str, track: str) -> None:
    """remove a track from a playlist."""
    client = _get_client(require_auth=True)
    track_ref = _parse_track_ref(track)

    with console.status("removing track..."):
        try:
            playlist = client.playlists.remove_track(playlist_id, track_ref)
        except ValueError as e:
            _error(str(e))
        except httpx.HTTPStatusError as e:
            _handle_http_error(e, "playlist or track")

    console.print(
        f"[green]removed[/] track from {playlist.name} ({playlist.track_count} tracks)"
    )


@playlists_app.command(name="update")
def playlists_update(
    playlist_id: str,
    *,
    name: Annotated[str | None, cyclopts.Parameter("--name")] = None,
    show_on_profile: Annotated[
        bool | None, cyclopts.Parameter("--show-on-profile")
    ] = None,
) -> None:
    """update a playlist."""
    client = _get_client(require_auth=True)

    try:
        playlist = client.playlists.update(
            playlist_id, name=name, show_on_profile=show_on_profile
        )
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "playlist")

    console.print(f"[green]updated:[/] {playlist.name}")


@playlists_app.command(name="delete")
def playlists_delete(
    playlist_id: str,
    *,
    yes: Annotated[
        bool, cyclopts.Parameter("--yes", alias="-y", help="skip confirmation")
    ] = False,
) -> None:
    """delete a playlist."""
    client = _get_client(require_auth=True)

    if not yes:
        try:
            playlist = client.playlists.get(playlist_id)
        except httpx.HTTPStatusError as e:
            _handle_http_error(e, "playlist")

        console.print(
            f"delete '{playlist.name}' ({playlist.track_count} tracks)? [y/N] ", end=""
        )
        if input().lower() != "y":
            console.print("cancelled")
            return

    try:
        client.playlists.delete(playlist_id)
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "playlist")

    console.print("[green]deleted[/]")


# ---------------------------------------------------------------------------
# tags
# ---------------------------------------------------------------------------

tags_app = cyclopts.App(name="tags", help="browse tags.")
app.command(tags_app)


@tags_app.command(name="list")
def tags_list(
    *,
    limit: Annotated[int, cyclopts.Parameter("--limit")] = 20,
) -> None:
    """list tags with track counts."""
    client = _get_client()
    tags = client.tags.list(limit=limit)

    if not tags:
        console.print("no tags found")
        return

    table = Table(title="tags")
    table.add_column("tag", style="magenta")
    table.add_column("tracks", justify="right")

    for t in tags:
        table.add_row(f"#{t.name}", str(t.track_count))

    console.print(table)


@tags_app.command(name="get")
def tags_get(
    name: str,
    *,
    limit: Annotated[int, cyclopts.Parameter("--limit")] = 20,
) -> None:
    """list tracks with a specific tag."""
    client = _get_client()
    tracks = client.tags.tracks(name, limit=limit)

    if not tracks:
        console.print(f"no tracks found with tag '{name}'")
        return

    table = Table(title=f"tracks tagged #{name}")
    table.add_column("ID", style="cyan")
    table.add_column("title")
    table.add_column("artist")

    for t in tracks:
        table.add_row(str(t.id), t.title, t.artist)

    console.print(table)


# ---------------------------------------------------------------------------
# artists
# ---------------------------------------------------------------------------

artists_app = cyclopts.App(name="artists", help="manage artist profiles.")
app.command(artists_app)


@artists_app.command(name="me")
def artists_me() -> None:
    """show your artist profile."""
    client = _get_client(require_auth=True)

    try:
        profile = client.artists.me()
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "profile")

    console.print(f"[cyan]handle:[/] {profile.handle}")
    console.print(f"[cyan]display_name:[/] {profile.display_name or '-'}")
    console.print(f"[cyan]bio:[/] {profile.bio or '-'}")
    console.print(f"[cyan]support_url:[/] {profile.support_url or '-'}")


@artists_app.command(name="update")
def artists_update(
    *,
    bio: Annotated[str | None, cyclopts.Parameter("--bio")] = None,
    display_name: Annotated[str | None, cyclopts.Parameter("--display-name")] = None,
    support_url: Annotated[str | None, cyclopts.Parameter("--support-url")] = None,
) -> None:
    """update your artist profile."""
    client = _get_client(require_auth=True)
    patch = ArtistProfilePatch(
        bio=bio, display_name=display_name, support_url=support_url
    )

    try:
        profile = client.artists.update(patch)
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "profile")

    console.print("[green]updated profile[/]")
    console.print(f"[cyan]display_name:[/] {profile.display_name or '-'}")
    console.print(f"[cyan]bio:[/] {profile.bio or '-'}")


# ---------------------------------------------------------------------------
# discover
# ---------------------------------------------------------------------------

discover_app = cyclopts.App(name="discover", help="search and discover audio.")
app.command(discover_app)


@discover_app.command(name="search")
def discover_search(
    query: str,
    *,
    limit: Annotated[int, cyclopts.Parameter("--limit")] = 20,
) -> None:
    """search tracks, artists, albums, and tags."""
    client = _get_client()
    results = client.discover.search(query, limit=limit)

    if not results.results:
        console.print("no results found")
        return

    console.print(f"[dim]found: {results.counts}[/]")

    for result in results.results:
        if result.type == "track":
            console.print(
                f"[cyan]track[/] {result.id}: {result.title} by {result.artist_display_name}"
            )
        elif result.type == "artist":
            console.print(f"[green]artist[/] @{result.handle}: {result.display_name}")
        elif result.type == "album":
            console.print(
                f"[yellow]album[/] {result.title} by {result.artist_display_name}"
            )
        elif result.type == "tag":
            console.print(
                f"[magenta]tag[/] #{result.name} ({result.track_count} tracks)"
            )
        elif result.type == "playlist":
            console.print(
                f"[blue]playlist[/] {result.name} by {result.owner_display_name}"
            )


@discover_app.command(name="top")
def discover_top(
    *,
    limit: Annotated[int, cyclopts.Parameter("--limit")] = 10,
) -> None:
    """top tracks by likes."""
    client = _get_client()
    tracks = client.discover.top_tracks(limit=limit)

    if not tracks:
        console.print("no tracks found")
        return

    table = Table(title="top tracks")
    table.add_column("#", style="dim")
    table.add_column("ID", style="cyan")
    table.add_column("title")
    table.add_column("artist")
    table.add_column("likes", justify="right")

    for i, t in enumerate(tracks, 1):
        table.add_row(str(i), str(t.id), t.title, t.artist, str(t.like_count))

    console.print(table)


# ---------------------------------------------------------------------------
# top-level
# ---------------------------------------------------------------------------


@app.command(name="me")
def cmd_me() -> None:
    """show current user."""
    client = _get_client(require_auth=True)

    try:
        info = client.me()
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, "user")

    console.print(f"[cyan]did:[/] {info['did']}")
    console.print(f"[cyan]handle:[/] {info['handle']}")


# ---------------------------------------------------------------------------
# entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    app()


if __name__ == "__main__":
    main()
