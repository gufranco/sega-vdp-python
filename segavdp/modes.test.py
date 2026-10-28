import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "ti-tms9918-python"))
sys.path.append(str(ROOT / "ti-sn76489-python"))

import unittest  # noqa: E402

from segavdp import models, modes  # noqa: E402

FIRST = models.lookup("315-5124")

SECOND = models.lookup("315-5246")

HANDHELD = models.lookup("315-5378")

MODE4 = 0x04

M2 = 0x02

M1 = 0x10

M3 = 0x08


class ModeTest(unittest.TestCase):
    def test_without_the_fourth_bit_the_part_names_the_legacy_mode(self) -> None:
        # Arrange
        r0, r1 = M2, 0x00

        # Act
        found = modes.decode(SECOND, r0, r1)

        # Assert
        self.assertEqual((found.name, found.height), ("graphics2", 192))

    def test_the_fourth_bit_alone_is_mode_4_at_192_lines(self) -> None:
        # Arrange
        r0, r1 = MODE4, 0x00

        # Act
        found = modes.decode(FIRST, r0, r1)

        # Assert
        self.assertEqual((found.name, found.height, found.tall), (modes.MODE4, 192, False))

    def test_the_second_part_reads_m1_with_m2_as_224_lines(self) -> None:
        # Arrange
        r0, r1 = MODE4 | M2, M1

        # Act
        found = modes.decode(SECOND, r0, r1)

        # Assert
        self.assertEqual((found.name, found.height, found.tall), (modes.MODE4, 224, True))

    def test_the_second_part_reads_m3_with_m2_as_240_lines(self) -> None:
        # Arrange
        r0, r1 = MODE4 | M2, M3

        # Act
        found = modes.decode(SECOND, r0, r1)

        # Assert
        self.assertEqual((found.name, found.height, found.tall), (modes.MODE4, 240, True))

    def test_m1_and_m3_together_with_m2_fall_back_to_192_lines(self) -> None:
        # Arrange
        r0, r1 = MODE4 | M2, M1 | M3

        # Act
        found = modes.decode(SECOND, r0, r1)

        # Assert
        self.assertEqual((found.name, found.height, found.tall), (modes.MODE4, 192, False))

    def test_m3_without_m2_has_no_effect(self) -> None:
        # Arrange
        r0, r1 = MODE4, M3

        # Act
        found = modes.decode(SECOND, r0, r1)

        # Assert
        self.assertEqual((found.name, found.height), (modes.MODE4, 192))

    def test_m1_without_m2_is_the_invalid_text_mode_on_every_part(self) -> None:
        # Arrange
        r0, r1 = MODE4, M1

        # Act
        found = [modes.decode(model, r0, r1).name for model in (FIRST, SECOND, HANDHELD)]

        # Assert
        self.assertEqual(found, [modes.INVALID_TEXT] * 3)

    def test_the_first_part_reads_m1_with_m2_as_the_invalid_text_mode(self) -> None:
        # Arrange
        r0, r1 = MODE4 | M2, M1

        # Act
        found = modes.decode(FIRST, r0, r1)

        # Assert
        self.assertEqual(found.name, modes.INVALID_TEXT)

    def test_the_handheld_in_its_own_mode_keeps_192_lines_but_the_tall_tables(self) -> None:
        # Arrange
        r0, r1 = MODE4 | M2, M1

        # Act
        found = modes.decode(HANDHELD, r0, r1, handheld_mode=True)

        # Assert
        self.assertEqual((found.height, found.tall), (192, True))

    def test_the_handheld_in_master_system_mode_shows_the_taller_screen(self) -> None:
        # Arrange
        r0, r1 = MODE4 | M2, M1

        # Act
        found = modes.decode(HANDHELD, r0, r1, handheld_mode=False)

        # Assert
        self.assertEqual((found.height, found.tall), (224, True))

    def test_a_mode_names_itself(self) -> None:
        # Arrange
        found = modes.decode(SECOND, MODE4 | M2, M1)

        # Act
        shown = repr(found)

        # Assert
        self.assertEqual(shown, "<Mode mode4, 224 lines>")


if __name__ == "__main__":
    unittest.main()
