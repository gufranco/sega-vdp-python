import hashlib
import json
import os
import sys
import zipfile
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from conformance import harness

RECORD = Path(__file__).resolve().parent / "testroms.json"

PLACES = "TEST_CARTRIDGES"

KEPT = (
    Path(__file__).resolve().parent.parent
    / "external"
    / "Master EverDrive"
    / "5 Tools & Service Test Carts.zip"
)

COLUMNS = 32

ROW_HEIGHT = 8

TABLE_BITS = 0x0E

TABLE_SHIFT = 10

INDEX_HIGH = 0x01

NOTHING_TO_RUN = 2

USAGE_ERROR = 3

INDENT = 2

USAGE = "usage: python3 -m conformance.testroms [--write] [image, folder or zip ...]"


def record(where: Path | str | None = None) -> dict[str, Any]:
    held = json.loads(Path(where or RECORD).read_text())
    assert isinstance(held, dict), "the record does not hold an object"
    return held


def entry(name: str, where: Path | str | None = None) -> dict[str, Any]:
    found = [one for one in record(where)["cartridges"] if one["id"] == name]
    assert found, f"{name} is not in the record"
    return dict(found[0])


def candidates(place: Path) -> Iterator[bytes]:
    if place.is_dir():
        for path in sorted(place.rglob("*")):
            yield from candidates(path)
    elif zipfile.is_zipfile(place):
        with zipfile.ZipFile(place) as archive:
            for member in archive.namelist():
                yield archive.read(member)
    elif place.is_file():
        yield place.read_bytes()


def images(places: Sequence[Path], wanted: set[str]) -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    for place in places:
        for data in candidates(place):
            digest = hashlib.sha256(data).hexdigest()
            if digest in wanted:
                found[digest] = data
    return found


def _tile(board: harness.Board, address: int) -> int:
    memory = board.vdp.memory
    low: int = memory.read8(address)
    high: int = memory.read8(address + 1)
    return low | (high & INDEX_HIGH) << 8


def _character(code: int) -> str:
    return chr(code) if 0x20 <= code < 0x7F else " "


def screen(board: harness.Board, offset: int) -> list[str]:
    base = (board.vdp.registers[2] & TABLE_BITS) << TABLE_SHIFT
    rows = board.vdp.mode.height // ROW_HEIGHT
    return [
        "".join(
            _character(_tile(board, base + (row * COLUMNS + column) * 2) - offset)
            for column in range(COLUMNS)
        )
        for row in range(rows)
    ]


def reported(row: str) -> bool:
    text = row.strip()
    printable = all(" " <= character <= "~" for character in row)
    return printable and any(character.isalnum() for character in text) and len(set(text)) > 1


def ran(
    image: bytes, run: dict[str, Any], build: type[harness.Board] = harness.Board
) -> dict[str, Any]:
    board = build(image, model=run["model"], region=run.get("region"))
    seen: list[str] = []
    for frames, pad in run["script"]:
        board.pads[0] = pad
        board.run_frames(frames)
        if run.get("offset") is not None:
            shown = [row.strip() for row in screen(board, run["offset"]) if reported(row)]
            seen = list(dict.fromkeys([*seen, *shown]))
    modes = sorted(board.seen.modes)
    return {"verdict": seen, "lost": board.lost, "modes": modes}


def measured(image: bytes, one: dict[str, Any]) -> list[dict[str, Any]]:
    return [{**run, **ran(image, run)} for run in one["runs"]]


def options(argv: Sequence[str]) -> tuple[bool, list[Path]] | None:
    write = "--write" in argv
    rest = [one for one in argv if one != "--write"]
    if any(one.startswith("--") for one in rest):
        return None
    return write, [Path(one) for one in rest]


def places_from(given: list[Path], kept: Path) -> list[Path]:
    if given:
        return given
    named = os.environ.get(PLACES, "")
    return [Path(one) for one in named.split(os.pathsep) if one] or [kept]


def judged(one: dict[str, Any], found: list[dict[str, Any]]) -> bool:
    same = bool(found == one["runs"])
    print(f"{'ran' if same else 'DIFFERS'} {one['id']}: {len(found)} runs")
    for run in found:
        where = f"{run['model']} {run.get('region') or 'ntsc'}"
        print(f"  {where}: {len(run['verdict'])} lines, lost {run['lost']}, modes {run['modes']}")
        for line in run["verdict"]:
            print(f"    {line}")
    return same


def main(
    argv: Sequence[str],
    where: Path | str | None = None,
    kept: Path = KEPT,
) -> int:
    parsed = options(argv)
    if parsed is None:
        print(USAGE)
        return USAGE_ERROR
    write, given = parsed
    held = record(where)
    wanted = [one for one in held["cartridges"] if one["outcome"] == "run"]
    found = images(places_from(given, kept), {one["sha256"] for one in wanted})
    if not found:
        print(f"SKIPPED none of the {len(wanted)} pinned images is on this machine")
        return NOTHING_TO_RUN
    good = True
    for one in wanted:
        if one["sha256"] not in found:
            print(f"SKIPPED {one['id']}: not on this machine")
            continue
        result = measured(found[one["sha256"]], one)
        good = judged(one, result) and good
        one["runs"] = result
    if write:
        Path(where or RECORD).write_text(json.dumps(held, indent=INDENT) + "\n")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
