"""tests for digital audio claudespace."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from dac import (
    Layer,
    Noise,
    Oscillator,
    RenderError,
    Sequence,
    Silence,
    Song,
    chord,
    note,
    render,
    rest,
)


class TestOscillator:
    def test_default_values(self):
        osc = Oscillator()
        assert osc.frequency == 440.0
        assert osc.waveform == "sine"
        assert osc._amplitude == 0.35
        assert osc._duration == 1.0

    def test_custom_frequency(self):
        osc = Oscillator(880)
        assert osc.frequency == 880.0

    def test_custom_waveform(self):
        osc = Oscillator(440, "square")
        assert osc.waveform == "square"

    def test_fluent_api(self):
        osc = Oscillator(440).duration(2.0).amplitude(0.5).fade_in(0.1).fade_out(0.2)
        assert osc._duration == 2.0
        assert osc._amplitude == 0.5
        assert osc._fade_in == 0.1
        assert osc._fade_out == 0.2

    def test_partials(self):
        osc = Oscillator(440).with_partials([880, (1320, 0.5)])
        assert len(osc.partials) == 2
        assert osc.partials[0] == (880, 1.0)
        assert osc.partials[1] == (1320, 0.5)

    def test_partials_only_for_sine(self):
        osc = Oscillator(440, "square")
        with pytest.raises(ValueError, match="partials only supported"):
            osc.with_partials([880])

    def test_invalid_frequency(self):
        with pytest.raises(ValueError, match="frequency must be positive"):
            Oscillator(-440)

    def test_invalid_amplitude(self):
        with pytest.raises(ValueError, match="amplitude must be between"):
            Oscillator().amplitude(0)
        with pytest.raises(ValueError, match="amplitude must be between"):
            Oscillator().amplitude(1.5)

    def test_invalid_duration(self):
        with pytest.raises(ValueError, match="duration must be positive"):
            Oscillator().duration(0)


class TestNoise:
    def test_default_values(self):
        noise = Noise()
        assert noise.color == "white"

    def test_pink_noise(self):
        noise = Noise("pink")
        assert noise.color == "pink"

    def test_fluent_api(self):
        noise = Noise("brown").duration(5.0).amplitude(0.2)
        assert noise._duration == 5.0
        assert noise._amplitude == 0.2


class TestSilence:
    def test_default_values(self):
        silence = Silence()
        assert silence._duration == 1.0

    def test_custom_duration(self):
        silence = Silence().duration(0.5)
        assert silence._duration == 0.5


class TestSequence:
    def test_empty_sequence(self):
        seq = Sequence()
        assert seq.nodes == []
        assert seq._duration == 0.0

    def test_sequence_with_nodes(self):
        seq = Sequence(
            [
                Oscillator(440).duration(1.0),
                Oscillator(880).duration(0.5),
            ]
        )
        assert len(seq.nodes) == 2
        assert seq._duration == 1.5

    def test_add_node(self):
        seq = Sequence().add(Oscillator().duration(1.0))
        assert len(seq.nodes) == 1
        assert seq._duration == 1.0

    def test_duration_raises(self):
        seq = Sequence()
        with pytest.raises(ValueError, match="sequence duration is calculated"):
            seq.duration(5.0)


class TestLayer:
    def test_empty_layer(self):
        layer = Layer()
        assert layer.nodes == []

    def test_layer_with_nodes(self):
        layer = Layer(
            [
                Oscillator(440),
                Noise("pink"),
            ]
        )
        assert len(layer.nodes) == 2

    def test_duration_sets_all(self):
        osc = Oscillator(440)
        noise = Noise()
        layer = Layer([osc, noise]).duration(3.0)
        assert osc._duration == 3.0
        assert noise._duration == 3.0
        assert layer._duration == 3.0


class TestRender:
    @pytest.fixture
    def tmp_output(self, tmp_path: Path) -> Path:
        return tmp_path / "test.wav"

    def test_render_oscillator(self, tmp_output: Path):
        tone = Oscillator(440).duration(0.1)
        result = render(tone, tmp_output)
        assert result.exists()
        assert result.stat().st_size > 0

    def test_render_noise(self, tmp_output: Path):
        noise = Noise("pink").duration(0.1)
        result = render(noise, tmp_output)
        assert result.exists()

    def test_render_with_fades(self, tmp_output: Path):
        tone = Oscillator(440).duration(0.5).fade_in(0.1).fade_out(0.1)
        result = render(tone, tmp_output)
        assert result.exists()

    def test_render_with_partials(self, tmp_output: Path):
        chord = Oscillator(440).with_partials([880, 1320]).duration(0.1)
        result = render(chord, tmp_output)
        assert result.exists()

    def test_render_square_wave(self, tmp_output: Path):
        tone = Oscillator(440, "square").duration(0.1)
        result = render(tone, tmp_output)
        assert result.exists()

    def test_render_creates_parent_dirs(self, tmp_path: Path):
        output = tmp_path / "nested" / "dir" / "test.wav"
        tone = Oscillator(440).duration(0.1)
        result = render(tone, output)
        assert result.exists()

    def test_dry_run(self, tmp_output: Path, capsys):
        tone = Oscillator(440).duration(0.1)
        render(tone, tmp_output, dry_run=True)
        captured = capsys.readouterr()
        assert "ffmpeg command:" in captured.out
        assert not tmp_output.exists()

    def test_ffmpeg_not_found(self, tmp_output: Path):
        with (
            patch("shutil.which", return_value=None),
            pytest.raises(RenderError, match="ffmpeg not found"),
        ):
            render(Oscillator(), tmp_output)

    def test_render_sequence(self, tmp_output: Path):
        seq = Sequence(
            [
                Oscillator(440).duration(0.1),
                Oscillator(550).duration(0.1),
            ]
        )
        result = render(seq, tmp_output)
        assert result.exists()

    def test_render_layer(self, tmp_output: Path):
        layer = Layer(
            [
                Oscillator(440).amplitude(0.3),
                Noise("pink").amplitude(0.1),
            ]
        ).duration(0.1)
        result = render(layer, tmp_output)
        assert result.exists()


class TestMusic:
    def test_note_parsing(self):
        # A4 = 440 Hz
        n = note("A4")
        assert abs(n.frequency - 440.0) < 0.01

        # C4 = middle C = 261.63 Hz
        n = note("C4")
        assert abs(n.frequency - 261.63) < 0.1

        # sharps and flats
        n = note("C#4")
        assert n.frequency > 261.63

        n = note("Db4")
        assert abs(n.frequency - note("C#4").frequency) < 0.01

    def test_note_with_duration(self):
        n = note("A4", 2.0)
        assert n._duration == 2.0

    def test_rest(self):
        r = rest(0.5)
        assert r._duration == 0.5

    def test_chord(self):
        c = chord(["C4", "E4", "G4"])
        assert len(c.nodes) == 3

    def test_song_basic(self):
        song = Song(bpm=120)
        song.add_track(["C4", "D4", "E4"])
        built = song.build()
        assert len(built.nodes) == 3
        # at 120 bpm, each beat is 0.5s
        assert abs(built._duration - 1.5) < 0.01

    def test_song_with_beats(self):
        song = Song(bpm=60)  # 1 beat = 1 second
        song.add_track([("C4", 2), ("D4", 1)])
        built = song.build()
        assert abs(built._duration - 3.0) < 0.01

    def test_song_with_chords(self):
        song = Song(bpm=120)
        song.add_track([("C4 E4 G4", 2)])
        built = song.build()
        # should be a Layer inside a Sequence
        assert len(built.nodes) == 1
        assert isinstance(built.nodes[0], Layer)

    def test_song_with_rests(self):
        song = Song(bpm=120)
        song.add_track(["C4", "-", "E4"])
        built = song.build()
        assert len(built.nodes) == 3
        assert isinstance(built.nodes[1], Silence)

    @pytest.fixture
    def tmp_output(self, tmp_path: Path) -> Path:
        return tmp_path / "test.wav"

    def test_render_song(self, tmp_output: Path):
        song = Song(bpm=120)
        song.add_track(["C4", "E4", "G4"])
        result = render(song.build(), tmp_output)
        assert result.exists()

    def test_render_multitrack_song(self, tmp_output: Path):
        song = Song(bpm=120)
        song.add_track(["C4", "E4"], waveform="sine")
        song.add_track(["C3", "E3"], waveform="triangle")
        result = render(song.build(), tmp_output)
        assert result.exists()
