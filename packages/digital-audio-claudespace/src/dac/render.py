"""render audio nodes to files via ffmpeg."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from itertools import count
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dac.primitives import AudioNode


class RenderError(Exception):
    """raised when rendering fails."""


# global counter for unique label generation
_label_counter = count()


def _next_label() -> str:
    """generate a unique label for ffmpeg filter graph."""
    return f"n{next(_label_counter)}"


def _reset_labels() -> None:
    """reset label counter (called before each render)."""
    global _label_counter
    _label_counter = count()


def _wave_expression(waveform: str, frequency: float) -> str:
    """generate lavfi expression for a waveform."""
    angular = f"2*PI*{frequency}*t"
    base = f"t*{frequency}"

    if waveform == "sine":
        return f"sin({angular})"
    if waveform == "square":
        return f"(gt(sin({angular}),0)*2-1)"
    if waveform == "triangle":
        return f"(abs(4*(({base})-floor({base}+0.75))-2)-1)"
    if waveform == "saw":
        return f"(2*((({base})-floor({base}+0.5))))"
    raise ValueError(f"unsupported waveform: {waveform}")


def _build_oscillator_graph(node: AudioNode) -> str:
    """build lavfi graph for an oscillator."""
    from dac.primitives import Oscillator

    if not isinstance(node, Oscillator):
        raise TypeError("expected Oscillator")

    expr = _wave_expression(node.waveform, node.frequency)

    if node.waveform == "sine" and node.partials:
        terms: list[tuple[str, float]] = [(expr, 1.0)]
        for freq, weight in node.partials:
            terms.append((_wave_expression("sine", freq), weight))
        total_weight = sum(w for _, w in terms)
        combined = "+".join(f"{w}*({t})" for t, w in terms)
        expr = f"({combined})/{total_weight}"

    expr = f"{node._amplitude}*({expr})"
    return f"aevalsrc=exprs='{expr}':s={node._sample_rate}:d={node._duration}"


def _build_noise_graph(node: AudioNode) -> str:
    """build lavfi graph for noise."""
    from dac.primitives import Noise

    if not isinstance(node, Noise):
        raise TypeError("expected Noise")

    return (
        f"anoisesrc="
        f"color={node.color}:"
        f"sample_rate={node._sample_rate}:"
        f"duration={node._duration}:"
        f"amplitude={node._amplitude}"
    )


def _build_silence_graph(node: AudioNode) -> str:
    """build lavfi graph for silence."""
    from dac.primitives import Silence

    if not isinstance(node, Silence):
        raise TypeError("expected Silence")

    return f"anullsrc=r={node._sample_rate}:d={node._duration}"


def _apply_fades(graph: str, node: AudioNode) -> str:
    """apply fade in/out to a graph."""
    filters = [graph]
    if node._fade_in > 0:
        filters.append(f"afade=t=in:ss=0:d={node._fade_in}")
    if node._fade_out > 0:
        start = max(node._duration - node._fade_out, 0)
        filters.append(f"afade=t=out:st={start}:d={node._fade_out}")
    return ",".join(filters)


def _build_graph(node: AudioNode) -> tuple[str, bool]:
    """build the complete lavfi graph for a node.

    returns:
        tuple of (graph_string, is_complex) where is_complex indicates
        whether this needs -filter_complex instead of -f lavfi.
    """
    from dac.composition import Layer, Sequence
    from dac.primitives import Noise, Oscillator, Silence

    if isinstance(node, Oscillator):
        graph = _build_oscillator_graph(node)
        return _apply_fades(graph, node), False
    elif isinstance(node, Noise):
        graph = _build_noise_graph(node)
        return _apply_fades(graph, node), False
    elif isinstance(node, Silence):
        graph = _build_silence_graph(node)
        return _apply_fades(graph, node), False
    elif isinstance(node, Sequence):
        if not node.nodes:
            raise ValueError("sequence cannot be empty")
        # build each child and concat them
        parts = []
        labels = []
        for child in node.nodes:
            child_result = _build_graph(child)
            child_graph = child_result[0]
            is_complex = child_result[1]
            if is_complex and len(child_result) > 2:
                # child already has an output label
                parts.append(child_graph)
                labels.append(f"[{child_result[2]}]")
            else:
                label = _next_label()
                parts.append(f"{child_graph}[{label}]")
                labels.append(f"[{label}]")
        out_label = _next_label()
        graph = (
            ";".join(parts)
            + f";{''.join(labels)}concat=n={len(node.nodes)}:v=0:a=1[{out_label}]"
        )
        return graph, True, out_label
    elif isinstance(node, Layer):
        if not node.nodes:
            raise ValueError("layer cannot be empty")
        # build each child and mix them
        parts = []
        labels = []
        for child in node.nodes:
            child_graph, is_complex, *rest = _build_graph(child)
            if is_complex and rest:
                # child already has an output label
                parts.append(child_graph)
                labels.append(f"[{rest[0]}]")
            else:
                label = _next_label()
                parts.append(f"{child_graph}[{label}]")
                labels.append(f"[{label}]")
        out_label = _next_label()
        graph = (
            ";".join(parts)
            + f";{''.join(labels)}amix=inputs={len(node.nodes)}:duration=longest[{out_label}]"
        )
        if node._fade_in or node._fade_out:
            # apply fades to the mixed output
            fades = []
            if node._fade_in > 0:
                fades.append(f"afade=t=in:ss=0:d={node._fade_in}")
            if node._fade_out > 0:
                start = max(node._duration - node._fade_out, 0)
                fades.append(f"afade=t=out:st={start}:d={node._fade_out}")
            pre_label = out_label
            out_label = _next_label()
            graph = graph + f";[{pre_label}]" + ",".join(fades) + f"[{out_label}]"
        return graph, True, out_label
    else:
        raise TypeError(f"unsupported node type: {type(node)}")


def render(
    node: AudioNode,
    output: str | Path,
    *,
    channels: int = 2,
    force: bool = True,
    dry_run: bool = False,
) -> Path:
    """render an audio node to a file.

    args:
        node: the audio node to render
        output: path for the output file (extension determines format)
        channels: number of audio channels (default: 2 for stereo)
        force: overwrite existing file (default: True)
        dry_run: print command without executing (default: False)

    returns:
        path to the rendered file

    raises:
        RenderError: if ffmpeg is not found or rendering fails
    """
    if shutil.which("ffmpeg") is None:
        raise RenderError("ffmpeg not found on PATH")

    output = Path(output)
    if not output.parent.exists():
        output.parent.mkdir(parents=True, exist_ok=True)

    _reset_labels()
    result = _build_graph(node)
    graph = result[0]
    is_complex = result[1]
    out_label = result[2] if len(result) > 2 else "out"

    if is_complex:
        # use -filter_complex for sequences/layers
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-filter_complex",
            graph,
            "-map",
            f"[{out_label}]",
            "-ar",
            str(node._sample_rate),
            "-ac",
            str(channels),
        ]
    else:
        # simple lavfi input for single nodes
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-f",
            "lavfi",
            "-i",
            graph,
            "-t",
            str(node._duration),
            "-ar",
            str(node._sample_rate),
            "-ac",
            str(channels),
        ]

    cmd.append("-y" if force else "-n")
    cmd.append(str(output))

    if dry_run:
        print("ffmpeg command:")
        print("  " + shlex.join(cmd))
        return output

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise RenderError(f"ffmpeg failed: {exc.stderr}") from exc

    return output
