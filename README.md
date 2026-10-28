# Sega VDP

The Sega 315-5124, 315-5246 and 315-5378 video display processors in Python, with the sound generator inside each, advanced one master clock tick at a time and held to Sega's Mark III reference manual.

English | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/sega-vdp-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/sega-vdp-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/sega-vdp-python)](https://github.com/gufranco/sega-vdp-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**2,608** distinct Master System and Game Gear images booted for **600** frames each, **0** property failures over the **794** retail ones on Sega's paging, **64** quotes located in the manual, **3** parts, **860** tests, **100%** statement and branch coverage, no dependencies beyond the standard library and two family members

```python
import segavdp

part = segavdp.Chip("315-5246", segavdp.Vram(fill=0))
part.reset()
part.read_status()

for register, value in {0: 0x06, 1: 0x40, 2: 0xFF, 8: 0x00, 9: 0x00}.items():
    part.write_control(value)
    part.write_control(0x80 | register)

part.write_control(0x00)
part.write_control(0xC0)
for colour in (0x00, 0x3F):
    part.write_data(colour)
    part.run_dots(64)

for address, value in {0x3800: 0x01, 0x0020: 0x80}.items():
    part.write_control(address & 0xFF)
    part.write_control(0x40 | address >> 8)
    part.write_data(value)
    part.run_dots(64)

for line in (1, 0):
    while (part.line, part.dot) != (line, 0):
        part.clock()

shown = []
for _ in range(3):
    part.clock()
    shown.append((part.shown, part.colour))
print(shown)
print(part.model, part.region, part.read_v_counter())
```

```
[('active', 63), ('active', 0), ('active', 0)]
315-5246 ntsc 0
```

A part powers up with scrambled registers, colour RAM and video memory, so the example resets it and reads the status once to clear the half-written command. Five register writes select mode 4, turn the display on, put the screen map at 3800h and zero both scrolls. Two colour RAM writes make colour 0 black and colour 1 white. The first cell of the screen map is pattern 1, whose top row starts with one dot of colour 1. Waiting for line 0 twice lets the vertical scroll latch at the top of a frame, as it does on the part.

## Install

| Requirement | Version                      |
| :---------- | :--------------------------- |
| Python      | 3.12 or newer                |
| git         | Any, to fetch the submodules |

```bash
git clone --recurse-submodules https://github.com/gufranco/sega-vdp-python.git
cd sega-vdp-python
export PYTHONPATH=.:ti-tms9918-python:ti-sn76489-python
python3 segavdp/doctor.py
```

This package composes two other members of the family instead of copying them. The TMS9918 modes come from `ti-tms9918-python` and the sound generator from `ti-sn76489-python`, both git submodules on the import path, which is what the `PYTHONPATH` line sets. A third submodule, `zilog-z80-python`, drives the census and the test cartridges. A source archive from the download-zip link carries no submodule and cannot run; clone with `--recurse-submodules` instead. Because it consumes members this way, the package is not installable from an index and publishes nothing there.

The doctor checks the machine and the checkout and ends with one line. Paste its whole output into any bug report.

```
  11 checks, nothing to report
```

Releases follow [Semantic Versioning](https://semver.org/) and are cut from the commit history by semantic-release. Every release is tagged and listed on the [releases page](https://github.com/gufranco/sega-vdp-python/releases).

## The interface

`segavdp.Chip(model, memory=None, seed=UNSET_SEED, region=None, handheld_mode=None)` builds one part. `model` is required. `memory` is any object with `read8(address)` and `write8(address, value)`, and the part builds a scrambled 16 KB `Vram` when it is left out. `region` is `ntsc` or `pal`, and the first the part runs in when left out. `handheld_mode` puts the Game Gear part in its own mode, which is where it starts; it is always off on the console parts.

| Model      | Aliases                           | Regions       | Screens             | Zoomed across | Legacy mode colours |
| :--------- | :-------------------------------- | :------------ | :------------------ | :------------ | :------------------ |
| `315-5124` | `5124`, `sms`, `mark3`, `markiii` | `ntsc`, `pal` | 192 lines           | 4 sprites     | A fixed table       |
| `315-5246` | `5246`, `sms2`                    | `ntsc`, `pal` | 192, 224, 240 lines | 8 sprites     | A fixed table       |
| `315-5378` | `5378`, `gg`, `gamegear`          | `ntsc`        | 192, 224 lines      | 8 sprites     | Colour RAM 16 to 31 |

### Calls

| Call                         | Effect                                                                                                                             |
| :--------------------------- | :--------------------------------------------------------------------------------------------------------------------------------- |
| `reset()`                    | Clears registers 0 and 1, the status flags and the half-written command, and moves the beam to the top of line 0. Returns the part |
| `write_control(value)`       | One byte to the control port: half of an address with its two command bits, or half of a register write                            |
| `write_data(value)`          | One byte to video memory, or to colour RAM after command 3. It lands after the access lead                                         |
| `read_data()`                | Returns the read buffer, then fetches the next byte                                                                                |
| `read_status()`              | Returns the status byte and clears the frame, overflow and collision flags and a pending line interrupt                            |
| `read_v_counter()`           | The V counter for the current line                                                                                                 |
| `read_h_counter()`           | The H counter as last latched                                                                                                      |
| `latch_h_counter()`          | Latches the H counter, as a change on a controller's TH line does                                                                  |
| `write_sound(value)`         | One byte to the sound generator inside the part                                                                                    |
| `read_port(address)`         | A read decoded on A7, A6 and A0 from 40h to BFh; `None` outside that range                                                         |
| `write_port(address, value)` | A write decoded the same way: data, control, or the sound generator                                                                |
| `tick()`                     | One master clock period, a third of a processor clock                                                                              |
| `clock()`                    | One dot, which is two ticks                                                                                                        |
| `run_dots(count)`            | `count` dots                                                                                                                       |

### State

| Attribute       | Meaning                                                                                                     |
| :-------------- | :---------------------------------------------------------------------------------------------------------- |
| `line`          | Line number, counted from the first active line. It steps 76 dots before the line's first active dot        |
| `dot`           | Dot number, counted from the first active dot                                                               |
| `shown`         | `active`, `border`, `blanking`, `sync` or `burst` for the last dot                                          |
| `colour`        | The colour RAM value of the last dot, six bits on the console parts and twelve on the Game Gear, or `None`  |
| `interrupt`     | True while the INT pin is asserted                                                                          |
| `status`        | The three status flags, read without clearing anything                                                      |
| `registers`     | The eleven registers as a `bytearray`                                                                       |
| `mode`          | The `Mode` the registers select: `name`, `height` and whether the taller screen's tables are in use, `tall` |
| `cram`          | The colour RAM: `entry(index)`, `entries()` and `write(address, value, handheld_mode)`                      |
| `sound`         | The sound generator inside the part                                                                         |
| `region`        | `ntsc` or `pal`                                                                                             |
| `handheld_mode` | Whether the Game Gear part is in its own mode                                                               |
| `lost`          | How many accesses were asked for before the one before them landed                                          |
| `model`         | The canonical model name                                                                                    |
| `part`          | The `Model` record                                                                                          |
| `memory`        | The video memory object                                                                                     |
| `cycles`        | Master clock ticks since the part was built                                                                 |

### Module contents

| Name                                       | Content                                                                                        |
| :----------------------------------------- | :--------------------------------------------------------------------------------------------- |
| `segavdp.MODELS`                           | The three `Model` records, keyed by canonical name                                             |
| `segavdp.Vram(fill=None, seed=UNSET_SEED)` | 16 KB of video memory, the TMS9918 member's own                                                |
| `segavdp.port(address)`                    | Which register a processor port reaches: `data`, `control`, `v counter`, `h counter` or `None` |
| `segavdp.NTSC`, `segavdp.PAL`              | The two region names                                                                           |
| `segavdp.UnknownModelError`                | Raised for a missing or unknown model name. The message lists the names accepted               |
| `segavdp.UnknownRegionError`               | Raised for a region the part does not run in                                                   |
| `segavdp.NoStereo`                         | Raised when a console part is asked for the Game Gear's stereo register                        |
| `segavdp.__version__`                      | The installed version                                                                          |

### Modules

Each module is a building block the part is made of, and a test or a caller may use it directly.

| Module               | Holds                                                                             |
| :------------------- | :-------------------------------------------------------------------------------- |
| `segavdp.core`       | The part itself, the port decode and the access leads                             |
| `segavdp.display`    | What each dot shows, in mode 4 and in the TMS9918 modes                           |
| `segavdp.background` | Mode 4 background cells, scrolling and the screen map address                     |
| `segavdp.sprites`    | Mode 4 sprite evaluation and one line of sprite dots                              |
| `segavdp.modes`      | Which mode and screen height the registers select                                 |
| `segavdp.timing`     | The frame layouts, the V and H counters and the dot of the line event             |
| `segavdp.palette`    | The colour RAM of both kinds of part, its intensities and the legacy mode colours |
| `segavdp.sound`      | The sound generator inside the part, built on `ti-sn76489-python`                 |
| `segavdp.models`     | The three `Model` records and the region names                                    |
| `segavdp.flags`      | The three status flags                                                            |
| `segavdp.errors`     | Everything the package raises                                                     |

```python
import segavdp

for name, model in segavdp.MODELS.items():
    print(name, model.aliases, model.regions, model.extended, model.zoomed_across)

for name in ("315-5124", "315-5246", "315-5378"):
    part = segavdp.Chip(name)
    print(part.model, part.region, len(part.kinds), part.handheld_mode)

print(
    segavdp.Chip("315-5246", region="pal").region,
    segavdp.Chip("gg", handheld_mode=False).handheld_mode,
)

try:
    segavdp.Chip("315-5313")
except segavdp.UnknownModelError as error:
    print(error)

try:
    segavdp.Chip("315-5378", region="pal")
except segavdp.UnknownRegionError as error:
    print(error)
```

```
315-5124 ('5124', 'sms', 'mark3', 'markiii') ('ntsc', 'pal') False 4
315-5246 ('5246', 'sms2') ('ntsc', 'pal') True 8
315-5378 ('5378', 'gg', 'gamegear') ('ntsc',) True 8
315-5124 ntsc 262 False
315-5246 ntsc 262 False
315-5378 ntsc 262 True
pal False
315-5313 is not a model this package covers; it has 315-5124, 315-5246, 315-5378
pal is not a region the 315-5378 runs in; it runs in ntsc
```

## The line counter

```python
import segavdp

part = segavdp.Chip("315-5124", segavdp.Vram(fill=0))
part.reset()
part.read_status()
for register, value in {0: 0x16, 1: 0x80, 10: 94}.items():
    part.write_control(value)
    part.write_control(0x80 | register)

for line in (200, 0):
    while (part.line, part.dot) != (line, 0):
        part.clock()
part.read_status()

raised = []
for _ in range(193 * 342):
    part.clock()
    if part.interrupt:
        raised.append(part.line)
        part.read_status()
print(raised)
```

```
[94, 189]
```

Sega's manual says to load register 10 with one less than the line to interrupt on. With 94, the request comes as the 95th line begins, counting lines from one, and again 95 lines later. The counter reloads outside the active display, so the third request of the frame never comes.

## The processor's access rate

Sega's manual says the part takes data no faster than every 29 T states in the active display and 16 in vertical blanking. Two test cartridges written against hardware go faster than both, so the model lands an access 26 T states after the one before it in the active display and never loses one in blanking. A second access that arrives while the first is still waiting replaces it.

```python
import segavdp


def spaced(gap, display):
    part = segavdp.Chip("315-5124", segavdp.Vram(fill=0))
    part.reset()
    part.read_status()
    part.write_control(0x40 if display else 0x00)
    part.write_control(0x81)
    while (part.line, part.dot) != (10, 0):
        part.clock()
    part.write_control(0x00)
    part.write_control(0x40)
    for value in (0x11, 0x22, 0x33):
        part.write_data(value)
        for _ in range(gap * 3):
            part.tick()
    part.run_dots(100)
    return [hex(part.memory.read8(address)) for address in range(3)], part.lost


print(spaced(26, display=True))
print(spaced(20, display=True))
print(spaced(12, display=False))
```

```
(['0x11', '0x22', '0x33'], 0)
(['0x0', '0x0', '0x33'], 2)
(['0x11', '0x22', '0x33'], 0)
```

## The census

```bash
python3 -m conformance.census "external/Master EverDrive" "external/EverDrive GG" --frames 600 --jobs 12
```

The census boots every image in a Master System and Game Gear library on a board built from this part, the `zilog-z80-python` processor and Sega's paging, and runs each for a fixed number of frames. A `.sms` image runs on the 315-5246 and a `.gg` image on the 315-5378 in its own mode. It accepts directories, zip archives and single images, counts each distinct image once by digest, prints a summary, writes [`conformance/corpus.json`](conformance/corpus.json), and exits 1 when a property breaks.

Two properties gate the run: the model raises no exception on any image, and every retail image on Sega's paging turns its display on. [`conformance/boards.json`](conformance/boards.json) names, by whole-file SHA-1 as MAME's software lists record them, the images built on another board, such as Codemasters' paging; those run without their board and are counted apart. Lost accesses are counted and named per image but gate nothing.

| Result of the last run                                                       | Count     |
| :--------------------------------------------------------------------------- | :-------- |
| Listings across both libraries                                               | 5,110     |
| Distinct images                                                              | 2,608     |
| Retail images on Sega's paging, the ones that gate                           | 794       |
| Images on another board, run without it                                      | 59        |
| Mode 4, 192 lines                                                            | 2,429     |
| Mode 4, 224 lines                                                            | 8         |
| Graphics II                                                                  | 68        |
| Graphics I                                                                   | 29        |
| Text with the Multicolor bit set                                             | 2         |
| The invalid text mode of mode 4                                              | 2         |
| Never turned the display on, none of them retail on Sega's paging            | 79        |
| Sprites 8 by 8                                                               | 1,778     |
| Sprites 8 by 16                                                              | 764       |
| Sprites 8 by 8, zoomed                                                       | 9         |
| Asked for a line interrupt                                                   | 1,011     |
| Lost accesses on retail images, 45% of them in CJ Elephant Fugitive          | 91,127    |
| Lost accesses on the rest, mostly from public-domain test programs and demos | 2,991,054 |

[`conformance/corpus.json`](conformance/corpus.json) holds those counts and nothing from any cartridge, so the suite checks them on a machine with no library.

## Test cartridges

```bash
python3 -m conformance.testroms "/path/to/5 Tools & Service Test Carts.zip"
```

[`conformance/testroms.json`](conformance/testroms.json) lists every test cartridge that exercises this part, by SHA-256, the script of controller presses each run takes, and what it printed.

| Cartridge                                    | Run on                                      | What the record holds                                                                                 |
| :------------------------------------------- | :------------------------------------------ | :---------------------------------------------------------------------------------------------------- |
| SEGA Master System TestSuite 0.32, by sverx  | 315-5124 at 60 Hz, 315-5246 at 60 and 50 Hz | Its System Info page names each part and each TV standard correctly, with no access lost              |
| V Counter Test Program, by Charles MacDonald | 315-5246 at 60 Hz                           | Its pages print 00h to DAh, then D5h to FFh, the run MacDonald's document prints, with no access lost |
| Line Interrupt Test #1, by Charles MacDonald | 315-5246 at 60 Hz                           | Stimulus only; 1 access lost                                                                          |
| Interrupt Test                               | 315-5246 at 60 Hz                           | Stimulus only; no access lost                                                                         |
| BG Test 0.01                                 | 315-5124 at 60 Hz                           | Stimulus only; 721 accesses lost                                                                      |
| Sprite Test                                  | 315-5246 at 60 Hz                           | Stimulus only; 600,408 accesses lost, written every 11 and 18 T states with the display on            |
| 64 Color Palette Test                        | 315-5124 at 60 Hz                           | Stimulus only; 15,568 accesses lost                                                                   |
| Color & Switch Test                          | 315-5124 at 60 Hz                           | Stimulus only; no access lost                                                                         |
| Palette Tool 1.0                             | 315-5246 at 60 Hz                           | Stimulus only; no access lost                                                                         |

The System Info page also names the console model, the region and the boot program. The census board answers those, not this part, so the record keeps them without judging them. Whether a console loses the writes the three stimulus cartridges lose here is not known; [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) says what would settle it.

## Is it right

Every fact Sega printed that a test can reach is held to the code. [`conformance/hardware.json`](conformance/hardware.json) carries each fact with its sentence and page, and [`conformance/hardware.test.py`](conformance/hardware.test.py) and [`conformance/display.test.py`](conformance/display.test.py) drive the part against them. `python3 -m conformance.quotes` finds every quoted sentence in the documents it names.

Every value the manual does not print sits under `notStated` in the same file, marked unverified, with its source and the measurement that would settle it. [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) lists what is still open. The places where two sources part, the manual among them, are in [`conformance/divergences.json`](conformance/divergences.json).

## Working on it

| Need                                                            | Where                                                               |
| :-------------------------------------------------------------- | :------------------------------------------------------------------ |
| Every gate and the order to run them                            | [CONTRIBUTING.md](CONTRIBUTING.md)                                  |
| The same material for a coding agent                            | [AGENTS.md](AGENTS.md)                                              |
| The standard this repository shares with the rest of the family | [FAMILY.md](FAMILY.md)                                              |
| Bug reports                                                     | [GitHub Issues](https://github.com/gufranco/sega-vdp-python/issues) |
| Security reports                                                | [SECURITY.md](SECURITY.md)                                          |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 segavdp/core.test.py
```

Each module has a test file beside it, named after it, and each runs on its own as above. Coverage is a hard gate at 100% statement and branch.

## References

- _Software Reference Manual for the SEGA Mark III Console_, Sega, undated, retyped. 45 pages, 184,840 bytes, SHA-256 `166f09331ba9df055f7a352f10c6a7843911470bc72d9347eda4a0de86e8cfce`. It is not in this repository. `python3 -m conformance.documents` downloads it from https://segaretro.org/images/d/d6/SoftwareReferenceManualForSegaMarkIIIEU.pdf and refuses any other file.
- _Sega Master System VDP documentation_, Charles MacDonald, 12 November 2002. 43,417 bytes, SHA-256 `dc16f8e687b8b137d9f7d457659135ebb7b21e6e7874250fac0719dd1eb6207c`, from https://www.smspower.org/uploads/Development/msvdp-20021112.txt.
- _SN76489_, SMS Power, the page maintained by Maxim, in its print view. 54,534 bytes, SHA-256 `14d146c13d4d98a04b2c2c05498753bc60197696cea1b73860bfa23416cd15ce`, from https://www.smspower.org/Development/SN76489?action=print.
- Genesis Plus GX, `core/hvc.h` and `core/vdp_render.c` at commit `a5834b3df455c49bb97bfaa328c20845831f576b`, https://github.com/ekeeke/Genesis-Plus-GX, for the H counter, the order of events in a line and the legacy mode colours. Facts only; no code is taken.
- MAME, `hash/sms.xml` and `hash/gamegear.xml` at commit `94fc55c9692b180dcb608e2e222e48315db5017a`, https://github.com/mamedev/mame, for the cartridge boards. Facts only; no code is taken.

## Citing this

[CITATION.cff](CITATION.cff) is updated with each release by the script that stamps the package version.

## License

MIT. See [LICENSE](LICENSE).
