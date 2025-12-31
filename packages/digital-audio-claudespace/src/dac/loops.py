"""eno-style phasing loops - notes repeat at incommensurable intervals."""

from pathlib import Path

from dac._internal.ffmpeg import build_note_filter, run_ffmpeg
from dac._internal.loops import Loop, Waveform
from dac._internal.notes import note_to_freq

# golden ratio for natural-feeling stagger offsets
PHI = 0.618033988749895


def render(
    loops: list[Loop | dict],
    duration: float,
    output: str | Path,
    *,
    amp: float = 0.08,
    attack: float = 0.35,
    release: float = 0.45,
    wave: Waveform = "sine",
    fade_in: float = 6.0,
    fade_out: float = 10.0,
    stagger: bool = True,
    sample_rate: int = 48000,
) -> Path:
    """render phasing loops to audio.

    each loop repeats at its own interval, creating evolving textures
    as the notes drift in and out of phase with each other.

    args:
        loops: list of Loop objects or dicts with:
            - note: pitch name (e.g. "A2", "C#4")
            - loop_length: seconds between repetitions
            - note_duration: how long each note sounds
            - amplitude: volume (optional, uses default)
            - start_offset: when to start (optional, auto-staggers)
            - attack: attack as fraction of note duration (optional)
            - release: release as fraction of note duration (optional)
            - wave: waveform - sine, square, triangle, saw (optional)
        duration: total piece length in seconds
        output: path for the output file
        amp: default amplitude if not specified per-loop
        attack: default attack time as fraction of note duration
        release: default release time as fraction of note duration
        wave: default waveform (sine, square, triangle, saw)
        fade_in: overall fade in time (seconds)
        fade_out: overall fade out time (seconds)
        stagger: offset loops so they don't all start at t=0
        sample_rate: audio sample rate

    example:
        render([
            {"note": "A2", "loop_length": 11.3, "note_duration": 8},
            {"note": "E3", "loop_length": 13.7, "note_duration": 9, "attack": 0.5},
            {"note": "C6", "loop_length": 7.0, "note_duration": 0.3, "wave": "triangle"},
        ], duration=120, output="ambient.wav")
    """
    output = Path(output)

    # expand loops into individual note events
    # each event: (start, freq, dur, amp, attack_ratio, release_ratio, wave)
    events: list[tuple[float, float, float, float, float, float, Waveform]] = []

    for i, loop in enumerate(loops):
        # coerce to Loop model if dict
        spec = loop if isinstance(loop, Loop) else Loop.model_validate(loop)
        resolved = spec.resolve(
            default_amp=amp,
            default_attack=attack,
            default_release=release,
            default_wave=wave,
        )

        # determine start offset
        if resolved.start_offset is not None:
            start_offset = resolved.start_offset
        elif stagger:
            start_offset = (resolved.loop_length * PHI * i) % resolved.loop_length
        else:
            start_offset = 0.0

        freq = note_to_freq(resolved.note)
        t = start_offset

        while t < duration:
            if t + resolved.note_duration <= duration + resolved.note_duration * 0.5:
                events.append(
                    (
                        t,
                        freq,
                        min(resolved.note_duration, duration - t),
                        resolved.amplitude,
                        resolved.attack,
                        resolved.release,
                        resolved.wave,
                    )
                )
            t += resolved.loop_length

    if not events:
        raise ValueError("no events generated")

    # build filter graph
    parts: list[str] = []
    labels: list[str] = []

    for i, (
        start,
        freq,
        dur,
        note_amp,
        note_attack,
        note_release,
        note_wave,
    ) in enumerate(events):
        att = dur * note_attack
        rel = dur * note_release
        label = f"n{i}"

        part = build_note_filter(
            freq,
            dur,
            note_amp,
            wave=note_wave,
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
