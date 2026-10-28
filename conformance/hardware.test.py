import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "ti-tms9918-python"))
sys.path.append(str(ROOT / "ti-sn76489-python"))

import segavdp  # noqa: E402
from conformance import bench  # noqa: E402
from segavdp import flags, modes, palette, timing  # noqa: E402

CODE_SHIFT = 6

LINE_ENABLE_SETUP = {0: 0x16, 1: 0x80}


def requests(part: segavdp.core.Chip, lines: int) -> list[int]:
    seen: list[int] = []
    for _ in range(lines * bench.DOTS):
        part.clock()
        if part.interrupt:
            seen = [*seen, part.line]
            part.read_status()
    return seen


def from_frame_start(part: segavdp.core.Chip) -> segavdp.core.Chip:
    bench.to_line(part, 200)
    bench.to_line(part, 0)
    part.read_status()
    return part


def spaced_writes(gap_t_states: int, count: int, display_on: bool) -> segavdp.core.Chip:
    part: segavdp.core.Chip = bench.program(
        bench.chip("315-5124"), {1: 0x40 if display_on else 0x00}
    )
    bench.to_line(part, 10)
    part.write_control(0x00)
    part.write_control(0x40)
    for number in range(count):
        part.write_data(number + 1)
        for _ in range(gap_t_states * 3):
            part.tick()
    return part


class PortTest(unittest.TestCase):
    def test_the_part_has_the_printed_number_of_registers(self) -> None:
        # Arrange
        printed = bench.value("registerCount")
        part = bench.chip()

        # Act
        bench.program(part, {printed: 0x55, printed - 1: 0x66})

        # Assert
        self.assertEqual((len(part.registers), part.registers[printed - 1]), (printed, 0x66))

    def test_the_four_codes_do_what_the_manual_names(self) -> None:
        # Arrange
        printed = bench.value("commandCodes")
        part = bench.chip()
        part.memory.write8(0x0010, 0x77)

        # Act
        done: list[int] = []
        for code in sorted(printed, key=int):
            part.write_control(0x10)
            part.write_control(int(code) << CODE_SHIFT)
            done = [*done, part.code]
        bench.to_line(part, 5)

        # Assert
        self.assertEqual((done, part.buffer, part.registers[0]), ([0, 1, 2, 3], 0x77, 0x10))

    def test_the_printed_ports_reach_data_and_control(self) -> None:
        # Arrange
        printed = bench.value("ports")

        # Act
        found = [segavdp.port(int(printed[name], 16)) for name in ("data", "control")]

        # Assert
        self.assertEqual(found, [segavdp.core.DATA, segavdp.core.CONTROL])

    def test_data_writes_step_through_memory_and_colour_ram(self) -> None:
        # Arrange
        printed = bench.value("autoIncrement")
        part = bench.chip()
        part.write_control(0x04)
        part.write_control(0xC0)

        # Act
        for value in (0x11, 0x22):
            part.write_data(value)
            for _ in range(segavdp.core.ACTIVE_LEAD):
                part.tick()

        # Assert
        self.assertEqual((printed, part.cram.entry(4), part.cram.entry(5)), (True, 0x11, 0x22))

    def test_a_read_setup_followed_by_writes_still_writes(self) -> None:
        # Arrange
        printed = bench.value("readsOrWrites")
        part = bench.chip()
        part.write_control(0x00)
        part.write_control(0x00)
        bench.to_line(part, 3)

        # Act
        part.write_data(0x42)
        bench.to_line(part, 6)

        # Assert
        self.assertEqual((bool(printed), part.memory.read8(0x0001)), (True, 0x42))


class AccessTest(unittest.TestCase):
    def test_accesses_at_the_printed_blanking_rate_all_land(self) -> None:
        # Arrange
        printed = bench.value("accessBound")["blankingTStates"]

        # Act
        part = spaced_writes(printed, 4, display_on=False)

        # Assert
        self.assertEqual((part.lost, [part.memory.read8(at) for at in range(4)]), (0, [1, 2, 3, 4]))

    def test_accesses_at_the_printed_active_rate_all_land(self) -> None:
        # Arrange
        printed = bench.value("accessBound")["activeTStates"]

        # Act
        part = spaced_writes(printed, 4, display_on=True)

        # Assert
        self.assertEqual((part.lost, [part.memory.read8(at) for at in range(4)]), (0, [1, 2, 3, 4]))

    def test_faster_accesses_lose_one(self) -> None:
        # Arrange
        printed = bench.value("accessBound")["activeTStates"]
        landing = bench.unstated("accessLead")["activeTicks"] // 3

        # Act
        part = spaced_writes(landing - 1, 2, display_on=True)

        # Assert
        self.assertEqual((landing < printed, part.lost), (True, 1))


class StatusTest(unittest.TestCase):
    def test_the_status_bits_sit_where_printed(self) -> None:
        # Arrange
        printed = bench.value("statusBits")

        # Act
        held = {int(bit): name for bit, name in printed.items()}

        # Assert
        self.assertEqual(
            (1 << 7, 1 << 6, 1 << 5),
            (flags.FRAME, flags.OVERFLOW, flags.COLLISION),
        )
        self.assertEqual(sorted(held), [5, 6, 7])

    def test_reading_the_status_releases_the_request(self) -> None:
        # Arrange
        printed = bench.value("statusClears")
        part = bench.program(bench.chip(), {1: 0xA0})
        bench.to_line(part, 0xC2)
        raised = part.interrupt

        # Act
        part.read_status()

        # Assert
        self.assertEqual((bool(printed), raised, part.interrupt), (True, True, False))

    def test_each_enable_gates_its_own_request(self) -> None:
        # Arrange
        printed = bench.value("interruptEnables")
        part = bench.program(bench.chip(), {0: 0x06, 1: 0x80, 10: 0x00})
        from_frame_start(part)
        bench.to_line(part, 3)
        line_only = part.interrupt

        # Act
        bench.program(part, {0: 0x16})

        # Assert
        self.assertEqual((printed["line"], line_only, part.interrupt), ("R0 bit 4", False, True))


class LineCounterTest(unittest.TestCase):
    def test_the_request_comes_as_raster_line_r10_plus_one_begins_counting_from_one(self) -> None:
        # Arrange
        printed = bench.value("lineCounter")
        part = bench.program(bench.chip(), {**LINE_ENABLE_SETUP, 10: 94})
        from_frame_start(part)

        # Act
        found = requests(part, 193)

        # Assert
        self.assertEqual(
            (printed["interruptOnLine"], found),
            ("R10 + 1, counting raster lines from one", [94, 189]),
        )

    def test_a_new_value_takes_effect_one_request_later(self) -> None:
        # Arrange
        printed = bench.value("lineCounterDelay")
        part = bench.program(bench.chip(), {**LINE_ENABLE_SETUP, 10: 20})
        from_frame_start(part)
        bench.program(part, {10: 150})

        # Act
        found = requests(part, 193)

        # Assert
        self.assertEqual((printed, found), ("one interrupt", [20, 171]))


class ColourTest(unittest.TestCase):
    def test_colour_ram_holds_the_printed_entries_and_bits(self) -> None:
        # Arrange
        printed = bench.value("colourRam")
        part = bench.chip("315-5124")

        # Act
        part.cram.write(printed["entries"] + 1, 0xFF, False)

        # Assert
        self.assertEqual(
            (len(part.cram.entries()), part.cram.entry(1)),
            (printed["entries"], (1 << printed["bits"]) - 1),
        )

    def test_each_component_has_the_four_printed_intensities(self) -> None:
        # Arrange
        printed = bench.value("intensities")

        # Act
        found = [palette.levels(step, handheld=False)[0] for step in range(4)]

        # Assert
        self.assertEqual(found, printed)

    def test_sprites_draw_from_the_second_sixteen(self) -> None:
        # Arrange
        printed = bench.value("spritePalette")
        part = bench.painted()
        bench.sprite(part, 0, 9, 20, bench.SPRITE_TILE)

        # Act
        found = bench.colour_at(part, 12, 20)

        # Assert
        self.assertEqual(found, printed + bench.SPRITE_COLOUR)

    def test_the_border_draws_from_the_second_sixteen(self) -> None:
        # Arrange
        printed = bench.value("borderPalette")
        part = bench.painted()
        part.cram.write(printed + 3, 0x2B, False)
        bench.program(part, {7: 0x03})

        # Act
        found = bench.colour_at(part, 5, 260)

        # Assert
        self.assertEqual(found, 0x2B)


class CounterTest(unittest.TestCase):
    def test_the_counter_ports_are_the_printed_ones(self) -> None:
        # Arrange
        printed = bench.value("gunCounters")

        # Act
        found = [segavdp.port(int(printed[name], 16)) for name in ("vertical", "horizontal")]

        # Assert
        self.assertEqual(found, [segavdp.core.V_COUNTER, segavdp.core.H_COUNTER])


class UnstatedTest(unittest.TestCase):
    def test_every_unstated_value_is_marked_unverified(self) -> None:
        # Arrange
        held = bench.UNSTATED

        # Act
        verified = [name for name, entry in held.items() if entry["verified"] is not False]

        # Assert
        self.assertEqual(verified, [])

    def test_every_unstated_value_says_how_to_settle_it(self) -> None:
        # Arrange
        held = bench.UNSTATED

        # Act
        silent = [name for name, entry in held.items() if not entry["howToSettleIt"].strip()]

        # Assert
        self.assertEqual(silent, [])

    def test_the_frame_line_is_the_one_the_record_names(self) -> None:
        # Arrange
        named = bench.unstated("frameLine")

        # Act
        found = {str(height): f"0x{timing.frame_line(height):02X}" for height in timing.HEIGHTS}

        # Assert
        self.assertEqual(found, named)

    def test_the_line_event_is_the_one_the_record_names(self) -> None:
        # Arrange
        named = bench.unstated("lineEvent")

        # Act
        found = {
            "dot": timing.LINE_EVENT,
            "hCounter": f"0x{timing.h_counter(timing.LINE_EVENT):02X}",
        }

        # Assert
        self.assertEqual(found, named)

    def test_the_access_lead_is_the_one_the_record_names(self) -> None:
        # Arrange
        named = bench.unstated("accessLead")

        # Act
        found = {"activeTicks": segavdp.core.ACTIVE_LEAD, "blankingTicks": segavdp.core.BLANK_LEAD}

        # Assert
        self.assertEqual(found, named)

    def test_the_legacy_palette_is_the_one_the_record_names(self) -> None:
        # Arrange
        named = bench.unstated("legacyPalette")

        # Act
        found = [f"0x{value:02X}" for value in palette.LEGACY]

        # Assert
        self.assertEqual(found, named)

    def test_the_tall_screens_are_the_mode_bits_the_record_names(self) -> None:
        # Arrange
        named = bench.unstated("tallScreens")
        model = segavdp.models.lookup("315-5246")

        # Act
        found = {
            str(modes.decode(model, 0x06, 0x10).height): "M2 and M1",
            str(modes.decode(model, 0x06, 0x08).height): "M2 and M3",
        }

        # Assert
        self.assertEqual(found, named)


if __name__ == "__main__":
    unittest.main()
