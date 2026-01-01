"""digital audio claudespace - programmatic music via ffmpeg.

example:
    from dac.track import Sample, Sine, phase, mix
    from pathlib import Path

    # create tracks with effects
    harp = Sample("samples/harp/KSHarp_E3_mf1.wav").volume(0.4).lowpass(1500)
    pad = Sine(110, 8).volume(0.3).fade_in(1).tremolo(0.5, 0.3)

    # phase them at different intervals
    tracks = [
        *phase(harp, interval=8.7, duration=90),
        *phase(pad, interval=11.3, duration=90, offset=2),
    ]

    mix(tracks, Path("output.wav"), duration=90)
"""

from dac import chords, compose, track
from dac.compose import DrumKit, DrumSound, Humanize, Pedal, Phrase, Voice
from dac.track import RenderConfig, Sample, Sine, Tempo, mix, phase

__all__ = [
    "DrumKit",
    "DrumSound",
    "Humanize",
    "Pedal",
    "Phrase",
    "RenderConfig",
    "Sample",
    "Sine",
    "Tempo",
    "Voice",
    "chords",
    "compose",
    "mix",
    "phase",
    "track",
]
