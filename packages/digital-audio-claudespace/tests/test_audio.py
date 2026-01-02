"""empirical tests for audio output.

run with: uv run python tests/test_audio.py
"""

import subprocess
import sys
from pathlib import Path

# add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dac.track import Sine, mix, phase


def get_max_volume(path: Path) -> float:
    """get max volume in dB."""
    result = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    for line in result.stderr.split("\n"):
        if "max_volume" in line:
            return float(line.split(":")[-1].strip().replace(" dB", ""))
    raise ValueError("could not parse max volume")


def amp_to_db(amp: float) -> float:
    """convert amplitude to dB."""
    import math

    return 20 * math.log10(amp) if amp > 0 else -100


def test_single_sine():
    """a single sine wave should output at its specified amplitude."""
    print("\n=== TEST: single sine ===")

    out = Path("/tmp/test_single.wav")
    s = Sine(440, 2, amplitude=0.3, label="test")
    mix([s], out, duration=2)

    max_vol = get_max_volume(out)
    expected = amp_to_db(0.3)  # -10.5 dB

    print(f"  amplitude: 0.3 → expected max: {expected:.1f} dB")
    print(f"  actual max: {max_vol:.1f} dB")

    diff = abs(max_vol - expected)
    if diff < 1.0:
        print("  ✓ PASS")
        return True
    else:
        print(f"  ✗ FAIL (diff: {diff:.1f} dB)")
        return False


def test_two_sines():
    """two sines should sum (with normalize=0)."""
    print("\n=== TEST: two sines ===")

    out = Path("/tmp/test_two.wav")
    s1 = Sine(440, 2, amplitude=0.2, label="a")
    s2 = Sine(880, 2, amplitude=0.2, label="b")
    mix([s1, s2], out, duration=2)

    max_vol = get_max_volume(out)
    # two sines at 0.2 can peak at 0.4 when aligned
    expected_max = amp_to_db(0.4)  # -8 dB

    print(f"  two sines at 0.2 → expected max: ~{expected_max:.1f} dB")
    print(f"  actual max: {max_vol:.1f} dB")

    # should be between -10 dB (no overlap) and -8 dB (full overlap)
    if -11 < max_vol < -6:
        print("  ✓ PASS")
        return True
    else:
        print("  ✗ FAIL")
        return False


def test_fade_out():
    """fade_out should fade at the END of the track, not the start."""
    print("\n=== TEST: fade_out ===")

    out = Path("/tmp/test_fade.wav")
    s = Sine(440, 4, amplitude=0.3, label="test").fade_out(1)
    mix([s], out, duration=4)

    max_vol = get_max_volume(out)
    expected = amp_to_db(0.3)

    print(f"  sine with fade_out(1) → expected max: {expected:.1f} dB")
    print(f"  actual max: {max_vol:.1f} dB")

    # should still hit full amplitude before fade
    diff = abs(max_vol - expected)
    if diff < 1.0:
        print("  ✓ PASS - fade_out preserves peak")
        return True
    else:
        print("  ✗ FAIL - peak too low, fade_out may be at start")
        return False


def test_fade_in_and_out():
    """fade_in + fade_out should not conflict."""
    print("\n=== TEST: fade_in + fade_out ===")

    out = Path("/tmp/test_both_fades.wav")
    s = Sine(440, 4, amplitude=0.3, label="test").fade_in(1).fade_out(1)
    mix([s], out, duration=4)

    max_vol = get_max_volume(out)
    expected = amp_to_db(0.3)

    print(f"  sine with fade_in(1) + fade_out(1) → expected max: {expected:.1f} dB")
    print(f"  actual max: {max_vol:.1f} dB")

    diff = abs(max_vol - expected)
    if diff < 1.0:
        print("  ✓ PASS - fades don't conflict")
        return True
    else:
        print(f"  ✗ FAIL - fades may be overlapping (diff: {diff:.1f} dB)")
        return False


def test_phase():
    """phased copies should maintain amplitude."""
    print("\n=== TEST: phase ===")

    out = Path("/tmp/test_phase.wav")
    s = Sine(440, 2, amplitude=0.3, label="p")
    copies = phase(s, interval=4, duration=10)
    mix(copies, out, duration=10)

    max_vol = get_max_volume(out)
    expected = amp_to_db(0.3)

    print(f"  phased sine at 0.3 → expected max: {expected:.1f} dB")
    print(f"  actual max: {max_vol:.1f} dB")
    print(f"  ({len(copies)} copies)")

    diff = abs(max_vol - expected)
    if diff < 2.0:
        print("  ✓ PASS")
        return True
    else:
        print(f"  ✗ FAIL (diff: {diff:.1f} dB)")
        return False


def test_phase_with_fades():
    """phased copies with fades should maintain amplitude."""
    print("\n=== TEST: phase with fades ===")

    out = Path("/tmp/test_phase_fades.wav")
    s = Sine(440, 2, amplitude=0.3, label="p").fade_in(0.5).fade_out(0.5)
    copies = phase(s, interval=4, duration=10)
    mix(copies, out, duration=10)

    max_vol = get_max_volume(out)
    expected = amp_to_db(0.3)

    print(f"  phased sine with fades at 0.3 → expected max: {expected:.1f} dB")
    print(f"  actual max: {max_vol:.1f} dB")

    diff = abs(max_vol - expected)
    if diff < 2.0:
        print("  ✓ PASS")
        return True
    else:
        print(f"  ✗ FAIL (diff: {diff:.1f} dB)")
        return False


def test_continuous_plus_phased():
    """continuous track + phased tracks should sum correctly."""
    print("\n=== TEST: continuous + phased ===")

    out = Path("/tmp/test_mixed.wav")

    # continuous drone
    drone = Sine(110, 10, amplitude=0.2, label="drone")

    # phased melody
    melody = Sine(440, 2, amplitude=0.2, label="mel")
    mel_copies = phase(melody, interval=4, duration=10)

    all_tracks = [drone, *mel_copies]
    mix(all_tracks, out, duration=10)

    max_vol = get_max_volume(out)
    # when both play, max is 0.4 = -8 dB
    expected_max = amp_to_db(0.4)

    print(f"  drone(0.2) + melody(0.2) → expected max: ~{expected_max:.1f} dB")
    print(f"  actual max: {max_vol:.1f} dB")
    print(f"  (1 drone + {len(mel_copies)} melody copies)")

    if -10 < max_vol < -5:
        print("  ✓ PASS")
        return True
    else:
        print("  ✗ FAIL")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("DAC AUDIO TESTS")
    print("=" * 50)

    tests = [
        test_single_sine,
        test_two_sines,
        test_fade_out,
        test_fade_in_and_out,
        test_phase,
        test_phase_with_fades,
        test_continuous_plus_phased,
    ]

    results = []
    for test in tests:
        results.append(test())

    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"RESULTS: {passed}/{total} passed")

    if passed == total:
        print("All tests passed!")
    else:
        print("Some tests failed.")
        sys.exit(1)
