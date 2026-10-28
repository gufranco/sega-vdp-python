import hashlib
import json
import os
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any, override
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "ti-tms9918-python"))
sys.path.append(str(ROOT / "ti-sn76489-python"))

from conformance import bench, harness, testroms  # noqa: E402
from segavdp import NTSC, timing  # noqa: E402

READY = harness.why_not() is None

ROW = 0x0200

SETUP = bytes(
    [
        0xF3,
        *(0x31, 0xF0, 0xDF),
        *(0xDB, 0xBF),
        *(0x3E, 0x06, 0xD3, 0xBF, 0x3E, 0x80, 0xD3, 0xBF),
        *(0x3E, 0x00, 0xD3, 0xBF, 0x3E, 0x81, 0xD3, 0xBF),
        *(0x3E, 0xFF, 0xD3, 0xBF, 0x3E, 0x82, 0xD3, 0xBF),
        *(0x3E, 0x00, 0xD3, 0xBF, 0x3E, 0x78, 0xD3, 0xBF),
        *(0x01, 0x00, 0x06),
        *(0xAF, 0xD3, 0xBE, 0x0B, 0x78, 0xB1, 0x20, 0xF8),
        *(0x3E, 0x00, 0xD3, 0xBF, 0x3E, 0x78, 0xD3, 0xBF),
        *(0x21, ROW & 0xFF, ROW >> 8),
        *(0x06, 0x20),
        *(0x7E, 0xD3, 0xBE, 0xAF, 0xD3, 0xBE, 0x23, 0x10, 0xF7),
        *(0x3E, 0x40, 0xD3, 0xBF, 0x3E, 0x81, 0xD3, 0xBF),
        *(0x18, 0xFE),
    ]
)

A_SCRIPT = [[4, 0xFF]]


def a_program(row: str) -> bytes:
    image = bytearray(0x8000)
    image[: len(SETUP)] = SETUP
    image[ROW : ROW + 32] = row.ljust(32).encode()
    return bytes(image)


A_PROGRAM = a_program("  MEMORY OK")


def a_run(verdict: list[str] | None = None) -> dict[str, Any]:
    return {
        "model": "315-5246",
        "script": A_SCRIPT,
        "offset": 0,
        "verdict": verdict,
        "lost": 0,
        "modes": ["mode4 192"],
    }


def a_record(folder: Path, *images: bytes, verdict: list[str] | None = None) -> Path:
    listed: list[dict[str, Any]] = [
        {
            "id": f"probe-{index}",
            "sha256": hashlib.sha256(image).hexdigest(),
            "outcome": "run",
            "runs": [a_run(verdict)],
        }
        for index, image in enumerate(images)
    ]
    listed.append({"id": "waits", "sha256": "ab" * 32, "outcome": "hosted", "needs": "x"})
    path = folder / "testroms.json"
    path.write_text(json.dumps({"cartridges": listed}))
    return path


def held_in(folder: Path, image: bytes, name: str = "probe.sms") -> Path:
    path = folder / name
    path.write_bytes(image)
    return path


def pages(lines: list[str]) -> list[int]:
    found: list[int] = []
    for page in range(3):
        rows = [line for line in lines if re.fullmatch(r"([0-9A-F]{2} ){7}[0-9A-F]{2}", line)]
        block = rows[page * 16 : page * 16 + 16]
        columns = [[int(row.split()[column], 16) for row in block] for column in range(8)]
        found = [*found, *(value for column in columns for value in column)]
    return found


class RecordedVerdictTest(unittest.TestCase):
    def test_the_test_suite_names_each_part_it_runs_on(self) -> None:
        # Arrange
        runs = testroms.entry("test-suite-0-32")["runs"]

        # Act
        named = [
            next(line for line in run["verdict"] if line.startswith("VDP?:")).split(":")[1].strip()
            for run in runs
        ]

        # Assert
        self.assertEqual(named, [run["model"] for run in runs])

    def test_and_names_the_tv_standard_of_each(self) -> None:
        # Arrange
        runs = testroms.entry("test-suite-0-32")["runs"]

        # Act
        named = [
            next(line for line in run["verdict"] if line.startswith("TV? :")).split(":")[1].strip()
            for run in runs
        ]

        # Assert
        self.assertEqual(
            named,
            ["50Hz (PAL)" if run.get("region") == "pal" else "60Hz (NTSC)" for run in runs],
        )

    def test_and_lost_no_access_on_any_of_them(self) -> None:
        # Arrange
        runs = testroms.entry("test-suite-0-32")["runs"]

        # Act
        lost = [run["lost"] for run in runs]

        # Assert
        self.assertEqual(lost, [0, 0, 0])

    def test_the_v_counter_test_prints_the_run_macdonald_printed(self) -> None:
        # Arrange
        run = testroms.entry("v-counter-test")["runs"][0]
        printed = timing.v_counter(NTSC, 192)

        # Act
        found = pages(run["verdict"])

        # Assert
        self.assertEqual(found[: len(printed)], list(printed))
        self.assertEqual(bench.unstated("vCounter"), "the runs in segavdp/timing.py")

    def test_and_lost_no_access_doing_it(self) -> None:
        # Arrange
        run = testroms.entry("v-counter-test")["runs"][0]

        # Act
        lost = run["lost"]

        # Assert
        self.assertEqual(lost, 0)

    def test_the_stimulus_cartridges_all_reach_mode_4(self) -> None:
        # Arrange
        stimulus = [
            "line-interrupt-test-1",
            "interrupt-test",
            "bg-test-0-01",
            "sprite-test",
            "color-palette-64",
            "color-and-switch-test",
            "palette-tool-1-0",
        ]

        # Act
        modes = {name: testroms.entry(name)["runs"][0]["modes"] for name in stimulus}

        # Assert
        self.assertEqual(set(map(tuple, modes.values())), {("mode4 192",)})

    def test_an_id_the_record_does_not_hold_is_refused(self) -> None:
        # Arrange
        name = "no-such-cartridge"

        # Act
        attempt = lambda: testroms.entry(name)  # noqa: E731

        # Assert
        self.assertRaisesRegex(AssertionError, "not in the record", attempt)

    def test_a_record_that_is_not_an_object_is_refused(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "testroms.json"
        where.write_text("[]")

        # Act
        attempt = lambda: testroms.record(where)  # noqa: E731

        # Assert
        self.assertRaisesRegex(AssertionError, "does not hold an object", attempt)


class ReportedTest(unittest.TestCase):
    def test_a_row_of_words_is_a_report(self) -> None:
        # Arrange
        row = " VDP?:315-5246    "

        # Act
        found = testroms.reported(row)

        # Assert
        self.assertTrue(found)

    def test_a_row_holding_an_unprintable_byte_is_not(self) -> None:
        # Arrange
        row = "OK\x01"

        # Act
        found = testroms.reported(row)

        # Assert
        self.assertFalse(found)

    def test_a_row_of_digits_is_a_report(self) -> None:
        # Arrange
        row = " 00 10 20 30 "

        # Act
        found = testroms.reported(row)

        # Assert
        self.assertTrue(found)

    def test_a_row_without_a_letter_or_a_digit_is_not(self) -> None:
        # Arrange
        row = "  -- ..  "

        # Act
        found = testroms.reported(row)

        # Assert
        self.assertFalse(found)

    def test_a_row_of_one_repeated_letter_is_a_fill_pattern_not_a_report(self) -> None:
        # Arrange
        row = "AAAAAAAA"

        # Act
        found = testroms.reported(row)

        # Assert
        self.assertFalse(found)


@unittest.skipUnless(READY, "zilog-z80-python is not checked out")
class RunTest(unittest.TestCase):
    def test_what_the_program_prints_is_read_off_the_screen_map(self) -> None:
        # Arrange
        run = a_run()

        # Act
        found = testroms.ran(A_PROGRAM, run)

        # Assert
        self.assertEqual(found, {"verdict": ["MEMORY OK"], "lost": 0, "modes": ["mode4 192"]})

    def test_a_run_with_no_offset_reads_no_screen(self) -> None:
        # Arrange
        run = {**a_run(), "offset": None}

        # Act
        found = testroms.ran(A_PROGRAM, run)

        # Assert
        self.assertEqual(found["verdict"], [])

    def test_a_script_presses_the_buttons_it_names(self) -> None:
        # Arrange
        run = {**a_run(), "script": [[1, 0xEF]]}
        seen: list[int] = []

        class Watched(harness.Board):
            @override
            def run_frames(self, count: int) -> None:
                seen.append(self.pads[0])
                super().run_frames(count)

        # Act
        testroms.ran(A_PROGRAM, run, Watched)

        # Assert
        self.assertEqual(seen, [0xEF])


class FindingImagesTest(unittest.TestCase):
    def test_an_image_inside_a_zip_inside_a_folder_is_found_by_digest(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(folder / "held.zip", "w") as archive:
            archive.writestr("inner.sms", A_PROGRAM)
        held_in(folder, b"something else", "other.sms")
        digest = hashlib.sha256(A_PROGRAM).hexdigest()

        # Act
        found = testroms.images([folder], {digest})

        # Assert
        self.assertEqual(list(found), [digest])

    def test_a_place_that_is_not_there_holds_nothing(self) -> None:
        # Arrange
        place = Path(tempfile.mkdtemp()) / "absent"

        # Act
        found = testroms.images([place], {"ab" * 32})

        # Assert
        self.assertEqual(found, {})


@unittest.skipUnless(READY, "zilog-z80-python is not checked out")
class MainTest(unittest.TestCase):
    def test_a_program_that_prints_its_recorded_verdict_exits_zero(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        record = a_record(folder, A_PROGRAM, verdict=["MEMORY OK"])

        # Act
        code = testroms.main([str(held_in(folder, A_PROGRAM))], record)

        # Assert
        self.assertEqual(code, 0)

    def test_a_verdict_that_differs_from_the_record_exits_one(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        image = a_program("  MEMORY BAD")
        record = a_record(folder, image, verdict=["MEMORY OK"])

        # Act
        code = testroms.main([str(held_in(folder, image))], record)

        # Assert
        self.assertEqual(code, 1)

    def test_writing_keeps_the_verdict_measured(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        record = a_record(folder, A_PROGRAM)

        # Act
        testroms.main(["--write", str(held_in(folder, A_PROGRAM))], record)

        # Assert
        self.assertEqual(testroms.entry("probe-0", record)["runs"][0]["verdict"], ["MEMORY OK"])

    def test_an_image_absent_while_another_is_held_is_skipped_not_failed(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        other = a_program("  OTHER")
        record = a_record(folder, A_PROGRAM, other, verdict=["MEMORY OK"])

        # Act
        code = testroms.main([str(held_in(folder, A_PROGRAM))], record)

        # Assert
        self.assertEqual(code, 0)

    def test_the_places_can_come_from_the_environment(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        record = a_record(folder, A_PROGRAM, verdict=["MEMORY OK"])
        held_in(folder, A_PROGRAM)

        # Act
        with mock.patch.dict(os.environ, {testroms.PLACES: str(folder)}):
            code = testroms.main([], record)

        # Assert
        self.assertEqual(code, 0)


class NothingToRunTest(unittest.TestCase):
    def test_with_no_image_anywhere_it_exits_two(self) -> None:
        # Arrange
        environment = {k: v for k, v in os.environ.items() if k != testroms.PLACES}

        nothing = Path(tempfile.mkdtemp()) / "absent.zip"

        # Act
        with mock.patch.dict(os.environ, environment, clear=True):
            code = testroms.main([], kept=nothing)

        # Assert
        self.assertEqual(code, testroms.NOTHING_TO_RUN)

    def test_with_nothing_named_it_reads_the_zip_kept_in_external(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        record = a_record(folder, A_PROGRAM, verdict=["MEMORY OK"])
        held_in(folder, A_PROGRAM)
        environment = {k: v for k, v in os.environ.items() if k != testroms.PLACES}

        # Act
        with mock.patch.dict(os.environ, environment, clear=True):
            code = testroms.main([], record, kept=folder)

        # Assert
        self.assertEqual(code, 0)

    def test_an_option_it_does_not_know_is_a_usage_error(self) -> None:
        # Arrange
        argv = ["--jobs"]

        # Act
        code = testroms.main(argv)

        # Assert
        self.assertEqual(code, testroms.USAGE_ERROR)


if __name__ == "__main__":
    unittest.main()
