"""music theory primitives - intervals, chords, voicings, progressions."""

from __future__ import annotations

from dataclasses import dataclass, field

# intervals in semitones
INTERVALS = {
    "unison": 0,
    "m2": 1,  # minor 2nd
    "M2": 2,  # major 2nd
    "m3": 3,  # minor 3rd
    "M3": 4,  # major 3rd
    "P4": 5,  # perfect 4th
    "tritone": 6,
    "P5": 7,  # perfect 5th
    "m6": 8,  # minor 6th
    "M6": 9,  # major 6th
    "m7": 10,  # minor 7th
    "M7": 11,  # major 7th
    "octave": 12,
    "m9": 13,
    "M9": 14,
    "m10": 15,
    "M10": 16,
    "P11": 17,
    "P12": 19,  # octave + 5th
}

# chord qualities as interval patterns from root
CHORD_TYPES = {
    # triads
    "major": [0, 4, 7],
    "minor": [0, 3, 7],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    # sevenths
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "dom7": [0, 4, 7, 10],
    "dim7": [0, 3, 6, 9],
    "m7b5": [0, 3, 6, 10],  # half-diminished
    "minmaj7": [0, 3, 7, 11],
    # extensions
    "add9": [0, 4, 7, 14],
    "madd9": [0, 3, 7, 14],
    "maj9": [0, 4, 7, 11, 14],
    "min9": [0, 3, 7, 10, 14],
    "dom9": [0, 4, 7, 10, 14],
    # ambient-friendly voicings
    "power": [0, 7],  # root + 5th
    "open5": [0, 7, 12],  # root + 5th + octave
    "quartal": [0, 5, 10],  # stacked 4ths
    "quintal": [0, 7, 14],  # stacked 5ths
}

# modes as semitone patterns
MODES = {
    "ionian": [0, 2, 4, 5, 7, 9, 11],  # major
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "aeolian": [0, 2, 3, 5, 7, 8, 10],  # natural minor
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    # pentatonics
    "pentatonic": [0, 2, 4, 7, 9],
    "minor_pentatonic": [0, 3, 5, 7, 10],
    # other
    "whole_tone": [0, 2, 4, 6, 8, 10],
    "chromatic": list(range(12)),
}

# diatonic chord qualities for each scale degree in major
DIATONIC_CHORDS = {
    "I": "major",
    "ii": "minor",
    "iii": "minor",
    "IV": "major",
    "V": "major",
    "vi": "minor",
    "vii°": "dim",
    # sevenths
    "Imaj7": "maj7",
    "ii7": "min7",
    "iii7": "min7",
    "IVmaj7": "maj7",
    "V7": "dom7",
    "vi7": "min7",
    "vii7": "m7b5",
}

# roman numeral to scale degree
ROMAN_TO_DEGREE = {
    "I": 0,
    "i": 0,
    "II": 1,
    "ii": 1,
    "bII": 1,
    "III": 2,
    "iii": 2,
    "bIII": 2,
    "IV": 3,
    "iv": 3,
    "V": 4,
    "v": 4,
    "VI": 5,
    "vi": 5,
    "bVI": 5,
    "VII": 6,
    "vii": 6,
    "vii°": 6,
    "bVII": 6,
}


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


def _freq_to_semitones_from_a4(freq: float) -> float:
    """convert frequency to semitones relative to A4."""
    import math

    return 12 * math.log2(freq / 440.0)


def _semitones_to_freq(semitones_from_a4: float) -> float:
    """convert semitones from A4 to frequency."""
    return 440.0 * (2 ** (semitones_from_a4 / 12))


@dataclass
class Interval:
    """represents a musical interval."""

    semitones: int

    @classmethod
    def from_name(cls, name: str) -> Interval:
        """create from interval name like 'M3', 'P5', 'm7'."""
        if name not in INTERVALS:
            raise ValueError(f"unknown interval: {name}")
        return cls(INTERVALS[name])

    @property
    def is_consonant(self) -> bool:
        """check if interval is consonant."""
        consonant = {0, 3, 4, 5, 7, 8, 9, 12}
        return (self.semitones % 12) in consonant

    def apply(self, freq: float) -> float:
        """apply interval to a frequency."""
        return freq * (2 ** (self.semitones / 12))


@dataclass
class Chord:
    """a chord defined by root and quality."""

    root: str  # note name like "C4"
    quality: str = "major"

    def __post_init__(self):
        if self.quality not in CHORD_TYPES:
            raise ValueError(f"unknown chord quality: {self.quality}")
        self._root_freq = _parse_note(self.root)

    @property
    def intervals(self) -> list[int]:
        """get intervals in semitones."""
        return CHORD_TYPES[self.quality]

    @property
    def frequencies(self) -> list[float]:
        """get frequencies for all chord tones."""
        return [self._root_freq * (2 ** (i / 12)) for i in self.intervals]

    def voiced(self, voicing: Voicing) -> list[float]:
        """apply a voicing to get specific frequencies."""
        return voicing.apply(self._root_freq, self.intervals)

    def inversion(self, n: int) -> list[float]:
        """get nth inversion (0 = root position)."""
        freqs = self.frequencies
        for _ in range(n % len(freqs)):
            freqs = [*freqs[1:], freqs[0] * 2]  # move bass up an octave
        return freqs


@dataclass
class Voicing:
    """defines how chord tones are spread across octaves.

    examples:
        Voicing.close()      # notes within one octave
        Voicing.open()       # spread across octaves
        Voicing.drop2()      # drop 2nd voice down an octave
        Voicing.spread([0, 12, 19, 24])  # custom octave offsets
    """

    octave_offsets: list[int] = field(default_factory=lambda: [0, 0, 0, 0])

    @classmethod
    def close(cls) -> Voicing:
        """close voicing - all notes within an octave."""
        return cls([0, 0, 0, 0])

    @classmethod
    def open(cls) -> Voicing:
        """open voicing - notes spread across 2+ octaves."""
        return cls([0, 12, 0, 12])

    @classmethod
    def drop2(cls) -> Voicing:
        """drop 2 voicing - 2nd highest note dropped an octave."""
        return cls([0, 0, -12, 0])

    @classmethod
    def spread(cls, offsets: list[int]) -> Voicing:
        """custom spread with explicit octave offsets in semitones."""
        return cls(offsets)

    @classmethod
    def wide(cls) -> Voicing:
        """very wide voicing for ambient textures."""
        return cls([0, 12, 24, 12])

    def apply(self, root_freq: float, intervals: list[int]) -> list[float]:
        """apply voicing to chord intervals."""
        freqs = []
        for i, interval in enumerate(intervals):
            offset = self.octave_offsets[i % len(self.octave_offsets)]
            total_semitones = interval + offset
            freqs.append(root_freq * (2 ** (total_semitones / 12)))
        return sorted(freqs)


@dataclass
class Scale:
    """a scale/mode with a root."""

    root: str  # note name like "C"
    mode: str = "ionian"

    def __post_init__(self):
        if self.mode not in MODES:
            raise ValueError(f"unknown mode: {self.mode}")
        # parse root without octave
        self._root_offset = {
            "C": -9,
            "D": -7,
            "E": -5,
            "F": -4,
            "G": -2,
            "A": 0,
            "B": 2,
        }[self.root[0].upper()]
        if len(self.root) > 1 and self.root[1] in "#s":
            self._root_offset += 1
        elif len(self.root) > 1 and self.root[1] == "b":
            self._root_offset -= 1

    @property
    def intervals(self) -> list[int]:
        """get scale intervals."""
        return MODES[self.mode]

    def degree_to_semitones(self, degree: int) -> int:
        """convert scale degree (0-indexed) to semitones from root."""
        octave = degree // len(self.intervals)
        step = degree % len(self.intervals)
        return self.intervals[step] + octave * 12

    def freq_at_degree(self, degree: int, octave: int = 4) -> float:
        """get frequency for a scale degree at given octave."""
        base_semitones = self._root_offset + (octave - 4) * 12
        degree_semitones = self.degree_to_semitones(degree)
        return 440.0 * (2 ** ((base_semitones + degree_semitones) / 12))

    def chord_at_degree(
        self, degree: int, quality: str | None = None, octave: int = 4
    ) -> Chord:
        """get chord rooted on scale degree."""
        # default to diatonic quality
        if quality is None:
            roman = ["I", "ii", "iii", "IV", "V", "vi", "vii°"][degree % 7]
            quality = DIATONIC_CHORDS.get(roman, "major")

        freq = self.freq_at_degree(degree, octave)
        # convert freq back to note name (approximate)
        semitones = round(_freq_to_semitones_from_a4(freq))
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        note_idx = (semitones + 9) % 12  # A is index 9
        note_octave = 4 + (semitones + 9) // 12
        note_name = f"{note_names[note_idx]}{note_octave}"

        return Chord(note_name, quality)


@dataclass
class Progression:
    """a chord progression."""

    scale: Scale
    chords: list[str]  # roman numerals like ["I", "vi", "IV", "V"]
    beats_per_chord: list[int] | int = 4

    def __post_init__(self):
        if isinstance(self.beats_per_chord, int):
            self.beats_per_chord = [self.beats_per_chord] * len(self.chords)

    def get_chords(self, octave: int = 3) -> list[tuple[Chord, int]]:
        """get list of (chord, beats) tuples."""
        result = []
        for i, roman in enumerate(self.chords):
            # parse roman numeral
            # strip trailing modifiers like 7, °, 9
            base_roman = roman
            for suffix in ("maj7", "min7", "7", "°", "9"):
                if base_roman.endswith(suffix):
                    base_roman = base_roman[: -len(suffix)]
                    break
            degree = ROMAN_TO_DEGREE.get(base_roman, 0)

            # determine quality
            if "7" in roman:
                if base_roman.isupper():
                    quality = "maj7" if "maj" in roman.lower() else "dom7"
                else:
                    quality = "min7"
            elif "°" in roman:
                quality = "dim"
            elif base_roman.islower():
                quality = "minor"
            else:
                quality = "major"

            chord = self.scale.chord_at_degree(degree, quality, octave)
            beats = self.beats_per_chord[i]
            result.append((chord, beats))
        return result


def consonance_score(frequencies: list[float]) -> float:
    """rate how consonant a set of frequencies sounds (0-1).

    based on interval relationships between all pairs.
    """
    if len(frequencies) < 2:
        return 1.0

    consonant_intervals = {0, 3, 4, 5, 7, 8, 9, 12}
    total_pairs = 0
    consonant_pairs = 0

    for i, f1 in enumerate(frequencies):
        for f2 in frequencies[i + 1 :]:
            ratio = f2 / f1 if f2 > f1 else f1 / f2
            # convert to semitones
            import math

            semitones = round(12 * math.log2(ratio)) % 12
            total_pairs += 1
            if semitones in consonant_intervals:
                consonant_pairs += 1

    return consonant_pairs / total_pairs if total_pairs > 0 else 1.0


def voice_lead(from_freqs: list[float], to_chord: Chord) -> list[float]:
    """find smooth voice leading from one set of frequencies to a chord.

    minimizes total movement between voices.
    """
    target_freqs = to_chord.frequencies

    # extend targets to cover multiple octaves for better matching
    extended_targets = []
    for f in target_freqs:
        for octave_shift in [-1, 0, 1]:
            extended_targets.append(f * (2**octave_shift))

    # greedy assignment: for each source, find closest target
    result = []
    used = set()
    for src in sorted(from_freqs):
        best_target = None
        best_distance = float("inf")
        for tgt in extended_targets:
            if tgt not in used:
                # distance in semitones
                import math

                dist = abs(12 * math.log2(tgt / src))
                if dist < best_distance:
                    best_distance = dist
                    best_target = tgt
        if best_target:
            result.append(best_target)
            used.add(best_target)

    return sorted(result)
