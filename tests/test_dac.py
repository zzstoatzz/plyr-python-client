"""basic tests for dac."""

from pathlib import Path

import pytest
from dac import chords, events, loops


class TestRender:
    @pytest.fixture
    def tmp_output(self, tmp_path: Path) -> Path:
        return tmp_path / "test.wav"

    def test_events_render(self, tmp_output: Path):
        result = events.render([(0, "A4", 0.5)], tmp_output, fade_in=0, fade_out=0)
        assert result.exists()

    def test_loops_render(self, tmp_output: Path):
        result = loops.render(
            [("A3", 2.0, 1.5)],
            duration=4,
            output=tmp_output,
            fade_in=0,
            fade_out=0,
        )
        assert result.exists()


class TestChords:
    def test_major(self):
        assert chords.major("C4") == ["C4", "E4", "G4"]

    def test_minor(self):
        assert chords.minor("A3") == ["A3", "C4", "E4"]
