"""digital audio claudespace - programmatic music via ffmpeg.

example:
    from dac import Sine, Sample, mix, Tempo, note_to_freq
    from pathlib import Path

    # create tracks with effects
    tone = Sine(note_to_freq("A4"), 4, amplitude=0.3)
    tone.fade_in(0.5).fade_out(1)

    mix([tone], Path("output.wav"), duration=5)

for higher-level composition (evolving API):
    from dac.compose import Voice, Phrase, DrumKit

for analysis:
    from dac.analyze import analyze, analyze_bands

for real-time synth (experimental):
    from dac import live
    live.synth.play("bass", 110, 0.02)
"""

# core track primitives (stable)
from dac.track import RenderConfig, Sample, Sine, Tempo, Track, mix, phase

# note utilities (stable)
from dac._internal.notes import freq_to_note, interval, note_to_freq

# analysis (stable)
from dac.analyze import AudioMetrics, BandLevels, analyze, analyze_bands

# module access
from dac import analyze as _analyze_module
from dac import chords, compose, live, track

__all__ = [
    "AudioMetrics",
    "BandLevels",
    "RenderConfig",
    "Sample",
    "Sine",
    "Tempo",
    "Track",
    "analyze",
    "analyze_bands",
    "chords",
    "compose",
    "freq_to_note",
    "interval",
    "live",
    "mix",
    "note_to_freq",
    "phase",
    "track",
]
