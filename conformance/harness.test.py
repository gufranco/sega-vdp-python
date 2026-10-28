import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "ti-tms9918-python"))
sys.path.append(str(ROOT / "ti-sn76489-python"))

from conformance import harness  # noqa: E402

READY = harness.why_not() is None

LD_A = 0x3E

OUT = 0xD3

IN = 0xDB

JR = 0x18

LD_B = 0x06

DJNZ = 0x10

DI = 0xF3

EI = 0xFB

IM_PREFIX = 0xED

IM_ONE = 0x56

RETI = 0x4D

PAGE = 0x4000


def program(*parts: int, pages: int = 4) -> bytes:
    image = bytearray(PAGE * pages)
    image[: len(parts)] = bytes(parts)
    for page in range(pages):
        image[page * PAGE + 0x1000] = page
    return bytes(image)


def register_write(register: int, value: int) -> tuple[int, ...]:
    return (LD_A, value, OUT, 0xBF, LD_A, 0x80 | register, OUT, 0xBF)


@unittest.skipUnless(READY, "zilog-z80-python is not checked out")
class MemoryTest(unittest.TestCase):
    def test_a_console_board_starts_where_the_export_boot_program_hands_over(self) -> None:
        # Arrange
        image = program()

        # Act
        board = harness.Board(image)

        # Assert
        self.assertEqual((board.cpu.registers.sp, board.read8(0xC000)), (0xDFF0, 0xA8))

    def test_a_handheld_board_starts_with_nothing_handed_over(self) -> None:
        # Arrange
        image = program()

        # Act
        board = harness.Board(image, model="315-5378", handheld=True)

        # Assert
        self.assertNotEqual(board.cpu.registers.sp, 0xDFF0)

    def test_the_first_three_frames_start_on_pages_0_1_and_2(self) -> None:
        # Arrange
        board = harness.Board(program())

        # Act
        found = [board.read8(frame * PAGE + 0x1000) for frame in range(3)]

        # Assert
        self.assertEqual(found, [0, 1, 2])

    def test_a_write_to_ffff_pages_frame_2(self) -> None:
        # Arrange
        board = harness.Board(program())

        # Act
        board.write8(0xFFFF, 3)

        # Assert
        self.assertEqual(board.read8(0x9000), 3)

    def test_the_first_kilobyte_never_moves(self) -> None:
        # Arrange
        board = harness.Board(program(0x12))

        # Act
        board.write8(0xFFFD, 2)

        # Assert
        self.assertEqual((board.read8(0x0000), board.read8(0x1000)), (0x12, 2))

    def test_a_page_past_the_image_wraps_onto_it(self) -> None:
        # Arrange
        board = harness.Board(program())

        # Act
        board.write8(0xFFFE, 5)

        # Assert
        self.assertEqual(board.read8(0x5000), 1)

    def test_the_paging_registers_are_also_ram(self) -> None:
        # Arrange
        board = harness.Board(program())

        # Act
        board.write8(0xFFFF, 3)

        # Assert
        self.assertEqual((board.read8(0xFFFF), board.read8(0xDFFF)), (3, 3))

    def test_the_eight_kilobytes_of_ram_repeat_from_c000(self) -> None:
        # Arrange
        board = harness.Board(program())

        # Act
        board.write8(0xC010, 0x5A)

        # Assert
        self.assertEqual(board.read8(0xE010), 0x5A)

    def test_ffc_bit_3_puts_cartridge_ram_in_frame_2(self) -> None:
        # Arrange
        board = harness.Board(program())
        board.write8(0xFFFC, 0x08)

        # Act
        board.write8(0x8010, 0xA5)
        kept = board.read8(0x8010)
        board.write8(0xFFFC, 0x00)

        # Assert
        self.assertEqual((kept, board.read8(0x8010)), (0xA5, 0x00))

    def test_ffc_bit_2_picks_the_second_cartridge_ram_bank(self) -> None:
        # Arrange
        board = harness.Board(program())
        board.write8(0xFFFC, 0x08)
        board.write8(0x8000, 0x11)

        # Act
        board.write8(0xFFFC, 0x0C)
        board.write8(0x8000, 0x22)
        board.write8(0xFFFC, 0x08)

        # Assert
        self.assertEqual(board.read8(0x8000), 0x11)

    def test_a_write_to_rom_changes_nothing(self) -> None:
        # Arrange
        board = harness.Board(program(0x11))

        # Act
        board.write8(0x0000, 0x99)

        # Assert
        self.assertEqual(board.read8(0x0000), 0x11)


@unittest.skipUnless(READY, "zilog-z80-python is not checked out")
class PortTest(unittest.TestCase):
    def test_bf_writes_reach_the_vdp_and_are_counted(self) -> None:
        # Arrange
        board = harness.Board(program(*register_write(7, 0x1C), DI, JR, 0xFE))

        # Act
        board.run_frames(1)

        # Assert
        self.assertEqual((board.vdp.registers[7], board.seen.registers[(7, 0x1C)]), (0x1C, 1))

    def test_7f_writes_reach_the_sound_generator(self) -> None:
        # Arrange
        board = harness.Board(program(LD_A, 0x9A, OUT, 0x7F, DI, JR, 0xFE))

        # Act
        board.run_frames(1)

        # Assert
        self.assertEqual((board.seen.sound, board.vdp.sound.steps[0]), (1, 0x0A))

    def test_the_controller_ports_read_as_nothing_pressed(self) -> None:
        # Arrange
        board = harness.Board(program())

        # Act
        read = (board.read_port(0xDC), board.read_port(0xDD))

        # Assert
        self.assertEqual(read, (0xFF, 0xFF))

    def test_a_pressed_button_reads_low_on_its_port(self) -> None:
        # Arrange
        board = harness.Board(program())

        # Act
        board.pads[0] = 0xDF

        # Assert
        self.assertEqual((board.read_port(0xDC), board.read_port(0xDD)), (0xDF, 0xFF))

    def test_the_low_ports_read_as_open_bus(self) -> None:
        # Arrange
        board = harness.Board(program())

        # Act
        read = board.read_port(0x3E)

        # Assert
        self.assertEqual(read, harness.OPEN_BUS)

    def test_a_low_port_with_a_high_byte_still_reads_as_open_bus(self) -> None:
        # Arrange
        board = harness.Board(program())

        # Act
        read = board.read_port(0x123E)

        # Assert
        self.assertEqual(read, harness.OPEN_BUS)

    def test_a_th_change_latches_the_h_counter(self) -> None:
        # Arrange
        board = harness.Board(program())
        board.vdp.h_latched = 0x00
        board.vdp.run_dots(40)

        # Act
        board.write_port(0x3F, 0xF5)
        board.write_port(0x3F, 0x55)

        # Assert
        self.assertNotEqual(board.read_port(0x7F), 0x00)

    def test_the_handheld_start_port_reads_released(self) -> None:
        # Arrange
        board = harness.Board(program(), model="315-5378", handheld=True)

        # Act
        read = board.read_port(0x00)

        # Assert
        self.assertEqual(read, harness.HANDHELD_START)

    def test_the_handheld_serial_and_parallel_ports_read_their_power_on_values(self) -> None:
        # Arrange
        board = harness.Board(program(), model="315-5378", handheld=True)

        # Act
        read = [board.read_port(port) for port in range(1, 6)]

        # Assert
        self.assertEqual(read, [0x7F, 0xFF, 0x00, 0xFF, 0x00])

    def test_a_write_to_the_handheld_serial_control_keeps_only_its_top_five_bits(self) -> None:
        # Arrange
        board = harness.Board(program(), model="315-5378", handheld=True)

        # Act
        board.write_port(0x05, 0xFF)

        # Assert
        self.assertEqual(board.read_port(0x05), 0xF8)

    def test_the_handheld_parallel_port_reads_its_outputs_through_the_direction_register(
        self,
    ) -> None:
        # Arrange
        board = harness.Board(program(), model="315-5378", handheld=True)
        board.write_port(0x02, 0x00)

        # Act
        board.write_port(0x01, 0x55)

        # Assert
        self.assertEqual((board.read_port(0x01), board.read_port(0x02)), (0x55, 0x00))

    def test_a_write_to_the_handheld_receive_buffer_changes_nothing(self) -> None:
        # Arrange
        board = harness.Board(program(), model="315-5378", handheld=True)

        # Act
        board.write_port(0x04, 0x12)

        # Assert
        self.assertEqual(board.read_port(0x04), 0xFF)

    def test_the_handheld_transmit_buffer_reads_back_what_was_written(self) -> None:
        # Arrange
        board = harness.Board(program(), model="315-5378", handheld=True)

        # Act
        board.write_port(0x03, 0x3C)

        # Assert
        self.assertEqual(board.read_port(0x03), 0x3C)

    def test_the_handheld_ports_decode_the_low_byte_whatever_the_high_byte_carries(self) -> None:
        # Arrange
        board = harness.Board(program(), model="315-5378", handheld=True)
        board.write_port(0x3C05, 0x10)
        board.write_port(0x3C06, 0x0F)

        # Act
        read = board.read_port(0x3C05)

        # Assert
        self.assertEqual((read, board.vdp.sound.stereo), (0x10, 0x0F))

    def test_the_handheld_stereo_port_reads_as_open_bus(self) -> None:
        # Arrange
        board = harness.Board(program(), model="315-5378", handheld=True)

        # Act
        read = board.read_port(0x06)

        # Assert
        self.assertEqual(read, harness.OPEN_BUS)

    def test_the_handheld_stereo_port_reaches_the_sound_generator(self) -> None:
        # Arrange
        board = harness.Board(program(), model="315-5378", handheld=True)

        # Act
        board.write_port(0x06, 0x0F)

        # Assert
        self.assertEqual(board.vdp.sound.stereo, 0x0F)

    def test_a_console_board_ignores_port_06(self) -> None:
        # Arrange
        board = harness.Board(program())

        # Act
        board.write_port(0x06, 0x0F)

        # Assert
        self.assertEqual(board.vdp.sound.stereo, 0xFF)

    def test_a_second_access_before_the_first_lands_is_counted_as_lost(self) -> None:
        # Arrange
        board = harness.Board(program())

        # Act
        board.write_port(0xBE, 1)
        board.write_port(0xBE, 2)

        # Assert
        self.assertEqual(board.lost, 1)


@unittest.skipUnless(READY, "zilog-z80-python is not checked out")
class FrameTest(unittest.TestCase):
    def test_a_frame_is_counted_once_per_frame_flag(self) -> None:
        # Arrange
        board = harness.Board(program(JR, 0xFE))

        # Act
        board.run_frames(2)

        # Assert
        self.assertEqual(board.frames, 2)

    def test_the_vdp_interrupt_reaches_the_processor(self) -> None:
        # Arrange
        handler = 0x38
        code = bytearray(program(*register_write(1, 0x60), IM_PREFIX, IM_ONE, EI, JR, 0xFE))
        code[handler : handler + 5] = bytes([IN, 0xBF, EI, IM_PREFIX, RETI])
        board = harness.Board(bytes(code))

        # Act
        board.run_frames(3)

        # Assert
        self.assertGreaterEqual(board.seen.status_reads, 2)

    def test_a_mode_4_frame_with_the_display_on_is_recorded_with_its_height(self) -> None:
        # Arrange
        board = harness.Board(
            program(*register_write(0, 0x06), *register_write(1, 0x40), DI, JR, 0xFE)
        )

        # Act
        board.run_frames(2)

        # Assert
        self.assertEqual(board.seen.modes["mode4 192"], 2)

    def test_a_frame_lit_only_between_lines_is_recorded_too(self) -> None:
        # Arrange
        lit_for_a_while = (LD_B, 0x00, DJNZ, 0xFE)
        board = harness.Board(
            program(
                *register_write(0, 0x06),
                *register_write(1, 0x40),
                *lit_for_a_while,
                *register_write(1, 0x00),
                DI,
                JR,
                0xFE,
            )
        )

        # Act
        board.run_frames(1)

        # Assert
        self.assertEqual((board.seen.modes["mode4 192"], board.vdp.display_on), (1, False))

    def test_its_sprite_size_is_recorded_too(self) -> None:
        # Arrange
        board = harness.Board(
            program(*register_write(0, 0x06), *register_write(1, 0x43), DI, JR, 0xFE)
        )

        # Act
        board.run_frames(1)

        # Assert
        self.assertEqual(dict(board.seen.sprites), {"8x16 zoomed": 1})

    def test_a_frame_with_the_line_interrupt_on_is_counted(self) -> None:
        # Arrange
        board = harness.Board(
            program(*register_write(0, 0x16), *register_write(1, 0x40), DI, JR, 0xFE)
        )

        # Act
        board.run_frames(2)

        # Assert
        self.assertEqual(board.seen.line_interrupts, 2)

    def test_a_text_frame_records_no_sprite_size(self) -> None:
        # Arrange
        board = harness.Board(
            program(*register_write(0, 0x00), *register_write(1, 0x50), DI, JR, 0xFE)
        )

        # Act
        board.run_frames(2)

        # Assert
        self.assertEqual((board.seen.modes["text 192"], dict(board.seen.sprites)), (2, {}))


@unittest.skipUnless(READY, "zilog-z80-python is not checked out")
class RegionTest(unittest.TestCase):
    def test_a_board_built_for_fifty_hertz_runs_313_lines(self) -> None:
        # Arrange
        board = harness.Board(program(JR, 0xFE), region="pal")

        # Act
        lines = len(board.vdp.kinds)

        # Assert
        self.assertEqual(lines, 313)


class ReadinessTest(unittest.TestCase):
    def test_without_the_processor_the_reason_is_named(self) -> None:
        # Arrange
        absent = Path("/nonexistent")

        # Act
        why = harness.why_not(absent)

        # Assert
        self.assertIn("git submodule update --init", str(why))


if __name__ == "__main__":
    unittest.main()
