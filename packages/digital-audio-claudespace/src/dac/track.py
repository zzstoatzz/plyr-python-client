"""timeline-based composition - notes can overlap freely."""

from __future__ import annotations

from dataclasses import dataclass, field

from dac.primitives import Waveform


def _parse_note(name: str) -> float:
    """parse note name to frequency."""
    note_offsets = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    letter = name[0].upper()
    rest = name[1:]
    modifier = 0
    if rest.startswith(("#", "s")):
        modifier = 1
        rest = rest[1:]
    elif rest.startswith("b"):
        modifier = -1
        rest = rest[1:]
    octave = int(rest)
    semitones = note_offsets[letter] + modifier + (octave - 4) * 12
    return 440.0 * (2 ** (semitones / 12))


@dataclass
class Event:
    """a note event on a timeline."""

    start: float  # start time in seconds
    duration: float
    frequency: float
    amplitude: float = 0.2
    waveform: Waveform = "sine"
    attack: float | None = None  # defaults to 5% of duration
    release: float | None = None  # defaults to 15% of duration

    @classmethod
    def note(
        cls,
        start: float,
        name: str,
        duration: float,
        amplitude: float = 0.2,
        waveform: Waveform = "sine",
    ) -> Event:
        """create event from note name."""
        return cls(
            start=start,
            duration=duration,
            frequency=_parse_note(name),
            amplitude=amplitude,
            waveform=waveform,
        )


@dataclass
class Track:
    """a timeline of overlapping note events.

    this is the core primitive for harmonic composition -
    notes can start at any time and overlap freely.

    example:
        track = Track()
        # bass drone
        track.add("C2", start=0, duration=16, amplitude=0.15)
        # chord tones
        track.add("G3", start=0, duration=8, amplitude=0.1)
        track.add("E4", start=0, duration=8, amplitude=0.1)
        # melody
        track.add("G4", start=2, duration=3, amplitude=0.2)
        track.add("A4", start=6, duration=2, amplitude=0.2)

        render(track, "piece.wav")
    """

    events: list[Event] = field(default_factory=list)
    _sample_rate: int = 48000

    def add(
        self,
        note: str,
        start: float,
        duration: float,
        amplitude: float = 0.2,
        waveform: Waveform = "sine",
        attack: float | None = None,
        release: float | None = None,
    ) -> Track:
        """add a note to the timeline."""
        event = Event(
            start=start,
            duration=duration,
            frequency=_parse_note(note),
            amplitude=amplitude,
            waveform=waveform,
            attack=attack,
            release=release,
        )
        self.events.append(event)
        return self

    def add_chord(
        self,
        notes: list[str],
        start: float,
        duration: float,
        amplitude: float = 0.2,
        waveform: Waveform = "sine",
    ) -> Track:
        """add multiple notes at the same time."""
        per_note_amp = amplitude / (len(notes) ** 0.5)
        for note in notes:
            self.add(note, start, duration, per_note_amp, waveform)
        return self

    @property
    def duration(self) -> float:
        """total duration of the track."""
        if not self.events:
            return 0.0
        return max(e.start + e.duration for e in self.events)

    @property
    def _duration(self) -> float:
        """compatibility with AudioNode interface."""
        return self.duration

    def sample_rate(self, rate: int) -> Track:
        """set sample rate."""
        self._sample_rate = rate
        return self


# intervals in semitones for quick chord building
INTERVALS = {
    "root": 0,
    "m2": 1,
    "M2": 2,
    "m3": 3,
    "M3": 4,
    "P4": 5,
    "tritone": 6,
    "P5": 7,
    "m6": 8,
    "M6": 9,
    "m7": 10,
    "M7": 11,
    "octave": 12,
}

CHORD_SHAPES = {
    "major": [0, 4, 7],
    "minor": [0, 3, 7],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "dom7": [0, 4, 7, 10],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "add9": [0, 4, 7, 14],
    "power": [0, 7, 12],
}


def chord_freqs(root: str, shape: str = "major") -> list[float]:
    """get frequencies for a chord shape from a root note."""
    root_freq = _parse_note(root)
    intervals = CHORD_SHAPES.get(shape, CHORD_SHAPES["major"])
    return [root_freq * (2 ** (i / 12)) for i in intervals]


def interval(note: str, semitones: int) -> float:
    """get frequency of note + interval."""
    return _parse_note(note) * (2 ** (semitones / 12))
