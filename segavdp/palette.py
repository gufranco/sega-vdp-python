import random

ENTRIES = 32

CONSOLE_MASK = 0x3F

HANDHELD_MASK = 0x0FFF

HANDHELD_ADDRESS_MASK = 0x3F

CONSOLE_STEPS = 3

HANDHELD_STEPS = 15

LEGACY = (
    0x00,
    0x00,
    0x08,
    0x0C,
    0x10,
    0x30,
    0x01,
    0x3C,
    0x02,
    0x03,
    0x05,
    0x0F,
    0x04,
    0x33,
    0x15,
    0x3F,
)


def _widened(value: int) -> int:
    parts = [(value >> shift) & 3 for shift in (0, 2, 4)]
    return sum((part << 2 | part) << (4 * index) for index, part in enumerate(parts))


def levels(value: int, handheld: bool) -> tuple[float, float, float]:
    width, steps = (4, HANDHELD_STEPS) if handheld else (2, CONSOLE_STEPS)
    mask = (1 << width) - 1
    red, green, blue = ((value >> (width * index)) & mask for index in range(3))
    return (red / steps, green / steps, blue / steps)


class ColourRam:
    __slots__ = ("handheld", "latch", "words")

    def __init__(self, handheld: bool, seed: int) -> None:
        scrambled = random.Random(seed)
        mask = HANDHELD_MASK if handheld else CONSOLE_MASK
        self.handheld = handheld
        self.words = [scrambled.randrange(mask + 1) for _ in range(ENTRIES)]
        self.latch = scrambled.randrange(256)

    def entry(self, index: int) -> int:
        return self.words[index % ENTRIES]

    def entries(self) -> tuple[int, ...]:
        return tuple(self.words)

    def write(self, address: int, value: int, handheld_mode: bool) -> None:
        if handheld_mode:
            self._paired(address & HANDHELD_ADDRESS_MASK, value & 0xFF)
            return
        index = address % ENTRIES
        stored = value & CONSOLE_MASK
        self.words[index] = _widened(stored) if self.handheld else stored

    def _paired(self, address: int, value: int) -> None:
        if not address & 1:
            self.latch = value
            return
        self.words[address >> 1] = (value << 8 | self.latch) & HANDHELD_MASK
