import collections
import json
import random
import sys
from pathlib import Path
from typing import Any

import segavdp
from segavdp import core, timing

ROOT = Path(__file__).resolve().parent.parent

PROCESSOR = ROOT / "zilog-z80-python"

RECORD = ROOT / "conformance" / "hardware.json"

POWER_ON = {
    int(name.removeprefix("R")): int(value, 16)
    for name, value in json.loads(RECORD.read_text())["facts"]["powerOn"]["value"].items()
}

OPEN_BUS = 0xFF

NOTHING_PRESSED = 0xFF

HANDHELD_START = 0xC0

PADS = 0xC0

HANDHELD_PORTS = 0x07

STEREO_PORT = 0x06

HANDHELD_IO = (0x00, 0x00, 0xFF, 0x00, 0xFF, 0x00)

PARALLEL_PORT = 0x01

DIRECTION_PORT = 0x02

DIRECTION_PINS = 0x7F

SERIAL_CONTROL_PORT = 0x05

SERIAL_WRITABLE = 0xF8

HANDHELD_WRITABLE = (PARALLEL_PORT, DIRECTION_PORT, 0x03)

TICKS_PER_CYCLE = 3

SEED = 0x5246

PAGE = 0x4000

FIXED = 0x0400

RAM = 0x2000

RAM_START = 0xC000

HANDOFF_STACK = 0xDFF0

HANDOFF_MEMORY_CONTROL = 0xA8

CONTROL = 0xFFFC

CARTRIDGE_RAM = 0x08

CARTRIDGE_BANK = 0x04

PORT_GROUP = 0xC1

MEMORY_CONTROL = 0x00

IO_CONTROL = 0x01

TH_LEVELS = 0xA0

GROUPS_TO_VDP = (0x40, 0x41, 0x80, 0x81)

SIZE = 0x02

ZOOM = 0x01

LINE_ENABLE = 0x10


def why_not(where: Path = PROCESSOR) -> str | None:
    if (where / "z80" / "__init__.py").is_file():
        return None
    return (
        f"the census drives zilog-z80-python from {where}, which is not checked out."
        " Run git submodule update --init --recursive"
    )


def _processor() -> Any:
    if str(PROCESSOR) not in sys.path:
        sys.path.append(str(PROCESSOR))
    import z80

    return z80


class Seen:
    __slots__ = ("line_interrupts", "modes", "registers", "sound", "sprites", "status_reads")

    def __init__(self) -> None:
        self.registers: collections.Counter[tuple[int, int]] = collections.Counter()
        self.modes: collections.Counter[str] = collections.Counter()
        self.sprites: collections.Counter[str] = collections.Counter()
        self.sound = 0
        self.status_reads = 0
        self.line_interrupts = 0


class Paging:
    __slots__ = ("control", "pages", "ram", "rom")

    def __init__(self, rom: bytes) -> None:
        self.rom = rom
        self.pages = [0, 1, 2]
        self.control = 0
        self.ram = bytearray(random.Random(SEED).randbytes(PAGE * 2))

    def _in_ram(self, address: int) -> bool:
        return address >> 14 == 2 and bool(self.control & CARTRIDGE_RAM)

    def _ram_at(self, address: int) -> int:
        return (1 if self.control & CARTRIDGE_BANK else 0) * PAGE + (address & (PAGE - 1))

    def read(self, address: int) -> int:
        if self._in_ram(address):
            return self.ram[self._ram_at(address)]
        if address < FIXED:
            return self.rom[address] if address < len(self.rom) else OPEN_BUS
        count = max(1, len(self.rom) // PAGE)
        at = (self.pages[address >> 14] % count) * PAGE + (address & (PAGE - 1))
        return self.rom[at] if at < len(self.rom) else OPEN_BUS

    def write(self, address: int, value: int) -> None:
        if self._in_ram(address):
            self.ram[self._ram_at(address)] = value
        elif address == CONTROL:
            self.control = value
        elif address > CONTROL:
            self.pages[address - CONTROL - 1] = value


class Ports:
    __slots__ = ("board",)

    def __init__(self, board: "Board") -> None:
        self.board = board

    def read(self, address: int) -> int:
        return self.board.read_port(address)

    def write(self, address: int, value: int) -> None:
        self.board.write_port(address, value)


class Board:
    __slots__ = (
        "cpu",
        "frames",
        "handheld",
        "handheld_io",
        "io_control",
        "last_line",
        "lit",
        "pads",
        "paging",
        "ram",
        "seen",
        "vdp",
    )

    def __init__(
        self,
        rom: bytes,
        model: str = "315-5246",
        handheld: bool = False,
        region: str | None = None,
    ) -> None:
        z80 = _processor()
        self.paging = Paging(rom)
        self.ram = bytearray(random.Random(SEED).randbytes(RAM))
        self.handheld = handheld
        self.handheld_io = bytearray(HANDHELD_IO)
        self.vdp: core.Chip = segavdp.Chip(model, seed=SEED, handheld_mode=handheld, region=region)
        self.vdp.reset()
        for register, value in POWER_ON.items():
            self.vdp.write_control(value)
            self.vdp.write_control(0x80 | register)
        self.seen = Seen()
        self.frames = 0
        self.io_control = NOTHING_PRESSED
        self.pads = [NOTHING_PRESSED, NOTHING_PRESSED]
        self.last_line = self.vdp.line
        self.lit: Any = None
        self.cpu = z80.Cpu("z80", self, ports=Ports(self), seed=SEED)
        self.cpu.on_cycle = self.cycle
        self.cpu.reset()
        if not handheld:
            self.cpu.registers.sp = HANDOFF_STACK
            self.ram[0] = HANDOFF_MEMORY_CONTROL

    @property
    def lost(self) -> int:
        return self.vdp.lost

    def read8(self, address: int) -> int:
        if address >= RAM_START:
            return self.ram[address & (RAM - 1)]
        return self.paging.read(address)

    def write8(self, address: int, value: int) -> None:
        if address >= RAM_START:
            self.ram[address & (RAM - 1)] = value & 0xFF
        self.paging.write(address, value & 0xFF)

    def read_port(self, address: int) -> int:
        low = address & 0xFF
        if self.handheld and low < HANDHELD_PORTS:
            return self._handheld_read(low)
        group = low & PORT_GROUP
        if group in GROUPS_TO_VDP:
            self.seen.status_reads += group == 0x81
            found = self.vdp.read_port(low)
            return OPEN_BUS if found is None else found
        return self.pads[low & 1] if low >= PADS else OPEN_BUS

    def _handheld_read(self, address: int) -> int:
        held = self.handheld_io
        if address == 0:
            return HANDHELD_START
        if address == PARALLEL_PORT:
            pins = held[DIRECTION_PORT] & DIRECTION_PINS
            return (held[PARALLEL_PORT] & ~pins) | pins
        return OPEN_BUS if address == STEREO_PORT else held[address]

    def _handheld_write(self, low: int, value: int) -> None:
        if low == STEREO_PORT:
            self.vdp.sound.write_stereo(value)
        elif low in HANDHELD_WRITABLE:
            self.handheld_io[low] = value & 0xFF
        elif low == SERIAL_CONTROL_PORT:
            self.handheld_io[low] = value & SERIAL_WRITABLE

    def write_port(self, address: int, value: int) -> None:
        low = address & 0xFF
        if self.handheld and low < HANDHELD_PORTS:
            self._handheld_write(low, value)
            return
        group = low & PORT_GROUP
        if group == IO_CONTROL:
            self._io_control(value)
        elif group in (0x40, 0x41):
            self.seen.sound += 1
            self.vdp.write_port(low, value)
        elif group == 0x81:
            self._control(value)
        elif group == 0x80:
            self.vdp.write_port(low, value)

    def _io_control(self, value: int) -> None:
        if (value ^ self.io_control) & TH_LEVELS:
            self.vdp.latch_h_counter()
        self.io_control = value

    def _control(self, value: int) -> None:
        vdp = self.vdp
        if vdp.latch and value >> 6 == core.CODE_REGISTER:
            self.seen.registers[(value & 0x0F, vdp.address & 0xFF)] += 1
        vdp.write_control(value)

    def cycle(self) -> None:
        vdp = self.vdp
        for _ in range(TICKS_PER_CYCLE):
            vdp.tick()
        self.cpu.irq_line = vdp.interrupt
        if vdp.line != self.last_line:
            self.last_line = vdp.line
            if vdp.display_on:
                self.lit = vdp.mode
            if vdp.line == timing.frame_line(vdp.mode.height):
                self._frame()

    def _frame(self) -> None:
        self.frames += 1
        vdp, lit = self.vdp, self.lit
        self.lit = None
        if lit is None:
            return
        self.seen.modes[f"{lit.name} {lit.height}"] += 1
        if vdp.registers[0] & LINE_ENABLE:
            self.seen.line_interrupts += 1
        if lit.name == segavdp.modes.MODE4:
            held = vdp.registers[1]
            size = "8x16" if held & SIZE else "8x8"
            self.seen.sprites[f"{size} {'zoomed' if held & ZOOM else 'plain'}"] += 1

    def run_frames(self, count: int) -> None:
        target = self.frames + count
        while self.frames < target:
            self.cpu.step()
