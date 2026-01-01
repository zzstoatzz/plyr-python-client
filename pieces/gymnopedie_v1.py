"""Gymnopédie No. 1 (v1) - first attempt at Satie's piece using dac.

run: uv run python pieces/gymnopedie_v1.py
output: /tmp/gymnopedie_v1.wav
"""

from pathlib import Path

from dac.track import RenderConfig, Sine, Tempo, mix, note_to_freq

# --- config ---
tempo = Tempo(bpm=50, time_sig=(3, 4))
n = note_to_freq
duration = 8 * tempo.measure + 3  # 8 measures + tail

# --- tracks ---
tracks = []

# continuous F#4 pedal - the common tone between Gmaj7 and Dmaj7
pedal = (
    Sine(n("F#4"), duration, amplitude=0.04, label="pedal")
    .lowpass(400)
    .fade_in(4)
    .fade_out(4)
)
tracks.append(pedal)


# bass notes - G2 for Gmaj7, D3 for Dmaj7
def bass(note: str, beat: int) -> Sine:
    return (
        Sine(n(note), tempo.beats(2.8), amplitude=0.08, label=f"b{beat}")
        .lowpass(150)
        .fade_in(0.6)
        .fade_out(0.8)
        .delay(tempo.at_beat(beat))
    )


for m in range(8):
    beat = 1 + m * 3
    tracks.append(bass("G2" if m % 2 == 0 else "D3", beat))


# inner voices - B3/D4 for Gmaj7, A3/C#4 for Dmaj7
def voice(note: str, beat: int, amp: float = 0.035) -> Sine:
    return (
        Sine(n(note), tempo.beats(2.8), amplitude=amp, label=f"v{beat}")
        .lowpass(400)
        .fade_in(0.7)
        .fade_out(0.7)
        .delay(tempo.at_beat(beat))
    )


for m in range(8):
    beat = 1 + m * 3
    if m % 2 == 0:  # Gmaj7
        tracks.extend([voice("B3", beat), voice("D4", beat, 0.03)])
    else:  # Dmaj7
        tracks.extend([voice("A3", beat), voice("C#4", beat, 0.03)])


# melody - from MIDI: F#5, A5, G5, F#5, C#5, B4, C#5, D5, A4
def melody_note(note: str, beat: int, dur: float = 1.8) -> Sine:
    return (
        Sine(n(note), tempo.beats(dur), amplitude=0.07, label=f"m{beat}")
        .lowpass(600)
        .fade_in(0.3)
        .fade_out(0.5)
        .delay(tempo.at_beat(beat))
    )


melody = [
    ("F#5", 13),
    ("A5", 14),
    ("G5", 15),
    ("F#5", 16),
    ("C#5", 17),
    ("B4", 18),
    ("C#5", 19),
    ("D5", 20),
    ("A4", 21),
]
for note, beat in melody:
    tracks.append(melody_note(note, beat))

# --- render ---
if __name__ == "__main__":
    output = Path("/tmp/gymnopedie_v1.wav")
    config = RenderConfig(duration=duration)
    mix(tracks, output, config=config)
    print(f"rendered {output} ({len(tracks)} tracks, {duration:.1f}s)")
