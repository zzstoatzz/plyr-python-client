"""eno-style phasing loops - notes repeat at incommensurable intervals."""

from pathlib import Path

from dac._internal.ffmpeg import build_note_filter, run_ffmpeg
from dac._internal.notes import note_to_freq

# golden ratio for natural-feeling stagger offsets
PHI = 0.618033988749895


def render(
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
    """render phasing loops to audio.

    each loop repeats at its own interval, creating evolving textures
    as the notes drift in and out of phase with each other.

    args:
        loops: list of tuples, each can be:
            - (note, loop_length, note_duration)
            - (note, loop_length, note_duration, amplitude)
            - (note, loop_length, note_duration, amplitude, start_offset)
        duration: total piece length in seconds
        output: path for the output file
        amp: default amplitude if not specified per-loop
        attack: attack time as fraction of note duration
        release: release time as fraction of note duration
        fade_in: overall fade in time (seconds)
        fade_out: overall fade out time (seconds)
        stagger: offset loops so they don't all start at t=0
        sample_rate: audio sample rate

    example:
        render([
            ("A2", 11.3, 8, 0.07),   # bass, repeats every 11.3s
            ("E3", 13.7, 9, 0.05),   # fifth, different phase
            ("B3", 9.1, 7, 0.04),    # 9th for color
        ], duration=120, output="ambient.wav")
    """
    output = Path(output)

    # expand loops into individual note events
    events: list[tuple[float, float, float, float]] = []

    for i, loop in enumerate(loops):
        note, loop_len, note_dur = loop[0], loop[1], loop[2]
        loop_amp = loop[3] if len(loop) > 3 else amp

        # determine start offset
        if len(loop) > 4:
            start_offset = float(loop[4])
        elif stagger:
            start_offset = (loop_len * PHI * i) % loop_len
        else:
            start_offset = 0.0

        freq = note_to_freq(note)
        t = start_offset

        while t < duration:
            if t + note_dur <= duration + note_dur * 0.5:
                events.append((t, freq, min(note_dur, duration - t), loop_amp))
            t += loop_len

    if not events:
        raise ValueError("no events generated")

    # build filter graph
    parts: list[str] = []
    labels: list[str] = []

    for i, (start, freq, dur, note_amp) in enumerate(events):
        att = dur * attack
        rel = dur * release
        label = f"n{i}"

        part = build_note_filter(
            freq,
            dur,
            note_amp,
            attack=att,
            release=rel,
            delay_ms=int(start * 1000),
            label=label,
            sample_rate=sample_rate,
            fade_curve="tri",
        )
        parts.append(part)
        labels.append(f"[{label}]")

    # mix all notes
    mix = f"{''.join(labels)}amix=inputs={len(events)}:duration=longest:normalize=0"
    if fade_in > 0:
        mix += f",afade=t=in:d={fade_in}:curve=tri"
    if fade_out > 0:
        mix += f",afade=t=out:st={duration - fade_out}:d={fade_out}:curve=tri"
    mix += "[out]"

    graph = ";".join(parts) + ";" + mix
    return run_ffmpeg(graph, output, sample_rate=sample_rate)
