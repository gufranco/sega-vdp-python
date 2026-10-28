from collections.abc import Callable
from typing import Any

Reader = Callable[[int], int]

COUNT = 64

SHOWN_PER_LINE = 8

TERMINATOR = 0xD0

TABLE_BITS = 0x7E

TABLE_SHIFT = 7

POSITIONS = 0x80

HIGH_PATTERNS = 0x04

HIGH_PATTERN_SHIFT = 6

MASK_INDEX_EIGHT = 0x02

MASK_INDEX_SIX = 0x01

INDEX_EIGHT = 0x100

INDEX_SIX = 0x40

TALL = 0x02

ZOOM = 0x01

SHIFT_LEFT = 0x08

SHIFTED_BY = 8

ACTIVE_DOTS = 256

PATTERN_BYTES = 32

ROW_BYTES = 4

PLANES = 4

ADDRESS_MASK = 0x3FFF


class Sprite:
    __slots__ = ("planes", "wide", "x")

    def __init__(self, x: int, planes: tuple[int, ...], wide: bool) -> None:
        self.x = x
        self.planes = planes
        self.wide = wide


class Found:
    __slots__ = ("overflow", "shown")

    def __init__(self, shown: tuple[Sprite, ...], overflow: bool) -> None:
        self.shown = shown
        self.overflow = overflow


class Drawn:
    __slots__ = ("collision", "colours")

    def __init__(self, colours: list[int | None], collision: int | None) -> None:
        self.colours = colours
        self.collision = collision


def _index(held: bytearray, model: Any, tag: int, row: int) -> int:
    index = tag | (held[6] & HIGH_PATTERNS) << HIGH_PATTERN_SHIFT
    if held[1] & TALL:
        index = (index & ~1) | row >> 3
    if model.masks and not held[6] & MASK_INDEX_EIGHT:
        index &= ~INDEX_EIGHT
    if model.masks and not held[6] & MASK_INDEX_SIX:
        index &= ~INDEX_SIX
    return index


def _sprite(read: Reader, held: bytearray, model: Any, number: int, row: int, wide: bool) -> Sprite:
    base = (held[5] & TABLE_BITS) << TABLE_SHIFT
    place = base | POSITIONS | number * 2
    if model.masks and not held[5] & 1:
        place &= ~POSITIONS
    x = read(place) - (SHIFTED_BY if held[0] & SHIFT_LEFT else 0)
    start = _index(held, model, read(place + 1), row) * PATTERN_BYTES + (row & 7) * ROW_BYTES
    planes = tuple(read((start + plane) & ADDRESS_MASK) for plane in range(PLANES))
    return Sprite(x, planes, wide)


def evaluate(read: Reader, held: bytearray, model: Any, tall: bool, line: int) -> Found:
    base = (held[5] & TABLE_BITS) << TABLE_SHIFT
    zoom = held[1] & ZOOM
    height = (16 if held[1] & TALL else 8) << zoom
    shown: tuple[Sprite, ...] = ()
    for number in range(COUNT):
        y = read(base | number)
        if not tall and y == TERMINATOR:
            break
        offset = (line - y - 1) & 0xFF
        if offset >= height:
            continue
        if len(shown) == SHOWN_PER_LINE:
            return Found(shown, True)
        wide = bool(zoom) and len(shown) < model.zoomed_across
        shown = (*shown, _sprite(read, held, model, number, offset >> zoom, wide))
    return Found(shown, False)


def _colour(planes: tuple[int, ...], pixel: int) -> int:
    bit = 7 - pixel
    return sum(((planes[plane] >> bit) & 1) << plane for plane in range(PLANES))


def draw(shown: tuple[Sprite, ...]) -> Drawn:
    colours: list[int | None] = [None] * ACTIVE_DOTS
    collision: int | None = None
    for sprite in shown:
        scale = 2 if sprite.wide else 1
        for pixel in range(8):
            colour = _colour(sprite.planes, pixel)
            if not colour:
                continue
            for repeat in range(scale):
                dot = sprite.x + pixel * scale + repeat
                if not 0 <= dot < ACTIVE_DOTS:
                    continue
                if colours[dot] is None:
                    colours[dot] = colour
                elif collision is None or dot < collision:
                    collision = dot
    return Drawn(colours, collision)
