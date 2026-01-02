"""basic tests for dac."""

from dac import chords


class TestChords:
    def test_major(self):
        assert chords.major("C4") == ["C4", "E4", "G4"]

    def test_minor(self):
        assert chords.minor("A3") == ["A3", "C4", "E4"]
