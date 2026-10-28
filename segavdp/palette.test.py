import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "ti-tms9918-python"))
sys.path.append(str(ROOT / "ti-sn76489-python"))

import random  # noqa: E402
import unittest  # noqa: E402

from segavdp import palette  # noqa: E402

SEED = 0x5246


class ConsoleColourRamTest(unittest.TestCase):
    def test_a_write_keeps_six_bits_at_its_entry(self) -> None:
        # Arrange
        ram = palette.ColourRam(handheld=False, seed=SEED)

        # Act
        ram.write(0x23, 0xFF, handheld_mode=False)

        # Assert
        self.assertEqual(ram.entry(0x03), 0x3F)

    def test_the_address_wraps_at_32_entries(self) -> None:
        # Arrange
        ram = palette.ColourRam(handheld=False, seed=SEED)

        # Act
        ram.write(0x3F, 0x15, handheld_mode=False)

        # Assert
        self.assertEqual(ram.entry(0x1F), 0x15)

    def test_it_comes_up_scrambled_and_reproducibly_so(self) -> None:
        # Arrange
        seeds = (SEED, SEED)

        # Act
        built = [palette.ColourRam(handheld=False, seed=seed).entries() for seed in seeds]

        # Assert
        self.assertEqual(built[0], built[1])
        self.assertNotEqual(set(built[0]), {0})


class HandheldColourRamTest(unittest.TestCase):
    def test_an_even_write_only_latches(self) -> None:
        # Arrange
        ram = palette.ColourRam(handheld=True, seed=SEED)
        before = ram.entries()

        # Act
        ram.write(0x00, 0xFF, handheld_mode=True)

        # Assert
        self.assertEqual(ram.entries(), before)

    def test_an_odd_write_stores_the_latch_and_its_own_byte(self) -> None:
        # Arrange
        ram = palette.ColourRam(handheld=True, seed=SEED)
        ram.write(0x00, 0xFF, handheld_mode=True)

        # Act
        ram.write(0x21, 0x0F, handheld_mode=True)

        # Assert
        self.assertEqual(ram.entry(0x10), 0x0FFF)

    def test_one_latch_can_fill_two_entries(self) -> None:
        # Arrange
        ram = palette.ColourRam(handheld=True, seed=SEED)
        ram.write(0x02, 0x34, handheld_mode=True)

        # Act
        ram.write(0x05, 0x02, handheld_mode=True)
        ram.write(0x07, 0x01, handheld_mode=True)

        # Assert
        self.assertEqual((ram.entry(2), ram.entry(3)), (0x0234, 0x0134))

    def test_a_master_system_write_widens_each_component_to_four_bits(self) -> None:
        # Arrange
        ram = palette.ColourRam(handheld=True, seed=SEED)

        # Act
        ram.write(0x01, 0b00_11_10_01, handheld_mode=False)

        # Assert
        self.assertEqual(ram.entry(0x01), 0xFA5)


class LevelTest(unittest.TestCase):
    def test_a_console_component_is_one_of_four_thirds(self) -> None:
        # Arrange
        value = 0b00_11_10_01

        # Act
        found = palette.levels(value, handheld=False)

        # Assert
        self.assertEqual(found, (1 / 3, 2 / 3, 1.0))

    def test_a_handheld_component_is_one_of_sixteen_fifteenths(self) -> None:
        # Arrange
        value = 0xF50

        # Act
        found = palette.levels(value, handheld=True)

        # Assert
        self.assertEqual(found, (0.0, 5 / 15, 1.0))


class LegacyTest(unittest.TestCase):
    def test_the_fixed_table_has_one_six_bit_value_per_colour(self) -> None:
        # Arrange
        table = palette.LEGACY

        # Act
        widths = {value <= 0x3F for value in table}

        # Assert
        self.assertEqual((len(table), widths), (16, {True}))

    def test_legacy_white_is_full_white(self) -> None:
        # Arrange
        white = 15

        # Act
        found = palette.LEGACY[white]

        # Assert
        self.assertEqual(found, 0x3F)

    def test_a_random_entry_survives_a_round_trip(self) -> None:
        # Arrange
        chosen = random.Random(SEED)
        ram = palette.ColourRam(handheld=False, seed=SEED)
        entry, value = chosen.randrange(32), chosen.randrange(64)

        # Act
        ram.write(entry, value, handheld_mode=False)

        # Assert
        self.assertEqual(ram.entry(entry), value)


if __name__ == "__main__":
    unittest.main()
