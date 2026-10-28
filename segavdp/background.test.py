import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "ti-tms9918-python"))
sys.path.append(str(ROOT / "ti-sn76489-python"))

import unittest  # noqa: E402

from tms9918.memory import Vram  # noqa: E402

from segavdp import background, models  # noqa: E402

FIRST = models.lookup("315-5124")

SECOND = models.lookup("315-5246")

LETTER_C = bytes([0xFF, 0x00, 0xFF, 0x00] + [0x00, 0x00, 0xC0, 0xC0] * 6 + [0x00, 0xFF, 0x00, 0x00])


def registers(**changed: int) -> bytearray:
    held = bytearray([0x06, 0xE0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFB, 0x00, 0x00, 0x00, 0xFF])
    for name, value in changed.items():
        held[int(name.removeprefix("r"))] = value
    return held


def screen(word: int, at: int = 0x3800, pattern: int = 1) -> Vram:
    memory = Vram(fill=0)
    memory.write8(at, word & 0xFF)
    memory.write8(at + 1, word >> 8)
    for offset, byte in enumerate(LETTER_C):
        memory.write8(pattern * 32 + offset, byte)
    return memory


class CellTest(unittest.TestCase):
    def test_the_manual_s_letter_c_reads_colour_5_across_its_first_row(self) -> None:
        # Arrange
        memory = screen(0x0001)

        # Act
        found = background.cell(memory.read8, registers(), FIRST, False, 0, 0)

        # Assert
        self.assertEqual(found.colours, (5,) * 8)

    def test_its_second_row_is_colour_12_then_colour_0(self) -> None:
        # Arrange
        memory = screen(0x0001)

        # Act
        found = background.cell(memory.read8, registers(), FIRST, False, 1, 0)

        # Assert
        self.assertEqual(found.colours, (12, 12, 0, 0, 0, 0, 0, 0))

    def test_its_last_row_is_colour_2(self) -> None:
        # Arrange
        memory = screen(0x0001)

        # Act
        found = background.cell(memory.read8, registers(), FIRST, False, 7, 0)

        # Assert
        self.assertEqual(found.colours, (2,) * 8)

    def test_a_horizontal_flip_reverses_the_row(self) -> None:
        # Arrange
        memory = screen(0x0201)

        # Act
        found = background.cell(memory.read8, registers(), FIRST, False, 1, 0)

        # Assert
        self.assertEqual(found.colours, (0, 0, 0, 0, 0, 0, 12, 12))

    def test_a_vertical_flip_reads_the_rows_bottom_up(self) -> None:
        # Arrange
        memory = screen(0x0401)

        # Act
        found = background.cell(memory.read8, registers(), FIRST, False, 0, 0)

        # Assert
        self.assertEqual(found.colours, (2,) * 8)

    def test_the_palette_bit_moves_the_colours_to_the_second_sixteen(self) -> None:
        # Arrange
        memory = screen(0x0801)

        # Act
        found = background.cell(memory.read8, registers(), FIRST, False, 0, 0)

        # Assert
        self.assertEqual(found.colours, (21,) * 8)

    def test_the_priority_bit_puts_only_non_zero_colours_in_front(self) -> None:
        # Arrange
        memory = screen(0x1001)

        # Act
        found = background.cell(memory.read8, registers(), FIRST, False, 1, 0)

        # Assert
        self.assertEqual(found.front, (True, True, False, False, False, False, False, False))

    def test_the_ninth_index_bit_reaches_the_second_256_patterns(self) -> None:
        # Arrange
        memory = screen(0x0100, pattern=0x100)

        # Act
        found = background.cell(memory.read8, registers(), FIRST, False, 0, 0)

        # Assert
        self.assertEqual(found.colours, (5,) * 8)


class NameTableTest(unittest.TestCase):
    def test_register_2_picks_one_of_eight_2k_tables(self) -> None:
        # Arrange
        values = (0xFF, 0xF1, 0xF7)

        # Act
        found = [background.name_base(registers(r2=value), False) for value in values]

        # Assert
        self.assertEqual(found, [0x3800, 0x0000, 0x1800])

    def test_a_tall_screen_starts_its_table_at_a_0700_offset(self) -> None:
        # Arrange
        values = (0xF3, 0xF7, 0xFB, 0xFF)

        # Act
        found = [background.name_base(registers(r2=value), True) for value in values]

        # Assert
        self.assertEqual(found, [0x0700, 0x1700, 0x2700, 0x3700])

    def test_the_first_part_masks_row_bit_4_with_register_2_bit_0(self) -> None:
        # Arrange
        memory = screen(0x0001, at=0x3800)
        memory.write8(0x3800 + 16 * 64, 0x00)

        # Act
        found = background.cell(memory.read8, registers(r2=0xFE), FIRST, False, 16 * 8, 0)

        # Assert
        self.assertEqual(found.colours, (5,) * 8)

    def test_the_second_part_ignores_register_2_bit_0(self) -> None:
        # Arrange
        memory = screen(0x0001, at=0x3800)

        # Act
        found = background.cell(memory.read8, registers(r2=0xFE), SECOND, False, 16 * 8, 0)

        # Assert
        self.assertEqual(found.colours, (0,) * 8)


class ScrollTest(unittest.TestCase):
    def test_fine_scroll_leaves_its_first_dots_without_a_column(self) -> None:
        # Arrange
        scroll = 0x03

        # Act
        found = [background.place(dot, scroll) for dot in (0, 2, 3, 10, 11)]

        # Assert
        self.assertEqual(found, [None, None, (0, 0), (0, 7), (1, 0)])

    def test_the_coarse_scroll_is_subtracted_from_the_column(self) -> None:
        # Arrange
        scroll = 0x1D << 3

        # Act
        found = background.name_column(0, scroll)

        # Assert
        self.assertEqual(found, 3)

    def test_the_top_two_rows_ignore_horizontal_scroll_when_locked(self) -> None:
        # Arrange
        held = registers(r0=0x46)

        # Act
        found = [background.scroll_x(held, line, 0x55) for line in (15, 16)]

        # Assert
        self.assertEqual(found, [0, 0x55])

    def test_the_right_eight_columns_ignore_vertical_scroll_when_locked(self) -> None:
        # Arrange
        held = registers(r0=0x86)

        # Act
        found = [background.source_line(held, 10, column, 0x30, False) for column in (23, 24)]

        # Assert
        self.assertEqual(found, [0x3A, 10])

    def test_a_short_screen_wraps_its_rows_at_224(self) -> None:
        # Arrange
        held = registers()

        # Act
        found = background.source_line(held, 100, 0, 200, False)

        # Assert
        self.assertEqual(found, 76)

    def test_a_tall_screen_wraps_its_rows_at_256(self) -> None:
        # Arrange
        held = registers()

        # Act
        found = background.source_line(held, 100, 0, 200, True)

        # Assert
        self.assertEqual(found, 44)


if __name__ == "__main__":
    unittest.main()
