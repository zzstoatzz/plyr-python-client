"""bells - vibraphone phasing, minimal."""

from pathlib import Path

from dac.track import Sample, Sine, mix, phase

HERE = Path(__file__).parent
SAMPLES = HERE.parent / "samples"
OUTPUT = HERE / ".raw" / "bells.wav"

duration = 60

# just two vibraphone notes phasing - keep it simple
vibe_a = (
    Sample(SAMPLES / "vibraphone" / "Vibes_soft_A2_v1_rr1_Main.wav", label="va")
    .volume(0.4)
    .fade_in(0.1)
)

vibe_b = (
    Sample(SAMPLES / "vibraphone" / "Vibes_soft_B3_v1_rr1_Main.wav", label="vb")
    .volume(0.35)
    .fade_in(0.1)
)

# sine pad underneath
pad = Sine(55, 15, amplitude=0.12, label="pad").fade_in(4).fade_out(5).lowpass(300)

# phase at different intervals - fewer repetitions
tracks = [
    *phase(vibe_a, interval=11.0, duration=duration, offset=0),
    *phase(vibe_b, interval=14.0, duration=duration, offset=4),
    *phase(pad, interval=18.0, duration=duration, offset=2),
]

result = mix(tracks, OUTPUT, duration=duration)
print(f"rendered: {result}")
