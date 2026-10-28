import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "ti-tms9918-python"))
sys.path.append(str(ROOT / "ti-sn76489-python"))

import unittest  # noqa: E402

from tms9918 import geometry  # noqa: E402
from tms9918.memory import Vram  # noqa: E402

from segavdp import core, flags, models, timing  # noqa: E402

SEED = 0x5124

BLANK_LEAD = core.BLANK_LEAD


def fresh(model: str = "315-5246", region: str | None = None) -> core.Chip:
    chip = core.Chip(models.lookup(model), Vram(fill=0), seed=SEED, region=region)
    chip.reset()
    chip.read_status()
    return chip


def register(chip: core.Chip, number: int, value: int) -> None:
    chip.write_control(value)
    chip.write_control(0x80 | number)


def settle(chip: core.Chip) -> None:
    for _ in range(core.ACTIVE_LEAD):
        chip.tick()


def run_to_line(chip: core.Chip, line: int) -> None:
    budget = timing.lines_of(chip.region) * geometry.DOTS
    while (chip.line, chip.dot) != (line, 0) and budget:
        chip.clock()
        budget -= 1


class PortTest(unittest.TestCase):
    def test_a_register_write_lands_from_the_command_pair(self) -> None:
        # Arrange
        chip = fresh()

        # Act
        register(chip, 7, 0x0A)

        # Assert
        self.assertEqual(chip.registers[7], 0x0A)

    def test_register_numbers_past_ten_change_nothing(self) -> None:
        # Arrange
        chip = fresh()
        before = bytes(chip.registers)

        # Act
        register(chip, 11, 0x55)

        # Assert
        self.assertEqual(bytes(chip.registers), before)

    def test_the_first_byte_updates_the_address_at_once(self) -> None:
        # Arrange
        chip = fresh()

        # Act
        chip.write_control(0x34)

        # Assert
        self.assertEqual(chip.address & 0xFF, 0x34)

    def test_a_status_read_clears_the_half_written_pair(self) -> None:
        # Arrange
        chip = fresh()
        chip.write_control(0x00)

        # Act
        chip.read_status()

        # Assert
        self.assertFalse(chip.latch)

    def test_a_vram_write_lands_after_its_lead(self) -> None:
        # Arrange
        chip = fresh()
        chip.write_control(0x00)
        chip.write_control(0x40 | 0x10)

        # Act
        chip.write_data(0x99)
        settle(chip)

        # Assert
        self.assertEqual(chip.memory.read8(0x1000), 0x99)

    def test_a_data_write_also_loads_the_read_buffer(self) -> None:
        # Arrange
        chip = fresh()
        chip.write_control(0x00)
        chip.write_control(0x40)

        # Act
        chip.write_data(0x5A)

        # Assert
        self.assertEqual(chip.read_data(), 0x5A)

    def test_a_read_setup_prefetches_the_byte_it_names(self) -> None:
        # Arrange
        chip = fresh()
        chip.memory.write8(0x0123, 0x77)
        chip.write_control(0x23)
        chip.write_control(0x01)
        settle(chip)

        # Act
        found = chip.read_data()

        # Assert
        self.assertEqual(found, 0x77)

    def test_code_3_sends_data_to_colour_ram(self) -> None:
        # Arrange
        chip = fresh()
        chip.write_control(0x11)
        chip.write_control(0xC0)

        # Act
        chip.write_data(0x2A)
        settle(chip)

        # Assert
        self.assertEqual(chip.cram.entry(0x11), 0x2A)

    def test_a_second_access_inside_the_lead_loses_the_first(self) -> None:
        # Arrange
        chip = fresh()
        chip.write_control(0x00)
        chip.write_control(0x40)

        # Act
        chip.write_data(0x11)
        chip.write_data(0x22)
        settle(chip)

        # Assert
        self.assertEqual((chip.lost, chip.memory.read8(0), chip.memory.read8(1)), (1, 0, 0x22))

    def test_accesses_spaced_by_the_blank_lead_all_land(self) -> None:
        # Arrange
        chip = fresh()
        register(chip, 1, 0x80)
        chip.write_control(0x00)
        chip.write_control(0x40)

        # Act
        for value in (1, 2, 3):
            chip.write_data(value)
            for _ in range(BLANK_LEAD):
                chip.tick()

        # Assert
        self.assertEqual((chip.lost, [chip.memory.read8(at) for at in range(3)]), (0, [1, 2, 3]))


class DecodeTest(unittest.TestCase):
    def test_port_decode_uses_a7_a6_and_a0(self) -> None:
        # Arrange
        addresses = (0x7E, 0x41, 0xBE, 0x81, 0xBF, 0x3F, 0xC0)

        # Act
        found = [core.port(address) for address in addresses]

        # Assert
        self.assertEqual(
            found,
            [core.V_COUNTER, core.H_COUNTER, core.DATA, core.CONTROL, core.CONTROL, None, None],
        )

    def test_a_write_to_either_counter_port_reaches_the_sound_generator(self) -> None:
        # Arrange
        chip = fresh()

        # Act
        chip.write_port(0x7F, 0x9A)
        chip.write_port(0x40, 0xBF)

        # Assert
        self.assertEqual(chip.sound.steps[:2], [0x0A, 0x0F])

    def test_reads_through_the_port_decode_reach_the_right_register(self) -> None:
        # Arrange
        chip = fresh()
        run_to_line(chip, 5)

        # Act
        found = (chip.read_port(0x7E), chip.read_port(0x3E))

        # Assert
        self.assertEqual(found, (5, None))

    def test_data_and_control_writes_through_the_decode_reach_their_ports(self) -> None:
        # Arrange
        chip = fresh()

        # Act
        chip.write_port(0xBF, 0x00)
        chip.write_port(0xBF, 0x40)
        chip.write_port(0xBE, 0x5C)
        chip.run_dots(core.ACTIVE_LEAD)

        # Assert
        self.assertEqual(chip.memory.read8(0x0000), 0x5C)

    def test_writes_outside_the_decode_are_ignored(self) -> None:
        # Arrange
        chip = fresh()
        before = bytes(chip.registers)

        # Act
        chip.write_port(0x3F, 0x00)

        # Assert
        self.assertEqual(bytes(chip.registers), before)


class CounterTest(unittest.TestCase):
    def test_the_v_counter_jumps_back_at_the_printed_line(self) -> None:
        # Arrange
        chip = fresh()
        run_to_line(chip, 0xDB)

        # Act
        found = chip.read_v_counter()

        # Assert
        self.assertEqual(found, 0xD5)

    def test_the_h_counter_holds_what_was_latched(self) -> None:
        # Arrange
        chip = fresh()
        run_to_line(chip, 3)
        for _ in range(20):
            chip.clock()
        chip.latch_h_counter()

        # Act
        for _ in range(30):
            chip.clock()
        found = chip.read_h_counter()

        # Assert
        self.assertEqual(found, 10)

    def test_the_frame_flag_rises_as_the_counter_reaches_c1(self) -> None:
        # Arrange
        chip = fresh()
        run_to_line(chip, 0xC0)
        chip.read_status()

        # Act
        run_to_line(chip, 0xC1)

        # Assert
        self.assertEqual(chip.read_status() & flags.FRAME, flags.FRAME)

    def test_the_frame_flag_drives_the_pin_only_when_enabled(self) -> None:
        # Arrange
        chip = fresh()
        register(chip, 1, 0xA0)
        run_to_line(chip, 0xC2)

        # Act
        asserted = chip.interrupt
        register(chip, 1, 0x80)

        # Assert
        self.assertEqual((asserted, chip.interrupt), (True, False))

    def test_reading_the_status_releases_the_pin(self) -> None:
        # Arrange
        chip = fresh()
        register(chip, 1, 0xA0)
        run_to_line(chip, 0xC2)

        # Act
        chip.read_status()

        # Assert
        self.assertFalse(chip.interrupt)

    def test_register_10_of_94_interrupts_as_the_95th_line_begins(self) -> None:
        # Arrange
        chip = fresh()
        register(chip, 0, 0x16)
        register(chip, 10, 94)
        run_to_line(chip, 200)
        run_to_line(chip, 0)
        chip.read_status()

        # Act
        raised: list[int] = []
        for _ in range(193 * geometry.DOTS):
            chip.clock()
            if chip.interrupt:
                raised = [*raised, chip.line]
                chip.read_status()

        # Assert
        self.assertEqual(raised, [94, 189])

    def test_register_10_of_1_interrupts_as_every_second_line_begins(self) -> None:
        # Arrange
        chip = fresh()
        register(chip, 0, 0x16)
        register(chip, 10, 1)
        run_to_line(chip, 200)
        run_to_line(chip, 0)
        chip.read_status()

        # Act
        raised: list[int] = []
        for _ in range(12 * geometry.DOTS):
            chip.clock()
            if chip.interrupt:
                raised = [*raised, chip.line]
                chip.read_status()

        # Assert
        self.assertEqual(raised, [1, 3, 5, 7, 9, 11])

    def test_a_new_register_10_waits_for_the_next_reload(self) -> None:
        # Arrange
        chip = fresh()
        register(chip, 0, 0x16)
        register(chip, 10, 20)
        run_to_line(chip, 200)
        run_to_line(chip, 0)
        chip.read_status()
        register(chip, 10, 150)

        # Act
        raised: list[int] = []
        for _ in range(193 * geometry.DOTS):
            chip.clock()
            if chip.interrupt:
                raised = [*raised, chip.line]
                chip.read_status()

        # Assert
        self.assertEqual(raised, [20, 171])

    def test_a_pal_part_counts_313_lines(self) -> None:
        # Arrange
        chip = fresh(region="pal")

        # Act
        seen: set[int] = set()
        for _ in range(313 * geometry.DOTS):
            chip.clock()
            seen = {*seen, chip.line}

        # Assert
        self.assertEqual(len(seen), 313)


class ResetTest(unittest.TestCase):
    def test_reset_puts_the_part_at_the_top_of_line_0(self) -> None:
        # Arrange
        chip = core.Chip(models.lookup("315-5124"), Vram(fill=0), seed=SEED)

        # Act
        chip.reset()

        # Assert
        self.assertEqual((chip.line, chip.dot, chip.half), (0, 0, 0))

    def test_the_handheld_starts_in_its_own_mode(self) -> None:
        # Arrange
        model = models.lookup("315-5378")

        # Act
        chip = core.Chip(model, Vram(fill=0), seed=SEED)

        # Assert
        self.assertTrue(chip.handheld_mode)

    def test_the_handheld_can_be_built_in_master_system_mode(self) -> None:
        # Arrange
        model = models.lookup("315-5378")

        # Act
        chip = core.Chip(model, Vram(fill=0), seed=SEED, handheld_mode=False)

        # Assert
        self.assertFalse(chip.handheld_mode)

    def test_a_console_part_cannot_be_put_in_handheld_mode(self) -> None:
        # Arrange
        model = models.lookup("315-5246")

        # Act
        chip = core.Chip(model, Vram(fill=0), seed=SEED, handheld_mode=True)

        # Assert
        self.assertFalse(chip.handheld_mode)


if __name__ == "__main__":
    unittest.main()
