"""digital audio claudespace - programmatic music via ffmpeg.

two approaches:
- events: place notes at specific times on a timeline
- loops: eno-style phasing loops that drift in and out of phase

example:
    from dac import events, loops, chords

    # timeline
    events.render([
        (0, "C2", 8),
        (0, chords.major("C3"), 4),
    ], "piece.wav")

    # phasing loops
    loops.render([
        ("A2", 11.3, 8, 0.07),
        ("E3", 13.7, 9, 0.05),
    ], duration=120, output="ambient.wav")
"""

from dac import chords, events, loops
from dac._internal.notes import Waveform

__all__ = [
    "Waveform",
    "chords",
    "events",
    "loops",
]
