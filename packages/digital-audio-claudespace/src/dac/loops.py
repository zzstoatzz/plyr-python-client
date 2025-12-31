"""loop-based generative music in the style of eno.

the idea: loops of different lengths phase against each other,
creating music that never repeats.

    from dac.loops import render_loops

    loops = [
        # (note, loop_length, note_duration)
        ("C2", 23.5, 18),   # bass, repeats every 23.5s
        ("G3", 27.3, 14),   # mid, repeats every 27.3s
        ("E4", 31.7, 12),   # high, repeats every 31.7s
    ]

    render_loops(loops, duration=180, output="eno.wav")
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _note_to_freq(name: str) -> float:
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


def _wave_expr(freq: float) -> str:
    return f"sin(2*PI*{freq}*t)"


def render_loops(
    loops: list[tuple],
    duration: float,
    output: str | Path,
    *,
    amp: float = 0.08,
    attack_ratio: float = 0.35,
    release_ratio: float = 0.45,
    sample_rate: int = 48000,
    fade_in: float = 6.0,
    fade_out: float = 10.0,
    stagger: bool = True,
) -> Path:
    """render phasing loops to audio.

    loops: list of (note, loop_length, note_duration) or
           (note, loop_length, note_duration, amplitude) or
           (note, loop_length, note_duration, amplitude, start_offset) tuples

    duration: total piece length in seconds
    stagger: if True, automatically offset loops so they don't all start at 0
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found")

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    # expand loops into individual note events
    events = []  # (start_time, freq, note_dur, amp)

    for i, loop in enumerate(loops):
        note, loop_len, note_dur = loop[0], loop[1], loop[2]
        loop_amp = loop[3] if len(loop) > 3 else amp
        # explicit start offset, or auto-stagger based on loop index
        if len(loop) > 4:
            start_offset = loop[4]
        elif stagger:
            # stagger each loop by a fraction of its loop length
            # using golden ratio for good distribution
            start_offset = (loop_len * 0.618 * i) % loop_len
        else:
            start_offset = 0.0

        freq = _note_to_freq(note)

        # generate all occurrences of this loop
        t = start_offset
        while t < duration:
            # only add if the note fits within duration
            if t + note_dur <= duration + note_dur * 0.5:
                events.append((t, freq, min(note_dur, duration - t), loop_amp))
            t += loop_len

    if not events:
        raise ValueError("no events generated")

    # build filter graph
    parts = []
    labels = []

    for i, (start, freq, dur, note_amp) in enumerate(events):
        att = dur * attack_ratio
        rel = dur * release_ratio
        rel_start = max(dur - rel, att)  # ensure release doesn't overlap attack

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

    # mix all
    mix = f"{''.join(labels)}amix=inputs={len(events)}:duration=longest:normalize=0"

    # overall fades
    if fade_in > 0:
        mix += f",afade=t=in:d={fade_in}:curve=tri"
    if fade_out > 0:
        mix += f",afade=t=out:st={duration - fade_out}:d={fade_out}:curve=tri"

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
