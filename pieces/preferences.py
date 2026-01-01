"""learned preferences from user feedback.

update these as patterns emerge from feedback.
new compositions should start from these defaults.
"""

# amplitude limits
MAX_AMPLITUDE = 0.15  # user prefers quiet, soft sounds
MELODY_AMPLITUDE = 0.07  # melody should be subtle
CHORD_AMPLITUDE = 0.035  # chords should support, not dominate
BASS_AMPLITUDE = 0.08  # bass provides foundation
PEDAL_AMPLITUDE = 0.04  # pedal is background glue

# frequency filtering (lowpass cutoffs)
LOWPASS_BASS = 150  # very dark bass
LOWPASS_CHORDS = 400  # soft, fuzzed chords
LOWPASS_MELODY = 600  # melody can be brighter but still soft
LOWPASS_PEDAL = 400  # pedal blends into background

# timing (in seconds)
FADE_IN_MIN = 0.3  # no abrupt attacks
FADE_OUT_MIN = 0.5  # notes should decay naturally
NOTE_OVERLAP = 0.8  # notes should overlap slightly (legato)

# feel
DEFAULT_BPM = 50  # slow, contemplative
TIME_SIGNATURE = (3, 4)  # waltz time for Satie-style

# quality thresholds
TARGET_PEAK_DB = -12  # plenty of headroom
MIN_DYNAMIC_RANGE_DB = 6  # should have some dynamics
