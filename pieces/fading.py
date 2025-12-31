"""fading - after eno's fading music.

incommensurable loops: each sound repeats at its own prime-number
cycle time. the loops phase naturally, creating combinations that
never exactly repeat.

"if there is any score for the piece, it must be the operational
diagram of the particular apparatus." - eno, 1975
"""

from pathlib import Path

from dac.track import Sample, Sine, mix, phase

HERE = Path(__file__).parent
SAMPLES = HERE.parent / "samples"
OUTPUT = HERE / ".raw" / "fading.wav"

# 4 minutes - enough time for the phase relationships to evolve
duration = 240


def eno_loop(sample: Sample, cycle: float, offset: float = 0) -> list:
    """create an eno-style loop: sound padded to cycle time, repeating.

    the sound plays once, then silence fills the rest of the cycle.
    cycle times should be prime/coprime for incommensurable phasing.
    """
    # add pad to the sample's effects, then phase it
    sample.pad(cycle)
    return phase(sample, interval=cycle, duration=duration, offset=offset)


# continuous drone - G2, the tonal anchor
# not looped - just present throughout
drone = (
    Sine(98.0, duration, amplitude=0.08, label="dr")
    .fade_in(20)
    .fade_out(20)
    .lowpass(150)
)

# stream texture - continuous
stream = (
    Sample(SAMPLES / "field" / "stream.wav", label="st")
    .trim(duration + 10)
    .volume(0.04)
    .fade_in(15)
    .lowpass(1500)
)

# === THE LOOPS ===
# each harp note loops at a prime-number cycle
# all notes are in G major - mutually compatible in any combination

# G3 - home, cycle every 17 seconds
loop_g3 = Sample(SAMPLES / "harp" / "KSHarp_G3_mf1.wav", label="g3").volume(0.35)

# D4 - fifth, cycle every 19 seconds
loop_d4 = Sample(SAMPLES / "harp" / "KSHarp_D4_mf1.wav", label="d4").volume(0.32)

# B3 - third, cycle every 23 seconds
loop_b3 = Sample(SAMPLES / "harp" / "KSHarp_B3_mf1.wav", label="b3").volume(0.28)

# E3 - sixth, cycle every 29 seconds
loop_e3 = Sample(SAMPLES / "harp" / "KSHarp_E3_mf1.wav", label="e3").volume(0.30)

# A2 - second (low), cycle every 31 seconds
loop_a2 = Sample(SAMPLES / "harp" / "KSHarp_A2_mf1.wav", label="a2").volume(0.38)

# F4 - seventh (lydian color), cycle every 37 seconds - rare
loop_f4 = Sample(SAMPLES / "harp" / "KSHarp_F4_mf1.wav", label="f4").volume(0.22)

# assemble the system - just harp loops, no glockenspiel
tracks = [
    stream,
    drone,
    # harp loops at prime intervals, staggered offsets
    *eno_loop(loop_g3, cycle=17, offset=0),
    *eno_loop(loop_d4, cycle=19, offset=3),
    *eno_loop(loop_b3, cycle=23, offset=7),
    *eno_loop(loop_e3, cycle=29, offset=11),
    *eno_loop(loop_a2, cycle=31, offset=5),
    *eno_loop(loop_f4, cycle=37, offset=15),
]

print(f"system: {len(tracks)} tracks")
print("loop cycles: 17, 19, 23, 29, 31, 37 (all prime)")
print(f"LCM would be ~{17 * 19 * 23 * 29 * 31 * 37:,} seconds before exact repeat")

result = mix(tracks, OUTPUT, duration=duration)
print(f"rendered: {result}")
