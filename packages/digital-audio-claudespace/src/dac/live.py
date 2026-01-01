"""live - real-time synth control.

usage:
    from dac.live import synth

    synth.play("bass", 49, 0.025)    # start voice
    synth.play("mid", 294, 0.02)     # start another
    synth.vol("bass", 0.01)          # adjust volume
    synth.freq("bass", 55)           # adjust frequency
    synth.stop("bass")               # stop one
    synth.stopall()                  # stop all
    synth.list()                     # show running
"""

import json
import os
import signal
import subprocess
from pathlib import Path

STATE_FILE = Path("/tmp/dac_synth_state.json")


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state))


def _start_ffplay(freq: float, amp: float) -> int:
    """start ffplay and return pid."""
    expr = f"aevalsrc=exprs='{amp}*(sin(2*PI*{freq}*t))':s=48000"
    proc = subprocess.Popen(
        ["ffplay", "-f", "lavfi", "-i", expr, "-nodisp", "-loglevel", "quiet"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.pid


def _kill_pid(pid: int):
    """kill a process by pid."""
    import contextlib

    with contextlib.suppress(ProcessLookupError):
        os.kill(pid, signal.SIGTERM)


def play(name: str, freq: float, amp: float = 0.02):
    """start or restart a named voice."""
    state = _load_state()

    # stop existing if any
    if name in state:
        _kill_pid(state[name]["pid"])

    # start new
    pid = _start_ffplay(freq, amp)
    state[name] = {"pid": pid, "freq": freq, "amp": amp}
    _save_state(state)
    print(f"{name}: {freq}Hz @ {amp}")


def stop(name: str):
    """stop a named voice."""
    state = _load_state()
    if name in state:
        _kill_pid(state[name]["pid"])
        del state[name]
        _save_state(state)
        print(f"stopped {name}")
    else:
        print(f"{name} not running")


def stopall():
    """stop all voices."""
    state = _load_state()
    for name, info in state.items():
        _kill_pid(info["pid"])
        print(f"stopped {name}")
    _save_state({})


def vol(name: str, amp: float):
    """change volume of a voice (restarts it)."""
    state = _load_state()
    if name in state:
        freq = state[name]["freq"]
        play(name, freq, amp)
    else:
        print(f"{name} not running")


def freq(name: str, new_freq: float):
    """change frequency of a voice (restarts it)."""
    state = _load_state()
    if name in state:
        amp = state[name]["amp"]
        play(name, new_freq, amp)
    else:
        print(f"{name} not running")


def list():
    """show running voices."""
    state = _load_state()
    if not state:
        print("no voices running")
    for name, info in state.items():
        print(f"{name}: {info['freq']}Hz @ {info['amp']}")


# module-level instance for easy import
class _Synth:
    play = staticmethod(play)
    stop = staticmethod(stop)
    stopall = staticmethod(stopall)
    vol = staticmethod(vol)
    freq = staticmethod(freq)
    list = staticmethod(list)


synth = _Synth()


# --- clips: looping audio files ---

CLIPS_STATE_FILE = Path("/tmp/dac_clips_state.json")


def _load_clips_state() -> dict:
    if CLIPS_STATE_FILE.exists():
        return json.loads(CLIPS_STATE_FILE.read_text())
    return {}


def _save_clips_state(state: dict):
    CLIPS_STATE_FILE.write_text(json.dumps(state))


def clips_play(name: str, path: str | Path, vol: float = 1.0):
    """play a loop by name."""
    state = _load_clips_state()

    # stop existing if any
    if name in state:
        _kill_pid(state[name]["pid"])

    # start looping playback
    proc = subprocess.Popen(
        [
            "ffplay",
            "-loop",
            "0",
            "-nodisp",
            "-loglevel",
            "quiet",
            "-af",
            f"volume={vol}",
            str(path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    state[name] = {"pid": proc.pid, "path": str(path), "vol": vol}
    _save_clips_state(state)
    print(f"{name}: {Path(path).name} @ {vol}")


def clips_stop(name: str):
    """stop a clip."""
    state = _load_clips_state()
    if name in state:
        _kill_pid(state[name]["pid"])
        del state[name]
        _save_clips_state(state)
        print(f"stopped {name}")
    else:
        print(f"{name} not running")


def clips_stopall():
    """stop all clips."""
    state = _load_clips_state()
    for name, info in state.items():
        _kill_pid(info["pid"])
        print(f"stopped {name}")
    _save_clips_state({})


def clips_vol(name: str, vol: float):
    """change volume of a clip (restarts it)."""
    state = _load_clips_state()
    if name in state:
        path = state[name]["path"]
        clips_play(name, path, vol)
    else:
        print(f"{name} not running")


def clips_list():
    """show running clips."""
    state = _load_clips_state()
    if not state:
        print("no clips running")
    for name, info in state.items():
        print(f"{name}: {Path(info['path']).name} @ {info['vol']}")


class _Clips:
    play = staticmethod(clips_play)
    stop = staticmethod(clips_stop)
    stopall = staticmethod(clips_stopall)
    vol = staticmethod(clips_vol)
    list = staticmethod(clips_list)


clips = _Clips()
