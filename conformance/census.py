import collections
import hashlib
import json
import sys
import zipfile
from collections.abc import Iterator, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from conformance import harness

CONSOLE = ".sms"

HANDHELD = ".gg"

SUFFIXES = (CONSOLE, HANDHELD)

MODELS = {CONSOLE: "315-5246", HANDHELD: "315-5378"}

GATED_SETS = ("US - A-Z", "Europe - A-Z", "Japan - A-Z")

NOT_GAMES = ("[BIOS]", "(Beta", "(Proto", "(Demo", "(Sample")

FRAMES = 600

JOBS = 10

BOARDS = Path(__file__).resolve().parent / "boards.json"

DISPLAYS = "every retail image on Sega's paging turns the display on within the frame bound"

LOST = "accesses asked for before the last one landed"

OTHER_BOARD = "images on a board the census does not model, run without it"

RAISES_NOTHING = "the model raises on no image"

PROPERTIES = (RAISES_NOTHING, DISPLAYS)

CORPUS = Path(__file__).resolve().parent / "corpus.json"

CORPUS_INDENT = 2

USAGE = "usage: python3 -m conformance.census <path> [path ...] [--frames N] [--jobs N]"

Image = tuple[str, str, bytes]


def boards(where: Path = BOARDS) -> dict[str, str]:
    held = json.loads(where.read_text())["boards"]
    return {str(one["sha1"]): str(one["board"]) for one in held}


def _members(where: Path) -> Iterator[Image]:
    with zipfile.ZipFile(where) as bundle:
        for entry in bundle.infolist():
            if not entry.is_dir() and Path(entry.filename).suffix.lower() in SUFFIXES:
                yield where.name, Path(entry.filename).name, bundle.read(entry)


def images_in(where: Path) -> Iterator[Image]:
    if where.is_dir():
        for path in sorted(where.rglob("*")):
            if path.is_file() and path.suffix.lower() == ".zip":
                yield from _members(path)
            elif path.is_file() and path.suffix.lower() in SUFFIXES:
                yield where.name, path.name, path.read_bytes()
        return
    if where.suffix.lower() == ".zip":
        yield from _members(where)
        return
    if where.suffix.lower() in SUFFIXES:
        yield where.parent.name, where.name, where.read_bytes()


def board_of(rom: bytes, listed: Mapping[str, str]) -> str | None:
    return listed.get(hashlib.sha1(rom, usedforsecurity=False).hexdigest())


def gated(collection: str, name: str) -> bool:
    retail = any(one in collection for one in GATED_SETS)
    shipped = not any(tag in name for tag in NOT_GAMES)
    return retail and shipped


def _seen(board: harness.Board, raised: str | None) -> dict[str, Any]:
    seen = board.seen
    return {
        "modes": sorted(seen.modes),
        "registers": sorted({(register, value) for register, value in seen.registers}),
        "sprites": sorted(seen.sprites),
        "lineInterrupts": seen.line_interrupts > 0,
        "lost": board.lost,
        "raised": raised,
    }


def examine(
    job: tuple[bytes, int, str], build: type[harness.Board] = harness.Board
) -> dict[str, Any]:
    rom, frames, suffix = job
    board = build(rom, model=MODELS[suffix], handheld=suffix == HANDHELD)
    try:
        board.run_frames(frames)
    except Exception as error:
        return _seen(board, f"{type(error).__name__}: {error} at frame {board.frames}")
    return _seen(board, None)


Distinct = tuple[bool, bytes, str, str | None]


def _distinct(paths: list[Path], listed: Mapping[str, str]) -> tuple[int, list[Distinct]]:
    count = 0
    seen: dict[str, Distinct] = {}
    for where in paths:
        for collection, name, rom in images_in(where):
            count += 1
            digest = hashlib.sha256(rom).hexdigest()
            held = seen.get(digest)
            retail = bool(held and held[0]) or gated(collection, name)
            seen[digest] = (retail, rom, name, board_of(rom, listed))
    return count, [seen[digest] for digest in sorted(seen)]


def _suffix(name: str) -> str:
    return HANDHELD if name.lower().endswith(HANDHELD) else CONSOLE


def _results(images: list[Distinct], frames: int, jobs: int) -> list[dict[str, Any]]:
    work = [(rom, frames, _suffix(name)) for _, rom, name, _ in images]
    if jobs <= 1:
        return [examine(one) for one in work]
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        return list(pool.map(examine, work))


def tally(images: Sequence[Distinct], results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    modes: collections.Counter[str] = collections.Counter()
    sprites: collections.Counter[str] = collections.Counter()
    registers: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    broken = dict.fromkeys(PROPERTIES, 0)
    lost = {"retail": 0, "other": 0}
    silent = other_board = line_interrupts = 0
    for (retail, _, _, board), found in zip(images, results, strict=True):
        modes.update(found["modes"])
        sprites.update(found["sprites"])
        for register, value in found["registers"]:
            registers[str(register)][f"0x{value:02X}"] += 1
        lost["retail" if retail else "other"] += found["lost"]
        silent += not found["modes"]
        other_board += board is not None
        line_interrupts += found["lineInterrupts"]
        broken[DISPLAYS] += retail and board is None and not found["modes"]
        broken[RAISES_NOTHING] += found["raised"] is not None
    return {
        "properties": broken,
        "modes": dict(sorted(modes.items())),
        "sprites": dict(sorted(sprites.items())),
        "registers": {key: dict(sorted(held.items())) for key, held in sorted(registers.items())},
        "lost": lost,
        "silent": silent,
        "otherBoards": other_board,
        "lineInterrupts": line_interrupts,
    }


def culprits(images: Sequence[Distinct], results: Sequence[dict[str, Any]]) -> dict[str, list[str]]:
    named: dict[str, list[str]] = {name: [] for name in (*PROPERTIES, LOST, OTHER_BOARD)}
    for (retail, _, image, board), found in zip(images, results, strict=True):
        if found["raised"] is not None:
            named[RAISES_NOTHING].append(f"{image}: {found['raised']}")
        if retail and board is None and not found["modes"]:
            named[DISPLAYS].append(image)
        if found["lost"]:
            named[LOST].append(f"{image}: {found['lost']}")
        if board is not None:
            named[OTHER_BOARD].append(f"{image}: {board}")
    return named


def take(paths: list[Path], frames: int = FRAMES, jobs: int = JOBS) -> Mapping[str, Any]:
    count, images = _distinct(paths, boards())
    results = _results(images, frames, jobs)
    return {
        "listings": count,
        "images": len(images),
        "gated": sum(1 for retail, _, _, board in images if retail and board is None),
        "frames": frames,
        **tally(images, results),
        "culprits": culprits(images, results),
    }


def _options(argv: list[str]) -> tuple[list[Path], int, int] | None:
    paths: list[Path] = []
    frames, jobs = FRAMES, JOBS
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item in ("--frames", "--jobs"):
            if not rest:
                return None
            value = int(rest.pop(0))
            frames, jobs = (value, jobs) if item == "--frames" else (frames, value)
        else:
            paths.append(Path(item))
    return (paths, frames, jobs) if paths else None


def report(taken: Mapping[str, Any]) -> list[str]:
    named = taken["culprits"]
    lines = [
        f"{taken['listings']} listings, {taken['images']} distinct images, "
        f"{taken['gated']} retail on Sega's paging, {taken['frames']} frames each"
    ]
    for name, count in taken["properties"].items():
        lines.append(f"  {'ok  ' if not count else '   !'}  {name}: {count} broken")
        lines.extend(f"         {one}" for one in named[name])
    for name in (LOST, OTHER_BOARD):
        lines.append(f"  observed  {name}: {len(named[name])} images")
        lines.extend(f"         {one}" for one in named[name])
    return lines


def main(argv: list[str], into: Path = CORPUS) -> int:
    chosen = _options(argv)
    if chosen is None:
        print(USAGE)
        return 2
    paths, frames, jobs = chosen
    for one in paths:
        if not one.exists():
            print(f"absent: {one}")
    taken = take([one for one in paths if one.exists()], frames, jobs)
    for line in report(taken):
        print(line)
    if taken["images"]:
        kept = {key: value for key, value in taken.items() if key != "culprits"}
        into.write_text(json.dumps(kept, indent=CORPUS_INDENT) + "\n")
    failed = any(taken["properties"].values()) or not taken["images"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
