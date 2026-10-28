import functools

from tms9918 import geometry

from segavdp.models import NTSC, PAL

HEIGHTS = (192, 224, 240)

LINES = {NTSC: 262, PAL: 313}

BOTTOM_BLANKING = 3

VERTICAL_SYNC = 3

TOP_BLANKING = 13

BORDERS = {
    (NTSC, 192): (24, 27),
    (NTSC, 224): (8, 11),
    (PAL, 192): (48, 54),
    (PAL, 224): (32, 38),
    (PAL, 240): (24, 30),
}

V_RUNS = {
    (NTSC, 192): ((0x00, 0xDA), (0xD5, 0xFF)),
    (NTSC, 224): ((0x00, 0xEA), (0xE5, 0xFF)),
    (NTSC, 240): ((0x00, 0xFF), (0x00, 0x05)),
    (PAL, 192): ((0x00, 0xF2), (0xBA, 0xFF)),
    (PAL, 224): ((0x00, 0xFF), (0x00, 0x02), (0xCA, 0xFF)),
    (PAL, 240): ((0x00, 0xFF), (0x00, 0x0A), (0xD2, 0xFF)),
}

H_JUMP = 296

H_SKIP = 170

LINE_EVENT = 266


def lines_of(region: str) -> int:
    return LINES[region]


def _rolling(region: str, height: int) -> tuple[str, ...]:
    return (geometry.ACTIVE,) * height + (geometry.BLANKING,) * (LINES[region] - height)


@functools.cache
def layout(region: str, height: int) -> tuple[str, ...]:
    borders = BORDERS.get((region, height))
    if borders is None:
        return _rolling(region, height)
    bottom, top = borders
    return (
        (geometry.ACTIVE,) * height
        + (geometry.BORDER,) * bottom
        + (geometry.BLANKING,) * BOTTOM_BLANKING
        + (geometry.SYNC,) * VERTICAL_SYNC
        + (geometry.BLANKING,) * TOP_BLANKING
        + (geometry.BORDER,) * top
    )


@functools.cache
def v_counter(region: str, height: int) -> tuple[int, ...]:
    return tuple(
        value for first, last in V_RUNS[(region, height)] for value in range(first, last + 1)
    )


def h_counter(dot: int) -> int:
    counted = dot if dot < H_JUMP else dot + H_SKIP
    return counted >> 1


def frame_line(height: int) -> int:
    return height + 1


def counts_down(line: int, height: int) -> bool:
    return line <= height
