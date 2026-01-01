"""thursday - after eno's thursday afternoon and big empty country.

10-minute ambient piece with continuous texture.
16 independent loops at different cycle lengths (17-79 seconds).
harmonic base: G dominant 7th (G, B, D, F) + extensions (A, E).

"I play it every... 23 seconds, or thereabouts. Then I do the same
for another note... every 21½ seconds, perhaps." - eno

the piece should feel holographic - any section representative of the whole.
"""

from pathlib import Path

from dac.track import Sample, Sine, mix, phase

HERE = Path(__file__).parent
SAMPLES = HERE.parent / "samples"
OUTPUT = HERE / ".raw" / "thursday.wav"

# 10 minutes
duration = 600


def eno_loop(sample: Sample, cycle: float, offset: float = 0) -> list:
    """eno-style loop: sound plays, silence fills the cycle, repeats."""
    sample.pad(cycle)
    return phase(sample, interval=cycle, duration=duration, offset=offset)


# === CONTINUOUS BED ===
# these run throughout, providing constant texture

stream = (
    Sample(SAMPLES / "field" / "stream.wav", label="st")
    .trim(duration + 30)
    .volume(0.035)
    .fade_in(20)
    .fade_out(30)
    .lowpass(1200)
)

# dual drones - root and fifth, like thursday afternoon's G triad base
drone_g = (
    Sine(98.0, duration, amplitude=0.07, label="drg")  # G2
    .fade_in(30)
    .fade_out(40)
    .lowpass(200)
)

drone_d = (
    Sine(147.0, duration, amplitude=0.04, label="drd")  # D3
    .fade_in(40)
    .fade_out(50)
    .lowpass(250)
)

# === HARP LOOPS ===
# G7 chord tones + extensions, each at a prime cycle time
# staggered offsets prevent clustering

# G3 - home, frequent (cycle 19s)
harp_g3 = Sample(SAMPLES / "harp" / "KSHarp_G3_mf1.wav", label="hg3").volume(0.32)

# G3 with reverb - rare echo of home (cycle 71s)
harp_g3_rev = (
    Sample(SAMPLES / "harp" / "KSHarp_G3_mf1.wav", label="hg3r")
    .volume(0.22)
    .reverb(wet=0.6, decay=0.7)
)

# D4 - fifth (cycle 23s)
harp_d4 = Sample(SAMPLES / "harp" / "KSHarp_D4_mf1.wav", label="hd4").volume(0.28)

# B3 - major third (cycle 31s)
harp_b3 = Sample(SAMPLES / "harp" / "KSHarp_B3_mf1.wav", label="hb3").volume(0.26)

# E3 - sixth/13th, warmth (cycle 37s)
harp_e3 = Sample(SAMPLES / "harp" / "KSHarp_E3_mf1.wav", label="he3").volume(0.30)

# F4 - dominant 7th, the blue note (cycle 53s)
harp_f4 = Sample(SAMPLES / "harp" / "KSHarp_F4_mf1.wav", label="hf4").volume(0.20)

# A2 - low 9th, grounding (cycle 43s)
harp_a2 = Sample(SAMPLES / "harp" / "KSHarp_A2_mf1.wav", label="ha2").volume(0.35)

# A2 pitched down - rare low rumble (cycle 67s)
harp_a2_low = (
    Sample(SAMPLES / "harp" / "KSHarp_A2_mf1.wav", label="ha2l")
    .volume(0.25)
    .pitch(-5)
    .reverb(wet=0.5, decay=0.6)
)

# === VIBRAPHONE LOOPS ===
# warmer, sustaining tones for depth

# B3 vibes - warm third (cycle 41s)
vibes_b3 = (
    Sample(SAMPLES / "vibraphone" / "Vibes_soft_B3_v1_rr1_Main.wav", label="vb3")
    .volume(0.18)
    .reverb(wet=0.4, decay=0.5)
)

# A2 vibes - low warmth (cycle 61s)
vibes_a2 = (
    Sample(SAMPLES / "vibraphone" / "Vibes_soft_A2_v1_rr1_Main.wav", label="va2")
    .volume(0.22)
    .reverb(wet=0.45, decay=0.55)
)

# === ADDITIONAL TEXTURE ===
# more loops for density - variations on existing notes

# D4 with pan left (cycle 47s)
harp_d4_l = (
    Sample(SAMPLES / "harp" / "KSHarp_D4_mf1.wav", label="hd4l").volume(0.20).pan(-0.5)
)

# E3 with pan right (cycle 59s)
harp_e3_r = (
    Sample(SAMPLES / "harp" / "KSHarp_E3_mf1.wav", label="he3r").volume(0.22).pan(0.5)
)

# G3 pitched up octave - shimmer (cycle 79s, rare)
harp_g4 = (
    Sample(SAMPLES / "harp" / "KSHarp_G3_mf1.wav", label="hg4").volume(0.14).pitch(12)
)

# F4 slow - stretched 7th (cycle 73s)
harp_f4_slow = (
    Sample(SAMPLES / "harp" / "KSHarp_F4_mf1.wav", label="hf4s")
    .volume(0.16)
    .speed(0.7)
    .reverb(wet=0.55, decay=0.6)
)

# === ASSEMBLE THE SYSTEM ===
# 16 loops at prime cycle times, staggered offsets
# offsets chosen to spread events across the timeline

tracks = [
    # continuous bed
    stream,
    drone_g,
    drone_d,
    # harp loops - main voices
    *eno_loop(harp_g3, cycle=19, offset=0),  # home
    *eno_loop(harp_d4, cycle=23, offset=5),  # fifth
    *eno_loop(harp_b3, cycle=31, offset=11),  # third
    *eno_loop(harp_e3, cycle=37, offset=7),  # sixth
    *eno_loop(harp_a2, cycle=43, offset=3),  # low 9th
    *eno_loop(harp_f4, cycle=53, offset=17),  # 7th
    # vibraphone - warm sustain
    *eno_loop(vibes_b3, cycle=41, offset=13),  # warm third
    *eno_loop(vibes_a2, cycle=61, offset=21),  # low warmth
    # variations - spatial and timbral
    *eno_loop(harp_d4_l, cycle=47, offset=9),  # fifth left
    *eno_loop(harp_e3_r, cycle=59, offset=25),  # sixth right
    *eno_loop(harp_a2_low, cycle=67, offset=29),  # pitched low rumble
    *eno_loop(harp_g3_rev, cycle=71, offset=33),  # reverbed home
    *eno_loop(harp_f4_slow, cycle=73, offset=37),  # stretched 7th
    *eno_loop(harp_g4, cycle=79, offset=41),  # octave shimmer
]

# cycle info
cycles = [19, 23, 31, 37, 43, 53, 41, 61, 47, 59, 67, 71, 73, 79]
print(f"system: {len(tracks)} tracks")
print(f"loop cycles: {', '.join(str(c) for c in sorted(cycles))} (all prime)")
print(f"duration: {duration // 60} minutes")
print(f"shortest cycle: {min(cycles)}s, longest: {max(cycles)}s")

result = mix(tracks, OUTPUT, duration=duration)
print(f"rendered: {result}")
