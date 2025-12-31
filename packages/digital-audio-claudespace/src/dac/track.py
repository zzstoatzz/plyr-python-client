"""track - composable audio with effects chains."""

from pathlib import Path


class Track:
    """an audio source with chainable effects."""

    def __init__(self, source: str, label: str = "t0"):
        self._source = source  # ffmpeg source expression
        self._effects: list[str] = []
        self._label = label

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
        """fade out to silence."""
        if start is not None:
            self._effects.append(f"afade=t=out:st={start}:d={duration}:curve={curve}")
        else:
            self._effects.append(f"afade=t=out:d={duration}:curve={curve}")
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
        super().__init__(source, label)


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
    """
    copies = []
    t = offset
    i = 0
    while t < duration:
        # create a delayed copy with unique label
        copy = Track(track._source, label=f"{track._label}_{i}")
        copy._effects = track._effects.copy()
        copy.delay(int(t * 1000))
        copies.append(copy)
        t += interval
        i += 1
    return copies


def mix(
    tracks: list[Track], output: Path, *, duration: float, sample_rate: int = 48000
) -> Path:
    """mix multiple tracks to a file."""
    import subprocess

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
        str(duration),
        "-ar",
        str(sample_rate),
        "-ac",
        "2",
        "-y",
        str(output),
    ]

    subprocess.run(cmd, check=True)
    return output
