from typing import Any

from tms9918 import geometry, patterns
from tms9918 import sprites as legacy_sprites

from segavdp import background, modes, palette, sprites
from segavdp.flags import COLLISION, OVERFLOW
from segavdp.models import CRAM

LEFT_BLANK = 0x20

LEFT_COLUMN = 8

SHIFT_LEFT = 0x08

SHIFTED_BY = 8

SECOND_SIXTEEN = 16

MAGNIFY = 0x01

DISPLAY_ON = 0x40


class Display:
    __slots__ = ("cell", "colour", "column", "drawn", "shown", "status")

    cell: Any
    colour: int | None
    column: tuple[str, int] | int
    drawn: Any
    shown: str
    status: int

    cram: Any
    dot: int
    hscroll: int
    kinds: tuple[str, ...]
    line: int
    memory: Any
    mode: Any
    part: Any
    registers: bytearray
    vscroll: int

    @property
    def display_on(self) -> bool:
        return bool(self.registers[1] & DISPLAY_ON)

    def _show(self) -> None:
        text = patterns.is_text(self.mode.name)
        row = geometry.TEXT_ROW if text else geometry.PATTERN_ROW
        self.shown = geometry.region(self.kinds[self.line], row[self.dot])
        if self.shown == geometry.ACTIVE:
            self.colour = self._active(text)
        elif self.shown == geometry.BORDER:
            self.colour = self._backdrop()
        else:
            self.colour = None

    def _evaluate(self) -> None:
        self.drawn = None
        if self.kinds[self.line] != geometry.ACTIVE or not self.display_on:
            return
        name = self.mode.name
        if name == modes.MODE4:
            self._mode4_sprites()
        elif name != modes.INVALID_TEXT and not patterns.is_text(name):
            self._legacy_sprites()

    def _mode4_sprites(self) -> None:
        found = sprites.evaluate(
            self.memory.read8, self.registers, self.part, self.mode.tall, self.line
        )
        if found.overflow:
            self.status |= OVERFLOW
        self.drawn = sprites.draw(found.shown)

    def _legacy_sprites(self) -> None:
        held = self.registers
        found = legacy_sprites.evaluate(self.memory.read8, held, self.line)
        if found.fifth is not None:
            self.status |= OVERFLOW
        shift = SHIFTED_BY if held[0] & SHIFT_LEFT else 0
        shown = tuple(
            legacy_sprites.Sprite(one.plane, one.x - shift, one.colour, one.row, one.bits)
            for one in found.shown
        )
        self.drawn = legacy_sprites.draw(shown, bool(held[1] & MAGNIFY))

    def _legacy(self, colour: int) -> int:
        if self.part.legacy == CRAM:
            return int(self.cram.entry(SECOND_SIXTEEN + colour))
        return palette.LEGACY[colour]

    def _backdrop(self) -> int:
        held = self.registers[7] & 0x0F
        if self.mode.name in (modes.MODE4, modes.INVALID_TEXT):
            return int(self.cram.entry(SECOND_SIXTEEN + held))
        return self._legacy(held)

    def _sprite_at(self, dot: int) -> int | None:
        drawn = self.drawn
        if drawn is None:
            return None
        if drawn.collision == dot:
            self.status |= COLLISION
        found: int | None = drawn.colours[dot]
        return found

    def _active(self, text: bool) -> int:
        name = self.mode.name
        if not self.display_on or name == modes.INVALID_TEXT:
            return self._backdrop()
        if name == modes.MODE4:
            return self._mode4()
        return self._legacy_active(text)

    def _legacy_active(self, text: bool) -> int:
        start = geometry.TEXT_OFFSET if text else 0
        column, within = divmod(self.dot - start, patterns.width(self.mode.name))
        if (self.mode.name, column) != self.column:
            self.column = (self.mode.name, column)
            self.cell = patterns.cell(
                self.memory.read8, self.registers, self.mode.name, self.line, column
            )
        sprite = None if text else self._sprite_at(self.dot)
        pattern: int = self.cell[within]
        return self._legacy(sprite or pattern or self.registers[7] & 0x0F)

    def _mode4(self) -> int:
        held, dot = self.registers, self.dot
        sprite = self._sprite_at(dot)
        if held[0] & LEFT_BLANK and dot < LEFT_COLUMN:
            return self._backdrop()
        scroll = background.scroll_x(held, self.line, self.hscroll)
        placed = background.place(dot, scroll)
        if placed is None:
            return int(self.cram.entry(SECOND_SIXTEEN + sprite)) if sprite else self._backdrop()
        column, within = placed
        if (modes.MODE4, column) != self.column:
            self.column = (modes.MODE4, column)
            y = background.source_line(held, self.line, column, self.vscroll, self.mode.tall)
            self.cell = background.cell(
                self.memory.read8,
                held,
                self.part,
                self.mode.tall,
                y,
                background.name_column(column, scroll),
            )
        if sprite and not self.cell.front[within]:
            return int(self.cram.entry(SECOND_SIXTEEN + sprite))
        return int(self.cram.entry(self.cell.colours[within]))
