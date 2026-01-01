"""Gymnopedie No. 1 (v4) - mix improvements.

changes from v3:
- melody amplitude increased (was buried in mix)
- stereo: bass left, chords right, melody center
- second melody phrase slightly louder (dynamic arc)

run: uv run python pieces/gymnopedie_v4.py
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
    VoicePreset,
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

# --- presets with stereo positioning ---
# melody louder than v3: 0.07 -> 0.14 (compensate for stereo split + more presence)
MELODY_LOUD = VoicePreset(
    amplitude=0.14, detune_cents=4, lowpass=800, attack=0.3, release=0.5
)
MELODY_LOUDER = VoicePreset(
    amplitude=0.16, detune_cents=4, lowpass=800, attack=0.3, release=0.5
)

# --- drums ---
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
        timing_offset=timedelta(milliseconds=-30),
    ),
    hihat=DrumSound(
        SAMPLES_DIR / "HiHat_HitC_v1_rr1_Mid.wav",
        volume_db=+12,
        lowpass=2000,
        timing_offset=timedelta(milliseconds=25),
    ),
    humanize=Humanize(
        timing=timedelta(milliseconds=8),
        velocity_db=0.6,
    ),
)

# --- melody phrases ---
melody_a = Phrase(
    ["F#5", "A5", "G5", "F#5", "C#5", "B4", "C#5", "D5", "A4"],
    preset=MELODY_LOUD,
)
melody_b = Phrase(
    ["F#5", "A5", "G5", "F#5", "C#5", "B4", "C#5", "D5", "A4"],
    preset=MELODY_LOUDER,  # second time builds slightly
)

# --- build tracks ---
tracks = []

# pedal - F#4 throughout (amplitude doubled for stereo)
pedal = Pedal("F#4", duration, amplitude=0.08)
tracks.extend(pedal.render())

# bass - alternating G2/D3, panned slightly left
# amplitude doubled from BASS_PRESET to compensate for stereo
for m in range(TOTAL_MEASURES):
    beat = 1 + m * 3
    note = "G2" if m % 2 == 0 else "D3"
    voice = Voice(
        note, tempo.beats(2.8), preset=BASS_PRESET, amplitude=0.16, label=f"b{m}"
    )
    for t in voice.at_beat(beat, tempo):
        t.pan(-0.3)  # slight left
        tracks.append(t)

# chords - alternating voicings, panned slightly right
# amplitudes doubled for stereo
for m in range(TOTAL_MEASURES):
    beat = 1 + m * 3
    if m % 2 == 0:
        chord_notes = [("B3", 0.07), ("D4", 0.06)]
    else:
        chord_notes = [("A3", 0.07), ("C#4", 0.06)]

    for note, amp in chord_notes:
        voice = Voice(
            note, tempo.beats(2.8), preset=CHORD_PRESET, amplitude=amp, label=f"c{m}"
        )
        for t in voice.at_beat(beat, tempo):
            t.pan(0.3)  # slight right
            tracks.append(t)

# melody - center, enters at measure 5, repeats at measure 13
melody_a_start = 1 + INTRO_END * 3
melody_b_start = 1 + 12 * 3
tracks.extend(melody_a.render(melody_a_start, tempo, label="ma"))
tracks.extend(melody_b.render(melody_b_start, tempo, label="mb"))

# drums - fade in during intro, fade out during outro
for m in range(TOTAL_MEASURES):
    b1 = 1 + m * 3
    b2 = 2 + m * 3
    b3 = 3 + m * 3

    if m < INTRO_END:
        fade = (m + 1) / INTRO_END
        vol_adj = -12 * (1 - fade)
    elif m >= OUTRO_START - 1:
        fade = (TOTAL_MEASURES - m) / (TOTAL_MEASURES - OUTRO_START + 1)
        vol_adj = -12 * (1 - fade)
    else:
        vol_adj = 0

    if t := kit.render_kick(b1, tempo, volume_db=+18 + vol_adj):
        tracks.append(t)
    if t := kit.render_snare(b3, tempo, volume_db=+12 + vol_adj):
        tracks.append(t)
    for b in [b1, b2, b3]:
        if t := kit.render_hihat(b, tempo, volume_db=+12 + vol_adj):
            tracks.append(t)


if __name__ == "__main__":
    output = Path("/tmp/gymnopedie_v4.wav")
    config = RenderConfig(duration=duration, limit_db=-3, channels=2)  # stereo
    mix(tracks, output, config=config)

    from dac.analyze import analyze, analyze_bands

    metrics = analyze(output)
    bands = analyze_bands(output)
    print(f"rendered {output} ({len(tracks)} tracks)")
    print(metrics.summary())
    print()
    print(bands.summary())
