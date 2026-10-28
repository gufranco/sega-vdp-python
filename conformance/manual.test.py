import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import manual as _manual  # noqa: E402

manual: Any = _manual


class FlattenTest(unittest.TestCase):
    def test_only_letters_and_digits_survive_and_in_lower_case(self) -> None:
        # Arrange
        laid_out = "Dur-\n  ing the active display, (Register 2) *400(hex)."

        # Act
        found = manual.flatten(laid_out)

        # Assert
        self.assertEqual(found, "duringtheactivedisplayregister2400hex")


class TextTest(unittest.TestCase):
    def test_a_document_that_is_not_there_reads_as_nothing(self) -> None:
        # Arrange
        absent = Path(tempfile.mkdtemp()) / "absent.pdf"

        # Act
        found = manual.text(absent)

        # Assert
        self.assertEqual(found, "")

    def test_without_the_converter_a_document_reads_as_nothing(self) -> None:
        # Arrange
        present = Path(tempfile.mkdtemp()) / "present.pdf"
        present.write_bytes(b"%PDF-1.2")
        held = manual.shutil.which
        manual.shutil.which = lambda _name: None
        self.addCleanup(setattr, manual.shutil, "which", held)

        # Act
        found = manual.text(present)

        # Assert
        self.assertEqual(found, "")

    def test_a_converted_document_reads_as_its_flattened_output(self) -> None:
        # Arrange
        present = Path(tempfile.mkdtemp()) / "present.pdf"
        present.write_bytes(b"%PDF-1.2")
        which, run = manual.shutil.which, manual.subprocess.run
        manual.shutil.which = lambda _name: "/usr/bin/pdftotext"
        manual.subprocess.run = lambda *_args, **_kwargs: manual.subprocess.CompletedProcess(
            args=[], returncode=0, stdout="VIDEO   DISPLAY\n  PROCESSORS"
        )
        self.addCleanup(setattr, manual.shutil, "which", which)
        self.addCleanup(setattr, manual.subprocess, "run", run)

        # Act
        found = manual.text(present)

        # Assert
        self.assertEqual(found, "videodisplayprocessors")

    @unittest.skipUnless(manual.HELD.is_file() and shutil.which("pdftotext"), "no manual here")
    def test_the_pinned_manual_reads_as_its_flattened_text(self) -> None:  # pragma: no cover
        # Arrange
        heading = "softwarereferencemanualforthesegamarkiiiconsole"

        # Act
        found = manual.text()

        # Assert
        self.assertIn(heading, found)


class PlainTest(unittest.TestCase):
    def test_a_plain_file_that_is_not_there_reads_as_nothing(self) -> None:
        # Arrange
        absent = Path(tempfile.mkdtemp()) / "absent.txt"

        # Act
        found = manual.plain(absent)

        # Assert
        self.assertEqual(found, "")

    def test_a_text_file_reads_as_its_flattened_body(self) -> None:
        # Arrange
        present = Path(tempfile.mkdtemp()) / "notes.txt"
        present.write_text(" $7E = V counter (read)\n")

        # Act
        found = manual.plain(present)

        # Assert
        self.assertEqual(found, "7evcounterread")

    def test_a_page_loses_its_tags_and_entities(self) -> None:
        # Arrange
        present = Path(tempfile.mkdtemp()) / "page.html"
        present.write_text("<p>bits 0 &amp; 3 <b>($0009)</b></p>")

        # Act
        found = manual.plain(present)

        # Assert
        self.assertEqual(found, "bits030009")


class HeldTest(unittest.TestCase):
    def test_a_folder_holding_nothing_yields_no_document(self) -> None:
        # Arrange
        empty = Path(tempfile.mkdtemp())

        # Act
        found = manual.held(empty)

        # Assert
        self.assertEqual(found, {})

    def test_a_folder_holding_one_document_yields_that_one_by_name(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp())
        name = manual.FILES[1]
        (where / name).parent.mkdir(parents=True)
        (where / name).write_text("Display timing")

        # Act
        found = manual.held(where)

        # Assert
        self.assertEqual(found, {name: "displaytiming"})


if __name__ == "__main__":
    unittest.main()
