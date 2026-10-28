import statistics
import sys
import time
from collections.abc import Sequence

import segavdp
from segavdp.core import Chip

MEASURED_HERE = 980_000

HEADROOM = 10

FLOOR_STEP = 10_000

FLOOR = MEASURED_HERE // HEADROOM // FLOOR_STEP * FLOOR_STEP

DOTS = 342 * 262

REPEATS = 5

BUSY = {0: 0x06, 1: 0xE2, 2: 0xFF, 3: 0xFF, 4: 0xFF, 5: 0xFF, 6: 0xFB, 7: 0x00, 8: 0x03, 9: 0x00}

SEED = 5246

SPRITE_TABLE = 0x3F00


def busy_chip() -> Chip:
    part: Chip = segavdp.Chip("315-5246", segavdp.Vram(seed=SEED), seed=SEED)
    part.reset()
    part.read_status()
    for register, value in BUSY.items():
        part.write_control(value)
        part.write_control(0x80 | register)
    for number in range(64):
        part.memory.write8(SPRITE_TABLE + number, (number * 3) & 0xBF)
    return part


class Timed:
    __slots__ = ("calls", "seconds", "what")

    def __init__(self, what: str, calls: int, seconds: Sequence[float]) -> None:
        self.what = what
        self.calls = calls
        self.seconds = list(seconds)

    def median(self) -> float:
        return statistics.median(self.seconds)

    def rate(self) -> float:
        taken = self.median()
        return self.calls / taken if taken > 0 else 0.0

    def beats(self, floor: int) -> bool:
        return self.rate() >= floor


def measure(calls: int = DOTS, repeats: int = REPEATS) -> Timed:
    seconds = []
    for _ in range(repeats):
        part = busy_chip()
        started = time.perf_counter()
        for _ in range(calls):
            part.clock()
        seconds.append(time.perf_counter() - started)
    return Timed("dots of a mode 4 frame with sprites on every line", calls, seconds)


def lines_for(found: Timed, floor: int = FLOOR) -> list[str]:
    runtime = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    lines = [
        f"  {found.what}: {found.rate():,.0f} per second"
        f" (median of {len(found.seconds)}) on Python {runtime}",
        f"  floor: {floor:,} per second",
    ]
    if not found.beats(floor):
        lines.append(f"  below the floor: {found.rate():,.0f} is under {floor:,}")
    return lines


def main(calls: int = DOTS, repeats: int = REPEATS, floor: int = FLOOR) -> int:
    found = measure(calls, repeats)
    for line in lines_for(found, floor):
        print(line)
    return 0 if found.beats(floor) else 1


if __name__ == "__main__":
    raise SystemExit(main())
