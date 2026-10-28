import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "ti-tms9918-python"))
sys.path.append(str(ROOT / "ti-sn76489-python"))

from conformance import bench  # noqa: E402


class RecordTest(unittest.TestCase):
    def test_a_value_is_read_from_the_fact_it_names(self) -> None:
        # Arrange
        name = "registerCount"

        # Act
        held = bench.value(name)

        # Assert
        self.assertEqual(held, 11)

    def test_an_unstated_value_is_read_from_its_own_block(self) -> None:
        # Arrange
        name = "frameLine"

        # Act
        held = bench.unstated(name)

        # Assert
        self.assertEqual(held["192"], "0xC1")


class PartTest(unittest.TestCase):
    def test_a_bench_part_comes_up_reset_with_its_flags_read(self) -> None:
        # Arrange
        model = "315-5124"

        # Act
        part = bench.chip(model)

        # Assert
        self.assertEqual(
            (part.model, part.line, part.dot, part.latch, part.status), (model, 0, 0, False, 0)
        )

    def test_a_program_writes_each_register_it_names(self) -> None:
        # Arrange
        part = bench.chip()

        # Act
        bench.program(part, {7: 0x05, 8: 0x10})

        # Assert
        self.assertEqual((part.registers[7], part.registers[8]), (0x05, 0x10))

    def test_running_to_a_line_stops_on_its_first_dot(self) -> None:
        # Arrange
        part = bench.chip()

        # Act
        bench.to_line(part, 7)

        # Assert
        self.assertEqual((part.line, part.dot), (7, 0))

    def test_a_painted_screen_draws_its_tile_colour(self) -> None:
        # Arrange
        part = bench.painted()

        # Act
        found = bench.colour_at(part, 4, 40)

        # Assert
        self.assertEqual(found, bench.TILE_COLOUR)

    def test_a_placed_sprite_lands_in_the_table(self) -> None:
        # Arrange
        part = bench.painted()

        # Act
        bench.sprite(part, 3, 20, 30, 2)

        # Assert
        self.assertEqual([part.memory.read8(at) for at in (0x3F03, 0x3F86, 0x3F87)], [20, 30, 2])

    def test_a_row_is_the_256_active_dots_of_a_line(self) -> None:
        # Arrange
        part = bench.painted()

        # Act
        found = bench.row(part, 2)

        # Assert
        self.assertEqual(found, [bench.TILE_COLOUR] * 256)


if __name__ == "__main__":
    unittest.main()
