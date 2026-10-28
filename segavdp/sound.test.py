import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "ti-tms9918-python"))
sys.path.append(str(ROOT / "ti-sn76489-python"))

import unittest  # noqa: E402

from segavdp import errors, sound  # noqa: E402

SEED = 0x7F

WHITE_NOISE = 0xE7

PERIODIC_FROM_TONE_THREE = 0xE3

SCRAMBLED_COUNT = 1 << 10


def generator(handheld: bool = False) -> sound.Generator:
    return sound.Generator(handheld=handheld, seed=SEED)


def rotated(register: int, white: bool, count: int) -> list[int]:
    seen: list[int] = []
    for _ in range(count):
        register = sound.shifted(register, white)
        seen = [*seen, register]
    return seen


def steps_to_return(start: int, bound: int) -> int:
    register, steps = sound.shifted(start, True), 1
    while register != start and steps <= bound:
        register, steps = sound.shifted(register, True), steps + 1
    return steps


def held_bits(chip: sound.Generator, clocks: int) -> set[tuple[int, int, int, int]]:
    seen: set[tuple[int, int, int, int]] = set()
    for _ in range(clocks):
        chip.clock()
        seen = {*seen, chip.bits}
    return seen


class PowerOnTest(unittest.TestCase):
    def test_it_starts_silent_with_every_period_at_zero(self) -> None:
        # Arrange
        chip = generator()

        # Act
        state = (chip.periods, chip.steps, chip.control)

        # Assert
        self.assertEqual(state, ([0, 0, 0], [15, 15, 15, 15], 0))


class NoiseTest(unittest.TestCase):
    def test_a_noise_write_resets_the_register_to_its_top_bit_of_sixteen(self) -> None:
        # Arrange
        chip = generator()

        # Act
        chip.write(WHITE_NOISE)

        # Assert
        self.assertEqual(chip.shift, 0x8000)

    def test_periodic_noise_rotates_sixteen_bits(self) -> None:
        # Arrange
        register = sound.TOP

        # Act
        seen = rotated(register, False, 16)

        # Assert
        self.assertEqual((seen[0], seen[-1]), (0x4000, 0x8000))

    def test_white_noise_feeds_bits_zero_and_three_into_bit_fifteen(self) -> None:
        # Arrange
        register = 0x0009

        # Act
        found = sound.shifted(register, True)

        # Assert
        self.assertEqual(found, 0x0004)

    def test_white_noise_with_one_tap_set_feeds_a_one(self) -> None:
        # Arrange
        register = 0x0008

        # Act
        found = sound.shifted(register, True)

        # Assert
        self.assertEqual(found, 0x8004)

    def test_white_noise_from_its_reset_value_repeats_after_57337_steps(self) -> None:
        # Arrange
        start = sound.TOP

        # Act
        steps = steps_to_return(start, 1 << 16)

        # Assert
        self.assertEqual(steps, 57337)


class ToneTest(unittest.TestCase):
    def test_a_period_of_zero_or_one_holds_the_output_high(self) -> None:
        # Arrange
        chip = generator()
        for value in (0x80, 0x00, 0xA1, 0x00):
            chip.write(value)

        # Act
        seen = held_bits(chip, 64)

        # Assert
        self.assertEqual({(bits[0], bits[1]) for bits in seen}, {(1, 1)})

    def test_a_held_tone_three_does_not_drive_the_noise(self) -> None:
        # Arrange
        chip = generator()
        for value in (WHITE_NOISE, 0xC0, 0x00):
            chip.write(value)
        before = chip.shift

        # Act
        held_bits(chip, 64)

        # Assert
        self.assertEqual(chip.shift, before)


class CountingTest(unittest.TestCase):
    def test_a_period_of_two_toggles_the_tone(self) -> None:
        # Arrange
        chip = generator()
        for value in (0x82, 0x00):
            chip.write(value)

        # Act
        seen = held_bits(chip, SCRAMBLED_COUNT + 8)

        # Assert
        self.assertEqual({bits[0] for bits in seen}, {0, 1})

    def test_tone_three_rising_drives_the_noise(self) -> None:
        # Arrange
        chip = generator()
        for value in (WHITE_NOISE, 0xC2, 0x00):
            chip.write(value)
        before = chip.shift

        # Act
        held_bits(chip, SCRAMBLED_COUNT + 8)

        # Assert
        self.assertNotEqual(chip.shift, before)


class NoiseRateTest(unittest.TestCase):
    def test_a_fixed_rate_shifts_the_register_once_per_thirty_two_periods(self) -> None:
        # Arrange
        chip = generator()
        chip.write(0xE4)
        before = chip.shift

        # Act
        for _ in range(32):
            chip.clock()

        # Assert
        self.assertNotEqual(chip.shift, before)


class StereoTest(unittest.TestCase):
    def test_a_console_part_has_no_stereo_register(self) -> None:
        # Arrange
        chip = generator()

        # Act
        attempt = lambda: chip.write_stereo(0xF0)  # noqa: E731

        # Assert
        self.assertRaisesRegex(errors.NoStereo, "Game Gear", attempt)

    def test_the_handheld_sends_each_channel_where_its_bits_say(self) -> None:
        # Arrange
        chip = generator(handheld=True)

        # Act
        chip.write_stereo(0x81)

        # Assert
        self.assertEqual(chip.sides, ((True, False, False, False), (False, False, False, True)))

    def test_the_handheld_comes_up_sending_every_channel_both_ways(self) -> None:
        # Arrange
        chip = generator(handheld=True)

        # Act
        sides = chip.sides

        # Assert
        self.assertEqual(sides, ((True,) * 4, (True,) * 4))


if __name__ == "__main__":
    unittest.main()
