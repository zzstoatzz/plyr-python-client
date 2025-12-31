"""note and frequency utilities."""

import math
from typing import Literal

Waveform = Literal["sine", "square", "triangle", "saw"]

_NOTE_OFFSETS: dict[str, int] = {
    "C": -9,
    "D": -7,
    "E": -5,
    "F": -4,
    "G": -2,
    "A": 0,
    "B": 2,
}

_NOTE_NAMES: list[str] = [
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
]


def note_to_freq(name: str) -> float:
    """convert note name to frequency. A4 = 440 Hz."""
    letter = name[0].upper()
    rest = name[1:]
    mod = 0

    if rest.startswith("#"):
        mod, rest = 1, rest[1:]
    elif rest.startswith("b"):
        mod, rest = -1, rest[1:]

    octave = int(rest)
    semitones = _NOTE_OFFSETS[letter] + mod + (octave - 4) * 12
    return 440.0 * (2 ** (semitones / 12))


def freq_to_note(freq: float) -> str:
    """convert frequency to nearest note name."""
    semitones = round(12 * math.log2(freq / 440.0))
    note_idx = (semitones + 9) % 12
    octave = 4 + (semitones + 9) // 12
    return f"{_NOTE_NAMES[note_idx]}{octave}"


def interval(root: str, semitones: int) -> str:
    """get note at interval from root."""
    freq = note_to_freq(root) * (2 ** (semitones / 12))
    return freq_to_note(freq)
