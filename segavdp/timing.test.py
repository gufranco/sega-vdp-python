import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "ti-tms9918-python"))
sys.path.append(str(ROOT / "ti-sn76489-python"))

import itertools  # noqa: E402
import unittest  # noqa: E402

from tms9918 import geometry  # noqa: E402

from segavdp import (  # noqa: E402
    NTSC,
    PAL,
    timing,
)


def runs(values: tuple[int, ...]) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    for value in values:
        if found and value == found[-1][1] + 1:
            found = [*found[:-1], (found[-1][0], value)]
        else:
            found = [*found, (value, value)]
    return found


class FrameTest(unittest.TestCase):
    def test_an_ntsc_frame_is_262_lines_and_a_pal_frame_313(self) -> None:
        # Arrange
        regions = (NTSC, PAL)

        # Act
        found = [timing.lines_of(region) for region in regions]

        # Assert
        self.assertEqual(found, [262, 313])

    def test_every_layout_fills_its_frame_exactly(self) -> None:
        # Arrange
        cases = [(region, height) for region in (NTSC, PAL) for height in timing.HEIGHTS]

        # Act
        sizes = {case: len(timing.layout(*case)) for case in cases}

        # Assert
        self.assertEqual(sizes, {case: timing.lines_of(case[0]) for case in cases})

    def test_the_ntsc_192_line_frame_is_laid_out_as_printed(self) -> None:
        # Arrange
        kinds = timing.layout(NTSC, 192)

        # Act
        counted = [(kind, sum(1 for _ in group)) for kind, group in itertools.groupby(kinds)]

        # Assert
        self.assertEqual(
            counted,
            [
                (geometry.ACTIVE, 192),
                (geometry.BORDER, 24),
                (geometry.BLANKING, 3),
                (geometry.SYNC, 3),
                (geometry.BLANKING, 13),
                (geometry.BORDER, 27),
            ],
        )

    def test_the_pal_240_line_frame_keeps_a_24_line_bottom_border(self) -> None:
        # Arrange
        kinds = timing.layout(PAL, 240)

        # Act
        border = kinds[240:264]

        # Assert
        self.assertEqual(set(border), {geometry.BORDER})


class VerticalCounterTest(unittest.TestCase):
    def test_the_ntsc_192_line_counter_jumps_back_after_da(self) -> None:
        # Arrange
        counted = timing.v_counter(NTSC, 192)

        # Act
        found = runs(counted)

        # Assert
        self.assertEqual(found, [(0x00, 0xDA), (0xD5, 0xFF)])

    def test_the_ntsc_224_line_counter_jumps_back_after_ea(self) -> None:
        # Arrange
        counted = timing.v_counter(NTSC, 224)

        # Act
        found = runs(counted)

        # Assert
        self.assertEqual(found, [(0x00, 0xEA), (0xE5, 0xFF)])

    def test_the_pal_counters_match_each_printed_run(self) -> None:
        # Arrange
        heights = timing.HEIGHTS

        # Act
        found = {height: runs(timing.v_counter(PAL, height)) for height in heights}

        # Assert
        self.assertEqual(
            found,
            {
                192: [(0x00, 0xF2), (0xBA, 0xFF)],
                224: [(0x00, 0xFF), (0x00, 0x02), (0xCA, 0xFF)],
                240: [(0x00, 0xFF), (0x00, 0x0A), (0xD2, 0xFF)],
            },
        )

    def test_the_ntsc_240_line_counter_wraps_and_stops_one_short_of_the_print(self) -> None:
        # Arrange
        counted = timing.v_counter(NTSC, 240)

        # Act
        found = runs(counted)

        # Assert
        self.assertEqual(found, [(0x00, 0xFF), (0x00, 0x05)])

    def test_every_counter_has_one_value_per_line(self) -> None:
        # Arrange
        cases = [(region, height) for region in (NTSC, PAL) for height in timing.HEIGHTS]

        # Act
        sizes = {case: len(timing.v_counter(*case)) for case in cases}

        # Assert
        self.assertEqual(sizes, {case: timing.lines_of(case[0]) for case in cases})


class HorizontalCounterTest(unittest.TestCase):
    def test_the_first_active_dot_reads_zero(self) -> None:
        # Arrange
        dot = 0

        # Act
        found = timing.h_counter(dot)

        # Assert
        self.assertEqual(found, 0x00)

    def test_the_counter_reads_93_before_its_jump_and_e9_after(self) -> None:
        # Arrange
        dots = (timing.H_JUMP - 1, timing.H_JUMP)

        # Act
        found = tuple(timing.h_counter(dot) for dot in dots)

        # Assert
        self.assertEqual(found, (0x93, 0xE9))

    def test_the_last_dot_of_a_line_reads_ff(self) -> None:
        # Arrange
        dot = geometry.DOTS - 1

        # Act
        found = timing.h_counter(dot)

        # Assert
        self.assertEqual(found, 0xFF)

    def test_each_value_is_held_for_two_dots(self) -> None:
        # Arrange
        dots = range(geometry.DOTS)

        # Act
        values = [timing.h_counter(dot) for dot in dots]

        # Assert
        self.assertEqual(len(set(values)), geometry.DOTS // 2)


class EventTest(unittest.TestCase):
    def test_the_frame_flag_rises_on_the_line_after_the_first_border_line(self) -> None:
        # Arrange
        heights = timing.HEIGHTS

        # Act
        found = [timing.frame_line(height) for height in heights]

        # Assert
        self.assertEqual(found, [0xC1, 0xE1, 0xF1])

    def test_the_line_counter_counts_down_through_the_first_border_line(self) -> None:
        # Arrange
        lines = (0, 192, 193, 261)

        # Act
        found = [timing.counts_down(line, 192) for line in lines]

        # Assert
        self.assertEqual(found, [True, True, False, False])


if __name__ == "__main__":
    unittest.main()
