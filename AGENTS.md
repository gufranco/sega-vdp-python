# Working in this repository

Read [FAMILY.md](FAMILY.md) first. It is the standard every member of this
family carries, byte for byte, and it decides most questions before they are
asked. What follows is only what is true of this member. [README.md](README.md)
is the document written for a person.

## What this project is, in one paragraph

A model of the Sega 315-5124, 315-5246 and 315-5378 video display processors,
the parts inside the Mark III, both Master Systems and the Game Gear, advanced
one master clock tick at a time. Each package holds a TI-derived video block
and a TI sound generator, so this member composes `ti-tms9918-python` for the
TMS9918 modes and `ti-sn76489-python` for the sound generator, and holds only
what Sega changed or added: mode 4, colour RAM, the line counter, the V and H
counters, the taller screens, the Game Gear's colour RAM and stereo register,
the port decode, and the sound generator's sixteen bit noise register. What
the manual prints comes from Sega's Mark III reference manual. What it does
not comes from Charles MacDonald's document, the SMS Power sound page and
Genesis Plus GX, marked unverified. What real software asks of the part comes
from a census over the Master System and Game Gear libraries and from nine
test cartridges.

## The interface a caller drives

- `segavdp.Chip(model, memory, region=..., handheld_mode=...)` builds a part.
  `model` is one of `315-5124`, `315-5246` or `315-5378`. `memory` is a `Vram`,
  and the part builds its own when it is left out. Everything comes up
  scrambled, so call `reset()` and read the status once, as real software
  does, before programming registers.
- `write_control`, `write_data`, `read_data`, `read_status`, `read_v_counter`,
  `read_h_counter` and `write_sound` are the port operations, and `read_port`
  and `write_port` decode a processor port on A7, A6 and A0 into them.
- `tick()` advances one master clock period, a third of a processor clock.
  `clock()` advances one dot, which is two ticks.
- After each dot, `shown` and `colour` describe it. `interrupt` is the INT
  pin, true while it is asserted.

Everything the package raises lives in
[`segavdp/errors.py`](segavdp/errors.py) and nowhere else.

This is a part, not a clocked part in the family's sense. It runs no program,
so it has no `step`, and it is built by `Chip`.

## The authority ladder

1. **[`conformance/hardware.json`](conformance/hardware.json) facts**, quoted
   from Sega's Mark III reference manual and matched against its text layer by
   [`conformance/quotes.py`](conformance/quotes.py).
2. **The test cartridges**, through
   [`conformance/testroms.py`](conformance/testroms.py), for what programs
   written against hardware print about this part.
3. **The cartridge libraries**, through
   [`conformance/census.py`](conformance/census.py), for what real software
   reaches.
4. **MacDonald's document, the SMS Power sound page and Genesis Plus GX** for
   what Sega never printed, each under `notStated` with `verified: false`.
   Genesis Plus GX carries MacDonald's copyright, so the two count as one
   source.

[`conformance/divergences.json`](conformance/divergences.json) records every
place two sources part, including the places the manual is contradicted by a
cartridge written against hardware.

## What is settled and what is not

**Settled: everything the manual prints and a test can reach.** Each fact in
[`conformance/hardware.json`](conformance/hardware.json) names, under `heldBy`,
the test in [`conformance/hardware.test.py`](conformance/hardware.test.py) that
holds it. One fact, the power-on register values, is marked unreachable: the
manual does not say whether the chip or the boot program sets them.

**Not settled: 38 things**, every entry under `notStated`, each in
[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) with what would close it. Do not close
one by argument.

## The access rate is measured from cartridges, not printed

The manual prints 29 T states between accesses in the active display and 16
in blanking. Two test cartridges written against hardware go faster than
both: the SEGA Master System TestSuite writes its text every 26 T states with
the display on, and MacDonald's Line Interrupt Test #1 writes every 12 with
it off. Both garble their screens on the model at the printed rates, so
[`segavdp/core.py`](segavdp/core.py) lands an access 26 T states after the one
before it in the active display and loses none in blanking.

**If you are about to change a lead, run the test cartridges before and
after.** A cartridge that starts printing garbage means accesses started
going missing.

## Files kept in `external/`

Everything this member reads and may not ship sits in `external/`, which git
ignores and Dropbox is told to leave alone, per FAMILY.md's "Where the files a
member reads are kept". [`artifacts.manifest.json`](artifacts.manifest.json)
names all 185 files by size, CRC32, MD5, SHA-1 and SHA-256:

- `external/Master EverDrive/`, 110 archives from the Master EverDrive pack of
  2022-05-04, which the census walks whole. One of them,
  `5 Tools & Service Test Carts.zip`, holds the nine test cartridges.
- `external/EverDrive GG/`, 75 archives from the EverDrive GG pack of
  2020-12-21, which the census walks whole.

```bash
python3 -m conformance.external
python3 -m conformance.external --describe external/<file>
```

The first says which are here, verified, missing or wrong. The second prints
the manifest entry for a file being added. A file added to `external/` gets an
entry in the same change, and a census over a library that is not in the
manifest is not a result anyone else can reproduce.

## The census board is not the console

[`conformance/harness.py`](conformance/harness.py) builds just enough of a
console to run cartridges: the processor, this part, 8K of RAM, Sega's own
paging and two controllers that read as nothing pressed unless a script
presses them. It starts every cartridge from the register values the manual
prints for power on, because cartridges such as the SMS Sprite Test rely on
them. It is not `sega-sms-python`. What the test suite's System Info page
says about the console model, the region and the boot program is the board's
answer, not this part's.

Four things it does were each found by a retail cartridge that stayed dark
without it:

- **A Master System board starts where the export boot program hands over.**
  The stack pointer is `DFF0h`, which the v1.3 and v2.0 boot programs load at
  `0003h`, and RAM `C000h` holds `A8h`, the memory control value Genesis Plus
  GX writes there when it starts a cartridge without a boot program. Ace of
  Aces reads `C000h` and calls before it sets a stack.
- **A Game Gear board answers ports 1 to 5 as registers**, at Genesis Plus
  GX's reset values: port 1 reads through port 2's direction bits, ports 2 and
  3 hold what was written, port 4 reads `FFh`, and port 5 keeps bits 3 to 7 of
  a write and reads its low three bits as zero. Lemmings, Mean Bean Machine
  and seven others poll port 5 until its low bits clear.
- **Every port is decoded on its low byte.** `IN A,(n)` puts A on the upper
  address lines, so a board that compared the whole address missed the Game
  Gear ports whenever A was not zero.
- **A frame counts as lit when the display was on during any line of it.** F1
  and Gunstar Heroes turn the display on for a band of lines and off before
  the frame line.

Each is held by a test in
[`conformance/harness.test.py`](conformance/harness.test.py). The line counter
change found by the same census lives in the part, recorded as the divergence
`line-counter-line`.

## Test cartridges

[`conformance/testroms.json`](conformance/testroms.json) lists every test
cartridge that exercises this part, by SHA-256, as FAMILY.md's fifth
requirement asks. All nine come from the Master EverDrive set's
`5 Tools & Service Test Carts.zip`, kept at
`external/Master EverDrive/` as [`artifacts.manifest.json`](artifacts.manifest.json) records.

- **Run, with a verdict: the SEGA Master System TestSuite 0.32.** Its System
  Info page tells the parts apart by how they behave. The record runs it on
  the 315-5124 at 60 Hz and on the 315-5246 at 60 and 50 Hz, and it names each
  part and each TV standard correctly.
- **Run, with a verdict: MacDonald's V Counter Test Program.** It prints the
  V counter on every line it scans, and the order is checked against the run
  MacDonald's document prints.
- **Run, stimulus only: the other seven.** They draw bars, colours and
  sprites for a person to judge. The record holds that each runs and how many
  accesses it lost. The SMS Sprite Test writes faster than any spacing known
  to work and loses writes on the model; whether a console does is not known.

```bash
python3 -m conformance.testroms [--write] <zip, folder or image ...>
```

With no argument it reads the folders and zips named in `TEST_CARTRIDGES`,
and with that unset, the zip kept under `external/`.
With none present it says so and exits 2, and CI turns that into a notice.
[`conformance/testroms.test.py`](conformance/testroms.test.py) replays the
recorded verdicts with no image present.

## Every gate, in the order to run them

```bash
export PYTHONPATH=.:ti-tms9918-python:ti-sn76489-python
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
uvx yamllint==1.38.0 --strict .
cov=(uvx --python 3.12 --from coverage==7.6.10 coverage)
"${cov[@]}" erase
for f in $(find segavdp conformance -name '*.test.py' | sort); do
  "${cov[@]}" run -a "$f" || echo "FAILED $f"
done
"${cov[@]}" report
```

Then the ones outside the coverage step:

```bash
python3 -m conformance.corpus
python3 -m conformance.speed
python3 -m conformance.documents --check
python3 -m conformance.quotes
```

And, with the libraries present, the three that read them:

```bash
python3 -m conformance.external
python3 -m conformance.census "external/Master EverDrive" "external/EverDrive GG" --frames 600 --jobs 12
python3 -m conformance.testroms
```

Everything under [`conformance/`](conformance) runs as a module. Run as a
script, its own directory goes on the import path and a file there shadows any
standard library module of the same name.

## Conventions that are not negotiable

| Thing                       | Rule                                                                                                                                              |
| :-------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------ |
| Language                    | Python only                                                                                                                                       |
| Comments                    | None in source or in build files, and a docstring counts as one. Names, small functions, constants and types carry what a comment would have said |
| Test layout                 | `<module>.test.py` beside the module it covers                                                                                                    |
| Test shape                  | Arrange, act, assert, each opened by its bare marker                                                                                              |
| Coverage                    | 100% statements and branches, enforced                                                                                                            |
| Types                       | `mypy` at strict, plus every optional error class                                                                                                 |
| Package manager for tooling | pnpm, never npm                                                                                                                                   |
| Commits                     | Conventional Commits, subject at most 50 characters                                                                                               |
| Documents                   | Read, quoted and pinned by digest. Never committed                                                                                                |
| Cartridges                  | Never committed, in any form, for any reason                                                                                                      |

The linter's ignores in [`pyproject.toml`](pyproject.toml) carry no comments, so
their reasons live here:

- `N818`: some exceptions are signals rather than failures. The standard
  library names those without the suffix too.
- `N999` and `PLR2004` in tests: a test file is named after its module with a
  dot, and its literals are the expected values.
- `T201` in `conformance/`, the doctor and `environment.py`: printing is their
  output.
- `BLE001` in the doctor, `environment.py` and the census: a check that throws
  has to become a line in the report rather than end the run. One image that
  raises must not throw away the census's results for every other image.
- `known-third-party` for `tms9918`, `sn76489` and `z80`: they are submodules
  on the import path, and the import sorter has to place them as such.
- `mypy_path` for the two composed members, and the `z80.*` override: the
  members are typed and checked through their imports, while the processor is
  checked in its own repository against its own gate.
- `@unittest\.skipUnless\(CLOCKED,` in the coverage exclusions: this member is
  not a clocked part, so the family tests that drive a clock are skipped here
  and their bodies never run.
- `@unittest\.skipUnless\(SOLD_AS_A_COMPONENT,`, `^def machine_mentions\(`
  and `^def listing\(`: these parts were never sold on their own, so the
  family check that sweeps for the names of machines a catalogue part shipped
  in is skipped here, and the helpers only it calls never run.

The formatter's ignores in [`.prettierignore`](.prettierignore) carry no
comments either, so their reasons live here:

- `pnpm-lock.yaml` and `package-lock.json`: the package manager writes them, in
  its own layout, on every install.
- `node_modules/`, `.venv/`, `venv/`, `build/`, `dist/` and `*.egg-info/`:
  installed or built, never written by hand.
- `.coverage`, `coverage.json`, `htmlcov/` and the tool caches: the output of a
  run, never committed.
- `docs/`, `specs/`, `.work/` and `.claude/`: local working material, never
  committed.
- [`zilog-z80-python`](zilog-z80-python), [`ti-tms9918-python`](ti-tms9918-python)
  and [`ti-sn76489-python`](ti-sn76489-python): submodules. Each is a member
  that formats and checks itself, and the commit pinned here is not this
  repository's to change.

## Layout

```
segavdp/
  core.py        the part: ports, the port decode, the access engine, the line events and status
  display.py     what each dot shows, mode 4 and the TMS9918 modes
  background.py  mode 4 background cells, scrolling and the name table
  sprites.py     mode 4 sprite evaluation and one line of sprite dots
  modes.py       which mode and screen height the registers select
  timing.py      the frame layouts, the V and H counters and the line event
  palette.py     colour RAM on both kinds of part, and the legacy mode colours
  sound.py       the sound generator inside the part, built on ti-sn76489-python
  models.py      the three parts and what differs between them
  flags.py       the status flags
  errors.py      everything this package raises
  doctor.py      what the machine and the package look like, for a report
  environment.py what the doctor reads about the machine
  version.py     rewritten by the release job and by nothing else
conformance/
  census.py         boots every image in a library you own and counts what it reaches
  harness.py        the board the census and the test cartridges run on
  boards.json       which images need a board other than Sega's paging, from MAME's lists
  corpus.json       the census counts, holding nothing from any cartridge
  corpus.py         replays them
  testroms.json     every test cartridge that exercises the part, and what each run printed
  testroms.py       runs the ones you hold on the census board and reads their screens
  external.py       which of the files in external/ are here, verified, missing or wrong
  family_external.test.py  the manifest complete, external/ ignored, nothing read from outside
  bench.py          the record and a programmed part, shared by the record's tests
  documents.json    the documents, by digest
  documents.py      brings them down and refuses any other file
  hardware.json     Sega's manual, fact by fact, and every value it does not print
  divergences.json  every place two sources part
  manual.py         each document's text, flattened to letters and digits
  quotes.py         every quote the records carry, found in the documents
  links.py          the weekly check that every cited address still answers
  speed.py          the throughput floor
  source.py         the check that no documentation string remains
  family_*.test.py  the family standard, held as tests, one topic a file
  family_member.py  what this member answers to them
  family_shared.py  what more than one of them reads
ti-tms9918-python/  the TMS9918 modes this part inherited, a pinned submodule
ti-sn76489-python/  the sound generator inside the part, a pinned submodule
zilog-z80-python/   the processor the census drives, a pinned submodule
external/           the libraries the census and the test cartridges read, never committed
artifacts.manifest.json  every file in external/, by size and every digest
```

## Things that will bite you

**`PYTHONPATH` has to name the two composed members.** Without
`ti-tms9918-python` and `ti-sn76489-python` on the path, `import segavdp`
fails. The doctor puts them there itself and says when they are missing.

**The latch comes up scrambled.** A part straight out of `reset()` may take
your first control byte as the second half of a pair. Read the status first,
which is what every real program does and what clears it.

**The scrolls latch at the line event, not at the first dot.** A part that
has just been reset is already at line 0, so the vertical scroll it draws with
is whatever came up at power on until a frame has passed.

**`line` steps 76 dots before the line's first active dot.** The V counter
and the line interrupt move at dot 266, ten dots after the active display
ends, so a loop waiting for a line sees it before its pixels.

**`region` is the TV standard and `shown` is what the last dot was.** The
TMS9918 member calls the second one `region`; here that name belongs to
`ntsc` and `pal`.

## Before calling anything finished

[`FAMILY.md`](FAMILY.md) carries a checklist under "What a new repository has to
have before it is a member". Every line on it was a defect found in one of these
repositories and fixed in all of them. Read it before adding a surface, and read
it again before saying a change is done.

**A check nobody has seen fail is not known to work.** Drive it, once,
deliberately, against input that should fail it.

**Silence and success produce the same output.** A census that walked no file
says so, and exits non-zero.

## What a change is expected to leave behind

A gate that would have caught the bug. A change to timing, the access leads or
a display mode also runs the test cartridges and the census over a real
library. The tests check what the manual says. The cartridges check what
programs written against hardware print, and the census checks what software
that ran on the part still does.
