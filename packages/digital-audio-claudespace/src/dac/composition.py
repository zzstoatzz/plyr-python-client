"""composition primitives for combining audio nodes."""

from __future__ import annotations

from dataclasses import dataclass, field

from dac.primitives import AudioNode


@dataclass
class Sequence(AudioNode):
    """play audio nodes one after another.

    examples:
        Sequence([
            Oscillator(440).duration(0.5),
            Oscillator(494).duration(0.5),
            Oscillator(523).duration(0.5),
        ])
    """

    nodes: list[AudioNode] = field(default_factory=list)

    def __init__(self, nodes: list[AudioNode] | None = None) -> None:
        super().__init__()
        self.nodes = nodes or []
        self._recalculate_duration()

    def _recalculate_duration(self) -> None:
        self._duration = sum(node._duration for node in self.nodes)

    def add(self, node: AudioNode) -> Sequence:
        """append a node to the sequence."""
        self.nodes.append(node)
        self._recalculate_duration()
        return self

    def duration(self, seconds: float) -> Sequence:
        """override: sequence duration is derived from its nodes."""
        raise ValueError(
            "sequence duration is calculated from nodes; "
            "set duration on individual nodes instead"
        )


@dataclass
class Layer(AudioNode):
    """play audio nodes simultaneously (mixed together).

    examples:
        Layer([
            Noise("pink").amplitude(0.2),
            Oscillator(220).amplitude(0.5),
        ]).duration(5.0)
    """

    nodes: list[AudioNode] = field(default_factory=list)

    def __init__(self, nodes: list[AudioNode] | None = None) -> None:
        super().__init__()
        self.nodes = nodes or []

    def add(self, node: AudioNode) -> Layer:
        """add a node to the layer."""
        self.nodes.append(node)
        return self

    def duration(self, seconds: float) -> Layer:
        """set duration for all layered nodes."""
        super().duration(seconds)
        for node in self.nodes:
            node._duration = seconds
        return self
