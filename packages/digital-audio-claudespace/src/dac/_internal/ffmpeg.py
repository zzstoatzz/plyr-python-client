"""ffmpeg filter graph utilities."""

import shutil
import subprocess
from pathlib import Path
from typing import Literal

from dac._internal.notes import Waveform

FadeCurve = Literal[
    "tri",
    "qsin",
    "hsin",
    "esin",
    "log",
    "ipar",
    "qua",
    "cub",
    "squ",
    "cbr",
    "par",
    "exp",
    "iqsin",
    "ihsin",
    "dese",
    "desi",
    "losi",
    "sinc",
    "isinc",
    "nofade",
]


def wave_expr(freq: float, wave: Waveform = "sine") -> str:
    """generate ffmpeg aevalsrc expression for a waveform."""
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


def build_note_filter(
    freq: float,
    duration: float,
    amplitude: float,
    *,
    wave: Waveform = "sine",
    attack: float = 0.0,
    release: float = 0.0,
    delay_ms: int = 0,
    label: str = "n0",
    sample_rate: int = 48000,
    fade_curve: FadeCurve = "tri",
) -> str:
    """build a single note filter with envelope and delay."""
    expr = wave_expr(freq, wave)
    src = f"aevalsrc=exprs='{amplitude}*({expr})':s={sample_rate}:d={duration}"

    filters = [src]

    if attack > 0:
        filters.append(f"afade=t=in:d={attack}:curve={fade_curve}")
    if release > 0:
        rel_start = max(duration - release, attack)
        filters.append(f"afade=t=out:st={rel_start}:d={release}:curve={fade_curve}")

    if delay_ms > 0:
        filters.append(f"adelay={delay_ms}:all=1")

    return ",".join(filters) + f"[{label}]"


def build_sample_filter(
    sample_path: str,
    amplitude: float,
    *,
    attack: float = 0.0,
    release: float = 0.0,
    delay_ms: int = 0,
    label: str = "s0",
    fade_curve: FadeCurve = "tri",
) -> str:
    """build a filter that plays a sample with envelope and delay."""
    # load sample and apply volume
    filters = [f"amovie={sample_path},volume={amplitude}"]

    # get sample duration for release timing (we'll need to handle this differently)
    # for now, assume release starts near the end of the sample

    if attack > 0:
        filters.append(f"afade=t=in:d={attack}:curve={fade_curve}")
    if release > 0:
        # apply fade out - ffmpeg will handle timing automatically with 'out' type
        filters.append(f"afade=t=out:d={release}:curve={fade_curve}")

    if delay_ms > 0:
        filters.append(f"adelay={delay_ms}:all=1")

    return ",".join(filters) + f"[{label}]"


def run_ffmpeg(
    graph: str,
    output: Path,
    *,
    sample_rate: int = 48000,
    channels: int = 2,
) -> Path:
    """execute ffmpeg with a filter graph."""
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
        str(channels),
        "-y",
        str(output),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg failed: {e.stderr}") from e

    return output
