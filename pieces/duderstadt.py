"""duderstadt - winter study ambient.

drones and instruments paired - when a drone enters, its
matching instrument punctuates. harmonic unity.
"""

from pathlib import Path

from dac.track import Sample, Sine, mix, phase

HERE = Path(__file__).parent
SAMPLES = HERE.parent / "samples"
OUTPUT = HERE / ".raw" / "duderstadt.wav"

duration = 90

# wind - quiet texture
wind = (
    Sample(SAMPLES / "field" / "wind.wav", label="wd")
    .trim(duration + 10)
    .volume(0.03)
    .fade_in(5)
    .highpass(250)
)

# --- E foundation: drone + low vibe together ---
drone_e = Sine(82.4, 16, amplitude=0.24, label="de").fade_in(2).fade_out(3).lowpass(150)
vibe_e = Sample(
    SAMPLES / "vibraphone" / "Vibes_soft_A2_v1_rr1_Main.wav", label="ve"
).volume(0.4)

# --- B layer: drone + vibe together ---
drone_b = Sine(246.9, 14, amplitude=0.12, label="db").fade_in(2).fade_out(2)
vibe_b = Sample(
    SAMPLES / "vibraphone" / "Vibes_soft_B3_v1_rr1_Main.wav", label="vb"
).volume(0.35)

# --- high accent: glockenspiel on its own cycle ---
glock = Sample(SAMPLES / "glockenspiel" / "glock_medium_G5_01.wav", label="gl").volume(
    0.18
)

# paired intervals - drone and instrument enter together
E_INTERVAL = 11.0
B_INTERVAL = 13.0
GLOCK_INTERVAL = 17.0

tracks = [
    wind,
    # E foundation - drone and vibe at same interval, slight instrument delay
    *phase(drone_e, interval=E_INTERVAL, duration=duration, offset=0),
    *phase(
        vibe_e, interval=E_INTERVAL, duration=duration, offset=0.3
    ),  # vibe follows drone
    # B layer - same pairing
    *phase(drone_b, interval=B_INTERVAL, duration=duration, offset=5),
    *phase(
        vibe_b, interval=B_INTERVAL, duration=duration, offset=5.3
    ),  # vibe follows drone
    # high crystalline accent - independent slower cycle
    *phase(glock, interval=GLOCK_INTERVAL, duration=duration, offset=8),
]

result = mix(tracks, OUTPUT, duration=duration)
print(f"rendered: {result} ({len(tracks)} tracks)")
