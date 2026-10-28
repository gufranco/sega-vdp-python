from collections.abc import Callable
from typing import Any

Reader = Callable[[int], int]

SHORT_TABLE_BITS = 0x0E

TALL_TABLE_BITS = 0x0C

TABLE_SHIFT = 10

TALL_OFFSET = 0x0700

ROW_FOUR = 0x0400

SHORT_WRAP = 224

TALL_WRAP = 256

LOCK_TOP = 0x40

LOCK_RIGHT = 0x80

LOCKED_LINES = 16

LOCKED_FROM_COLUMN = 24

COLUMNS = 32

PATTERN_BYTES = 32

ROW_BYTES = 4

PLANES = 4

ADDRESS_MASK = 0x3FFF

INDEX_HIGH = 0x01

FLIP_ACROSS = 0x02

FLIP_DOWN = 0x04

SECOND_PALETTE = 0x08

IN_FRONT = 0x10

PALETTE_SIZE = 16


class Cell:
    __slots__ = ("colours", "front")

    def __init__(self, colours: tuple[int, ...], front: tuple[bool, ...]) -> None:
        self.colours = colours
        self.front = front


def name_base(held: bytearray, tall: bool) -> int:
    if tall:
        return (held[2] & TALL_TABLE_BITS) << TABLE_SHIFT | TALL_OFFSET
    return (held[2] & SHORT_TABLE_BITS) << TABLE_SHIFT


def scroll_x(held: bytearray, line: int, latched: int) -> int:
    return 0 if held[0] & LOCK_TOP and line < LOCKED_LINES else latched


def place(dot: int, scroll: int) -> tuple[int, int] | None:
    fine = scroll & 7
    if dot < fine:
        return None
    return divmod(dot - fine, 8)


def name_column(column: int, scroll: int) -> int:
    return (column - (scroll >> 3)) % COLUMNS


def source_line(held: bytearray, line: int, column: int, latched: int, tall: bool) -> int:
    scroll = 0 if held[0] & LOCK_RIGHT and column >= LOCKED_FROM_COLUMN else latched
    return (line + scroll) % (TALL_WRAP if tall else SHORT_WRAP)


def _address(held: bytearray, model: Any, tall: bool, row: int, column: int) -> int:
    address = name_base(held, tall) + (row * COLUMNS + column) * 2
    if model.masks and not held[2] & 1:
        address &= ~ROW_FOUR
    return address & ADDRESS_MASK


def _pixels(planes: list[int], across: bool, offset: int) -> tuple[int, ...]:
    order = range(8) if across else range(7, -1, -1)
    return tuple(
        sum(((planes[plane] >> bit) & 1) << plane for plane in range(PLANES)) + offset
        for bit in order
    )


def cell(read: Reader, held: bytearray, model: Any, tall: bool, y: int, column: int) -> Cell:
    address = _address(held, model, tall, y >> 3, column)
    low, high = read(address), read(address + 1)
    index = low | (high & INDEX_HIGH) << 8
    row = (y & 7) ^ (7 if high & FLIP_DOWN else 0)
    start = index * PATTERN_BYTES + row * ROW_BYTES
    planes = [read((start + plane) & ADDRESS_MASK) for plane in range(PLANES)]
    colours = _pixels(
        planes, bool(high & FLIP_ACROSS), PALETTE_SIZE if high & SECOND_PALETTE else 0
    )
    front = tuple(bool(high & IN_FRONT) and colour % PALETTE_SIZE != 0 for colour in colours)
    return Cell(colours, front)
