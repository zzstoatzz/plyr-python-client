# autonomous iteration plan

how to iterate on compositions with minimal user input.

## 1. self-assessment tooling

build analyzers that examine wav files programmatically:

```python
# dac/analyze.py
def analyze(path: Path) -> dict:
    """return metrics I can reason about."""
    return {
        "peak_db": ...,           # clipping risk
        "rms_db": ...,            # overall loudness
        "dynamic_range_db": ...,  # difference between loud/quiet
        "frequency_balance": {    # is it muddy? thin?
            "low": ...,           # <200Hz
            "mid": ...,           # 200-2000Hz
            "high": ...           # >2000Hz
        },
        "silence_pct": ...,       # dead space
        "duration": ...,
    }
```

this lets me catch obvious problems (clipping, no dynamics, all bass) without asking.

## 2. feedback taxonomy

categorize feedback so I know what to adjust:

| feedback | likely cause | adjustment |
|----------|--------------|------------|
| "harsh" | high frequencies | lower lowpass cutoff |
| "muddy" | too much bass | raise highpass, reduce bass amp |
| "thin" | not enough low end | lower lowpass, add bass |
| "choppy" | short notes, fast fades | longer notes, slower fades |
| "mechanical" | exact timing | add micro-timing variation |
| "too loud" | amplitude too high | reduce amplitudes |
| "buried melody" | poor balance | raise melody amp, lower chords |

when user gives feedback, I map it to adjustments and encode in the piece.

## 3. preference config

accumulate learned preferences:

```python
# pieces/preferences.py
PREFERENCES = {
    "max_peak_db": -3,          # headroom
    "lowpass_melody": 600,      # user likes soft melody
    "lowpass_bass": 150,        # user likes dark bass
    "fade_in_min": 0.3,         # user doesn't like abrupt attacks
    "fade_out_min": 0.5,
    "amplitude_ceiling": 0.15,  # user likes quiet
}
```

new compositions start from these defaults.

## 4. specific questions protocol

when I need feedback, ask about ONE thing:

**good questions:**
- "is the melody audible over the chords?"
- "does the bass feel present or missing?"
- "are the note attacks too abrupt or natural?"
- "rate the overall brightness: too dark / good / too harsh?"

**bad questions:**
- "does it sound good?" (too vague)
- "what should I change?" (puts burden on user)
- "is the mix balanced and the timing right?" (multiple things)

## 5. iteration loop

```
1. make change to piece
2. render wav
3. run self-analysis
   - if clipping: fix automatically
   - if outside preferences: fix automatically
4. if analysis passes:
   - play for user
   - ask ONE specific question
5. incorporate feedback:
   - adjust piece
   - update preferences if pattern emerges
6. repeat
```

## 6. version control

each iteration is a new file or git commit:
- `gymnopedie_v1.py` - first attempt
- `gymnopedie_v2.py` - softer, slower (from feedback)
- `gymnopedie_v3.py` - added second phrase

can diff versions to see what changed.

## next steps

1. [ ] build `dac/analyze.py` with basic wav analysis
2. [ ] create `pieces/preferences.py` with current learned values
3. [ ] iterate on gymnopedie using this process
