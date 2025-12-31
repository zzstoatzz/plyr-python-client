"""chord construction helpers."""

from dac._internal.notes import interval


def major(root: str) -> list[str]:
    """major triad: root + M3 + P5."""
    return [root, interval(root, 4), interval(root, 7)]


def minor(root: str) -> list[str]:
    """minor triad: root + m3 + P5."""
    return [root, interval(root, 3), interval(root, 7)]


def maj7(root: str) -> list[str]:
    """major 7th: root + M3 + P5 + M7."""
    return [root, interval(root, 4), interval(root, 7), interval(root, 11)]


def min7(root: str) -> list[str]:
    """minor 7th: root + m3 + P5 + m7."""
    return [root, interval(root, 3), interval(root, 7), interval(root, 10)]


def dom7(root: str) -> list[str]:
    """dominant 7th: root + M3 + P5 + m7."""
    return [root, interval(root, 4), interval(root, 7), interval(root, 10)]


def sus2(root: str) -> list[str]:
    """suspended 2nd: root + M2 + P5."""
    return [root, interval(root, 2), interval(root, 7)]


def sus4(root: str) -> list[str]:
    """suspended 4th: root + P4 + P5."""
    return [root, interval(root, 5), interval(root, 7)]


def add9(root: str) -> list[str]:
    """add 9: root + M3 + P5 + M9."""
    return [root, interval(root, 4), interval(root, 7), interval(root, 14)]


def power(root: str) -> list[str]:
    """power chord: root + P5 + octave."""
    return [root, interval(root, 7), interval(root, 12)]
