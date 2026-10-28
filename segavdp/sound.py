from typing import override

import sn76489
from sn76489 import core, noise, tone

from segavdp.errors import NoStereo

WIDTH = 16

TOP = 1 << (WIDTH - 1)

TAP = 3

HELD_BELOW = 2

SILENT = 15

ALL_SIDES = 0xFF

LEFT_SHIFT = 4


class Generator(core.Chip):
    __slots__ = ("handheld", "stereo")

    def __init__(self, handheld: bool, seed: int) -> None:
        super().__init__(sn76489.models.lookup("sn76489an"), seed=seed)
        self.handheld = handheld
        self.stereo = ALL_SIDES
        self.periods = [0] * core.TONES
        self.steps = [SILENT] * core.CHANNELS
        self.control = 0

    @property
    def sides(self) -> tuple[tuple[bool, ...], tuple[bool, ...]]:
        right = tuple(bool(self.stereo & (1 << channel)) for channel in range(core.CHANNELS))
        left = tuple(
            bool(self.stereo & (1 << (channel + LEFT_SHIFT))) for channel in range(core.CHANNELS)
        )
        return (right, left)

    def write_stereo(self, value: int) -> None:
        if not self.handheld:
            raise NoStereo("only the Game Gear part carries the stereo register at port 06h")
        self.stereo = value & 0xFF

    @override
    def _noise(self, data: int) -> None:
        self.control = data & noise.CONTROL_MASK
        self.shift = TOP

    @override
    def _period(self) -> None:
        rose = False
        for channel in range(core.TONES):
            if self.periods[channel] < HELD_BELOW:
                self.flips[channel] = 1
                continue
            self.counters[channel] = tone.counted(self.counters[channel])
            if self.counters[channel] == 0:
                self.flips[channel] ^= 1
                self.counters[channel] = self.periods[channel]
                rose = rose or (channel == core.TONE_THREE and self.flips[channel] == 1)
        self._noise_period(rose)

    @override
    def _noise_period(self, tone_three_rose: bool) -> None:
        if noise.follows_tone_three(self.control):
            due = tone_three_rose
        else:
            self.noise_count = (self.noise_count + 1) % noise.rate(self.control)
            due = self.noise_count == 0
        if due:
            self.shift = shifted(self.shift, noise.is_white(self.control))


def shifted(register: int, white: bool) -> int:
    feedback = (register ^ (register >> TAP)) & 1 if white else register & 1
    return (register >> 1) | (TOP if feedback else 0)
