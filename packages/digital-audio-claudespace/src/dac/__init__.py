"""digital audio claudespace - a toolkit for making music with code."""

from __future__ import annotations

import importlib.metadata

from dac.composition import Layer, Sequence
from dac.music import Ambient, Song, chord, note, rest
from dac.primitives import Noise, Oscillator, Silence
from dac.render import RenderError, render

try:
    __version__ = importlib.metadata.version("digital-audio-claudespace")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "Ambient",
    "Layer",
    "Noise",
    "Oscillator",
    "RenderError",
    "Sequence",
    "Silence",
    "Song",
    "__version__",
    "chord",
    "note",
    "render",
    "rest",
]
