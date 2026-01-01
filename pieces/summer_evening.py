"""summer evening - ambient piece.

a summer evening in the woods, just before dark.
distant piano, clear air, peace.

constant barely-perceptible sound as a bed,
sparse melodic fragments floating above.

run: uv run python pieces/summer_evening.py
"""

import random
from pathlib import Path

from dac.track import RenderConfig, Sine, Tempo, mix, note_to_freq

random.seed(42)  # reproducible

# --- config ---
DURATION = 360  # 6 minutes
tempo = Tempo(bpm=40, time_sig=(4, 4))

# very quiet - barely perceptible
DRONE_AMP = 0.015
MELODY_AMP = 0.025

n = note_to_freq

tracks = []

# --- drone bed: layered frequencies creating warmth ---
# multiple sine waves at related frequencies, very quiet, slow beating

# root drone - D2 with slight detuning for organic movement
drone_freqs = [
    n("D2"),
    n("D2") * 1.002,  # slight sharp for beating
    n("A2") * 0.5,  # sub-octave hint
]

for i, freq in enumerate(drone_freqs):
    t = Sine(freq, DURATION, amplitude=DRONE_AMP * 0.6, label=f"drone{i}")
    t.lowpass(120).fade_in(20).fade_out(30)
    tracks.append(t)

# mid drone - D3 and A3 for warmth
mid_freqs = [
    n("D3"),
    n("A3") * 0.998,  # slight flat
]

for i, freq in enumerate(mid_freqs):
    t = Sine(freq, DURATION, amplitude=DRONE_AMP * 0.4, label=f"mid{i}")
    t.lowpass(200).fade_in(30).fade_out(40)
    tracks.append(t)

# high shimmer - very quiet, creates "air"
shimmer_freqs = [n("D5"), n("A4"), n("F#5")]
for i, freq in enumerate(shimmer_freqs):
    t = Sine(freq, DURATION, amplitude=DRONE_AMP * 0.15, label=f"shim{i}")
    t.lowpass(800).fade_in(45).fade_out(45)
    # slow tremolo for organic movement
    t.tremolo(freq=0.1, depth=0.3)
    tracks.append(t)


# --- melodic fragments: sparse, distant piano feel ---
# pentatonic in D major: D, E, F#, A, B
# notes appear randomly, widely spaced, with long decay

melody_notes = ["D4", "E4", "F#4", "A4", "B4", "D5", "A3", "F#3"]
melody_weights = [3, 2, 2, 3, 1, 2, 2, 1]  # favor D and A


def weighted_choice(notes, weights):
    total = sum(weights)
    r = random.random() * total
    cumulative = 0
    for note, weight in zip(notes, weights, strict=False):
        cumulative += weight
        if r <= cumulative:
            return note
    return notes[-1]


# place notes sparsely throughout
# average one note every 8-15 seconds
time = 30  # start after drones establish
note_count = 0

while time < DURATION - 60:  # stop 60s before end
    note = weighted_choice(melody_notes, melody_weights)
    freq = n(note)

    # vary duration: 4-10 seconds
    dur = random.uniform(4, 10)

    # vary amplitude slightly
    amp = MELODY_AMP * random.uniform(0.7, 1.0)

    t = Sine(freq, dur, amplitude=amp, label=f"m{note_count}")
    t.lowpass(600)  # warm, muted
    t.fade_in(1.5)  # gentle attack
    t.fade_out(dur * 0.6)  # long decay
    t.delay(int(time * 1000))

    # add slight reverb/echo for distance
    t.echo(delay_ms=800, decay=0.2)

    tracks.append(t)

    # next note: 8-20 seconds later
    time += random.uniform(8, 20)
    note_count += 1

# --- occasional two-note intervals for depth ---
time = 60
interval_count = 0

while time < DURATION - 90:
    # pick a root and add a fifth or octave
    root = random.choice(["D3", "A3", "D4"])
    root_freq = n(root)

    # fifth above
    fifth_freq = root_freq * 1.5

    dur = random.uniform(6, 12)
    amp = MELODY_AMP * 0.5  # quieter than single notes

    # root
    t1 = Sine(root_freq, dur, amplitude=amp, label=f"int{interval_count}r")
    t1.lowpass(400).fade_in(2).fade_out(dur * 0.5).delay(int(time * 1000))
    tracks.append(t1)

    # fifth, slightly delayed
    t2 = Sine(fifth_freq, dur * 0.8, amplitude=amp * 0.7, label=f"int{interval_count}f")
    t2.lowpass(500).fade_in(2.5).fade_out(dur * 0.4).delay(int((time + 0.5) * 1000))
    tracks.append(t2)

    time += random.uniform(30, 50)
    interval_count += 1


if __name__ == "__main__":
    output = Path("/tmp/summer_evening.wav")
    config = RenderConfig(duration=DURATION, limit_db=-6)
    mix(tracks, output, config=config)

    from dac.analyze import analyze, analyze_bands

    metrics = analyze(output)
    bands = analyze_bands(output)
    print(f"rendered {output} ({len(tracks)} tracks, {DURATION / 60:.1f} min)")
    print(metrics.summary())
    print()
    print(bands.summary())
