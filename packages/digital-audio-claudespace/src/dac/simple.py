"""simple timeline-based music.

the core idea: music is just notes at times.

    from dac.simple import play, render

    music = [
        # (time, note(s), duration)
        (0, "C2", 8),                    # bass
        (0, ["C3", "E3", "G3"], 4),       # chord
        (4, ["A2", "C3", "E3"], 4),       # next chord
        (2, "G4", 2),                    # melody
        (5, "E4", 3),
    ]

    render(music, "piece.wav")
"""

from __future__ import annotations

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
    """generate ffmpeg aevalsrc expression."""
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


def render(
    events: list[tuple],
    output: str | Path,
    *,
    amp: float = 0.15,
    wave: str = "sine",
    attack_pct: float = 0.05,
    release_pct: float = 0.15,
    sample_rate: int = 48000,
    fade_in: float = 2.0,
    fade_out: float = 4.0,
) -> Path:
    """render a timeline of note events to audio.

    events: list of (start_time, note_or_notes, duration) tuples
        - start_time: when the note begins (seconds)
        - note_or_notes: "C4" or ["C4", "E4", "G4"]
        - duration: how long the note lasts (seconds)

    example:
        render([
            (0, "C2", 8),
            (0, ["E3", "G3"], 4),
            (2, "C4", 3),
        ], "out.wav")
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found")

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    # flatten events: each note becomes a separate filter
    notes = []  # (start, freq, duration)
    for event in events:
        start, note_spec, dur = event[0], event[1], event[2]
        if isinstance(note_spec, list):
            # chord - reduce amplitude per note
            chord_amp = amp / (len(note_spec) ** 0.5)
            for n in note_spec:
                notes.append((start, _note_to_freq(n), dur, chord_amp))
        else:
            notes.append((start, _note_to_freq(note_spec), dur, amp))

    if not notes:
        raise ValueError("no notes to render")

    # calculate total duration
    total_dur = max(start + dur for start, _, dur, _ in notes)

    # build filter graph
    # each note: aevalsrc -> afade (envelope) -> adelay -> [label]
    parts = []
    labels = []

    for i, (start, freq, dur, note_amp) in enumerate(notes):
        # envelope times
        att = min(dur * attack_pct, 0.05)
        rel = min(dur * release_pct, 0.15)
        rel_start = max(dur - rel, 0)

        # generate note with envelope
        expr = _wave_expr(freq, wave)
        src = f"aevalsrc=exprs='{note_amp}*({expr})':s={sample_rate}:d={dur}"
        fades = f"afade=t=in:d={att},afade=t=out:st={rel_start}:d={rel}"

        # delay to start time (adelay takes milliseconds)
        delay_ms = int(start * 1000)
        delay = f"adelay={delay_ms}:all=1" if delay_ms > 0 else ""

        label = f"n{i}"
        if delay:
            parts.append(f"{src},{fades},{delay}[{label}]")
        else:
            parts.append(f"{src},{fades}[{label}]")
        labels.append(f"[{label}]")

    # mix all notes together
    mix = f"{''.join(labels)}amix=inputs={len(notes)}:duration=longest:normalize=0"

    # add overall fade in/out
    if fade_in > 0 or fade_out > 0:
        fades = []
        if fade_in > 0:
            fades.append(f"afade=t=in:d={fade_in}")
        if fade_out > 0:
            fades.append(f"afade=t=out:st={total_dur - fade_out}:d={fade_out}")
        mix = mix + "," + ",".join(fades)

    mix += "[out]"
    graph = ";".join(parts) + ";" + mix

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


# convenience: common chord shapes
def major(root: str) -> list[str]:
    """major triad from root."""
    return [root, _interval_note(root, 4), _interval_note(root, 7)]


def minor(root: str) -> list[str]:
    """minor triad from root."""
    return [root, _interval_note(root, 3), _interval_note(root, 7)]


def _interval_note(root: str, semitones: int) -> str:
    """get note name at interval from root."""
    freq = _note_to_freq(root) * (2 ** (semitones / 12))
    # convert back to note name (approximate to nearest semitone)
    import math

    total_semitones = round(12 * math.log2(freq / 440.0))
    note_idx = (total_semitones + 9) % 12
    octave = 4 + (total_semitones + 9) // 12
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[note_idx]}{octave}"
