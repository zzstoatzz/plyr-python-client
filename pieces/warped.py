"""warped - testing new audio effects.

uses reverse, pitch, speed, pan, flanger, phaser.
"""

from pathlib import Path

from dac.track import Sample, Sine, mix

HERE = Path(__file__).parent
SAMPLES = HERE.parent / "samples"
OUTPUT = HERE / ".raw" / "warped.wav"

duration = 60

# continuous drone - slightly detuned for texture
drone = (
    Sine(110, duration, amplitude=0.12, label="dr").fade_in(8).fade_out(8).lowpass(200)
)

# harp - normal
harp_normal = (
    Sample(SAMPLES / "harp" / "KSHarp_G3_mf1.wav", label="h1").volume(0.4).delay(2000)
)

# harp - pitched down 5 semitones (darker)
harp_low = (
    Sample(SAMPLES / "harp" / "KSHarp_G3_mf1.wav", label="h2")
    .volume(0.35)
    .pitch(-5)
    .delay(8000)
)

# harp - pitched up 7 semitones (brighter)
harp_high = (
    Sample(SAMPLES / "harp" / "KSHarp_G3_mf1.wav", label="h3")
    .volume(0.3)
    .pitch(7)
    .delay(14000)
)

# harp - reversed
harp_rev = (
    Sample(SAMPLES / "harp" / "KSHarp_D4_mf1.wav", label="h4")
    .volume(0.35)
    .reverse()
    .delay(22000)
)

# harp - slowed down (stretched)
harp_slow = (
    Sample(SAMPLES / "harp" / "KSHarp_E3_mf1.wav", label="h5")
    .volume(0.4)
    .speed(0.6)  # 40% slower
    .delay(30000)
)

# harp - with flanger
harp_flange = (
    Sample(SAMPLES / "harp" / "KSHarp_B3_mf1.wav", label="h6")
    .volume(0.35)
    .flanger(delay=4, depth=3, speed=0.3)
    .delay(40000)
)

# harp - panned left with phaser
harp_left = (
    Sample(SAMPLES / "harp" / "KSHarp_A2_mf1.wav", label="h7")
    .volume(0.4)
    .pan(-0.7)
    .phaser(speed=0.3)
    .delay(48000)
)

# harp - panned right
harp_right = (
    Sample(SAMPLES / "harp" / "KSHarp_F4_mf1.wav", label="h8")
    .volume(0.35)
    .pan(0.7)
    .delay(52000)
)

tracks = [
    drone,
    harp_normal,
    harp_low,
    harp_high,
    harp_rev,
    harp_slow,
    harp_flange,
    harp_left,
    harp_right,
]

result = mix(tracks, OUTPUT, duration=duration)
print(f"rendered: {result} ({len(tracks)} tracks)")
