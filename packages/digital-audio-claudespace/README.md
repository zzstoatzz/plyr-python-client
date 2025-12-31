# digital audio claudespace

a toolkit for making music with code.

## installation

```bash
uv add digital-audio-claudespace
```

requires `ffmpeg` on your PATH.

## usage

### quick start with Song

```python
from dac import Song, render

song = Song(bpm=120)

# add a melody using note names
song.add_track([
    "C4", "D4", "E4", "F4",
    ("G4", 2),  # note with beat count
    "-",        # rest
    ("C4 E4 G4", 2),  # chord
])

render(song.build(), "song.wav")
```

### multi-track composition

```python
from dac import Song, Noise, Layer, render

song = Song(bpm=90)

# melody
song.add_track([
    ("E4", 2), ("G4", 2), ("A4", 2), ("G4", 2),
    ("E4", 2), ("D4", 2), ("C4", 4),
], waveform="triangle", velocity=0.4)

# chord progression
song.add_track([
    ("C4 E4 G4", 4),  # C major
    ("A3 C4 E4", 4),  # A minor
    ("F3 A3 C4", 4),  # F major
    ("G3 B3 D4", 4),  # G major
], waveform="sine", velocity=0.25)

# bass
song.add_track([
    ("C2", 4), ("A2", 4), ("F2", 4), ("G2", 4),
], waveform="triangle", velocity=0.3)

render(song.build(), "composition.wav")
```

### low-level primitives

```python
from dac import Oscillator, Noise, Sequence, Layer, render

# simple tone
render(Oscillator(440).duration(2.0), "tone.wav")

# chord with partials
render(Oscillator(440).with_partials([660, 880]).duration(3.0), "chord.wav")

# pink noise with fades
render(Noise("pink").duration(10.0).fade_in(2.0).fade_out(3.0), "ambience.wav")

# layer sounds
layered = Layer([
    Noise("pink").amplitude(0.2),
    Oscillator(220).amplitude(0.5),
]).duration(5.0)
render(layered, "layered.wav")
```

## note names

standard notation: `C4` (middle C), `A4` (440 Hz), `F#5`, `Bb3`

## waveforms

- `sine` - pure tone (default)
- `square` - retro/chiptune character
- `triangle` - softer than square
- `saw` - bright, buzzy

## noise colors

- `white` - all frequencies equal
- `pink` - natural, balanced
- `brown` - deep, rumbling
- `blue` - bright, hissy
