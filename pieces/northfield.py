"""northfield - evening in G major.

deliberately composed, not algorithmically generated.
each note placed with intent.
"""

from pathlib import Path

from dac.track import Sample, Sine, mix

HERE = Path(__file__).parent
SAMPLES = HERE.parent / "samples"
OUTPUT = HERE / ".raw" / "northfield.wav"

duration = 90


def harp(note: str, time: float, vol: float = 0.45) -> Sample:
    """place a harp note at a specific time."""
    return (
        Sample(
            SAMPLES / "harp" / f"KSHarp_{note}_mf1.wav", label=f"h{note}_{int(time)}"
        )
        .volume(vol)
        .delay(int(time * 1000))
    )


def glock(note: str, time: float, vol: float = 0.15) -> Sample:
    """place a glockenspiel note at a specific time."""
    return (
        Sample(
            SAMPLES / "glockenspiel" / f"glock_medium_{note}_01.wav",
            label=f"g{note}_{int(time)}",
        )
        .volume(vol)
        .delay(int(time * 1000))
    )


# continuous elements
stream = (
    Sample(SAMPLES / "field" / "stream.wav", label="st")
    .trim(duration + 10)
    .volume(0.05)
    .fade_in(6)
    .lowpass(1800)
)

drone_g = (
    Sine(98.0, duration - 5, amplitude=0.12, label="dg")
    .fade_in(8)
    .fade_out(8)
    .lowpass(180)
)

# --- COMPOSITION ---
# Section A (0-30s): Sparse opening, establishing G
# Section B (30-60s): Building, more voices
# Section C (60-90s): Full, then fading

tracks = [
    stream,
    drone_g,
    # === Section A: sparse, establishing home ===
    harp("G3", 4),  # first note - home
    harp("D4", 10),  # fifth answers
    harp("G3", 16),  # return home
    harp("E3", 22, 0.4),  # sixth adds warmth
    harp("G3", 28),  # home again
    # === Section B: building ===
    harp("D4", 32),  # fifth
    harp("B3", 36, 0.4),  # third - new color
    harp("G3", 40),  # home
    harp("A2", 44, 0.5),  # low second - grounding
    harp("D4", 48),  # fifth
    harp("G3", 52),  # home
    glock("G5", 54, 0.12),  # high shimmer - first glock, mirrors the G
    harp("E3", 58, 0.4),  # sixth
    # === Section C: fullest, then resolve ===
    harp("G3", 62),  # home
    harp("B3", 65, 0.4),  # third
    harp("D4", 68),  # fifth - G major triad spread out
    harp("A2", 72, 0.5),  # low anchor
    harp("G3", 76),  # home
    glock("G5", 78, 0.1),  # shimmer
    harp("E3", 82, 0.35),  # gentle sixth
    harp("G3", 86),  # final home
]

result = mix(tracks, OUTPUT, duration=duration)
print(f"rendered: {result} ({len(tracks)} tracks)")
