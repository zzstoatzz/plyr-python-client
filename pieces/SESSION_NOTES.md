# session notes: gymnopedie v2 percussion

## what happened

1. tried synthesizing drums with sine waves - sounded terrible
2. found VCSL samples (CC0) - kick, snare, hi-hat
3. initial integration: drums way too loud, overpowering
4. discovered `volume()` method expected linear values, not dB - my negative dB values were ignored
5. added `volume_db()` method to Track class
6. iterated on levels: -48dB (inaudible) -> -18dB (still quiet) -> -6dB (audible) -> -2dB kick (better)
7. filtering: lower lowpass = more muted/lo-fi character

## bugs fixed

- `volume()` now has `volume_db()` companion for dB values
- added `limit_db` to RenderConfig with limiter in mix chain
- mix function has `volume=0.18` reduction to prevent clipping with many tracks

## current drum settings

- kick: -2dB, lowpass 60Hz (sub-bass thump)
- snare: -6dB, lowpass 250Hz (muted brush)
- hi-hat: -8dB, lowpass 1200Hz (muted tick)

## problems

1. **no ears** - I cannot hear what I produce. analyze.py only gives peak/mean dB.
2. **no spectral analysis** - can't tell if drums are balanced vs melody
3. **no A/B comparison** - can't systematically compare versions
4. **no version history** - should log each iteration with settings + feedback

## order-of-magnitude improvements needed

### 1. spectral analysis tool
```python
def analyze_bands(path: Path) -> dict:
    """per-frequency-band loudness."""
    return {
        "sub": ...,      # <60Hz (kick body)
        "bass": ...,     # 60-200Hz
        "low_mid": ...,  # 200-500Hz
        "mid": ...,      # 500-2kHz (melody lives here)
        "high_mid": ..., # 2k-6kHz
        "high": ...,     # >6kHz (hi-hat, air)
    }
```

### 2. comparison tool
```python
def compare(a: Path, b: Path) -> dict:
    """what changed between versions."""
    return {
        "peak_diff": ...,
        "band_diffs": {...},
        "perceived_loudness_diff": ...,
    }
```

### 3. mix validation
```python
def validate_mix(path: Path, preferences: dict) -> list[str]:
    """check against learned preferences, return issues."""
```

### 4. iteration logger
- auto-save each render with timestamp
- log settings used
- log analysis results
- log user feedback when given

### 5. better effects
- compression (control dynamics)
- saturation (warmth)
- proper EQ curves (not just lowpass)
- reverb sends (space)

### 6. stereo field
- currently mono
- panning could add width and separation

### 7. humanization
- micro-timing variation (not machine-perfect)
- velocity/amplitude variation per hit
