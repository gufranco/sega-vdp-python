from typing import Any, override

from tms9918 import patterns

MODE4 = "mode4"

INVALID_TEXT = "invalid text"

SELECT_MODE4 = 0x04

SELECT_M2 = 0x02

SELECT_M1 = 0x10

SELECT_M3 = 0x08

SHORT = 192

MIDDLE = 224

TALL = 240


class Mode:
    __slots__ = ("height", "name", "tall")

    def __init__(self, name: str, height: int, tall: bool) -> None:
        self.name = name
        self.height = height
        self.tall = tall

    @override
    def __repr__(self) -> str:
        return f"<Mode {self.name}, {self.height} lines>"


def _selected(model: Any, r0: int, r1: int) -> int:
    if not model.extended or not r0 & SELECT_M2:
        return SHORT
    m1, m3 = bool(r1 & SELECT_M1), bool(r1 & SELECT_M3)
    if m1 == m3:
        return SHORT
    return MIDDLE if m1 else TALL


def _invalid_text(model: Any, r0: int, r1: int) -> bool:
    if not r1 & SELECT_M1:
        return False
    return not (model.extended and r0 & SELECT_M2)


def decode(model: Any, r0: int, r1: int, handheld_mode: bool = False) -> Mode:
    if not r0 & SELECT_MODE4:
        return Mode(patterns.mode_of(r0, r1), SHORT, False)
    if _invalid_text(model, r0, r1):
        return Mode(INVALID_TEXT, SHORT, False)
    selected = _selected(model, r0, r1)
    shown = SHORT if handheld_mode else selected
    return Mode(MODE4, shown, selected != SHORT)
