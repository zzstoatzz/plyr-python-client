"""tests for digital audio claudespace."""

from pathlib import Path
from unittest.mock import patch

import pytest
from dac import major, minor, render_events, render_loops


class TestRenderEvents:
    @pytest.fixture
    def tmp_output(self, tmp_path: Path) -> Path:
        return tmp_path / "test.wav"

    def test_single_note(self, tmp_output: Path):
        result = render_events([(0, "A4", 0.5)], tmp_output, fade_in=0, fade_out=0)
        assert result.exists()
        assert result.stat().st_size > 0

    def test_chord(self, tmp_output: Path):
        result = render_events(
            [(0, ["C4", "E4", "G4"], 0.5)], tmp_output, fade_in=0, fade_out=0
        )
        assert result.exists()

    def test_overlapping_notes(self, tmp_output: Path):
        result = render_events(
            [
                (0, "C3", 2),
                (0.5, "E3", 1.5),
                (1, "G3", 1),
            ],
            tmp_output,
            fade_in=0,
            fade_out=0,
        )
        assert result.exists()

    def test_ffmpeg_not_found(self, tmp_output: Path):
        with (
            patch("dac.shutil.which", return_value=None),
            pytest.raises(RuntimeError, match="ffmpeg not found"),
        ):
            render_events([(0, "A4", 1)], tmp_output)


class TestRenderLoops:
    @pytest.fixture
    def tmp_output(self, tmp_path: Path) -> Path:
        return tmp_path / "test.wav"

    def test_basic_loops(self, tmp_output: Path):
        result = render_loops(
            [
                ("A3", 2.0, 1.5),
                ("E3", 2.5, 1.8),
            ],
            duration=5,
            output=tmp_output,
            fade_in=0,
            fade_out=0,
        )
        assert result.exists()

    def test_staggered_starts(self, tmp_output: Path):
        result = render_loops(
            [
                ("C3", 3.0, 2.0, 0.1),
                ("G3", 3.5, 2.5, 0.08),
            ],
            duration=8,
            output=tmp_output,
            stagger=True,
            fade_in=0,
            fade_out=0,
        )
        assert result.exists()

    def test_custom_amplitude(self, tmp_output: Path):
        result = render_loops(
            [("A3", 2.0, 1.5, 0.05)],
            duration=4,
            output=tmp_output,
            fade_in=0,
            fade_out=0,
        )
        assert result.exists()


class TestChordHelpers:
    def test_major(self):
        c_major = major("C4")
        assert len(c_major) == 3
        assert c_major[0] == "C4"
        assert c_major[1] == "E4"
        assert c_major[2] == "G4"

    def test_minor(self):
        a_minor = minor("A3")
        assert len(a_minor) == 3
        assert a_minor[0] == "A3"
        assert a_minor[1] == "C4"
        assert a_minor[2] == "E4"
