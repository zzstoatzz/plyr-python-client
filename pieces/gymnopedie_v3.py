"""Gymnopedie No. 1 (v3) - using compose abstractions.

same musical content as v2, but written with higher-level abstractions.
this version should be easier to read and modify.

structure:
- intro (4 measures): pedal + bass + chords, drums fade in
- main A (8 measures): melody enters
- main B (8 measures): melody repeats
- outro (4 measures): melody fades, drums fade out

run: uv run python pieces/gymnopedie_v3.py
"""

from datetime import timedelta
from pathlib import Path

from dac.compose import (
    BASS_PRESET,
    CHORD_PRESET,
    DrumKit,
    DrumSound,
    Humanize,
    Pedal,
    Phrase,
    Voice,
)
from dac.track import RenderConfig, Tempo, mix

# --- samples ---
SAMPLES_DIR = Path(__file__).parent.parent / "samples" / "drums"

# --- structure ---
TOTAL_MEASURES = 24
INTRO_END = 4
OUTRO_START = 21
tempo = Tempo(bpm=45, time_sig=(3, 4))
duration = TOTAL_MEASURES * tempo.measure + 2

# --- drums with lo-fi character ---
kit = DrumKit(
    kick=DrumSound(
        SAMPLES_DIR / "BDrumNew_hit_v2_rr1_Sum.wav",
        volume_db=+18,
        lowpass=80,
    ),
    snare=DrumSound(
        SAMPLES_DIR / "Snare2_HitNS_v2_rr1_Mid.wav",
        volume_db=+12,
        lowpass=400,
        timing_offset=timedelta(milliseconds=-30),  # pushes early
    ),
    hihat=DrumSound(
        SAMPLES_DIR / "HiHat_HitC_v1_rr1_Mid.wav",
        volume_db=+12,
        lowpass=2000,
        timing_offset=timedelta(milliseconds=25),  # drags late
    ),
    humanize=Humanize(
        timing=timedelta(milliseconds=8),
        velocity_db=0.6,  # +/- 0.6 dB variation
    ),
)

# --- melody phrase (Satie's opening) ---
melody = Phrase(
    [
        "F#5",
        "A5",
        "G5",
        "F#5",
        "C#5",
        "B4",
        "C#5",
        "D5",
        "A4",
    ],
    default_duration=1.0,
)

# --- build tracks ---
tracks = []

# pedal - F#4 throughout
pedal = Pedal("F#4", duration, amplitude=0.04)
tracks.extend(pedal.render())

# bass - alternating G2/D3 each measure
for m in range(TOTAL_MEASURES):
    beat = 1 + m * 3
    note = "G2" if m % 2 == 0 else "D3"
    voice = Voice(note, tempo.beats(2.8), preset=BASS_PRESET, label=f"b{m}")
    tracks.extend(voice.at_beat(beat, tempo))

# chords - alternating voicings each measure
for m in range(TOTAL_MEASURES):
    beat = 1 + m * 3
    if m % 2 == 0:
        # G major: B3, D4
        for note, amp in [("B3", 0.035), ("D4", 0.03)]:
            voice = Voice(
                note,
                tempo.beats(2.8),
                preset=CHORD_PRESET,
                amplitude=amp,
                label=f"c{m}",
            )
            tracks.extend(voice.at_beat(beat, tempo))
    else:
        # D major: A3, C#4
        for note, amp in [("A3", 0.035), ("C#4", 0.03)]:
            voice = Voice(
                note,
                tempo.beats(2.8),
                preset=CHORD_PRESET,
                amplitude=amp,
                label=f"c{m}",
            )
            tracks.extend(voice.at_beat(beat, tempo))

# melody - enters at measure 5, repeats at measure 13
melody_a_start = 1 + INTRO_END * 3  # beat 13
melody_b_start = 1 + 12 * 3  # beat 37
tracks.extend(melody.render(melody_a_start, tempo, label="ma"))
tracks.extend(melody.render(melody_b_start, tempo, label="mb"))

# drums - fade in during intro, fade out during outro
for m in range(TOTAL_MEASURES):
    b1 = 1 + m * 3
    b2 = 2 + m * 3
    b3 = 3 + m * 3

    # calculate fade
    if m < INTRO_END:
        fade = (m + 1) / INTRO_END
        vol_adj = -12 * (1 - fade)
    elif m >= OUTRO_START - 1:
        fade = (TOTAL_MEASURES - m) / (TOTAL_MEASURES - OUTRO_START + 1)
        vol_adj = -12 * (1 - fade)
    else:
        vol_adj = 0

    # kick on 1
    if t := kit.render_kick(b1, tempo, volume_db=+18 + vol_adj):
        tracks.append(t)

    # snare on 3
    if t := kit.render_snare(b3, tempo, volume_db=+12 + vol_adj):
        tracks.append(t)

    # hats on every beat
    for b in [b1, b2, b3]:
        if t := kit.render_hihat(b, tempo, volume_db=+12 + vol_adj):
            tracks.append(t)


if __name__ == "__main__":
    output = Path("/tmp/gymnopedie_v3.wav")
    config = RenderConfig(duration=duration, limit_db=-3)
    mix(tracks, output, config=config)

    from dac.analyze import analyze, analyze_bands

    metrics = analyze(output)
    bands = analyze_bands(output)
    print(f"rendered {output} ({len(tracks)} tracks)")
    print(metrics.summary())
    print()
    print(bands.summary())
