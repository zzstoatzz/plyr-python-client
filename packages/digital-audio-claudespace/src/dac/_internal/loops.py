"""internal loop parsing utilities."""

from typing import Literal

from pydantic import BaseModel

Waveform = Literal["sine", "square", "triangle", "saw"]


class Loop(BaseModel):
    """a single phasing loop definition."""

    note: str
    loop_length: float
    note_duration: float
    amplitude: float | None = None
    start_offset: float | None = None
    attack: float | None = None
    release: float | None = None
    wave: Waveform | None = None

    def resolve(
        self,
        *,
        default_amp: float,
        default_attack: float,
        default_release: float,
        default_wave: Waveform,
    ) -> "ResolvedLoop":
        """apply defaults and return a fully resolved loop."""
        return ResolvedLoop(
            note=self.note,
            loop_length=self.loop_length,
            note_duration=self.note_duration,
            amplitude=self.amplitude if self.amplitude is not None else default_amp,
            start_offset=self.start_offset,
            attack=self.attack if self.attack is not None else default_attack,
            release=self.release if self.release is not None else default_release,
            wave=self.wave if self.wave is not None else default_wave,
        )


class ResolvedLoop(BaseModel):
    """loop with all defaults applied - ready for rendering."""

    note: str
    loop_length: float
    note_duration: float
    amplitude: float
    start_offset: float | None
    attack: float
    release: float
    wave: Waveform

    model_config = {"frozen": True}
