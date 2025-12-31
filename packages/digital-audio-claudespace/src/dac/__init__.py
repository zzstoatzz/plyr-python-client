"""digital audio claudespace - programmatic music via ffmpeg.

two ways to make music:

1. render_events() - place notes at specific times
2. render_loops() - eno-style phasing loops

examples:

    from dac import render_events, render_loops

    # timeline approach
    render_events([
        (0, "C2", 8),
        (0, ["E3", "G3"], 4),
        (2, "C4", 3),
    ], "piece.wav")

    # phasing loops
    render_loops([
        ("A2", 11.3, 8, 0.07),
        ("E3", 13.7, 9, 0.05),
    ], duration=120, output="ambient.wav")
"""

import shutil
import subprocess
from pathlib import Path


def _note_to_freq(name: str) -> float:
    """C4 = middle C = 261.63 Hz, A4 = 440 Hz."""
    offsets = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    letter = name[0].upper()
    rest = name[1:]
    mod = 0
    if rest.startswith("#"):
        mod, rest = 1, rest[1:]
    elif rest.startswith("b"):
        mod, rest = -1, rest[1:]
    octave = int(rest)
    semitones = offsets[letter] + mod + (octave - 4) * 12
    return 440.0 * (2 ** (semitones / 12))


def _wave_expr(freq: float, wave: str = "sine") -> str:
    ang = f"2*PI*{freq}*t"
    base = f"t*{freq}"
    if wave == "sine":
        return f"sin({ang})"
    if wave == "square":
        return f"(gt(sin({ang}),0)*2-1)"
    if wave == "triangle":
        return f"(abs(4*(({base})-floor({base}+0.75))-2)-1)"
    if wave == "saw":
        return f"(2*((({base})-floor({base}+0.5))))"
    return f"sin({ang})"


def _run_ffmpeg(graph: str, output: Path, sample_rate: int = 48000) -> Path:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found")
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-filter_complex",
        graph,
        "-map",
        "[out]",
        "-ar",
        str(sample_rate),
        "-ac",
        "2",
        "-y",
        str(output),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg failed: {e.stderr}") from e
    return output


def render_events(
    events: list[tuple],
    output: str | Path,
    *,
    amp: float = 0.15,
    wave: str = "sine",
    attack: float = 0.05,
    release: float = 0.15,
    fade_in: float = 2.0,
    fade_out: float = 4.0,
    sample_rate: int = 48000,
) -> Path:
    """render a timeline of note events to audio.

    events: list of (start_time, note_or_notes, duration) tuples
        - start_time: when the note begins (seconds)
        - note_or_notes: "C4" or ["C4", "E4", "G4"] for chords
        - duration: how long the note lasts (seconds)
    """
    output = Path(output)

    # flatten chords into individual notes
    notes = []
    for start, note_spec, dur in events:
        if isinstance(note_spec, list):
            chord_amp = amp / (len(note_spec) ** 0.5)
            for n in note_spec:
                notes.append((start, _note_to_freq(n), dur, chord_amp))
        else:
            notes.append((start, _note_to_freq(note_spec), dur, amp))

    if not notes:
        raise ValueError("no notes to render")

    total_dur = max(start + dur for start, _, dur, _ in notes)

    # build filter graph
    parts = []
    labels = []
    for i, (start, freq, dur, note_amp) in enumerate(notes):
        att = min(dur * attack, 0.05)
        rel = min(dur * release, 0.15)
        rel_start = max(dur - rel, 0)

        expr = _wave_expr(freq, wave)
        src = f"aevalsrc=exprs='{note_amp}*({expr})':s={sample_rate}:d={dur}"
        fades = f"afade=t=in:d={att},afade=t=out:st={rel_start}:d={rel}"
        delay_ms = int(start * 1000)

        if delay_ms > 0:
            parts.append(f"{src},{fades},adelay={delay_ms}:all=1[n{i}]")
        else:
            parts.append(f"{src},{fades}[n{i}]")
        labels.append(f"[n{i}]")

    mix = f"{''.join(labels)}amix=inputs={len(notes)}:duration=longest:normalize=0"
    if fade_in > 0:
        mix += f",afade=t=in:d={fade_in}"
    if fade_out > 0:
        mix += f",afade=t=out:st={total_dur - fade_out}:d={fade_out}"
    mix += "[out]"

    return _run_ffmpeg(";".join(parts) + ";" + mix, output, sample_rate)


def render_loops(
    loops: list[tuple],
    duration: float,
    output: str | Path,
    *,
    amp: float = 0.08,
    attack: float = 0.35,
    release: float = 0.45,
    fade_in: float = 6.0,
    fade_out: float = 10.0,
    stagger: bool = True,
    sample_rate: int = 48000,
) -> Path:
    """render phasing loops to audio (eno style).

    loops: list of tuples, each can be:
        - (note, loop_length, note_duration)
        - (note, loop_length, note_duration, amplitude)
        - (note, loop_length, note_duration, amplitude, start_offset)

    duration: total piece length in seconds
    stagger: offset loops so they don't all start at t=0
    """
    output = Path(output)

    # expand loops into individual note events
    events = []
    for i, loop in enumerate(loops):
        note, loop_len, note_dur = loop[0], loop[1], loop[2]
        loop_amp = loop[3] if len(loop) > 3 else amp

        if len(loop) > 4:
            start_offset = loop[4]
        elif stagger:
            start_offset = (loop_len * 0.618 * i) % loop_len
        else:
            start_offset = 0.0

        freq = _note_to_freq(note)
        t = start_offset
        while t < duration:
            if t + note_dur <= duration + note_dur * 0.5:
                events.append((t, freq, min(note_dur, duration - t), loop_amp))
            t += loop_len

    if not events:
        raise ValueError("no events generated")

    # build filter graph
    parts = []
    labels = []
    for i, (start, freq, dur, note_amp) in enumerate(events):
        att = dur * attack
        rel = dur * release
        rel_start = max(dur - rel, att)

        expr = _wave_expr(freq)
        src = f"aevalsrc=exprs='{note_amp}*({expr})':s={sample_rate}:d={dur}"
        fades = (
            f"afade=t=in:d={att}:curve=tri,afade=t=out:st={rel_start}:d={rel}:curve=tri"
        )
        delay_ms = int(start * 1000)

        if delay_ms > 0:
            parts.append(f"{src},{fades},adelay={delay_ms}:all=1[n{i}]")
        else:
            parts.append(f"{src},{fades}[n{i}]")
        labels.append(f"[n{i}]")

    mix = f"{''.join(labels)}amix=inputs={len(events)}:duration=longest:normalize=0"
    if fade_in > 0:
        mix += f",afade=t=in:d={fade_in}:curve=tri"
    if fade_out > 0:
        mix += f",afade=t=out:st={duration - fade_out}:d={fade_out}:curve=tri"
    mix += "[out]"

    return _run_ffmpeg(";".join(parts) + ";" + mix, output, sample_rate)


# chord helpers
def major(root: str) -> list[str]:
    """major triad: root + M3 + P5."""
    return [root, _interval(root, 4), _interval(root, 7)]


def minor(root: str) -> list[str]:
    """minor triad: root + m3 + P5."""
    return [root, _interval(root, 3), _interval(root, 7)]


def _interval(root: str, semitones: int) -> str:
    import math

    freq = _note_to_freq(root) * (2 ** (semitones / 12))
    total = round(12 * math.log2(freq / 440.0))
    note_idx = (total + 9) % 12
    octave = 4 + (total + 9) // 12
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[note_idx]}{octave}"
