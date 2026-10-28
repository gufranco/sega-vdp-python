import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "ti-tms9918-python"))
sys.path.append(str(ROOT / "ti-sn76489-python"))

import unittest  # noqa: E402

from segavdp import (  # noqa: E402
    UnknownModelError,
    UnknownRegionError,
    models,
)


class LookupTest(unittest.TestCase):
    def test_every_part_number_names_its_own_model(self) -> None:
        # Arrange
        names = ("315-5124", "315-5246", "315-5378")

        # Act
        found = [models.lookup(name).name for name in names]

        # Assert
        self.assertEqual(found, list(names))

    def test_an_alias_reaches_the_same_model(self) -> None:
        # Arrange
        alias = " GG "

        # Act
        found = models.lookup(alias)

        # Assert
        self.assertEqual(found.name, "315-5378")

    def test_no_name_is_refused_rather_than_defaulted(self) -> None:
        # Arrange
        name = None

        # Act
        attempt = lambda: models.lookup(name)  # noqa: E731

        # Assert
        self.assertRaisesRegex(UnknownModelError, "will not choose", attempt)

    def test_an_unknown_name_lists_what_exists(self) -> None:
        # Arrange
        name = "315-5313"

        # Act
        attempt = lambda: models.lookup(name)  # noqa: E731

        # Assert
        self.assertRaisesRegex(UnknownModelError, "315-5124", attempt)


class TraitTest(unittest.TestCase):
    def test_only_the_first_part_masks_its_table_addresses(self) -> None:
        # Arrange
        catalogue = models.MODELS.values()

        # Act
        masking = [model.name for model in catalogue if model.masks]

        # Assert
        self.assertEqual(masking, ["315-5124"])

    def test_only_the_first_part_lacks_the_taller_screens(self) -> None:
        # Arrange
        catalogue = models.MODELS.values()

        # Act
        short = [model.name for model in catalogue if not model.extended]

        # Assert
        self.assertEqual(short, ["315-5124"])

    def test_the_first_part_zooms_four_sprites_across_and_the_others_eight(self) -> None:
        # Arrange
        catalogue = models.MODELS.values()

        # Act
        zoomed = {model.name: model.zoomed_across for model in catalogue}

        # Assert
        self.assertEqual(zoomed, {"315-5124": 4, "315-5246": 8, "315-5378": 8})

    def test_only_the_handheld_colours_legacy_modes_from_colour_ram(self) -> None:
        # Arrange
        catalogue = models.MODELS.values()

        # Act
        legacy = {model.name: model.legacy for model in catalogue}

        # Assert
        self.assertEqual(
            legacy,
            {
                "315-5124": models.FIXED,
                "315-5246": models.FIXED,
                "315-5378": models.CRAM,
            },
        )


class RegionTest(unittest.TestCase):
    def test_a_console_part_runs_in_either_region(self) -> None:
        # Arrange
        model = models.lookup("315-5246")

        # Act
        regions = (model.region("ntsc"), model.region("PAL"))

        # Assert
        self.assertEqual(regions, (models.NTSC, models.PAL))

    def test_no_region_is_the_first_the_part_lists(self) -> None:
        # Arrange
        model = models.lookup("315-5124")

        # Act
        region = model.region(None)

        # Assert
        self.assertEqual(region, models.NTSC)

    def test_the_handheld_refuses_a_fifty_hertz_frame(self) -> None:
        # Arrange
        model = models.lookup("315-5378")

        # Act
        attempt = lambda: model.region("pal")  # noqa: E731

        # Assert
        self.assertRaisesRegex(UnknownRegionError, "runs in ntsc", attempt)

    def test_a_model_describes_itself_by_name_and_regions(self) -> None:
        # Arrange
        model = models.lookup("315-5124")

        # Act
        shown = repr(model)

        # Assert
        self.assertEqual(shown, "<Model 315-5124, ntsc/pal>")


if __name__ == "__main__":
    unittest.main()
