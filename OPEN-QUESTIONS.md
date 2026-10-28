# Open questions

What this project does not know for certain, and what it would take to find out.

Everything here is a place where being faithful is still a claim rather than a
measurement. The only Sega document is the Mark III reference manual, a retyped
copy that describes what a programmer sees and never the chip's timing. Below it
sit Charles MacDonald's VDP document and the SMS Power sound generator page,
which are leads rather than authorities, Genesis Plus GX, which shares their
lineage, and the cartridge libraries and test cartridges, which say what software
reaches but not what the part does with it.

Every entry is also in [`conformance/hardware.json`](conformance/hardware.json)
under `notStated`, or in [`conformance/divergences.json`](conformance/divergences.json),
so a program can read what a person reads here.

## What would settle almost all of them

A console of each part and a cartridge with writable save memory. A test program
that times its own port accesses against the V and H counters, writes what it
measured to save memory, and is read back off the card settles the access rate,
the line events, the counters and the interrupts at once. A Game Gear and an
EverDrive GG are available for the 315-5378; no console of the other two parts is.

## What the manual does not print

### Whether every port from 40h to BFh reaches the part

**This package does.** A7, A6 and A0 decode every port from 40h to BFh.

**Why it is open.** The manual names four ports and says nothing of mirrors.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Read port 41h and port 7Fh on a console and compare.

### When the low address byte lands

**This package does.** true.

**Why it is open.** The manual says the command register takes two bytes, not when the low address byte lands.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Write one control byte, then read the data port, on a console.

### Whether a data write loads the read buffer

**This package does.** true.

**Why it is open.** The manual does not describe a read buffer.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Write a byte to the data port, then read it back with no read setup between.

### What a second access does to one still waiting

**This package does.** a second access asked for before the first lands replaces the first.

**Why it is open.** The manual prints how often the part can be reached, not what happens when it is reached faster.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002, whose explanation is a guess in its own words, and the TMS9918 member's measured rule, inherited by assumption.

**What would settle it.** A logic analyser on the VDP's address, data and interrupt pins of a running console, or a test cartridge that writes what it measured to save memory, as decisions.md D8 of the plan describes

### How soon an access lands

**This package does.** {"activeTicks": 78, "blankingTicks": 30}.

**Why it is open.** The manual's bounds are rates for software to keep, not measurements of the part, and two test cartridges written against hardware exceed both. In the active display this package lets an access land 26 T states after the one before it: the SEGA Master System TestSuite, built on devkitSMS and run on consoles, writes its text every 26 T states with the display on, faster than the printed 29. In blanking it waits 10 T states, under the 11 the processor needs to issue two writes back to back, so no access there is lost: Charles MacDonald's Line Interrupt Test #1 writes every 12 T states with the display off, faster than the printed 16. divergences.json records both.

**Where the value came from.** The spacing measured on the census board from the two test cartridges, at three master ticks per processor clock.

**What would settle it.** A test cartridge that writes video memory at decreasing spacings in the active display and in blanking, reads every byte back and reports the first spacing that loses one, run on each console part.

### Where in a line the V counter steps and the interrupts rise

**This package does.** {"dot": 266, "hCounter": "0x85"}.

**Why it is open.** Neither document says where in a line the V counter steps or the interrupts rise.

**Where the value came from.** Genesis Plus GX at a5834b3df455c49bb97bfaa328c20845831f576b, https://github.com/ekeeke/Genesis-Plus-GX. Its core/hvc.h carries Charles MacDonald's copyright, so it counts with his document as one lineage. Facts only; no code is taken. MacDonald's document says it does not know.

**What would settle it.** A logic analyser on the VDP's address, data and interrupt pins of a running console, or a test cartridge that writes what it measured to save memory, as decisions.md D8 of the plan describes

### On which line the frame flag rises

**This package does.** {"192": "0xC1", "224": "0xE1", "240": "0xF1"}.

**Why it is open.** The manual says the frame request comes from vertical blanking, not on which line.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Read the V counter in the frame interrupt handler on a console.

### On which lines the line counter counts and reloads

**This package does.** {"countsOn": "lines 0 to the screen height", "reloadsOn": "every later line"}.

**Why it is open.** The manual gives the request lines, not when the counter reloads.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Program register 10 in the bottom border and count the first request of the next frame.

### Which values the V counter takes

**This package does.** the runs in segavdp/timing.py.

**Why it is open.** The manual names the gun's vertical register only.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Read port 7Eh on every line of a frame on each region and height.

### Which values the H counter takes

**This package does.** {"runs": ["0x00-0x93", "0xE9-0xFF"], "dotZero": 0}.

**Why it is open.** The manual names the gun's horizontal register only.

**Where the value came from.** Genesis Plus GX at a5834b3df455c49bb97bfaa328c20845831f576b, https://github.com/ekeeke/Genesis-Plus-GX. Its core/hvc.h carries Charles MacDonald's copyright, so it counts with his document as one lineage. Facts only; no code is taken. MacDonald's own table was taken on a Genesis and does not add up to 342 dots.

**What would settle it.** Latch the counter from the gun's TH line at known dots on a console.

### Which mode bits select the taller screens

**This package does.** {"224": "M2 and M1", "240": "M2 and M3"}.

**Why it is open.** The Mark III manual describes the first part only, which has no taller screen.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Select each combination on a second console part and count the active lines.

### What register 2 bit 0 does on the first part

**This package does.** R2 bit 0 ANDs bit 4 of the row.

**Why it is open.** The manual tells software to write FFh to R2's low bits and does not say what other values do.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Clear R2 bit 0 on a first console part and draw rows 16 to 23.

### What register 5 bit 0 does on the first part

**This package does.** R5 bit 0 clear reads positions and indices from the low half.

**Why it is open.** The manual prints R5 bit 0 as 1 and nothing else.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Clear R5 bit 0 on a first console part with different data in each half.

### What register 6 bits 0 and 1 do on the first part

**This package does.** {"R6 bit 1": "index bit 8", "R6 bit 0": "index bit 6"}.

**Why it is open.** The manual lists two valid R6 values only. Which low bit masks which index bit is this package's reading of an order the source does not spell out.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Clear each R6 low bit alone on a first console part with sprites using each index bit.

### How many sprites a line zooms across

**This package does.** {"315-5124": "four sprites wide", "others": "eight"}.

**Why it is open.** The Mark III manual does not mention zoom.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Zoom eight sprites on one line on each console part.

### Whether D0h ends the sprite table on a taller screen

**This package does.** D0h ends the table only on a 192 line screen.

**Why it is open.** The Mark III manual has no taller screen.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Put D0h in the table on a 224 line screen.

### On which line a sprite starts

**This package does.** a sprite starts on the line after its Y.

**Why it is open.** The manual says vertical position, not its offset.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Place a sprite at Y 0 and find its first line.

### Whether sprites off the screen count toward an overflow

**This package does.** true.

**Why it is open.** The manual says nine sprites on a raster line.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Put nine transparent sprites on one line off the screen's right edge.

### Which status bit is the collision flag

**This package does.** 5.

**Why it is open.** The manual prints bit 5. MacDonald prints bit 5 in his status table and bit 6 in his sprite section.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002, which contradicts itself; divergences.json records it.

**What would settle it.** Overlap two sprites and read the status on a console.

### What fills the dots fine scroll uncovers

**This package does.** the backdrop.

**Why it is open.** The manual says scrolling wraps, not what fills the dots the fine scroll uncovers.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002, which also says sprite pattern data sometimes shows there and that how is unknown.

**What would settle it.** Scroll by 1 to 7 and photograph the left edge on a console.

### When each scroll register is latched

**This package does.** {"horizontal": "at the line event", "vertical": "at the start of the frame"}.

**Why it is open.** The manual says R9 is latched in vertical blanking. Where R8 is latched is not printed.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002, and Genesis Plus GX at a5834b3df455c49bb97bfaa328c20845831f576b, https://github.com/ekeeke/Genesis-Plus-GX. Its core/hvc.h carries Charles MacDonald's copyright, so it counts with his document as one lineage. Facts only; no code is taken for the order of drawing and interrupting in a line.

**What would settle it.** A logic analyser on the VDP's address, data and interrupt pins of a running console, or a test cartridge that writes what it measured to save memory, as decisions.md D8 of the plan describes

### Which colours a console part shows in the TMS9918 modes

**This package does.** ["0x00", "0x00", "0x08", "0x0C", "0x10", "0x30", "0x01", "0x3C", "0x02", "0x03", "0x05", "0x0F", "0x04", "0x33", "0x15", "0x3F"].

**Why it is open.** No document prints the colours a console part shows in the TMS9918 modes.

**Where the value came from.** Genesis Plus GX at a5834b3df455c49bb97bfaa328c20845831f576b, https://github.com/ekeeke/Genesis-Plus-GX. Its core/hvc.h carries Charles MacDonald's copyright, so it counts with his document as one lineage. Facts only; no code is taken, core/vdp_render.c tms_crom. MacDonald describes the palette as hardwired without giving it.

**What would settle it.** Photograph each of the sixteen colours in Graphics I on each console part.

### Which colours the Game Gear part shows in the TMS9918 modes

**This package does.** colour RAM entries 16 to 31.

**Why it is open.** No Sega document describes the Game Gear part.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Draw each colour in Graphics I on a Game Gear.

### How the Game Gear part writes its twelve bit colours

**This package does.** {"entries": 32, "bits": 12, "latch": "even byte latched, odd byte stores the pair"}.

**Why it is open.** No Sega document describes the Game Gear part.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Write single even bytes on a Game Gear and look for a change.

### How the Game Gear part stores a six bit colour

**This package does.** a six bit write is widened to twelve by repeating each two bit component.

**Why it is open.** The source says the two modes share colours without saying how a six bit value is stored in a twelve bit entry.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002, for the sharing; the widening is this package's.

**What would settle it.** Write a colour in Master System mode, switch the Game Gear to its own mode, and photograph it.

### Whether register 0 bits 0 and 5 do anything on the Game Gear part

**This package does.** applied everywhere.

**Why it is open.** The source says R0 bits 0 and 5 have no effect on a Game Gear, which may mean nothing visible in its smaller window. This package applies both on every part.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Set R0 bit 5 on a Game Gear and read the colour of dot 48 on its window.

### What the status byte's low five bits read

**This package does.** scrambled at power on and held.

**Why it is open.** The manual says bits 4 to 0 have no significance.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Read the status many times on a console and record the low bits.

### Whether the sprite shift bit works in the TMS9918 modes

**This package does.** 8.

**Why it is open.** The manual describes mode 4 only.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Set R0 bit 3 in Graphics II with a sprite at X 8.

### What a fifth sprite reports in the TMS9918 modes

**This package does.** a fifth sprite in a legacy mode sets bit 6 and leaves the low bits alone.

**Why it is open.** No document says what a Sega part reports for the TMS9918 fifth sprite.

**Where the value came from.** This package's choice, from the TMS9918 member's rule and MacDonald's note that the low bits are not set.

**What would settle it.** Put five sprites on a line in Graphics II on a console and read the status.

### What the invalid text mode draws

**This package does.** the backdrop only.

**Why it is open.** The source describes the mode only loosely, and no fact here is solid enough to draw it.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Select each invalid text combination on each console part and photograph it.

### What the part's reset does

**This package does.** {"registers": "R0 and R1 cleared", "position": "line 0, dot 0", "status": "cleared"}.

**Why it is open.** Nothing printed says what the part's reset input does.

**Where the value came from.** The TMS9918 member's reset, inherited by assumption.

**What would settle it.** Pulse the console's reset with known register contents and read them back through their effect.

### How a 240 line screen runs at 60 Hz

**This package does.** {"lines": 262, "vCounter": ["0x00-0xFF", "0x00-0x05"]}.

**Why it is open.** The source prints a counter run of 263 values for a 262 line frame and says the screen rolls.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Select the 240 line screen on an NTSC second console part and read the V counter every line.

### Which of two overlapping sprites is on top

**This package does.** the lower numbered sprite wins.

**Why it is open.** The manual says the higher numbered sprite is on top. divergences.json records why this package does the opposite.

**Where the value came from.** Charles MacDonald, Sega Master System VDP documentation, 12 November 2002.

**What would settle it.** Overlap sprite 0 and sprite 1 on a console.

### How wide the noise shift register is and where it is tapped

**This package does.** {"bits": 16, "taps": "0x0009"}.

**Why it is open.** TI's data sheet does not print the register, and no Sega document describes the copy inside the VDP.

**Where the value came from.** SMS Power, SN76489, the page maintained by Maxim.

**What would settle it.** Record white noise from a console's audio output.

### What a noise write leaves in the shift register

**This package does.** 0x8000.

**Why it is open.** The TI data sheet says a noise write clears the register, not to what.

**Where the value came from.** SMS Power, SN76489, the page maintained by Maxim.

**What would settle it.** Record periodic noise right after a noise register write.

### What a tone period of zero or one does

**This package does.** periods 0 and 1 hold the output high.

**Why it is open.** The TI data sheet does not say what a zero period does.

**Where the value came from.** SMS Power, SN76489, the page maintained by Maxim.

**What would settle it.** Write periods 0 and 1 and record the output.

### What the sound generator holds at power on

**This package does.** {"periods": 0, "attenuations": 15}.

**Why it is open.** No document prints the part's power-on state; the source hedges its own claim.

**Where the value came from.** SMS Power, SN76489, the page maintained by Maxim.

**What would settle it.** Record a console's audio output before software writes the generator.

### How the Game Gear part's stereo register routes each channel

**This package does.** {"right": "bits 0 to 3", "left": "bits 4 to 7", "powerOn": "0xFF"}.

**Why it is open.** No Sega document describes the Game Gear part. The power-on value is this package's.

**Where the value came from.** SMS Power, SN76489, the page maintained by Maxim.

**What would settle it.** Write each bit and listen on each side of a Game Gear's headphone output.

## Where sources part

Every open disagreement in [`conformance/divergences.json`](conformance/divergences.json) is the same question as one of the entries above, seen from the documents' side: the sprite priority the manual prints, the access rates it prints, the frame flag line, the H counter table and the 240 line screen at 60 Hz.

## What is deliberately not modelled

### The Game Gear's screen

The part renders the full 256 by 192 picture in both modes. Which 160 by 144 window the Game Gear's screen shows, and how it squeezes a Master System picture into it, belongs to the board and its screen, not to this part.

### The bank number shift in register FFFCh

The census board pages cartridges the way retail Sega boards do and leaves out the bank shift the manual prints for a development board. The cartridge mapper is `sms-mapper-python`'s to model.
