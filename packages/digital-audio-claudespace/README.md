# digital audio claudespace

programmatic audio synthesis via ffmpeg.

## installation

```bash
uv add digital-audio-claudespace
```

requires `ffmpeg` on your PATH.

## usage

### synthesize and render

```python
from dac import Sine, Sample, mix
from pathlib import Path

# sine wave with effects
drone = Sine(110, duration=10, amplitude=0.3).lowpass(200).fade_in(2)

# sample with effects
harp = Sample("harp.wav").volume(0.4).delay(1000)

# render to file
mix([drone, harp], Path("output.wav"), duration=10)
```

### real-time playback

```python
from dac.live import synth, clips

# play continuous tones
synth.play("bass", 55, 0.02)
synth.play("mid", 220, 0.015)
synth.freq("bass", 60)      # change frequency
synth.vol("mid", 0.01)      # change volume
synth.stop("bass")          # stop one
synth.stopall()             # stop all

# loop audio files
clips.play("pad", "ambient.wav", 0.5)
clips.stop("pad")
```

### effects

```python
track.volume(0.5)           # amplitude
track.delay(1000)           # ms offset
track.fade_in(2)            # seconds
track.fade_out(2)
track.lowpass(500)          # hz
track.highpass(100)
track.trim(10)              # limit duration
track.pad(20)               # extend with silence
track.reverse()
track.speed(0.8)            # tempo (0.5-2.0)
track.pitch(2)              # semitones
track.pan(-0.5)             # stereo (-1 to 1)
```

