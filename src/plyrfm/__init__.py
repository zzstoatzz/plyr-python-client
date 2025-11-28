"""plyrfm - python sdk for plyr.fm."""

from __future__ import annotations

import importlib.metadata

from plyrfm.client import AsyncPlyrClient, PlyrClient
from plyrfm._internal.types import Album, Artist, Track, UploadResult

try:
    __version__ = importlib.metadata.version("plyrfm")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "Album",
    "Artist",
    "AsyncPlyrClient",
    "PlyrClient",
    "Track",
    "UploadResult",
    "__version__",
]
