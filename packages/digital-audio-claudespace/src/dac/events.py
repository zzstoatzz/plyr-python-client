"""timeline-based composition - notes placed at specific times."""

from pathlib import Path

from dac._internal.ffmpeg import build_note_filter, run_ffmpeg
from dac._internal.notes import Waveform, note_to_freq


def render(
    events: list[tuple[float, str | list[str], float]],
    output: str | Path,
    *,
    amp: float = 0.15,
    wave: Waveform = "sine",
    attack: float = 0.05,
    release: float = 0.15,
    fade_in: float = 2.0,
    fade_out: float = 4.0,
    sample_rate: int = 48_000,
) -> Path:
    """render a timeline of note events to audio.

    args:
        events: list of (start_time, note_or_notes, duration) tuples
            - start_time: when the note begins (seconds)
            - note_or_notes: "C4" or ["C4", "E4", "G4"] for chords
            - duration: how long the note lasts (seconds)
        output: path for the output file
        amp: amplitude (0-1)
        wave: waveform type
        attack: attack time as fraction of note duration
        release: release time as fraction of note duration
        fade_in: overall fade in time (seconds)
        fade_out: overall fade out time (seconds)
        sample_rate: audio sample rate

    example:
        render([
            (0, "C2", 8),
            (0, ["E3", "G3"], 4),
            (2, "C4", 3),
        ], "piece.wav")
    """
    output = Path(output)

    # flatten chords into individual notes
    notes: list[tuple[float, float, float, float]] = []
    for start, note_spec, dur in events:
        if isinstance(note_spec, list):
            chord_amp = amp / (len(note_spec) ** 0.5)
            for n in note_spec:
                notes.append((start, note_to_freq(n), dur, chord_amp))
        else:
            notes.append((start, note_to_freq(note_spec), dur, amp))

    if not notes:
        raise ValueError("no notes to render")

    total_dur = max(start + dur for start, _, dur, _ in notes)

    # build filter graph
    parts: list[str] = []
    labels: list[str] = []

    for i, (start, freq, dur, note_amp) in enumerate(notes):
        att = min(dur * attack, 0.05)
        rel = min(dur * release, 0.15)
        label = f"n{i}"

        part = build_note_filter(
            freq,
            dur,
            note_amp,
            wave=wave,
            attack=att,
            release=rel,
            delay_ms=int(start * 1000),
            label=label,
            sample_rate=sample_rate,
        )
        parts.append(part)
        labels.append(f"[{label}]")

    # mix all notes
    mix = f"{''.join(labels)}amix=inputs={len(notes)}:duration=longest:normalize=0"
    if fade_in > 0:
        mix += f",afade=t=in:d={fade_in}"
    if fade_out > 0:
        mix += f",afade=t=out:st={total_dur - fade_out}:d={fade_out}"
    mix += "[out]"

    graph = ";".join(parts) + ";" + mix
    return run_ffmpeg(graph, output, sample_rate=sample_rate)
