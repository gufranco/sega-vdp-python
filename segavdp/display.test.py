import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "ti-tms9918-python"))
sys.path.append(str(ROOT / "ti-sn76489-python"))

import unittest  # noqa: E402

from tms9918 import geometry  # noqa: E402
from tms9918.memory import Vram  # noqa: E402

from segavdp import core, flags, models, palette, timing  # noqa: E402

SEED = 0x5246

MODE4_SETUP = (0x06, 0xE0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFB, 0x00, 0x00, 0x00, 0xFF)

NAME_TABLE = 0x3800

SPRITE_TABLE = 0x3F00

TILE_COLOUR = 5

SPRITE_COLOUR = 3

BACKDROP = 0x30


def register(chip: core.Chip, number: int, value: int) -> None:
    chip.write_control(value)
    chip.write_control(0x80 | number)


def solid_pattern(memory: Vram, index: int, colour: int) -> None:
    for row in range(8):
        for plane in range(4):
            memory.write8(index * 32 + row * 4 + plane, 0xFF if colour >> plane & 1 else 0)


def painted(model: str = "315-5246", handheld_mode: bool | None = None) -> core.Chip:
    chip = core.Chip(models.lookup(model), Vram(fill=0), seed=SEED, handheld_mode=handheld_mode)
    chip.reset()
    chip.read_status()
    for number, value in enumerate(MODE4_SETUP):
        register(chip, number, value)
    for address in range(SPRITE_TABLE, SPRITE_TABLE + 64):
        chip.memory.write8(address, 0xD0)
    for entry in range(32):
        chip.cram.write(entry, entry, handheld_mode=False)
    chip.cram.write(16, BACKDROP, handheld_mode=False)
    solid_pattern(chip.memory, 1, TILE_COLOUR)
    solid_pattern(chip.memory, 2, SPRITE_COLOUR)
    for cell in range(32 * 28):
        chip.memory.write8(NAME_TABLE + cell * 2, 1)
    run_to_line(chip, 1)
    run_to_line(chip, 0)
    return chip


def place_sprite(chip: core.Chip, number: int, y: int, x: int, index: int) -> None:
    chip.memory.write8(SPRITE_TABLE + number, y)
    chip.memory.write8(SPRITE_TABLE + 0x80 + number * 2, x)
    chip.memory.write8(SPRITE_TABLE + 0x81 + number * 2, index)


def run_to_line(chip: core.Chip, line: int) -> None:
    budget = timing.lines_of(chip.region) * geometry.DOTS
    while (chip.line, chip.dot) != (line, 0) and budget:
        chip.clock()
        budget -= 1


def colour_at(chip: core.Chip, line: int, dot: int) -> int | None:
    run_to_line(chip, line)
    for _ in range(dot + 1):
        chip.clock()
    return chip.colour


def row_of(chip: core.Chip, line: int) -> list[int | None]:
    run_to_line(chip, line)
    seen: list[int | None] = []
    for _ in range(256):
        chip.clock()
        seen = [*seen, chip.colour]
    return seen


class BackgroundTest(unittest.TestCase):
    def test_an_active_dot_shows_its_tile_colour_from_colour_ram(self) -> None:
        # Arrange
        chip = painted()

        # Act
        found = colour_at(chip, 2, 40)

        # Assert
        self.assertEqual(found, TILE_COLOUR)

    def test_a_border_dot_shows_the_backdrop_from_the_sprite_palette(self) -> None:
        # Arrange
        chip = painted()

        # Act
        found = colour_at(chip, 2, 260)

        # Assert
        self.assertEqual(found, BACKDROP)

    def test_a_sync_dot_has_no_colour(self) -> None:
        # Arrange
        chip = painted()

        # Act
        found = colour_at(chip, 2, 290)

        # Assert
        self.assertEqual((found, chip.shown), (None, geometry.SYNC))

    def test_a_blanked_display_shows_the_backdrop_where_the_picture_was(self) -> None:
        # Arrange
        chip = painted()
        register(chip, 1, 0xA0)

        # Act
        found = colour_at(chip, 2, 40)

        # Assert
        self.assertEqual(found, BACKDROP)

    def test_the_left_column_blank_covers_the_first_eight_dots(self) -> None:
        # Arrange
        chip = painted()
        register(chip, 0, 0x26)

        # Act
        found = row_of(chip, 3)[:10]

        # Assert
        self.assertEqual(found, [BACKDROP] * 8 + [TILE_COLOUR] * 2)

    def test_fine_scroll_shows_the_backdrop_before_the_first_column(self) -> None:
        # Arrange
        chip = painted()
        register(chip, 8, 0x03)

        # Act
        found = row_of(chip, 3)[:5]

        # Assert
        self.assertEqual(found, [BACKDROP] * 3 + [TILE_COLOUR] * 2)

    def test_a_colour_ram_write_shows_from_the_next_dot_it_lands_on(self) -> None:
        # Arrange
        chip = painted()
        run_to_line(chip, 4)
        chip.cram.write(TILE_COLOUR, 0x2A, handheld_mode=False)

        # Act
        chip.clock()

        # Assert
        self.assertEqual(chip.colour, 0x2A)

    def test_vertical_scroll_written_mid_frame_waits_for_the_next(self) -> None:
        # Arrange
        chip = painted()
        chip.memory.write8(NAME_TABLE + 64, 0)
        run_to_line(chip, 2)
        register(chip, 9, 8)

        # Act
        found = colour_at(chip, 3, 0)

        # Assert
        self.assertEqual(found, TILE_COLOUR)


class SpriteTest(unittest.TestCase):
    def test_a_sprite_shows_over_a_low_priority_tile(self) -> None:
        # Arrange
        chip = painted()
        place_sprite(chip, 0, 9, 20, 2)

        # Act
        found = row_of(chip, 12)[20:29]

        # Assert
        self.assertEqual(found, [16 + SPRITE_COLOUR] * 8 + [TILE_COLOUR])

    def test_a_high_priority_tile_covers_the_sprite(self) -> None:
        # Arrange
        chip = painted()
        chip.memory.write8(NAME_TABLE + 64 + 1, 0x10)
        place_sprite(chip, 0, 9, 0, 2)

        # Act
        found = colour_at(chip, 12, 3)

        # Assert
        self.assertEqual(found, TILE_COLOUR)

    def test_two_overlapping_sprites_raise_the_collision_flag(self) -> None:
        # Arrange
        chip = painted()
        place_sprite(chip, 0, 9, 20, 2)
        place_sprite(chip, 1, 9, 24, 2)

        # Act
        row_of(chip, 12)

        # Assert
        self.assertEqual(chip.read_status() & flags.COLLISION, flags.COLLISION)

    def test_nine_sprites_on_a_line_raise_the_overflow_flag(self) -> None:
        # Arrange
        chip = painted()
        for number in range(9):
            place_sprite(chip, number, 9, number * 8, 2)

        # Act
        run_to_line(chip, 12)

        # Assert
        self.assertEqual(chip.read_status() & flags.OVERFLOW, flags.OVERFLOW)


class LegacyTest(unittest.TestCase):
    def test_a_console_part_colours_legacy_modes_from_its_fixed_table(self) -> None:
        # Arrange
        chip = painted()
        register(chip, 0, 0x00)
        register(chip, 7, 0x0F)
        for address in range(0x3800, 0x3B00):
            chip.memory.write8(address, 0)

        # Act
        found = colour_at(chip, 5, 40)

        # Assert
        self.assertEqual(found, palette.LEGACY[15])

    def test_the_handheld_colours_legacy_modes_from_the_second_sixteen(self) -> None:
        # Arrange
        chip = painted("315-5378", handheld_mode=False)
        register(chip, 0, 0x00)
        register(chip, 7, 0x0F)
        for address in range(0x3800, 0x3B00):
            chip.memory.write8(address, 0)

        # Act
        found = colour_at(chip, 5, 40)

        # Assert
        self.assertEqual(found, chip.cram.entry(31))

    def test_a_legacy_sprite_overlaps_count_as_a_collision(self) -> None:
        # Arrange
        chip = painted()
        register(chip, 0, 0x00)
        register(chip, 5, 0x7E)
        register(chip, 6, 0x00)
        for plane, x in ((0, 20), (1, 24)):
            for offset, value in enumerate((9, x, 0, 0x0F)):
                chip.memory.write8(0x3F00 + plane * 4 + offset, value)
        chip.memory.write8(0x3F08, 0xD0)
        for row in range(8):
            chip.memory.write8(row, 0xFF)

        # Act
        row_of(chip, 12)

        # Assert
        self.assertEqual(chip.read_status() & flags.COLLISION, flags.COLLISION)

    def test_the_invalid_text_mode_shows_only_the_backdrop(self) -> None:
        # Arrange
        chip = painted()
        register(chip, 0, 0x04)
        register(chip, 1, 0xF0)

        # Act
        found = colour_at(chip, 5, 40)

        # Assert
        self.assertEqual(found, BACKDROP)

    def test_a_mode_switched_mid_line_draws_the_rest_of_the_line_in_the_new_mode(self) -> None:
        # Arrange
        chip = painted()
        run_to_line(chip, 10)
        for _ in range(20):
            chip.clock()
        register(chip, 0, 0x00)

        # Act
        run_to_line(chip, 11)

        # Assert
        self.assertEqual((chip.line, chip.dot, chip.mode.name), (11, 0, "graphics1"))


if __name__ == "__main__":
    unittest.main()
