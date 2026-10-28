import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "ti-tms9918-python"))
sys.path.append(str(ROOT / "ti-sn76489-python"))

from conformance import bench  # noqa: E402
from segavdp import background, flags, sprites  # noqa: E402


class ScreenTest(unittest.TestCase):
    def test_the_active_area_is_the_printed_size(self) -> None:
        # Arrange
        printed = bench.value("screenSize")
        part = bench.painted()

        # Act
        active = sum(1 for kind in part.kinds if kind == "active")
        drawn = bench.row(part, 3)

        # Assert
        self.assertEqual((len(drawn), active), (printed["dots"], printed["lines"]))

    def test_the_tile_word_holds_the_printed_fields(self) -> None:
        # Arrange
        printed = bench.value("tileWord")

        # Act
        bits = (
            background.INDEX_HIGH.bit_length() + 8,
            bin(background.FLIP_ACROSS | background.FLIP_DOWN).count("1"),
            bin(background.SECOND_PALETTE).count("1"),
            bin(background.IN_FRONT).count("1"),
        )

        # Assert
        self.assertEqual(
            bits, (printed["index"], printed["flips"], printed["palette"], printed["priority"])
        )

    def test_the_printed_letter_c_draws_as_printed(self) -> None:
        # Arrange
        printed = bench.value("patternBytes")
        part = bench.chip()
        letter = [0xFF, 0x00, 0xFF, 0x00] + [0x00, 0x00, 0xC0, 0xC0] * 6 + [0x00, 0xFF, 0x00, 0x00]
        for offset, byte in enumerate(letter):
            part.memory.write8(printed + offset, byte)
        part.memory.write8(0x3800, 1)
        part.memory.write8(0x3801, 0)

        # Act
        rows = [
            background.cell(
                part.memory.read8, bytearray(bench.MODE4.values()), part.part, False, y, 0
            ).colours[0]
            for y in (0, 1, 7)
        ]

        # Assert
        self.assertEqual((len(letter), rows), (printed, [5, 12, 2]))

    def test_priority_covers_sprites_except_with_colour_0(self) -> None:
        # Arrange
        printed = bench.value("backgroundPriority")
        part = bench.painted()
        part.memory.write8(0x3800 + 64 + 1, 0x10)
        part.memory.write8(0x3800 + 64 + 2, 0)
        part.memory.write8(0x3800 + 64 + 3, 0x10)
        bench.sprite(part, 0, 9, 0, bench.SPRITE_TILE)
        bench.sprite(part, 1, 9, 8, bench.SPRITE_TILE)

        # Act
        shown = bench.row(part, 12)

        # Assert
        self.assertEqual(
            (bool(printed), shown[3], shown[11]),
            (True, bench.TILE_COLOUR, 16 + bench.SPRITE_COLOUR),
        )

    def test_register_2_places_the_map_where_printed(self) -> None:
        # Arrange
        printed = bench.value("nameTableBase")

        # Act
        found = {
            register: f"0x{background.name_base(bytearray([0, 0, int(register, 16)]), False):04X}"
            for register in printed
        }

        # Assert
        self.assertEqual(found, printed)


class ScrollTest(unittest.TestCase):
    def test_vertical_scroll_wraps_at_the_28th_row(self) -> None:
        # Arrange
        printed = bench.value("verticalWrap")
        held = bytearray(bench.MODE4.values())

        # Act
        found = background.source_line(held, 0, 0, printed * 8, False)

        # Assert
        self.assertEqual(found, 0)

    def test_register_9_waits_for_vertical_blanking(self) -> None:
        # Arrange
        printed = bench.value("verticalLatch")
        part = bench.painted()
        part.memory.write8(0x3800 + 64, 0)
        bench.to_line(part, 2)
        bench.program(part, {9: 8})

        # Act
        before = bench.colour_at(part, 3, 0)
        bench.to_line(part, 200)
        after = bench.colour_at(part, 3, 0)

        # Assert
        self.assertEqual((bool(printed), before, after), (True, bench.TILE_COLOUR, 0))

    def test_the_top_two_rows_hold_still(self) -> None:
        # Arrange
        printed = bench.value("topLock")
        held = bytearray(bench.MODE4.values())
        held[0] |= 0x40

        # Act
        found = [
            background.scroll_x(held, line, 0x21)
            for line in (printed["rows"] * 8 - 1, printed["rows"] * 8)
        ]

        # Assert
        self.assertEqual(found, [0, 0x21])

    def test_the_right_eight_columns_hold_still(self) -> None:
        # Arrange
        printed = bench.value("rightLock")
        held = bytearray(bench.MODE4.values())
        held[0] |= 0x80
        first = 32 - printed["columns"]

        # Act
        found = [
            background.source_line(held, 5, column, 40, False) for column in (first - 1, first)
        ]

        # Assert
        self.assertEqual(found, [45, 5])

    def test_the_left_column_shows_the_border(self) -> None:
        # Arrange
        printed = bench.value("leftBlank")
        part = bench.painted()
        bench.program(part, {0: 0x26})

        # Act
        shown = bench.row(part, 4)[:9]

        # Assert
        self.assertEqual((bool(printed), shown), (True, [bench.BACKDROP] * 8 + [bench.TILE_COLOUR]))


class SpriteTest(unittest.TestCase):
    def test_the_table_holds_the_printed_number_of_sprites(self) -> None:
        # Arrange
        printed = bench.value("spriteCount")

        # Act
        found = sprites.COUNT

        # Assert
        self.assertEqual(found, printed)

    def test_the_size_bit_picks_the_printed_heights(self) -> None:
        # Arrange
        printed = bench.value("spriteSize")
        part = bench.painted()
        bench.solid(part, bench.SPRITE_TILE + 1, bench.SPRITE_COLOUR)
        bench.sprite(part, 0, 9, 20, bench.SPRITE_TILE)

        # Act
        heights: list[int] = []
        for size in (0, 1):
            bench.program(part, {1: 0xE0 | size << 1})
            found = [bool(bench.row(part, line)[20] == 19) for line in range(10, 30)]
            heights = [*heights, sum(found)]

        # Assert
        self.assertEqual(heights, [int(printed[str(size)].split(" by ")[1]) for size in (0, 1)])

    def test_eight_sprites_show_and_a_ninth_is_flagged(self) -> None:
        # Arrange
        printed = bench.value("spritesPerLine")
        part = bench.painted()
        for number in range(printed + 1):
            bench.sprite(part, number, 9, number * 16, bench.SPRITE_TILE)

        # Act
        shown = bench.row(part, 12)

        # Assert
        self.assertEqual(
            (sum(1 for one in shown if one == 19) // 8, bool(part.read_status() & flags.OVERFLOW)),
            (printed, True),
        )

    def test_the_terminator_stops_the_search(self) -> None:
        # Arrange
        printed = bench.value("terminator")
        part = bench.painted()
        bench.sprite(part, 1, 9, 40, bench.SPRITE_TILE)
        part.memory.write8(bench.SPRITE_TABLE, int(printed, 16))

        # Act
        shown = bench.row(part, 12)

        # Assert
        self.assertEqual(shown[40], bench.TILE_COLOUR)

    def test_the_shift_bit_moves_sprites_the_printed_distance(self) -> None:
        # Arrange
        printed = bench.value("spriteShift")
        part = bench.painted()
        bench.sprite(part, 0, 9, 40, bench.SPRITE_TILE)
        bench.program(part, {0: 0x0E})

        # Act
        shown = bench.row(part, 12)

        # Assert
        self.assertEqual(shown.index(19), 40 - printed)

    def test_register_5_places_the_table_where_printed(self) -> None:
        # Arrange
        printed = bench.value("spriteTableBase")

        # Act
        found = {
            register: f"0x{(int(register, 16) & sprites.TABLE_BITS) << sprites.TABLE_SHIFT:04X}"
            for register in printed
        }

        # Assert
        self.assertEqual(found, printed)

    def test_register_6_picks_the_printed_half(self) -> None:
        # Arrange
        printed = bench.value("spritePatterns")
        part = bench.chip()
        part.memory.write8(0x2000, 0xAA)
        part.memory.write8(0x3F00, 0)
        part.memory.write8(0x3F01, 0xD0)
        part.memory.write8(0x3F80, 0)
        part.memory.write8(0x3F81, 0)

        # Act
        found = {
            register: sprites.evaluate(
                part.memory.read8,
                bytearray([0, 0, 0, 0, 0, 0xFF, int(register, 16)]),
                part.part,
                False,
                1,
            )
            .shown[0]
            .planes[0]
            for register in printed
        }

        # Assert
        self.assertEqual(found, {"0xFB": 0x00, "0xFF": 0xAA})


if __name__ == "__main__":
    unittest.main()
