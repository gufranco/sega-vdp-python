import json
from pathlib import Path
from typing import Any

import segavdp

RECORD = Path(__file__).resolve().parent / "hardware.json"

HELD: dict[str, Any] = json.loads(RECORD.read_text())

FACTS: dict[str, Any] = HELD["facts"]

UNSTATED: dict[str, Any] = HELD["notStated"]

SEED = 7

DOTS = 342

LONGEST_FRAME = 313

NAME_TABLE = 0x3800

SPRITE_TABLE = 0x3F00

TILE = 1

SPRITE_TILE = 2

TILE_COLOUR = 5

SPRITE_COLOUR = 3

BACKDROP = 0x30

MODE4 = {
    0: 0x06,
    1: 0xE0,
    2: 0xFF,
    3: 0xFF,
    4: 0xFF,
    5: 0xFF,
    6: 0xFB,
    7: 0x00,
    8: 0,
    9: 0,
    10: 0xFF,
}


def value(name: str) -> Any:
    return FACTS[name]["value"]


def unstated(name: str) -> Any:
    return UNSTATED[name]["value"]


def chip(model: str = "315-5246", region: str | None = None) -> Any:
    built: Any = segavdp.Chip(model, segavdp.Vram(fill=0), seed=SEED, region=region)
    built.reset()
    built.read_status()
    return built


def program(part: Any, values: dict[int, int]) -> Any:
    for register, held in values.items():
        part.write_control(held)
        part.write_control(0x80 | register)
    return part


def to_line(part: Any, line: int) -> Any:
    budget = DOTS * LONGEST_FRAME
    while (part.line, part.dot) != (line, 0) and budget:
        part.clock()
        budget -= 1
    return part


def solid(part: Any, index: int, colour: int) -> None:
    for row in range(8):
        for plane in range(4):
            part.memory.write8(index * 32 + row * 4 + plane, 0xFF if colour >> plane & 1 else 0)


def painted(model: str = "315-5246") -> Any:
    part = program(chip(model), MODE4)
    for number in range(64):
        part.memory.write8(SPRITE_TABLE + number, 0xD0)
    for entry in range(32):
        part.cram.write(entry, entry, False)
    part.cram.write(16, BACKDROP, False)
    solid(part, TILE, TILE_COLOUR)
    solid(part, SPRITE_TILE, SPRITE_COLOUR)
    for cell in range(32 * 28):
        part.memory.write8(NAME_TABLE + cell * 2, TILE)
    to_line(part, 1)
    return to_line(part, 0)


def sprite(part: Any, number: int, y: int, x: int, index: int) -> None:
    part.memory.write8(SPRITE_TABLE + number, y)
    part.memory.write8(SPRITE_TABLE + 0x80 + number * 2, x)
    part.memory.write8(SPRITE_TABLE + 0x81 + number * 2, index)


def colour_at(part: Any, line: int, dot: int) -> int | None:
    to_line(part, line)
    for _ in range(dot + 1):
        part.clock()
    found: int | None = part.colour
    return found


def row(part: Any, line: int) -> list[int | None]:
    to_line(part, line)
    seen: list[int | None] = []
    for _ in range(256):
        part.clock()
        seen = [*seen, part.colour]
    return seen
