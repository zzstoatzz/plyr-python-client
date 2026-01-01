# composing with dac

notes on making ambient music with digital audio claudespace.

## the track api

the core api centers on `Sample` and `Sine` - both subclasses of `Track`. effects chain via method calls.

```python
from dac import Sample, Sine, mix

# load a sample and chain effects
harp = (
    Sample("samples/harp/KSHarp_G3_mf1.wav", label="h1")
    .volume(0.4)
    .delay(2000)      # ms
    .fade_in(3)       # seconds
    .lowpass(2000)    # hz
)

# generate a sine drone
drone = (
    Sine(98.0, duration=60, amplitude=0.1, label="dr")
    .fade_in(10)
    .fade_out(10)
    .lowpass(150)
)

# mix to file
mix([harp, drone], Path("output.wav"), duration=60)
```

### available effects

| method | description |
|--------|-------------|
| `.volume(v)` | amplitude multiplier (0.0-1.0) |
| `.delay(ms)` | offset in milliseconds |
| `.fade_in(s)` / `.fade_out(s)` | fades in seconds |
| `.lowpass(hz)` / `.highpass(hz)` | frequency filters |
| `.bandpass(low, high)` | frequency band |
| `.trim(s)` | limit duration |
| `.pad(s)` | add silence to reach duration |
| `.reverb(...)` | room simulation |
| `.reverse()` | play backwards |
| `.speed(factor)` | tempo without pitch change |
| `.pitch(semitones)` | pitch without tempo change |
| `.pan(position)` | stereo position (-1 to 1) |
| `.flanger(...)` / `.phaser(...)` | modulation effects |

effects are chainable and order matters - they're applied sequentially in the ffmpeg filter graph.

## two approaches to composition

### 1. deliberate placement

place each sound at a specific time with intent. this is traditional composition - you decide exactly when things happen.

```python
def harp(note: str, time: float, vol: float = 0.45) -> Sample:
    """place a harp note at a specific time."""
    return (
        Sample(f"samples/harp/KSHarp_{note}_mf1.wav", label=f"h{note}_{int(time)}")
        .volume(vol)
        .delay(int(time * 1000))
    )

tracks = [
    stream, drone,
    # Section A: sparse
    harp("G3", 4),
    harp("D4", 10),
    harp("G3", 16),
    # Section B: building
    harp("D4", 32),
    harp("B3", 36, 0.4),
    # ...
]
```

this approach gives full control. you're writing a score. see `pieces/northfield.py`.

### 2. eno-style incommensurable loops

brian eno's insight: use loops of different prime-number lengths. they phase naturally and never exactly repeat.

from *music for airports*:
- loop A: 23.2 seconds
- loop B: 19.6 seconds
- loop C: 31.8 seconds

when these run simultaneously, their start points drift. at T=0, all align. at T=10min, completely different combinations emerge.

```python
from dac import phase

def eno_loop(sample: Sample, cycle: float, offset: float = 0) -> list:
    """sound padded to cycle time, repeating at that interval."""
    sample.pad(cycle)  # silence fills rest of cycle
    return phase(sample, interval=cycle, duration=duration, offset=offset)

# prime cycle times - coprime means they never sync
tracks = [
    *eno_loop(loop_g3, cycle=17, offset=0),
    *eno_loop(loop_d4, cycle=19, offset=3),
    *eno_loop(loop_b3, cycle=23, offset=7),
    *eno_loop(loop_e3, cycle=29, offset=11),
]
# LCM of 17*19*23*29 = 215,441 seconds before exact repeat
```

the `phase()` function creates copies of a sample at regular intervals across the duration. with `eno_loop`, you're designing a system, not a sequence.

key principle: choose notes that are "mutually compatible" - they should sound acceptable in any combination, because the system will eventually generate all of them.

see `pieces/fading.py`.

## lessons learned

### what works

- **continuous textures** - stream/wind/drone as a bed. keeps the piece alive during sparse moments.
- **harmonic compatibility** - stick to one key. G major works well: G, A, B, D, E (+F# for lydian color).
- **volume hierarchy** - background (0.03-0.06), drones (0.08-0.12), foreground (0.25-0.45).
- **low anchors** - bass drones (G2 ~98hz) and low notes (A2, E3) provide grounding.
- **slow fades** - 8-20 second fades feel natural. short fades feel abrupt.

### what doesn't work

- **glockenspiel** - bright metallic sounds often don't fit ambient contexts. remove if it sounds wrong.
- **algorithmic thinking** - "every N seconds" is the wrong mindset. composition, not automation.
- **too much space** - 40-second intervals feel empty. 8-20 seconds keeps movement.
- **no harmonic interplay** - drones need to pair with melodic elements at compatible intervals.
- **abrupt endings** - background textures that cut off suddenly break the spell.

### debugging audio issues

- **exit code 183** - usually file handle limits. reduce parallel complexity.
- **corrupt samples** - check with `file samples/foo.wav`. if it's HTML, the download failed.
- **no sound** - check volume levels. 0.01 is barely audible.
- **clipping** - reduce volumes. amix doesn't normalize by default.

## workflow with plyr.fm

### upload a track

```bash
# render the piece
uv run python pieces/fading.py

# upload to plyr.fm
plyrfm upload pieces/.raw/fading.wav "fading" \
  --description "incommensurable loops in G major"
```

### check your tracks

```bash
plyrfm my-tracks
```

### update track metadata

```bash
plyrfm update-track <track_id> \
  --title "new title" \
  --description "updated description"
```

### update artist profile

```bash
plyrfm update-profile \
  --bio "ambient composer" \
  --display-name "your name"
```

### delete a track

```bash
plyrfm delete <track_id>
```

## project structure

```
pieces/
  .raw/           # rendered wav files (gitignored)
  fading.py       # eno-style incommensurable loops
  northfield.py   # deliberate placement
  warped.py       # effects demonstration

samples/          # gitignored - see SAMPLES.md for sources
  harp/
  vibraphone/
  glockenspiel/
  field/          # ambient textures (stream, wind)
```

## eno's philosophy

from the research notes:

> "classical music is like architecture... you specify every detail. generative music is like gardening... you plant a seed and you watch it grow."

> "if there is any score for the piece, it must be the operational diagram of the particular apparatus I used for its production."

the composer's role shifts from authoring specific events to designing a probabilistic system. you create the seeds (rules), prepare the soil (the system), then surrender control.

## quick reference

```python
# basic ambient piece structure
from dac import Sample, Sine, mix, phase
from pathlib import Path

duration = 120  # seconds

# 1. continuous bed
stream = Sample("samples/field/stream.wav").volume(0.04).trim(duration + 10)
drone = Sine(98.0, duration, amplitude=0.1).fade_in(10).fade_out(10).lowpass(150)

# 2. melodic elements - either placed deliberately or phased
harp = Sample("samples/harp/KSHarp_G3_mf1.wav").volume(0.4).delay(5000)

# 3. mix
tracks = [stream, drone, harp]
mix(tracks, Path("output.wav"), duration=duration)
```
