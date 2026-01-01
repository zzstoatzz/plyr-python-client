"""track - composable audio with effects chains."""

from dataclasses import dataclass
from pathlib import Path

# --- note frequencies (equal temperament, A4 = 440Hz) ---

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_to_freq(name: str) -> float:
    """convert note name to frequency. e.g. 'A4' -> 440, 'C#5' -> 554.37"""
    # parse note name and octave
    if len(name) == 2:
        note, octave = name[0], int(name[1])
    elif len(name) == 3:
        note, octave = name[:2], int(name[2])
    else:
        raise ValueError(f"invalid note name: {name}")

    # semitones from A4
    note_idx = NOTE_NAMES.index(note)
    a4_idx = NOTE_NAMES.index("A")
    semitones = (octave - 4) * 12 + (note_idx - a4_idx)

    return 440.0 * (2 ** (semitones / 12))


# --- tempo and timing ---


@dataclass
class Tempo:
    """musical time - converts beats to seconds."""

    bpm: float
    time_sig: tuple[int, int] = (4, 4)  # (beats per measure, beat unit)

    @property
    def beat(self) -> float:
        """duration of one beat in seconds."""
        return 60.0 / self.bpm

    @property
    def measure(self) -> float:
        """duration of one measure in seconds."""
        return self.beat * self.time_sig[0]

    def beats(self, n: float) -> float:
        """convert beats to seconds."""
        return n * self.beat

    def at_beat(self, beat: float) -> int:
        """convert beat number to delay in milliseconds (1-indexed)."""
        return int((beat - 1) * self.beat * 1000)


@dataclass
class RenderConfig:
    """configuration for audio rendering."""

    duration: float
    sample_rate: int = 48000
    channels: int = 1  # mono by default - stereo causes -3dB drop from mono sources


class Track:
    """an audio source with chainable effects."""

    def __init__(self, source: str, label: str = "t0", duration: float | None = None):
        self._source = source  # ffmpeg source expression
        self._effects: list[str] = []
        self._label = label
        self._duration = duration  # track duration if known

    # --- effects (return self for chaining) ---

    def volume(self, level: float) -> "Track":
        """adjust volume (1.0 = unity)."""
        self._effects.append(f"volume={level}")
        return self

    def fade_in(self, duration: float, curve: str = "tri") -> "Track":
        """fade in from silence."""
        self._effects.append(f"afade=t=in:d={duration}:curve={curve}")
        return self

    def fade_out(
        self, duration: float, start: float | None = None, curve: str = "tri"
    ) -> "Track":
        """fade out to silence.

        if start is not specified, uses track duration to fade at the end.
        raises ValueError if duration is unknown and start not specified.
        """
        if start is not None:
            st = start
        elif self._duration is not None:
            st = max(0, self._duration - duration)
        else:
            raise ValueError(
                "fade_out requires start time when track duration is unknown. "
                "use fade_out(duration, start=X) or use Sine/Sample which have known durations."
            )
        self._effects.append(f"afade=t=out:st={st}:d={duration}:curve={curve}")
        return self

    def trim(self, duration: float, start: float = 0) -> "Track":
        """trim to a specific duration (in seconds)."""
        self._effects.append(
            f"atrim=start={start}:duration={duration},asetpts=PTS-STARTPTS"
        )
        return self

    def delay(self, ms: int) -> "Track":
        """delay the track."""
        self._effects.append(f"adelay={ms}:all=1")
        return self

    def lowpass(self, freq: float) -> "Track":
        """low-pass filter."""
        self._effects.append(f"lowpass=f={freq}")
        return self

    def highpass(self, freq: float) -> "Track":
        """high-pass filter."""
        self._effects.append(f"highpass=f={freq}")
        return self

    def tremolo(self, freq: float = 5.0, depth: float = 0.5) -> "Track":
        """amplitude modulation."""
        self._effects.append(f"tremolo=f={freq}:d={depth}")
        return self

    def vibrato(self, freq: float = 5.0, depth: float = 0.5) -> "Track":
        """pitch modulation."""
        self._effects.append(f"vibrato=f={freq}:d={depth}")
        return self

    def chorus(self, delays: str = "50|60", depths: str = "0.4|0.3") -> "Track":
        """chorus effect for width."""
        self._effects.append(f"chorus=0.5:0.9:{delays}:{depths}:0.25|0.3:2|2.3")
        return self

    def echo(self, delay_ms: int = 500, decay: float = 0.3) -> "Track":
        """simple echo/delay."""
        self._effects.append(f"aecho=0.8:0.9:{delay_ms}:{decay}")
        return self

    def pad(self, total_duration: float) -> "Track":
        """pad with silence to a fixed duration (for loop cycles)."""
        self._effects.append(f"apad=whole_dur={total_duration}")
        return self

    def reverb(self, wet: float = 0.3, decay: float = 0.5) -> "Track":
        """simple reverb using delays."""
        # simulate reverb with multiple echoes
        self._effects.append(
            f"aecho=0.8:{wet}:60|120|180:{decay}|{decay * 0.7}|{decay * 0.5}"
        )
        return self

    def reverse(self) -> "Track":
        """reverse the audio."""
        self._effects.append("areverse")
        return self

    def speed(self, factor: float) -> "Track":
        """change tempo without affecting pitch.

        factor > 1.0 = faster, factor < 1.0 = slower.
        range: 0.5 to 2.0 (can chain for wider range).
        """
        # atempo only accepts 0.5-2.0, chain for wider range
        if factor < 0.5:
            self._effects.append(f"atempo=0.5,atempo={factor / 0.5}")
        elif factor > 2.0:
            self._effects.append(f"atempo=2.0,atempo={factor / 2.0}")
        else:
            self._effects.append(f"atempo={factor}")
        return self

    def pitch(self, semitones: float) -> "Track":
        """shift pitch without affecting tempo.

        semitones > 0 = higher, semitones < 0 = lower.
        uses asetrate + atempo compensation.
        """
        # pitch ratio: 2^(semitones/12)
        ratio = 2 ** (semitones / 12)
        # asetrate changes pitch+tempo, atempo compensates tempo back
        self._effects.append(
            f"asetrate=48000*{ratio},aresample=48000,atempo={1 / ratio}"
        )
        return self

    def bandpass(self, low: float, high: float) -> "Track":
        """bandpass filter - keep frequencies between low and high."""
        self._effects.append(f"highpass=f={low},lowpass=f={high}")
        return self

    def pan(self, position: float) -> "Track":
        """stereo pan. -1.0 = full left, 0 = center, 1.0 = full right."""
        # pan filter: 0=left, 0.5=center, 1=right
        p = (position + 1) / 2  # convert -1..1 to 0..1
        self._effects.append(f"stereotools=mpan={p}")
        return self

    def flanger(
        self, delay: float = 3.0, depth: float = 2.0, speed: float = 0.5
    ) -> "Track":
        """flanger effect."""
        self._effects.append(f"flanger=delay={delay}:depth={depth}:speed={speed}")
        return self

    def phaser(self, speed: float = 0.5, decay: float = 0.4) -> "Track":
        """phaser effect."""
        self._effects.append(f"aphaser=speed={speed}:decay={decay}")
        return self

    # --- compilation ---

    def to_filter(self) -> str:
        """compile to ffmpeg filter string."""
        return ",".join([self._source, *self._effects]) + f"[{self._label}]"


class Sine(Track):
    """sine wave oscillator."""

    def __init__(
        self,
        freq: float,
        duration: float,
        *,
        amplitude: float = 0.5,
        sample_rate: int = 48000,
        label: str = "t0",
    ):
        source = f"aevalsrc=exprs='{amplitude}*(sin(2*PI*{freq}*t))':s={sample_rate}:d={duration}"
        super().__init__(source, label, duration=duration)


class Sample(Track):
    """sample playback."""

    def __init__(self, path: str | Path, *, label: str = "t0"):
        source = f"amovie={path}"
        super().__init__(source, label)


def phase(
    track: Track,
    *,
    interval: float,
    duration: float,
    offset: float = 0,
) -> list[Track]:
    """repeat a track at regular intervals, creating phasing copies.

    this is the core eno concept - the same sound repeating at its own interval,
    drifting in and out of phase with other sounds.

    each copy is padded to the full duration to prevent amix dropout issues.
    """
    copies = []
    t = offset
    i = 0
    while t < duration:
        # create a delayed copy with unique label
        copy = Track(track._source, label=f"{track._label}_{i}")
        copy._effects = track._effects.copy()
        copy.delay(int(t * 1000))
        copy.pad(duration)  # extend to full duration with silence
        copies.append(copy)
        t += interval
        i += 1
    return copies


def mix(
    tracks: list[Track],
    output: Path,
    *,
    config: RenderConfig | None = None,
    duration: float | None = None,
    sample_rate: int = 48000,
) -> Path:
    """mix multiple tracks to a file.

    accepts either a RenderConfig or individual kwargs for backwards compatibility.

    note: amix divides by track count. we compensate by boosting the output
    so that input amplitudes map predictably to output levels.
    """
    import subprocess

    # resolve config - prefer explicit config, fall back to kwargs
    if config is not None:
        cfg = config
    elif duration is not None:
        cfg = RenderConfig(duration=duration, sample_rate=sample_rate)
    else:
        raise ValueError("either config or duration must be provided")

    parts = [t.to_filter() for t in tracks]
    labels = [f"[{t._label}]" for t in tracks]

    mix_filter = (
        f"{''.join(labels)}amix=inputs={len(tracks)}:duration=longest:normalize=0[out]"
    )
    graph = ";".join(parts) + ";" + mix_filter

    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-filter_complex",
        graph,
        "-map",
        "[out]",
        "-t",
        str(cfg.duration),
        "-ar",
        str(cfg.sample_rate),
        "-ac",
        str(cfg.channels),
        "-y",
        str(output),
    ]

    subprocess.run(cmd, check=True)
    return output
