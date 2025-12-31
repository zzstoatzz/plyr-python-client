"""core audio primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Waveform = Literal["sine", "square", "triangle", "saw"]
NoiseColor = Literal["white", "pink", "brown", "blue"]


@dataclass
class AudioNode:
    """base class for all audio nodes."""

    _duration: float = 1.0
    _amplitude: float = 0.35
    _fade_in: float = 0.0
    _fade_out: float = 0.0
    _sample_rate: int = 48000

    def duration(self, seconds: float) -> AudioNode:
        """set the duration in seconds."""
        if seconds <= 0:
            raise ValueError("duration must be positive")
        self._duration = seconds
        return self

    def amplitude(self, level: float) -> AudioNode:
        """set the amplitude (0-1]."""
        if not 0 < level <= 1:
            raise ValueError("amplitude must be between 0 and 1 (exclusive of 0)")
        self._amplitude = level
        return self

    def fade_in(self, seconds: float) -> AudioNode:
        """apply a fade-in."""
        if seconds < 0:
            raise ValueError("fade_in must be non-negative")
        self._fade_in = seconds
        return self

    def fade_out(self, seconds: float) -> AudioNode:
        """apply a fade-out."""
        if seconds < 0:
            raise ValueError("fade_out must be non-negative")
        self._fade_out = seconds
        return self

    def sample_rate(self, rate: int) -> AudioNode:
        """set the sample rate."""
        if rate <= 0:
            raise ValueError("sample_rate must be positive")
        self._sample_rate = rate
        return self


@dataclass
class Oscillator(AudioNode):
    """a pitched oscillator.

    examples:
        Oscillator(440)  # A4 sine wave
        Oscillator(440, "square")  # square wave
        Oscillator(440).with_partials([880, 1320])  # with harmonics
    """

    frequency: float = 440.0
    waveform: Waveform = "sine"
    partials: list[tuple[float, float]] = field(default_factory=list)

    def __init__(
        self,
        frequency: float = 440.0,
        waveform: Waveform = "sine",
    ) -> None:
        super().__init__()
        if frequency <= 0:
            raise ValueError("frequency must be positive")
        self.frequency = frequency
        self.waveform = waveform
        self.partials = []

    def with_partials(
        self, frequencies: list[float | tuple[float, float]]
    ) -> Oscillator:
        """add harmonic partials.

        args:
            frequencies: list of frequencies, or (frequency, weight) tuples.
                         weights default to 1.0 if not specified.
        """
        if self.waveform != "sine":
            raise ValueError("partials only supported for sine waveform")
        for item in frequencies:
            if isinstance(item, tuple):
                freq, weight = item
            else:
                freq, weight = item, 1.0
            if freq <= 0:
                raise ValueError("partial frequency must be positive")
            if weight <= 0:
                raise ValueError("partial weight must be positive")
            self.partials.append((freq, weight))
        return self


@dataclass
class Noise(AudioNode):
    """a noise generator.

    examples:
        Noise()  # white noise
        Noise("pink")  # pink noise
        Noise("brown").amplitude(0.5)  # brown noise at half volume
    """

    color: NoiseColor = "white"

    def __init__(self, color: NoiseColor = "white") -> None:
        super().__init__()
        self.color = color


@dataclass
class Silence(AudioNode):
    """silence (useful for spacing in sequences)."""

    def __init__(self) -> None:
        super().__init__()
