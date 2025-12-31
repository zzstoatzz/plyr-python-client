"""higher-level music composition helpers."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

from dac.composition import Layer, Sequence
from dac.primitives import Noise, Oscillator, Silence, Waveform

# note name to semitone offset from A4
_NOTE_OFFSETS = {
    "C": -9,
    "D": -7,
    "E": -5,
    "F": -4,
    "G": -2,
    "A": 0,
    "B": 2,
}


def _parse_note(name: str) -> float:
    """parse a note name like 'A4', 'C#5', 'Bb3' to frequency."""
    if not name or len(name) < 2:
        raise ValueError(f"invalid note: {name}")

    # extract note letter
    letter = name[0].upper()
    if letter not in _NOTE_OFFSETS:
        raise ValueError(f"invalid note letter: {letter}")

    # check for sharp/flat
    rest = name[1:]
    modifier = 0
    if rest.startswith(("#", "s")):
        modifier = 1
        rest = rest[1:]
    elif rest.startswith("b"):
        modifier = -1
        rest = rest[1:]

    # extract octave
    try:
        octave = int(rest)
    except ValueError:
        raise ValueError(f"invalid octave in note: {name}") from None

    # calculate semitones from A4
    semitones = _NOTE_OFFSETS[letter] + modifier + (octave - 4) * 12

    # A4 = 440 Hz, each semitone is 2^(1/12)
    return 440.0 * (2 ** (semitones / 12))


def note(
    name: str,
    duration: float = 0.5,
    *,
    waveform: Waveform = "sine",
    velocity: float = 0.35,
    attack: float | None = None,
    release: float | None = None,
) -> Oscillator:
    """create a note by name.

    args:
        name: note name like "A4", "C#5", "Bb3"
        duration: length in seconds
        waveform: oscillator waveform
        velocity: amplitude (0-1]
        attack: fade in time (default: 5% of duration, max 0.05s)
        release: fade out time (default: 15% of duration, max 0.1s)

    examples:
        note("A4")         # A above middle C
        note("C4", 1.0)    # middle C, 1 second
        note("F#5", 0.25)  # F sharp, quarter beat
        note("Bb3")        # B flat below middle C
    """
    freq = _parse_note(name)
    osc = Oscillator(freq, waveform).duration(duration).amplitude(velocity)

    # apply gentle envelope to avoid clicks
    if attack is None:
        attack = min(duration * 0.05, 0.05)
    if release is None:
        release = min(duration * 0.15, 0.1)

    if attack > 0:
        osc.fade_in(attack)
    if release > 0:
        osc.fade_out(release)

    return osc


def rest(duration: float = 0.5) -> Silence:
    """create a rest (silence)."""
    return Silence().duration(duration)


def chord(
    notes: list[str],
    duration: float = 1.0,
    *,
    waveform: Waveform = "sine",
    velocity: float = 0.35,
    attack: float | None = None,
    release: float | None = None,
) -> Layer:
    """create a chord from note names.

    examples:
        chord(["C4", "E4", "G4"])  # C major
        chord(["A3", "C4", "E4"])  # A minor
    """
    # reduce velocity per note to avoid clipping
    per_note_velocity = velocity / (len(notes) ** 0.5)
    layer = Layer(
        [
            note(
                n,
                duration,
                waveform=waveform,
                velocity=per_note_velocity,
                attack=attack,
                release=release,
            )
            for n in notes
        ]
    )
    layer._duration = duration
    return layer


@dataclass
class Song:
    """a song with tempo and tracks.

    examples:
        song = Song(bpm=120)
        song.add_track([
            "C4", "D4", "E4", "F4",  # notes
            "-",                      # rest
            ("C4", 2),               # note with beat count
            ("C4 E4 G4", 2),         # chord with beat count
        ])
        render(song.build(), "song.wav")
    """

    bpm: float = 120
    tracks: list[list] = None

    def __post_init__(self):
        self.tracks = self.tracks or []

    @property
    def beat_duration(self) -> float:
        """duration of one beat in seconds."""
        return 60.0 / self.bpm

    def add_track(
        self,
        pattern: list,
        *,
        waveform: Waveform = "sine",
        velocity: float = 0.35,
    ) -> Song:
        """add a track to the song.

        pattern elements can be:
            - "C4" - a note (1 beat)
            - "-" or "." - a rest (1 beat)
            - ("C4", 2) - a note with beat count
            - ("C4 E4 G4", 2) - a chord with beat count
            - ("-", 2) - a rest with beat count
        """
        self.tracks.append(
            {
                "pattern": pattern,
                "waveform": waveform,
                "velocity": velocity,
            }
        )
        return self

    def _parse_pattern(
        self,
        pattern: list,
        waveform: Waveform,
        velocity: float,
    ) -> Sequence:
        """parse a pattern into a sequence."""
        nodes = []
        beat = self.beat_duration

        for item in pattern:
            if isinstance(item, tuple):
                value, beats = item
            else:
                value, beats = item, 1

            duration = beat * beats

            if value in ("-", ".", "rest"):
                nodes.append(rest(duration))
            elif " " in str(value):
                # chord: "C4 E4 G4"
                chord_notes = value.split()
                nodes.append(
                    chord(
                        chord_notes,
                        duration,
                        waveform=waveform,
                        velocity=velocity,
                    )
                )
            else:
                # single note
                nodes.append(
                    note(
                        value,
                        duration,
                        waveform=waveform,
                        velocity=velocity,
                    )
                )

        return Sequence(nodes)

    def build(self) -> Layer | Sequence:
        """build the song into a renderable node."""
        if not self.tracks:
            raise ValueError("song has no tracks")

        sequences = [
            self._parse_pattern(
                t["pattern"],
                t["waveform"],
                t["velocity"],
            )
            for t in self.tracks
        ]

        if len(sequences) == 1:
            return sequences[0]

        # layer all tracks together
        return Layer(sequences)


# common scales as semitone offsets from root
SCALES = {
    "pentatonic": [0, 2, 4, 7, 9],
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
}


@dataclass
class Ambient:
    """generative ambient music builder.

    inspired by brian eno's generative music concepts - slow evolution,
    overlapping loops of different lengths, subtle randomness.

    examples:
        piece = Ambient(duration=180, root="C", scale="pentatonic")
        piece.add_drone(octave=2, voices=4)
        piece.add_pads(octave_range=(3, 5), density=0.3)
        piece.add_texture("pink", amplitude=0.02)
        render(piece.build(), "ambient.wav")
    """

    duration: float = 120.0
    root: str = "C"
    scale: str = "pentatonic"
    seed: int | None = None
    layers: list = field(default_factory=list)

    def __post_init__(self):
        if self.seed is not None:
            random.seed(self.seed)
        self._root_freq = _parse_note(f"{self.root}4")

    def _scale_freq(self, octave: int, degree: int) -> float:
        """get frequency for a scale degree at given octave."""
        semitones = SCALES[self.scale][degree % len(SCALES[self.scale])]
        octave_shift = degree // len(SCALES[self.scale])
        total_semitones = semitones + (octave - 4) * 12 + octave_shift * 12
        return self._root_freq * (2 ** (total_semitones / 12))

    def add_drone(
        self,
        octave: int = 2,
        voices: int = 4,
        detune_cents: float = 5.0,
        velocity: float = 0.12,
    ) -> Ambient:
        """add a rich drone layer with subtle detuning."""
        base_freq = self._scale_freq(octave, 0)  # root note
        drone_oscs = []
        for i in range(voices):
            detune = (i - voices / 2) * detune_cents
            freq = base_freq * (2 ** (detune / 1200))
            osc = (
                Oscillator(freq, "sine")
                .duration(self.duration)
                .amplitude(velocity / voices)
            )
            drone_oscs.append(osc)

        drone = Layer(drone_oscs)
        drone._duration = self.duration
        self.layers.append(drone)
        return self

    def add_pads(
        self,
        octave_range: tuple[int, int] = (3, 5),
        density: float = 0.3,
        note_duration: tuple[float, float] = (8.0, 20.0),
        velocity: tuple[float, float] = (0.06, 0.12),
        waveform: Waveform = "sine",
    ) -> Ambient:
        """add slowly evolving pad notes.

        args:
            octave_range: (min_octave, max_octave) for note selection
            density: probability of overlapping notes (0-1)
            note_duration: (min, max) seconds per note
            velocity: (min, max) amplitude
            waveform: oscillator type
        """
        nodes = []
        t = 0.0
        scale_len = len(SCALES[self.scale])

        while t < self.duration:
            # random scale degree across octave range
            octave = random.randint(octave_range[0], octave_range[1])
            degree = random.randint(0, scale_len - 1)
            freq = self._scale_freq(octave, degree)

            # random duration
            dur = random.uniform(note_duration[0], note_duration[1])
            if t + dur > self.duration:
                dur = self.duration - t

            # random velocity
            vel = random.uniform(velocity[0], velocity[1])

            # slow attack and release
            attack = dur * random.uniform(0.2, 0.4)
            release = dur * random.uniform(0.3, 0.5)

            osc = (
                Oscillator(freq, waveform)
                .duration(dur)
                .amplitude(vel)
                .fade_in(attack)
                .fade_out(release)
            )
            nodes.append(osc)

            # advance time (with possible overlap based on density)
            advance = dur * (1.0 - density * random.random())
            t += max(advance, 1.0)

        pad = Sequence(nodes)
        self.layers.append(pad)
        return self

    def add_texture(
        self,
        color: Literal["white", "pink", "brown", "blue"] = "pink",
        amplitude: float = 0.02,
    ) -> Ambient:
        """add subtle noise texture."""
        texture = (
            Noise(color)
            .duration(self.duration)
            .amplitude(amplitude)
            .fade_in(self.duration * 0.05)
            .fade_out(self.duration * 0.1)
        )
        self.layers.append(texture)
        return self

    def add_bells(
        self,
        octave_range: tuple[int, int] = (4, 6),
        density: float = 0.1,
        velocity: tuple[float, float] = (0.03, 0.08),
    ) -> Ambient:
        """add sparse bell-like tones with harmonics."""
        nodes = []
        t = 0.0
        scale_len = len(SCALES[self.scale])

        while t < self.duration:
            if random.random() < density:
                octave = random.randint(octave_range[0], octave_range[1])
                degree = random.randint(0, scale_len - 1)
                freq = self._scale_freq(octave, degree)

                dur = random.uniform(3.0, 8.0)
                if t + dur > self.duration:
                    dur = self.duration - t

                vel = random.uniform(velocity[0], velocity[1])

                # bell-like: fast attack, long release, with partials
                osc = (
                    Oscillator(freq, "sine")
                    .with_partials([(freq * 2, 0.5), (freq * 3, 0.25)])
                    .duration(dur)
                    .amplitude(vel)
                    .fade_in(0.01)
                    .fade_out(dur * 0.8)
                )
                nodes.append(osc)
                t += dur
            else:
                # silence gap
                gap = random.uniform(2.0, 6.0)
                nodes.append(Silence().duration(min(gap, self.duration - t)))
                t += gap

        bells = Sequence(nodes)
        self.layers.append(bells)
        return self

    def build(self, fade_in: float = 8.0, fade_out: float = 15.0) -> Layer:
        """build the ambient piece."""
        if not self.layers:
            raise ValueError("no layers added")

        piece = Layer(self.layers)
        piece._duration = self.duration
        if fade_in > 0:
            piece.fade_in(fade_in)
        if fade_out > 0:
            piece.fade_out(fade_out)
        return piece
