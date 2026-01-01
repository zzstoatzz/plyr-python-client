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

this approach gives full control. you're writing a score.

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

## gymnopédie-style voice leading

satie's gymnopédies use I→IV motion with common tones and stepwise voice leading. here's how to achieve this with dac.

### the technique

use a **continuous pedal tone** as a common tone between chords. the pedal stays static while inner voices move stepwise.

example: Dmaj7 ↔ Gmaj7 with F#4 pedal

```
Gmaj7: G2 (bass) - B3 - D4 - F#4 (pedal)
Dmaj7: D3 (bass) - A3 - C#4 - F#4 (pedal)

voice leading:
  bass:  G2 → D3  (fifth motion)
  mid:   B3 → A3  (step down)
  upper: D4 → C#4 (step down)
  top:   F#4      (static pedal)
```

the F#4 works as the 7th of Gmaj7 and 3rd of Dmaj7 - a perfect pivot.

### code pattern

```python
from dac.track import Sine, mix, phase
from pathlib import Path

duration = 90
cycle = 16  # seconds per chord

# continuous pedal - stays for entire duration
pedal = Sine(370, duration, amplitude=0.1, label='pedal').lowpass(600)

# Gmaj7 voices (8 seconds each, repeating every 16s)
g_bass = Sine(98, 8, amplitude=0.15, label='gb').lowpass(300).fade_in(2).fade_out(2)
g_b3 = Sine(247, 8, amplitude=0.08, label='gb3').lowpass(500).fade_in(2).fade_out(2)
g_d4 = Sine(294, 8, amplitude=0.06, label='gd4').lowpass(500).fade_in(2).fade_out(2)

# Dmaj7 voices - delayed by 8s to alternate
d_bass = Sine(147, 8, amplitude=0.15, label='db').lowpass(300).fade_in(2).fade_out(2).delay(8000)
d_a3 = Sine(220, 8, amplitude=0.08, label='da3').lowpass(500).fade_in(2).fade_out(2).delay(8000)
d_c4 = Sine(277, 8, amplitude=0.06, label='dc4').lowpass(500).fade_in(2).fade_out(2).delay(8000)

# phase out copies for full duration
g_voices = (phase(g_bass, interval=cycle, duration=duration) +
            phase(g_b3, interval=cycle, duration=duration) +
            phase(g_d4, interval=cycle, duration=duration))
d_voices = (phase(d_bass, interval=cycle, duration=duration) +
            phase(d_a3, interval=cycle, duration=duration) +
            phase(d_c4, interval=cycle, duration=duration))

all_tracks = [pedal] + g_voices + d_voices
mix(all_tracks, Path('/tmp/gymno.wav'), duration=duration)
```

## lessons learned

### what works

- **continuous textures** - stream/wind/drone as a bed. keeps the piece alive during sparse moments.
- **harmonic compatibility** - stick to one key. G major works well: G, A, B, D, E (+F# for lydian color).
- **volume hierarchy** - background (0.05-0.1), drones (0.1-0.2), foreground (0.2-0.4).
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
# render the piece (output to /tmp or your preferred location)
uv run python my_piece.py

# upload to plyr.fm
plyrfm upload /tmp/output.wav "piece name" \
  --description "description here"
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
src/dac/
  __init__.py     # exports
  track.py        # Track, Sine, Sample, phase(), mix()
  chords.py       # chord construction helpers
  live.py         # real-time synth and clips playback
  _internal/      # note/frequency utilities

samples/          # gitignored - see SAMPLES.md for sources
  harp/
  vibraphone/
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
