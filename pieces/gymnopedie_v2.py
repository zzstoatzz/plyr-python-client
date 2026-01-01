"""Gymnopédie No. 1 (v2) - extended lo-fi arrangement.

structure:
- intro (4 measures): pedal + bass + chords, drums fade in
- main A (8 measures): melody enters
- main B (8 measures): melody continues/varies
- outro (4 measures): melody fades, just chords + drums fade out

run: uv run python pieces/gymnopedie_v2.py
"""

from pathlib import Path

from dac.track import RenderConfig, Sample, Sine, Tempo, mix, note_to_freq

# sample paths
SAMPLES_DIR = Path(__file__).parent.parent / "samples" / "drums"
KICK_SAMPLE = SAMPLES_DIR / "BDrumNew_hit_v2_rr1_Sum.wav"
SNARE_SAMPLE = SAMPLES_DIR / "Snare2_HitNS_v2_rr1_Mid.wav"
HIHAT_SAMPLE = SAMPLES_DIR / "HiHat_HitC_v1_rr1_Mid.wav"

# preferences
PEDAL_AMPLITUDE = 0.04
BASS_AMPLITUDE = 0.08
CHORD_AMPLITUDE = 0.035
MELODY_AMPLITUDE = 0.07
LOWPASS_BASS = 150
LOWPASS_CHORDS = 400
LOWPASS_MELODY = 600
LOWPASS_PEDAL = 400

tempo = Tempo(bpm=45, time_sig=(3, 4))
n = note_to_freq

# structure: 24 measures total = 72 beats
TOTAL_MEASURES = 24
INTRO_MEASURES = 4  # measures 1-4: no melody
MAIN_A_START = 5  # measures 5-12: first melody
MAIN_B_START = 13  # measures 13-20: second melody
OUTRO_START = 21  # measures 21-24: fade out

duration = TOTAL_MEASURES * tempo.measure + 2  # ~2 minutes


def warm_sine(
    freq: float, dur: float, amp: float, label: str, detune_cents: float = 4
) -> list[Sine]:
    """create a sine with a slightly detuned pair for warmth."""
    detune_ratio = 2 ** (detune_cents / 1200)
    main = Sine(freq, dur, amplitude=amp * 0.7, label=f"{label}_m")
    sharp = Sine(freq * detune_ratio, dur, amplitude=amp * 0.15, label=f"{label}_s")
    flat = Sine(freq / detune_ratio, dur, amplitude=amp * 0.15, label=f"{label}_f")
    return [main, sharp, flat]


tracks = []

# --- pedal - continuous F#4 throughout ---
for t in warm_sine(n("F#4"), duration, PEDAL_AMPLITUDE, "ped"):
    t.lowpass(LOWPASS_PEDAL).fade_in(6).fade_out(6)
    tracks.append(t)


# --- bass ---
def bass(note: str, beat: int) -> list[Sine]:
    result = []
    for t in warm_sine(n(note), tempo.beats(2.8), BASS_AMPLITUDE, f"b{beat}"):
        t.lowpass(LOWPASS_BASS).fade_in(0.6).fade_out(0.8).delay(tempo.at_beat(beat))
        result.append(t)
    return result


# bass throughout all measures
for m in range(TOTAL_MEASURES):
    beat = 1 + m * 3
    tracks.extend(bass("G2" if m % 2 == 0 else "D3", beat))


# --- inner voices (chords) ---
def voice(note: str, beat: int, amp: float = CHORD_AMPLITUDE) -> list[Sine]:
    result = []
    for t in warm_sine(n(note), tempo.beats(2.8), amp, f"v{beat}"):
        t.lowpass(LOWPASS_CHORDS).fade_in(0.7).fade_out(0.7).delay(tempo.at_beat(beat))
        result.append(t)
    return result


# chords throughout
for m in range(TOTAL_MEASURES):
    beat = 1 + m * 3
    if m % 2 == 0:
        tracks.extend(voice("B3", beat))
        tracks.extend(voice("D4", beat, 0.03))
    else:
        tracks.extend(voice("A3", beat))
        tracks.extend(voice("C#4", beat, 0.03))


# --- melody ---
def melody_note(note: str, beat: int, dur: float = 1.8) -> list[Sine]:
    result = []
    for t in warm_sine(n(note), tempo.beats(dur), MELODY_AMPLITUDE, f"m{beat}"):
        t.lowpass(LOWPASS_MELODY).fade_in(0.3).fade_out(0.5).delay(tempo.at_beat(beat))
        result.append(t)
    return result


# melody phrase A (measures 5-12)
melody_a = [
    ("F#5", 13),
    ("A5", 14),
    ("G5", 15),
    ("F#5", 16),
    ("C#5", 17),
    ("B4", 18),
    ("C#5", 19),
    ("D5", 20),
    ("A4", 21),
]
for note, beat in melody_a:
    tracks.extend(melody_note(note, beat))

# melody phrase B (measures 13-20) - repeat the phrase
melody_b = [
    ("F#5", 37),
    ("A5", 38),
    ("G5", 39),
    ("F#5", 40),
    ("C#5", 41),
    ("B4", 42),
    ("C#5", 43),
    ("D5", 44),
    ("A4", 45),
]
for note, beat in melody_b:
    tracks.extend(melody_note(note, beat))


# --- lo-fi percussion ---

SNARE_EARLY_MS = 30
HIHAT_LATE_MS = 25


def kick(beat: int, vol_db: float = +18) -> Sample:
    """lo-fi kick - sub thump."""
    return (
        Sample(KICK_SAMPLE, label=f"k{beat}")
        .lowpass(80)
        .volume_db(vol_db)
        .delay(tempo.at_beat(beat))
    )


def snare(beat: int, vol_db: float = +12) -> Sample:
    """lo-fi snare - pushes early."""
    return (
        Sample(SNARE_SAMPLE, label=f"s{beat}")
        .lowpass(400)
        .volume_db(vol_db)
        .delay(max(0, tempo.at_beat(beat) - SNARE_EARLY_MS))
    )


def hihat(beat: int, vol_db: float = +12) -> Sample:
    """lo-fi hi-hat - drags late, muted."""
    return (
        Sample(HIHAT_SAMPLE, label=f"hh{beat}")
        .lowpass(2000)  # more muted
        .volume_db(vol_db)
        .delay(tempo.at_beat(beat) + HIHAT_LATE_MS)
    )


# drums with fade in/out
for m in range(TOTAL_MEASURES):
    b1 = 1 + m * 3
    b2 = 2 + m * 3
    b3 = 3 + m * 3

    # fade drums in during intro, out during outro
    if m < INTRO_MEASURES:
        # fade in: quieter at start
        fade = (m + 1) / INTRO_MEASURES
        vol_adj = -12 * (1 - fade)  # starts -12dB quieter
    elif m >= OUTRO_START - 1:
        # fade out
        fade = (TOTAL_MEASURES - m) / (TOTAL_MEASURES - OUTRO_START + 1)
        vol_adj = -12 * (1 - fade)
    else:
        vol_adj = 0

    tracks.append(kick(b1, +18 + vol_adj))
    tracks.append(snare(b3, +12 + vol_adj))
    tracks.append(hihat(b1, +18 + vol_adj))
    tracks.append(hihat(b2, +18 + vol_adj))
    tracks.append(hihat(b3, +18 + vol_adj))


if __name__ == "__main__":
    output = Path("/tmp/gymnopedie_v2.wav")
    config = RenderConfig(duration=duration, limit_db=-3)
    mix(tracks, output, config=config)

    from dac.analyze import analyze, analyze_bands

    metrics = analyze(output)
    bands = analyze_bands(output)
    print(f"rendered {output} ({len(tracks)} tracks)")
    print(metrics.summary())
    print()
    print(bands.summary())
