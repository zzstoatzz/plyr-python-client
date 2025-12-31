"""plyr.fm CLI."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
from rich.console import Console
from rich.table import Table

from plyrfm._internal.types import ArtistProfilePatch
from plyrfm.client import PlyrClient

console = Console()


def _error(msg: str) -> None:
    """print error and exit."""
    console.print(f"[red]error:[/] {msg}")
    sys.exit(1)


def _get_client(require_auth: bool = False) -> PlyrClient:
    """get client, optionally requiring auth."""
    client = PlyrClient()
    if require_auth and not client._token:
        _error(
            "authentication required. "
            "set PLYR_TOKEN or create a token at plyr.fm/portal"
        )
    return client


# -----------------------------------------------------------------------------
# commands
# -----------------------------------------------------------------------------


def cmd_list(limit: int = 20) -> None:
    """list all public tracks (no auth required)."""
    client = _get_client()

    with console.status("fetching tracks..."):
        tracks = client.list_tracks(limit=limit)

    if not tracks:
        console.print("no tracks found")
        return

    table = Table(title="tracks")
    table.add_column("ID", style="cyan")
    table.add_column("title")
    table.add_column("artist")
    table.add_column("plays", justify="right")

    for track in tracks:
        table.add_row(
            str(track.id),
            track.title,
            track.artist,
            str(track.play_count),
        )

    console.print(table)


def cmd_my_tracks(limit: int = 20) -> None:
    """list your own tracks (requires auth)."""
    client = _get_client(require_auth=True)

    with console.status("fetching your tracks..."):
        try:
            tracks = client.my_tracks(limit=limit)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                _error("invalid or expired token")
            raise

    if not tracks:
        console.print("no tracks found")
        return

    table = Table(title="your tracks")
    table.add_column("ID", style="cyan")
    table.add_column("title")
    table.add_column("album")
    table.add_column("plays", justify="right")

    for track in tracks:
        album_name = track.album.title if track.album else "-"
        table.add_row(
            str(track.id),
            track.title,
            album_name,
            str(track.play_count),
        )

    console.print(table)


def cmd_upload(
    file: str, title: str, album: str | None = None, tags: set[str] | None = None
) -> None:
    """upload a track (requires auth)."""
    client = _get_client(require_auth=True)
    path = Path(file)

    if not path.exists():
        _error(f"file not found: {file}")

    with console.status("uploading..."):
        try:
            result = client.upload(path, title, album=album, tags=tags)
        except FileNotFoundError:
            _error(f"file not found: {file}")
        except ValueError as e:
            _error(str(e))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                _error("invalid or expired token")
            raise

    console.print(f"[green]uploaded:[/] track {result.track_id}")


def cmd_download(track_id: int, output: str | None = None) -> None:
    """download a track (requires auth)."""
    client = _get_client(require_auth=True)

    with console.status("downloading..."):
        try:
            out_path = Path(output) if output else None
            result = client.download(track_id, out_path)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                _error(f"track {track_id} not found")
            if e.response.status_code == 401:
                _error("invalid or expired token")
            raise

    size_mb = result.stat().st_size / 1024 / 1024
    console.print(f"[green]saved:[/] {result} ({size_mb:.1f} MB)")


def cmd_delete(track_id: int, yes: bool = False) -> None:
    """delete a track (requires auth)."""
    client = _get_client(require_auth=True)

    # get track info for confirmation
    with console.status("fetching track..."):
        try:
            track = client.get_track(track_id)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                _error(f"track {track_id} not found")
            if e.response.status_code == 401:
                _error("invalid or expired token")
            raise

    if not yes:
        console.print(f"delete '{track.title}'? [y/N] ", end="")
        if input().lower() != "y":
            console.print("cancelled")
            return

    try:
        client.delete(track_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            _error(f"track {track_id} not found")
        raise

    console.print(f"[green]deleted:[/] {track.title}")


def cmd_me() -> None:
    """show current user (requires auth)."""
    client = _get_client(require_auth=True)

    try:
        info = client.me()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            _error("invalid or expired token")
        raise

    console.print(f"[cyan]did:[/] {info['did']}")
    console.print(f"[cyan]handle:[/] {info['handle']}")


def cmd_profile() -> None:
    """show artist profile (requires auth)."""
    client = _get_client(require_auth=True)

    try:
        profile = client.get_artist_profile()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            _error("invalid or expired token")
        raise

    console.print(f"[cyan]handle:[/] {profile.handle}")
    console.print(f"[cyan]display_name:[/] {profile.display_name or '-'}")
    console.print(f"[cyan]bio:[/] {profile.bio or '-'}")
    console.print(f"[cyan]support_url:[/] {profile.support_url or '-'}")


def cmd_update_profile(
    bio: str | None = None,
    display_name: str | None = None,
    support_url: str | None = None,
) -> None:
    """update artist profile (requires auth)."""
    client = _get_client(require_auth=True)

    patch = ArtistProfilePatch(
        bio=bio,
        display_name=display_name,
        support_url=support_url,
    )

    try:
        profile = client.update_artist_profile(patch)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            _error("invalid or expired token")
        raise

    console.print("[green]updated profile[/]")
    console.print(f"[cyan]display_name:[/] {profile.display_name or '-'}")
    console.print(f"[cyan]bio:[/] {profile.bio or '-'}")


# -----------------------------------------------------------------------------
# main
# -----------------------------------------------------------------------------

USAGE = """\
[bold]plyrfm[/] - plyr.fm CLI

[bold]usage:[/]
    plyrfm <command> [options]

[bold]public commands (no auth):[/]
    list [--limit N]              list all tracks

[bold]authenticated commands:[/]
    my-tracks [--limit N]         list your tracks
    upload <file> <title> [--album NAME] [-t TAG ...]
                                  upload a track
    download <id> [--output FILE] download a track
    delete <id> [--yes]           delete a track
    me                            show current user
    profile                       show artist profile
    update-profile [--bio TEXT] [--display-name NAME] [--support-url URL]
                                  update artist profile

[bold]auth setup:[/]
    1. create a token at plyr.fm/portal -> "developer tokens"
    2. export PLYR_TOKEN="your_token"

[bold]examples:[/]
    plyrfm list                                  # no auth needed
    plyrfm my-tracks                             # requires auth
    plyrfm upload track.mp3 "My Song"            # requires auth
    plyrfm upload track.mp3 "My Song" -t ai      # with tag
    plyrfm upload track.mp3 "My Song" -t ai -t podcast  # multiple tags
    plyrfm download 42 -o song.mp3               # requires auth
    plyrfm update-profile --bio "music maker"    # update bio
"""


def main() -> None:
    """CLI entrypoint."""
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        console.print(USAGE)
        return

    cmd = args[0]

    if cmd == "list":
        limit = 20
        if "--limit" in args:
            idx = args.index("--limit")
            if idx + 1 < len(args):
                limit = int(args[idx + 1])
        cmd_list(limit=limit)

    elif cmd == "my-tracks":
        limit = 20
        if "--limit" in args:
            idx = args.index("--limit")
            if idx + 1 < len(args):
                limit = int(args[idx + 1])
        cmd_my_tracks(limit=limit)

    elif cmd == "upload":
        if len(args) < 3:
            _error("usage: plyrfm upload <file> <title> [--album NAME] [-t TAG ...]")
        file = args[1]
        title = args[2]
        album = None
        tags: set[str] = set()
        if "--album" in args:
            idx = args.index("--album")
            if idx + 1 < len(args):
                album = args[idx + 1]
        # collect all -t/--tag values
        i = 0
        while i < len(args):
            if args[i] in ("-t", "--tag") and i + 1 < len(args):
                tags.add(args[i + 1])
                i += 2
            else:
                i += 1
        cmd_upload(file, title, album, tags if tags else None)

    elif cmd == "download":
        if len(args) < 2:
            _error("usage: plyrfm download <id> [--output FILE]")
        track_id = int(args[1])
        output = None
        if "--output" in args:
            idx = args.index("--output")
            if idx + 1 < len(args):
                output = args[idx + 1]
        elif "-o" in args:
            idx = args.index("-o")
            if idx + 1 < len(args):
                output = args[idx + 1]
        cmd_download(track_id, output)

    elif cmd == "delete":
        if len(args) < 2:
            _error("usage: plyrfm delete <id> [--yes]")
        track_id = int(args[1])
        yes = "--yes" in args or "-y" in args
        cmd_delete(track_id, yes)

    elif cmd == "me":
        cmd_me()

    elif cmd == "profile":
        cmd_profile()

    elif cmd == "update-profile":
        bio = None
        display_name = None
        support_url = None
        if "--bio" in args:
            idx = args.index("--bio")
            if idx + 1 < len(args):
                bio = args[idx + 1]
        if "--display-name" in args:
            idx = args.index("--display-name")
            if idx + 1 < len(args):
                display_name = args[idx + 1]
        if "--support-url" in args:
            idx = args.index("--support-url")
            if idx + 1 < len(args):
                support_url = args[idx + 1]
        cmd_update_profile(bio=bio, display_name=display_name, support_url=support_url)

    else:
        _error(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
