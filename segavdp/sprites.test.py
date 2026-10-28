import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "ti-tms9918-python"))
sys.path.append(str(ROOT / "ti-sn76489-python"))

import unittest  # noqa: E402

from tms9918.memory import Vram  # noqa: E402

from segavdp import models, sprites  # noqa: E402

FIRST = models.lookup("315-5124")

SECOND = models.lookup("315-5246")

TABLE = 0x3F00

SOLID = 1

EMPTY = 3

OFF_SCREEN = 0xE0


def registers(**changed: int) -> bytearray:
    held = bytearray([0x06, 0xE0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFB, 0x00, 0x00, 0x00, 0xFF])
    for name, value in changed.items():
        held[int(name.removeprefix("r"))] = value
    return held


def table(*placed: tuple[int, int, int]) -> Vram:
    memory = Vram(fill=0)
    for number in range(64):
        memory.write8(TABLE + number, OFF_SCREEN)
    for number, (y, x, index) in enumerate(placed):
        memory.write8(TABLE + number, y)
        memory.write8(TABLE + 0x80 + number * 2, x)
        memory.write8(TABLE + 0x81 + number * 2, index)
    memory.write8(TABLE + len(placed), 0xD0)
    for row in range(16):
        memory.write8(SOLID * 32 + (row % 8) * 4, 0xFF)
        memory.write8(2 * 32 + (row % 8) * 4 + 1, 0x80)
    return memory


def shown(memory: Vram, held: bytearray, line: int, model: models.Model = SECOND) -> sprites.Drawn:
    found = sprites.evaluate(memory.read8, held, model, False, line)
    return sprites.draw(found.shown)


class EvaluateTest(unittest.TestCase):
    def test_a_y_of_zero_places_a_sprite_on_line_one(self) -> None:
        # Arrange
        memory = table((0, 10, SOLID))

        # Act
        found = [
            len(sprites.evaluate(memory.read8, registers(), SECOND, False, line).shown)
            for line in (0, 1, 8, 9)
        ]

        # Assert
        self.assertEqual(found, [0, 1, 1, 0])

    def test_the_terminator_ends_the_table_on_a_short_screen(self) -> None:
        # Arrange
        memory = table((0, 10, SOLID))
        memory.write8(TABLE + 2, 0)

        # Act
        found = sprites.evaluate(memory.read8, registers(), SECOND, False, 1)

        # Assert
        self.assertEqual(len(found.shown), 1)

    def test_a_tall_screen_ignores_the_terminator(self) -> None:
        # Arrange
        memory = table((0, 10, SOLID))
        memory.write8(TABLE + 2, 0)

        # Act
        found = sprites.evaluate(memory.read8, registers(), SECOND, True, 1)

        # Assert
        self.assertEqual(len(found.shown), 2)

    def test_eight_sprites_are_shown_and_a_ninth_raises_overflow(self) -> None:
        # Arrange
        memory = table(*[(0, 8 * number, SOLID) for number in range(9)])

        # Act
        found = sprites.evaluate(memory.read8, registers(), SECOND, False, 1)

        # Assert
        self.assertEqual((len(found.shown), found.overflow), (8, True))

    def test_eight_sprites_alone_raise_no_overflow(self) -> None:
        # Arrange
        memory = table(*[(0, 8 * number, SOLID) for number in range(8)])

        # Act
        found = sprites.evaluate(memory.read8, registers(), SECOND, False, 1)

        # Assert
        self.assertEqual((len(found.shown), found.overflow), (8, False))

    def test_a_sprite_near_the_bottom_of_the_counter_wraps_to_the_top(self) -> None:
        # Arrange
        memory = table((0xFC, 10, SOLID))

        # Act
        found = [
            len(sprites.evaluate(memory.read8, registers(), SECOND, False, line).shown)
            for line in (0, 4, 5)
        ]

        # Assert
        self.assertEqual(found, [1, 1, 0])

    def test_tall_sprites_are_sixteen_lines_and_read_the_next_pattern_below(self) -> None:
        # Arrange
        memory = table((0, 10, 2))
        memory.write8(3 * 32 + 4, 0x0F)

        # Act
        found = sprites.evaluate(memory.read8, registers(r1=0xE2), SECOND, False, 10)

        # Assert
        self.assertEqual(found.shown[0].planes, (0x0F, 0, 0, 0))

    def test_register_6_bit_2_moves_sprites_to_the_second_256_patterns(self) -> None:
        # Arrange
        memory = table((0, 10, 0))
        memory.write8(0x2000, 0xAA)

        # Act
        found = sprites.evaluate(memory.read8, registers(r6=0xFF), SECOND, False, 1)

        # Assert
        self.assertEqual(found.shown[0].planes[0], 0xAA)

    def test_the_first_part_masks_the_index_with_register_6_low_bits(self) -> None:
        # Arrange
        memory = table((0, 10, 0x41))
        memory.write8(0x2000 + 32, 0x77)

        # Act
        found = sprites.evaluate(memory.read8, registers(r6=0xFC), FIRST, False, 1)

        # Assert
        self.assertEqual(found.shown[0].planes[0], 0xFF)

    def test_the_first_part_reads_positions_from_the_low_half_when_register_5_bit_0_is_clear(
        self,
    ) -> None:
        # Arrange
        memory = table((0, 10, SOLID))
        memory.write8(TABLE + 0, 0)
        memory.write8(TABLE + 1, 0)

        # Act
        found = sprites.evaluate(memory.read8, registers(r5=0xFE), FIRST, False, 1)

        # Assert
        self.assertEqual(found.shown[0].x, 0)

    def test_the_shift_bit_moves_every_sprite_eight_dots_left(self) -> None:
        # Arrange
        memory = table((0, 10, SOLID))

        # Act
        found = sprites.evaluate(memory.read8, registers(r0=0x0E), SECOND, False, 1)

        # Assert
        self.assertEqual(found.shown[0].x, 2)


class ZoomTest(unittest.TestCase):
    def test_zoom_doubles_the_height(self) -> None:
        # Arrange
        memory = table((0, 10, SOLID))

        # Act
        found = [
            len(sprites.evaluate(memory.read8, registers(r1=0xE1), SECOND, False, line).shown)
            for line in (16, 17)
        ]

        # Assert
        self.assertEqual(found, [1, 0])

    def test_the_second_part_widens_all_eight(self) -> None:
        # Arrange
        memory = table(*[(0, 16 * number, SOLID) for number in range(8)])

        # Act
        found = sprites.evaluate(memory.read8, registers(r1=0xE1), SECOND, False, 1)

        # Assert
        self.assertEqual([one.wide for one in found.shown], [True] * 8)

    def test_the_first_part_widens_only_the_first_four(self) -> None:
        # Arrange
        memory = table(*[(0, 16 * number, SOLID) for number in range(8)])

        # Act
        found = sprites.evaluate(memory.read8, registers(r1=0xE1), FIRST, False, 1)

        # Assert
        self.assertEqual([one.wide for one in found.shown], [True] * 4 + [False] * 4)


class DrawTest(unittest.TestCase):
    def test_a_sprite_covers_eight_dots_from_its_x(self) -> None:
        # Arrange
        memory = table((0, 10, SOLID))

        # Act
        drawn = shown(memory, registers(), 1)

        # Assert
        self.assertEqual(
            [dot for dot, colour in enumerate(drawn.colours) if colour], list(range(10, 18))
        )

    def test_a_wide_sprite_covers_sixteen(self) -> None:
        # Arrange
        memory = table((0, 10, SOLID))

        # Act
        drawn = shown(memory, registers(r1=0xE1), 1)

        # Assert
        self.assertEqual(
            [dot for dot, colour in enumerate(drawn.colours) if colour], list(range(10, 26))
        )

    def test_a_sprite_past_the_right_edge_does_not_wrap(self) -> None:
        # Arrange
        memory = table((0, 252, SOLID))

        # Act
        drawn = shown(memory, registers(), 1)

        # Assert
        self.assertEqual(
            [dot for dot, colour in enumerate(drawn.colours) if colour], [252, 253, 254, 255]
        )

    def test_the_lower_numbered_sprite_wins_an_overlap_and_the_collision_is_noted(self) -> None:
        # Arrange
        memory = table((0, 10, SOLID), (0, 14, 2))

        # Act
        drawn = shown(memory, registers(), 1)

        # Assert
        self.assertEqual((drawn.colours[14], drawn.collision), (1, 14))

    def test_a_transparent_overlap_is_no_collision(self) -> None:
        # Arrange
        memory = table((0, 10, SOLID), (0, 11, EMPTY))

        # Act
        drawn = shown(memory, registers(), 1)

        # Assert
        self.assertEqual((drawn.colours[11], drawn.collision), (1, None))


if __name__ == "__main__":
    unittest.main()
