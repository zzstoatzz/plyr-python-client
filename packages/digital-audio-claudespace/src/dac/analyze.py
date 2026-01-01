"""audio analysis for self-assessment."""

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# frequency bands for spectral analysis
BANDS = {
    "sub": (20, 60),  # kick body, sub-bass
    "bass": (60, 200),  # bass, low end
    "low_mid": (200, 500),  # warmth, body
    "mid": (500, 2000),  # melody, vocals
    "high_mid": (2000, 6000),  # presence, clarity
    "high": (6000, 16000),  # air, hi-hats, brightness
}


@dataclass
class BandLevels:
    """loudness per frequency band."""

    sub: float
    bass: float
    low_mid: float
    mid: float
    high_mid: float
    high: float

    def summary(self) -> str:
        lines = ["frequency bands (mean dB):"]
        for name in BANDS:
            val = getattr(self, name)
            bar = "█" * max(0, int((val + 60) / 3))  # visual bar
            lines.append(f"  {name:8s}: {val:6.1f} dB {bar}")
        return "\n".join(lines)

    def balance_issues(self) -> list[str]:
        """detect balance problems."""
        issues = []
        # kick should be present but not dominating
        if self.sub > self.mid + 6:
            issues.append(f"sub-bass heavy: sub {self.sub:.1f} vs mid {self.mid:.1f}")
        if self.sub < self.mid - 20:
            issues.append(f"sub-bass weak: sub {self.sub:.1f} vs mid {self.mid:.1f}")
        # hi-hats shouldn't overpower
        if self.high > self.mid:
            issues.append(
                f"highs too bright: high {self.high:.1f} vs mid {self.mid:.1f}"
            )
        # muddy mix detection
        if self.low_mid > self.mid + 3:
            issues.append(f"muddy: low_mid {self.low_mid:.1f} vs mid {self.mid:.1f}")
        return issues


@dataclass
class AudioMetrics:
    """metrics extracted from a wav file."""

    peak_db: float  # maximum level (clipping if > 0)
    mean_db: float  # average level
    duration: float  # seconds

    @property
    def dynamic_range_db(self) -> float:
        """difference between peak and mean."""
        return self.peak_db - self.mean_db

    @property
    def is_clipping(self) -> bool:
        return self.peak_db >= 0

    @property
    def is_too_quiet(self) -> bool:
        return self.peak_db < -20

    @property
    def is_too_loud(self) -> bool:
        return self.peak_db > -3

    def issues(self) -> list[str]:
        """return list of detected issues."""
        problems = []
        if self.is_clipping:
            problems.append(f"clipping: peak at {self.peak_db:.1f} dB")
        if self.is_too_quiet:
            problems.append(f"too quiet: peak at {self.peak_db:.1f} dB")
        if self.is_too_loud:
            problems.append(f"hot: peak at {self.peak_db:.1f} dB (risk of harshness)")
        if self.dynamic_range_db < 3:
            problems.append(f"flat dynamics: only {self.dynamic_range_db:.1f} dB range")
        return problems

    def summary(self) -> str:
        """human-readable summary."""
        lines = [
            f"duration: {self.duration:.1f}s",
            f"peak: {self.peak_db:.1f} dB",
            f"mean: {self.mean_db:.1f} dB",
            f"dynamic range: {self.dynamic_range_db:.1f} dB",
        ]
        issues = self.issues()
        if issues:
            lines.append("issues:")
            for issue in issues:
                lines.append(f"  - {issue}")
        else:
            lines.append("no issues detected")
        return "\n".join(lines)


def analyze(path: Path | str) -> AudioMetrics:
    """analyze a wav file and return metrics."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"file not found: {path}")

    # use ffmpeg volumedetect filter
    result = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(path),
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )

    output = result.stderr
    peak_db = mean_db = None

    for line in output.split("\n"):
        if "max_volume" in line:
            peak_db = float(line.split(":")[-1].strip().replace(" dB", ""))
        if "mean_volume" in line:
            mean_db = float(line.split(":")[-1].strip().replace(" dB", ""))

    if peak_db is None or mean_db is None:
        raise ValueError("could not parse volume from ffmpeg output")

    # get duration
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    duration = float(result.stdout.strip())

    return AudioMetrics(peak_db=peak_db, mean_db=mean_db, duration=duration)


def analyze_bands(path: Path | str) -> BandLevels:
    """analyze loudness per frequency band."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"file not found: {path}")

    levels = {}
    for name, (low, high) in BANDS.items():
        # bandpass filter then measure volume
        result = subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(path),
                "-af",
                f"highpass=f={low},lowpass=f={high},volumedetect",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
        )
        output = result.stderr
        mean_db = -60.0  # default if no signal
        for line in output.split("\n"):
            if "mean_volume" in line:
                mean_db = float(line.split(":")[-1].strip().replace(" dB", ""))
        levels[name] = mean_db

    return BandLevels(**levels)


def full_analysis(path: Path | str) -> tuple[AudioMetrics, BandLevels]:
    """complete analysis: overall metrics + spectral bands."""
    return analyze(path), analyze_bands(path)


@dataclass
class IterationLog:
    """log of a single render iteration."""

    timestamp: str
    source_file: str
    output_file: str
    metrics: AudioMetrics
    bands: BandLevels
    settings: dict = field(default_factory=dict)
    feedback: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "source_file": self.source_file,
            "output_file": self.output_file,
            "metrics": {
                "peak_db": self.metrics.peak_db,
                "mean_db": self.metrics.mean_db,
                "duration": self.metrics.duration,
            },
            "bands": {
                "sub": self.bands.sub,
                "bass": self.bands.bass,
                "low_mid": self.bands.low_mid,
                "mid": self.bands.mid,
                "high_mid": self.bands.high_mid,
                "high": self.bands.high,
            },
            "settings": self.settings,
            "feedback": self.feedback,
        }


class IterationLogger:
    """tracks iterations for a piece."""

    def __init__(self, log_dir: Path | str):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "iterations.jsonl"
        self.renders_dir = self.log_dir / "renders"
        self.renders_dir.mkdir(exist_ok=True)

    def log(
        self,
        source_file: Path | str,
        output_file: Path | str,
        settings: dict | None = None,
    ) -> IterationLog:
        """log an iteration: analyze, archive, record."""
        source_file = Path(source_file)
        output_file = Path(output_file)

        # analyze
        metrics, bands = full_analysis(output_file)

        # archive render with timestamp
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{source_file.stem}_{ts}.wav"
        archive_path = self.renders_dir / archive_name
        shutil.copy(output_file, archive_path)

        # create log entry
        entry = IterationLog(
            timestamp=ts,
            source_file=str(source_file),
            output_file=str(archive_path),
            metrics=metrics,
            bands=bands,
            settings=settings or {},
        )

        # append to log file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

        return entry

    def load_history(self) -> list[dict]:
        """load all logged iterations."""
        if not self.log_file.exists():
            return []
        entries = []
        with open(self.log_file) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries

    def compare_last_two(self) -> str | None:
        """compare the last two iterations."""
        history = self.load_history()
        if len(history) < 2:
            return None
        return compare_iterations(history[-2], history[-1])


def compare_iterations(a: dict, b: dict) -> str:
    """compare two iteration logs."""
    lines = [f"comparing {a['timestamp']} -> {b['timestamp']}"]

    # overall metrics
    peak_diff = b["metrics"]["peak_db"] - a["metrics"]["peak_db"]
    mean_diff = b["metrics"]["mean_db"] - a["metrics"]["mean_db"]
    lines.append(f"  peak: {peak_diff:+.1f} dB")
    lines.append(f"  mean: {mean_diff:+.1f} dB")

    # band changes
    lines.append("  bands:")
    for band in BANDS:
        diff = b["bands"][band] - a["bands"][band]
        if abs(diff) > 1:  # only show significant changes
            direction = "↑" if diff > 0 else "↓"
            lines.append(f"    {band}: {diff:+.1f} dB {direction}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("usage: python -m dac.analyze <file.wav>")
        sys.exit(1)

    path = sys.argv[1]
    metrics = analyze(path)
    print(metrics.summary())
    print()
    bands = analyze_bands(path)
    print(bands.summary())
    issues = bands.balance_issues()
    if issues:
        print("\nbalance issues:")
        for issue in issues:
            print(f"  - {issue}")
