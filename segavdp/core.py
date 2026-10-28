import random
from typing import Any

from tms9918 import geometry
from tms9918.memory import ADDRESS_MASK

from segavdp import modes, timing
from segavdp.display import Display
from segavdp.flags import FLAGS, FRAME
from segavdp.palette import ColourRam
from segavdp.sound import Generator

UNSET_SEED = 0x5124

REGISTER_COUNT = 11

REGISTER_SLOTS = 16

FRAME_ENABLE = 0x20

LINE_ENABLE = 0x10

READ = "read"

WRITE = "write"

COLOUR = "colour"

CODE_READ = 0

CODE_REGISTER = 2

CODE_COLOUR = 3

ACTIVE_LEAD = 78

BLANK_LEAD = 30

TICKS_PER_SOUND_CLOCK = 3

DATA = "data"

CONTROL = "control"

V_COUNTER = "v counter"

H_COUNTER = "h counter"

PORT_SELECT = 0xC0

COUNTER_PORTS = 0x40

VDP_PORTS = 0x80


def port(address: int) -> str | None:
    selected = address & PORT_SELECT
    odd = bool(address & 1)
    if selected == COUNTER_PORTS:
        return H_COUNTER if odd else V_COUNTER
    if selected == VDP_PORTS:
        return CONTROL if odd else DATA
    return None


class Chip(Display):
    __slots__ = (
        "address",
        "asked",
        "buffer",
        "code",
        "counter",
        "cram",
        "cycles",
        "dot",
        "floating",
        "h_latched",
        "half",
        "handheld_mode",
        "hscroll",
        "kinds",
        "latch",
        "line",
        "line_pending",
        "lost",
        "memory",
        "mode",
        "model",
        "part",
        "pending",
        "region",
        "registers",
        "sound",
        "vscroll",
    )

    def __init__(
        self,
        part: Any,
        memory: Any,
        seed: int = UNSET_SEED,
        region: str | None = None,
        handheld_mode: bool | None = None,
    ) -> None:
        scrambled = random.Random(seed)
        self.part = part
        self.model: str = part.name
        self.memory = memory
        self.region = part.region(region)
        self.handheld_mode = (
            part.handheld if handheld_mode is None else part.handheld and handheld_mode
        )
        self.cram = ColourRam(part.handheld, seed)
        self.sound = Generator(part.handheld, seed)
        self.registers = bytearray(scrambled.randbytes(REGISTER_COUNT))
        self.status = scrambled.randrange(256) & FLAGS
        self.floating = scrambled.randrange(256) & ~FLAGS & 0xFF
        self.latch = bool(scrambled.getrandbits(1))
        self.line_pending = bool(scrambled.getrandbits(1))
        self.address = scrambled.randrange(ADDRESS_MASK + 1)
        self.code = scrambled.randrange(4)
        self.buffer = scrambled.randrange(256)
        self.counter = scrambled.randrange(256)
        self.hscroll = scrambled.randrange(256)
        self.vscroll = scrambled.randrange(256)
        self.h_latched = scrambled.randrange(256)
        self.mode = self._decoded()
        self.kinds = timing.layout(self.region, self.mode.height)
        self.line = scrambled.randrange(len(self.kinds))
        self.dot = scrambled.randrange(geometry.DOTS)
        self.half = scrambled.randrange(2)
        self.pending: tuple[str, int, int] | None = None
        self.asked = 0
        self.cycles = 0
        self.lost = 0
        self.shown = geometry.BLANKING
        self.colour = None
        self.drawn = None
        self.column = -1
        self.cell = None

    def reset(self) -> "Chip":
        self.registers[0] = 0
        self.registers[1] = 0
        self.status = 0
        self.line_pending = False
        self.latch = False
        self.mode = self._decoded()
        self.kinds = timing.layout(self.region, self.mode.height)
        self.line = 0
        self.dot = 0
        self.half = 0
        self.column = -1
        return self

    @property
    def interrupt(self) -> bool:
        frame = bool(self.status & FRAME and self.registers[1] & FRAME_ENABLE)
        return frame or (self.line_pending and bool(self.registers[0] & LINE_ENABLE))

    def write_control(self, value: int) -> None:
        if not self.latch:
            self.address = (self.address & 0x3F00) | value
            self.latch = True
            return
        self.latch = False
        self.address = (value & 0x3F) << 8 | (self.address & 0xFF)
        self.code = value >> 6
        if self.code == CODE_READ:
            self._ask(READ, 0)
        elif self.code == CODE_REGISTER:
            self._load(value & (REGISTER_SLOTS - 1), self.address & 0xFF)

    def write_data(self, value: int) -> None:
        self.latch = False
        self.buffer = value & 0xFF
        self._ask(COLOUR if self.code == CODE_COLOUR else WRITE, value & 0xFF)

    def read_data(self) -> int:
        self.latch = False
        held = self.buffer
        self._ask(READ, 0)
        return held

    def read_status(self) -> int:
        self.latch = False
        held = self.status | self.floating
        self.status = 0
        self.line_pending = False
        return held

    def read_v_counter(self) -> int:
        return timing.v_counter(self.region, self.mode.height)[self.line]

    def read_h_counter(self) -> int:
        return self.h_latched

    def latch_h_counter(self) -> None:
        self.h_latched = timing.h_counter(self.dot)

    def write_sound(self, value: int) -> None:
        self.sound.write(value)

    def read_port(self, address: int) -> int | None:
        chosen = port(address)
        if chosen is None:
            return None
        readers = {
            DATA: self.read_data,
            CONTROL: self.read_status,
            V_COUNTER: self.read_v_counter,
            H_COUNTER: self.read_h_counter,
        }
        return readers[chosen]()

    def write_port(self, address: int, value: int) -> None:
        chosen = port(address)
        if chosen == DATA:
            self.write_data(value)
        elif chosen == CONTROL:
            self.write_control(value)
        elif chosen is not None:
            self.write_sound(value)

    def clock(self) -> None:
        self.tick()
        self.tick()

    def run_dots(self, count: int) -> None:
        for _ in range(count):
            self.clock()

    def tick(self) -> None:
        if not self.half:
            self._show()
        self.cycles += 1
        self._serve()
        if self.cycles % TICKS_PER_SOUND_CLOCK == 0:
            self.sound.tick()
        self._advance()

    def _decoded(self) -> modes.Mode:
        return modes.decode(self.part, self.registers[0], self.registers[1], self.handheld_mode)

    def _load(self, register: int, value: int) -> None:
        if register >= REGISTER_COUNT:
            return
        self.registers[register] = value
        self.mode = self._decoded()

    def _ask(self, kind: str, value: int) -> None:
        self._serve()
        if self.pending is not None:
            self.lost += 1
        self.pending = (kind, self.address, value)
        self.asked = self.cycles
        self.address = (self.address + 1) & ADDRESS_MASK

    def _lead(self) -> int:
        busy = self.display_on and self.kinds[self.line] == geometry.ACTIVE
        return ACTIVE_LEAD if busy else BLANK_LEAD

    def _serve(self) -> None:
        if self.pending is None or self.cycles - self.asked < self._lead():
            return
        kind, address, value = self.pending
        self.pending = None
        if kind == WRITE:
            self.memory.write8(address, value)
        elif kind == COLOUR:
            self.cram.write(address, value, self.handheld_mode)
        else:
            self.buffer = self.memory.read8(address)

    def _advance(self) -> None:
        self.half ^= 1
        if self.half:
            return
        self.dot += 1
        if self.dot == timing.LINE_EVENT:
            self._line_event()
        if self.dot == geometry.DOTS:
            self.dot = 0
            self.column = -1

    def _line_event(self) -> None:
        height = self.mode.height
        self.kinds = timing.layout(self.region, height)
        self.line = (self.line + 1) % len(self.kinds)
        self._count_line(self.line, height)
        if self.line == 0:
            self.vscroll = self.registers[9]
        self.hscroll = self.registers[8]
        if self.line == timing.frame_line(height):
            self.status |= FRAME
        self._evaluate()

    def _count_line(self, finished: int, height: int) -> None:
        if not timing.counts_down(finished, height):
            self.counter = self.registers[10]
            return
        if self.counter == 0:
            self.counter = self.registers[10]
            self.line_pending = True
            return
        self.counter -= 1
