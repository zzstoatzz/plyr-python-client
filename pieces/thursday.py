"""thursday - after eno's thursday afternoon.

drone-forward. the continuous tones ARE the piece.
melodic touches are rare, quiet punctuation.
"""

from pathlib import Path

from dac.track import Sample, Sine, mix, phase

HERE = Path(__file__).parent
SAMPLES = HERE.parent / "samples"
OUTPUT = HERE / ".raw" / "thursday.wav"

duration = 600  # 10 minutes


def sparse_loop(sample: Sample, cycle: float, offset: float = 0) -> list:
    """rare melodic touch - long cycle, quiet."""
    sample.pad(cycle)
    return phase(sample, interval=cycle, duration=duration, offset=offset)


# === THE DRONE BED ===
# this is the piece. layered sine tones creating a rich, evolving texture.

# root drone - G2, the foundation
drone_g2 = (
    Sine(98.0, duration, amplitude=0.35, label="dg2")
    .fade_in(60)
    .fade_out(60)
    .lowpass(400)
)

# fifth above - D3, warmth
drone_d3 = (
    Sine(147.0, duration, amplitude=0.25, label="dd3")
    .fade_in(80)
    .fade_out(70)
    .lowpass(500)
)

# octave - G3, shimmer
drone_g3 = (
    Sine(196.0, duration, amplitude=0.15, label="dg3")
    .fade_in(100)
    .fade_out(80)
    .lowpass(600)
)

# third - B3, major color (quieter, enters later)
drone_b3 = (
    Sine(247.0, duration, amplitude=0.08, label="db3")
    .fade_in(120)
    .fade_out(90)
    .lowpass(700)
)

# === TEXTURE ===
# stream provides organic movement against the static drones

stream = (
    Sample(SAMPLES / "field" / "stream.wav", label="st")
    .trim(duration + 30)
    .volume(0.12)
    .fade_in(30)
    .fade_out(40)
    .lowpass(2000)
)

# === RARE MELODIC TOUCHES ===
# very quiet, very sparse - just occasional color

# G3 harp - home, every 90 seconds
touch_g3 = (
    Sample(SAMPLES / "harp" / "KSHarp_G3_mf1.wav", label="tg3")
    .volume(0.08)
    .reverb(wet=0.5, decay=0.6)
)

# D4 harp - fifth, every 120 seconds
touch_d4 = (
    Sample(SAMPLES / "harp" / "KSHarp_D4_mf1.wav", label="td4")
    .volume(0.06)
    .reverb(wet=0.5, decay=0.6)
)

# B3 harp - third, every 150 seconds (rare)
touch_b3 = (
    Sample(SAMPLES / "harp" / "KSHarp_B3_mf1.wav", label="tb3")
    .volume(0.07)
    .reverb(wet=0.5, decay=0.6)
)

# === ASSEMBLE ===
tracks = [
    # the drone bed - this IS the piece
    drone_g2,
    drone_d3,
    drone_g3,
    drone_b3,
    # organic texture
    stream,
    # rare touches - sparse punctuation
    *sparse_loop(touch_g3, cycle=89, offset=30),
    *sparse_loop(touch_d4, cycle=127, offset=70),
    *sparse_loop(touch_b3, cycle=151, offset=110),
]

print(f"tracks: {len(tracks)}")
print("drone stack: G2 + D3 + G3 + B3 (G major)")
print("melodic cycles: 89s, 127s, 151s (very sparse)")
print(f"duration: {duration // 60} minutes")

result = mix(tracks, OUTPUT, duration=duration)
print(f"rendered: {result}")
