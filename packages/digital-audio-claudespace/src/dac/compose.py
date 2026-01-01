"""higher-level composition abstractions.

makes writing music more delightful by reducing boilerplate
and encoding learned preferences as defaults.
"""

import random
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from .track import Sample, Sine, Tempo, Track, note_to_freq

# --- time handling ---


def to_ms(offset: timedelta | float, tempo: Tempo | None = None) -> float:
    """convert a time offset to milliseconds.

    accepts:
      - timedelta: converted directly
      - float: interpreted as beats (requires tempo)
    """
    if isinstance(offset, timedelta):
        return offset.total_seconds() * 1000
    if isinstance(offset, int | float):
        if tempo is None:
            raise ValueError("tempo required when offset is in beats")
        return tempo.beats(offset) * 1000
    raise TypeError(f"expected timedelta or float (beats), got {type(offset)}")


def to_seconds(duration: timedelta | float, tempo: Tempo | None = None) -> float:
    """convert a duration to seconds.

    accepts:
      - timedelta: converted directly
      - float: interpreted as beats (requires tempo)
    """
    if isinstance(duration, timedelta):
        return duration.total_seconds()
    if isinstance(duration, int | float):
        if tempo is None:
            raise ValueError("tempo required when duration is in beats")
        return tempo.beats(duration)
    raise TypeError(f"expected timedelta or float (beats), got {type(duration)}")


# --- defaults from learned preferences ---


@dataclass
class VoicePreset:
    """default voice characteristics."""

    amplitude: float = 0.07
    detune_cents: float = 4.0
    lowpass: float = 600.0
    attack: float = 0.3
    release: float = 0.5


MELODY_PRESET = VoicePreset(
    amplitude=0.07, detune_cents=4, lowpass=600, attack=0.3, release=0.5
)
CHORD_PRESET = VoicePreset(
    amplitude=0.035, detune_cents=4, lowpass=400, attack=0.7, release=0.7
)
BASS_PRESET = VoicePreset(
    amplitude=0.08, detune_cents=4, lowpass=150, attack=0.6, release=0.8
)
PEDAL_PRESET = VoicePreset(
    amplitude=0.04, detune_cents=4, lowpass=400, attack=2.0, release=2.0
)


# --- Voice: warm sine with detune and envelope ---


class Voice:
    """a musical voice with automatic warmth and envelope.

    creates detuned sine pairs for richness, applies filtering and fades.
    much less boilerplate than manual warm_sine + effects chains.
    """

    def __init__(
        self,
        note: str,
        duration: float,
        *,
        preset: VoicePreset | None = None,
        amplitude: float | None = None,
        detune_cents: float | None = None,
        lowpass: float | None = None,
        attack: float | None = None,
        release: float | None = None,
        label: str = "v",
    ):
        self.note = note
        self.freq = note_to_freq(note) if isinstance(note, str) else note
        self.duration = duration
        self.label = label

        # use preset as base, override with explicit values
        p = preset or MELODY_PRESET
        self.amplitude = amplitude if amplitude is not None else p.amplitude
        self.detune_cents = detune_cents if detune_cents is not None else p.detune_cents
        self.lowpass_freq = lowpass if lowpass is not None else p.lowpass
        self.attack = attack if attack is not None else p.attack
        self.release = release if release is not None else p.release

    def render(self, delay_ms: int = 0, label_suffix: str = "") -> list[Track]:
        """render to tracks with all effects applied."""
        tracks = []
        detune_ratio = 2 ** (self.detune_cents / 1200)

        # main + detuned pair for warmth
        components = [
            (self.freq, self.amplitude * 0.7, "m"),
            (self.freq * detune_ratio, self.amplitude * 0.15, "s"),
            (self.freq / detune_ratio, self.amplitude * 0.15, "f"),
        ]

        for freq, amp, suffix in components:
            lbl = f"{self.label}{label_suffix}_{suffix}"
            t = Sine(freq, self.duration, amplitude=amp, label=lbl)
            t.lowpass(self.lowpass_freq)
            t.fade_in(self.attack)
            t.fade_out(self.release)
            if delay_ms > 0:
                t.delay(delay_ms)
            tracks.append(t)

        return tracks

    def at_beat(self, beat: float, tempo: Tempo, label_suffix: str = "") -> list[Track]:
        """render at a specific beat."""
        return self.render(
            delay_ms=tempo.at_beat(beat), label_suffix=label_suffix or f"b{int(beat)}"
        )


# --- Phrase: melodic sequences ---


@dataclass
class Note:
    """a note in a phrase."""

    pitch: str  # e.g. "F#5"
    duration: float = 1.0  # in beats

    def __post_init__(self):
        self.freq = note_to_freq(self.pitch)


class Phrase:
    """a sequence of notes forming a melodic phrase.

    express melodies musically rather than as (note, beat) tuples.
    """

    def __init__(
        self,
        notes: list[str | tuple[str, float]],
        *,
        preset: VoicePreset | None = None,
        default_duration: float = 1.0,
    ):
        """
        notes can be:
          - "F#5" - note with default duration
          - ("F#5", 2) - note with explicit duration in beats
        """
        self.notes: list[Note] = []
        for n in notes:
            if isinstance(n, str):
                self.notes.append(Note(n, default_duration))
            else:
                self.notes.append(Note(n[0], n[1]))

        self.preset = preset or MELODY_PRESET

    def render(
        self,
        start_beat: float,
        tempo: Tempo,
        *,
        label: str = "m",
    ) -> list[Track]:
        """render phrase starting at given beat."""
        tracks = []
        current_beat = start_beat

        for i, note in enumerate(self.notes):
            dur_seconds = tempo.beats(note.duration * 0.9)  # slight gap between notes
            voice = Voice(
                note.pitch,
                dur_seconds,
                preset=self.preset,
                label=f"{label}{i}",
            )
            tracks.extend(voice.at_beat(current_beat, tempo))
            current_beat += note.duration

        return tracks

    def transpose(self, semitones: int) -> "Phrase":
        """return a new phrase transposed by semitones."""
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        new_notes = []

        for note in self.notes:
            # parse note
            if len(note.pitch) == 2:
                name, octave = note.pitch[0], int(note.pitch[1])
            else:
                name, octave = note.pitch[:2], int(note.pitch[2])

            # transpose
            idx = note_names.index(name)
            new_idx = (idx + semitones) % 12
            octave_shift = (idx + semitones) // 12
            new_name = note_names[new_idx]
            new_octave = octave + octave_shift

            new_pitch = f"{new_name}{new_octave}"
            new_notes.append((new_pitch, note.duration))

        return Phrase(new_notes, preset=self.preset)


# --- DrumKit: sample-based drums with humanization ---


@dataclass
class DrumSound:
    """a drum sound with its characteristics."""

    path: Path
    volume_db: float = 0.0
    lowpass: float = 20000.0
    timing_offset: timedelta | None = None  # negative = early, positive = late

    def render(
        self,
        beat: float,
        tempo: Tempo,
        *,
        label: str = "d",
        humanize: timedelta | None = None,
    ) -> Sample:
        """render at a beat with optional humanization."""
        base_delay = tempo.at_beat(beat)

        if self.timing_offset:
            base_delay += self.timing_offset.total_seconds() * 1000

        # humanize: random timing variation
        if humanize:
            humanize_ms = humanize.total_seconds() * 1000
            base_delay += random.uniform(-humanize_ms, humanize_ms)

        base_delay = max(0, base_delay)

        s = Sample(self.path, label=label)
        s.lowpass(self.lowpass)
        s.volume_db(self.volume_db)
        s.delay(int(base_delay))
        return s


@dataclass
class Humanize:
    """humanization settings - makes things feel less mechanical."""

    timing: timedelta = timedelta(0)  # random timing variation (+/-)
    velocity_db: float = 0.0  # random volume variation in dB (+/-)


class DrumKit:
    """a collection of drum sounds with humanization.

    handles timing offsets (snares early, hats late) and
    random micro-variations for human feel.
    """

    def __init__(
        self,
        kick: DrumSound | None = None,
        snare: DrumSound | None = None,
        hihat: DrumSound | None = None,
        *,
        humanize: Humanize | None = None,
    ):
        self.kick = kick
        self.snare = snare
        self.hihat = hihat
        self.humanize = humanize or Humanize()

    def _vary_volume(self, base_db: float) -> float:
        """apply random velocity variation."""
        if self.humanize.velocity_db <= 0:
            return base_db
        return base_db + random.uniform(
            -self.humanize.velocity_db, self.humanize.velocity_db
        )

    def _render_sound(
        self,
        sound: DrumSound,
        beat: float,
        tempo: Tempo,
        *,
        volume_db: float | None = None,
        label: str = "d",
    ) -> Sample:
        """render a drum sound with humanization applied."""
        vol = volume_db if volume_db is not None else sound.volume_db
        vol = self._vary_volume(vol)

        # temporarily override volume for this hit
        original_vol = sound.volume_db
        sound.volume_db = vol
        result = sound.render(
            beat,
            tempo,
            label=f"{label}{int(beat)}",
            humanize=self.humanize.timing
            if self.humanize.timing.total_seconds() > 0
            else None,
        )
        sound.volume_db = original_vol
        return result

    def render_kick(
        self,
        beat: float,
        tempo: Tempo,
        *,
        volume_db: float | None = None,
        label: str = "k",
    ) -> Sample | None:
        if not self.kick:
            return None
        return self._render_sound(
            self.kick, beat, tempo, volume_db=volume_db, label=label
        )

    def render_snare(
        self,
        beat: float,
        tempo: Tempo,
        *,
        volume_db: float | None = None,
        label: str = "s",
    ) -> Sample | None:
        if not self.snare:
            return None
        return self._render_sound(
            self.snare, beat, tempo, volume_db=volume_db, label=label
        )

    def render_hihat(
        self,
        beat: float,
        tempo: Tempo,
        *,
        volume_db: float | None = None,
        label: str = "hh",
    ) -> Sample | None:
        if not self.hihat:
            return None
        return self._render_sound(
            self.hihat, beat, tempo, volume_db=volume_db, label=label
        )

    def pattern(
        self,
        beats: int,
        tempo: Tempo,
        *,
        kick_beats: list[int] | None = None,
        snare_beats: list[int] | None = None,
        hihat_beats: list[int] | None = None,
        start_beat: int = 1,
    ) -> list[Sample]:
        """render a drum pattern over given beats."""
        tracks = []

        kick_beats = kick_beats or []
        snare_beats = snare_beats or []
        hihat_beats = hihat_beats or []

        for i in range(beats):
            beat = start_beat + i
            beat_in_pattern = (i % len(kick_beats)) + 1 if kick_beats else 0

            if ((i + 1) in kick_beats or beat_in_pattern in kick_beats) and (
                t := self.render_kick(beat, tempo)
            ):
                tracks.append(t)

            if (i + 1) in snare_beats and (t := self.render_snare(beat, tempo)):
                tracks.append(t)

            if (i + 1) in hihat_beats and (t := self.render_hihat(beat, tempo)):
                tracks.append(t)

        return tracks


# --- Pedal: sustained background tone ---


class Pedal:
    """a sustained pedal tone throughout a piece.

    provides harmonic foundation with long attack/release.
    """

    def __init__(
        self,
        note: str,
        duration: float,
        *,
        preset: VoicePreset | None = None,
        amplitude: float | None = None,
    ):
        self.note = note
        self.duration = duration
        self.preset = preset or PEDAL_PRESET
        self.amplitude = amplitude

    def render(self) -> list[Track]:
        """render pedal tone with long fades."""
        voice = Voice(
            self.note,
            self.duration,
            preset=self.preset,
            amplitude=self.amplitude,
            label="ped",
        )
        return voice.render()
