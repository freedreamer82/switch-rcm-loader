# Case

See the scope and disclaimer notes in the [top-level README](../README.md).

A remix of [Raspberry Pi Pico Case (1 & 2, Wireless)](https://www.printables.com/model/1368704)
by nmattia, released CC0 — the mesh is embedded in `build.py`, which that
licence allows and which is why the attribution is repeated at the blob. The snap fit, the USB mouth, the LED window and the
BOOTSEL flexure are the original author's and are untouched; `build.py` only
cuts and fills what the RCM dongle needs.

## Files

| file | what |
| --- | --- |
| `base.stl` | bottom half |
| `lid.stl` | top half |
| `build.py` | builds both, checks them, and draws the pictures |
| `preview.png` | the assembled case |
| `preview-open.png` | lid lifted, board and header in place, jig slid out |
| `section.png` | dimensioned cross-section |

Assembled: 26 × 56 × 11.9 mm — of which 4.30 mm is the jig slot under the
floor. The case itself is 7.5 mm.

## What changed from the original

- **Floor closed, and the pin-tail channels sunk.** The stock 1.4 mm
  castellation channel is not enough — printed and tried, and solder on the
  pads bottoms out on it. Both rows now go down to **4.2 mm**: the pin 21-40
  row is the cable duct and the pin 1-20 row (`TAIL_Z`) meets it at the same
  level, which is one internal surface fewer for the slicer to make a mess of.
  There is room because the jig slot lowered the floor under both. No need to
  clip tails.

  Nothing plugs the donor's slots any more. A 0.6 mm plug used to go in and
  every bit of it was removed again by those deeper cuts — it was doing nothing
  but adding a coplanar face. What seals the floor underneath is the jig tray's
  own skirt, 2 mm of it.
- **Jumper window**, 4.2 × 9 mm, over pins 18-19-20 only. The 3-pin header
  and its cap come out through the top; the cap sits on the outside of the
  lid with about 4 mm of pin to grip.
- **SW / PC raised on the lid**, each outlined by a moat sunk 0.6 mm and joined
  to the pair of pins it means by a leader that runs from the edge of the
  jumper window straight onto the word. Which way round comes
  from the firmware, not from taste: `MODE_PIN` is GP14 on pin 19, pin 18 is
  GND and pin 20 is GP15. Cap on 18-19 pulls GP14 down and the board comes up
  as a host — that pair is the **SW**itch. Cap on 19-20 leaves GP14 on its
  pull-up: device, so that pair is the **PC**.

  **A moat, not a sunken plate, and not engraved strokes.** The lid prints
  outer-face-down, so this face *is* the first layer, and all three ways of
  marking it have now been printed:

  | | what happens |
  | --- | --- |
  | strokes cut in | holes in the first layers. Squash closes them and the perimeters round a narrow slot smear together. At a 0.45 mm stroke it printed as nothing; at 1.0 mm it was still unreadable. |
  | a whole plate sunk round them | the plate's floor is a 17 × 15 mm **bridge over open air**, 0.6 mm off the glass, laid while the fan is still off, with nothing under it but the letters. It sags onto them. |
  | a moat round each stroke | the face stays flat and whole, the letters stand on the glass, and the only thing bridging is a 1.2 mm ribbon. |

  The second row is both halves of what the second print looked like: a field
  that came out chewed, and lettering that came out chewed because the field
  landed on it. So what is sunk now is only `HALO` = 1.2 mm either side of
  every stroke — the strokes dilated, less the strokes — and the rest of the
  lid's face is left alone. The letters read because they are outlined, not
  because they sit in a tray.

  Four things followed from the change, each caught by the check rather than
  by looking at it:

  - the stroke is **1.20 mm**, not 1.00. It is a whole number of beads — 3 × 0.4
    or 2 × 0.6 — so the slicer lays it as full extrusions instead of two
    perimeters and a gap it has to fudge. That fudge is the other half of
    "printed badly".
  - the words moved **1.2 mm up the lid**. Sunk as a plate the lettering could
    sit 0.5 mm from the rim, because the plate stopped short of it. A moat does
    not stop short: it left a 0.4 mm rib of plate between itself and the edge
    roundover.
  - the leader lost its **kink**, and now touches the word. The kinked version
    climbed past the top corner of the jumper window and pinched the plate to
    0.35 mm on the way; the 0.8 mm of daylight it used to leave before the
    lettering left a peninsula of plate reaching in behind it. Joined, leader
    and word are one island with one outline.
  - it meets the word at **the pin's own height**, clamped to the word's cap
    height (`lead_y()`). Aimed at the middle instead, SW's leader arrived at
    38° to the S and the moat closed to a point in the corner. Aimed at the
    foot, the leader and the foot of the S continue into each other. PC's pin
    gap is level with its own word, so it gets a straight horizontal leader.

  Two leaders leaving the same edge 2.54 mm apart and arriving 7.2 mm apart
  trap a wedge of plate between them, and a wedge has a point. There is
  nowhere to move it to, so `fan()` takes it into the moat and the leaders come
  out as its two edges.

  The **W needs a cell of its own**, which is what `GLYPH_W` is for. Its legs
  pass within 0.331 of the glyph width of each other, so at a 1.2 mm stroke a
  2.8 mm cell puts them 0.0 apart and they merge into a blob. 5.6 mm leaves
  0.65, clear of a bead. Nothing else in SW or PC is dense enough to care.

  The check is a morphological **opening** — erode by half a bead, dilate
  back — and what the opening removes is what the nozzle cannot lay down. The
  version before it tested whole connected pieces, which cleared a 0.5 mm neck
  inside an otherwise fat region; and it eroded from the edge of its own
  sampling grid, which produced false alarms until the border was excluded.
  Its window is now derived from the marking (`marking_box()`): the literal it
  replaces stopped 5 mm short of the W, so the one check that would have caught
  a merged letter was never looking at it.
- **Cable duct.** The power cable is soldered to the *underside* of the
  board, so it runs under it, never over: a 4 mm wide, 3.75 mm deep duct sunk
  into the floor along the pin 21-40 row, from the far end wall all the way to
  pins 39 and 38 (VSYS and GND) at the USB end. It replaces the stock 1.4 mm
  castellation channel on that side and is deeper than it, which there is
  room for now that the jig slot has lowered the floor. It is open upwards
  into the cavity for its whole length, so the board is its lid and there is
  nothing to bridge.
- **Cable entry is a notch, not a hole.** The cable is soldered before the
  board goes in, and the USB-A plug on its far end will not thread through
  anything a dongle can afford — so the end wall is open from the duct right
  up to the top of the base and the cable drops in from above. That in turn
  fixes the duct depth: a 4 mm cable lying in it tops out at +0.30 mm, and
  the lid's rim comes down to +0.50, so the lid closes over the cable instead
  of onto it and needs no notch of its own. The duct floor also has to put the
  cable *below* the cavity floor, or it lifts the board off its seat — hence
  −4.20 for a 4 mm cable, not −3.70.

  `CABLE_D` is the one number to measure: put a caliper on the jacket and set
  it. The duct depth and the lid tongue's cradle both follow. It is **3.0**
  here, measured on the cable this was built for. Getting it too big only loses
  the tongue's grip; too small and the cable jacks the board off its seat.
  Checked at 3.0, 3.6 and 4.0.
- **Cable tongue, grown off the lid.** What plugs the notch above the cable is
  part of `lid.stl`, not a separate piece. It descends into the notch until it
  meets the cable, and its underside is the cable's own radius less
  `CABLE_CLAMP`, so it beds 0.2 mm into it rather than resting on the crown.
  That is the strain relief: 1.7 mm³ of interference.

  This started life as a separate printed gland with a tooth that dropped into
  a pocket in the notch wall. It was printed, and it did not hold. A loose plug
  in a straight slot cannot be locked without a flexure, and a 4 mm slot has no
  room for one, so every version of that idea came back to friction. Growing
  the same shape off the lid solves it by not being a separate part at all: the
  lid's own snap is what retains it, there is nothing to lose, and it costs
  nothing to print.
- **Four ribs on the lid that hold the board down.** The donor's locating pegs
  stop at z = 1.28, which is 0.28 mm above a 1 mm board — enough to locate it,
  nothing to keep it there, and 2.55 mm of clear air above. Printed, the board
  lifts straight out of the case. The ribs land on it with 0.1 mm of bite. They
  are 0.9 mm blades on purpose: if the print comes out over size a thin blade
  deforms, where a post would hold the lid off its snap.

  **Where they land took five goes.** Three of the attempts were mine and all
  three were wrong:

  | \|x\| | what was wrong |
  | --- | --- |
  | 9.5 | on the castellated pads — copper runs to 2.4 mm in from the edge, so past 8.1 is on it. One rib sat on pin 40, a pad from where the cable is soldered. |
  | 7.0 | off the copper, but one rib landed on the **BOOTSEL flexure**. A rib on a spring holds nothing and jams the button. |
  | 5.7 | borrowed from *Raspberry Pi Pico Case Top V2*, which touches a Pico at \|x\| 5.15…6.25 on the mounting-hole line. Better, but one rib still sat on a 0.95 mm component. |

  What settled it was a scan of the board. `BOARD_KEEPOUT` is that scan reduced
  to a table: a 1 mm grid of the tallest thing in each cell, `.` for bare
  board, marked conservatively so the keep-out is slightly larger than the
  truth. **Measurements, not somebody's model** — the same principle as the jig
  profile. The hand-written component boxes are gone from the checks.

  **There are three, not four, and that is deliberate.** The scan says the
  −x/+y quadrant has no room at all: the flexure owns y 8.5…17.9 of the lid and
  the LED hole 20.9…22.5. On the +y half the only bare ground left was a
  two-millimetre window at y +11…+12. A land built round the locating peg was
  tried there and thrown out — a ring only has to be 0.1 mm oversize to stop
  seating — and a short blade squeezed into the window was dropped too. Better
  a support that is not there than one in a place it does not belong. The USB
  half is held by its two locating pegs and by the connector sitting in the
  case mouth.

  ```
  4.3-5.2 mm in from the pin 21-40 edge,  43.7-47.3 mm from the USB end
  4.5-5.5 mm in from the pin 1-20  edge,  43.7-47.3 mm from the USB end
  4.5-5.5 mm in from the pin 1-20  edge,  29.2-32.8 mm from the USB end
  ```

  Three checks guard them, and each caught a real mistake: the footprint must
  be over bare `BOARD_KEEPOUT`, must not reach past |x| = 8.1 onto the pad
  copper, and the lid must be **solid over the footprint grown by
  `HOLD_CLEAR`** — read off the finished lid, not off a list. Put a foot back on
  the component and it says:

  ```
  ON A COMPONENT: foot x 5.2..6.2 y 17.2..20.8 hits a 1 mm tall part at (6.0, 21.0)
  ```

- **Jig rail slot** under the floor, opening at the same end as the cable and
  1 mm off centre — the cable duct wants one side of the floor and the sunk
  pin-tail channel the other, and the slot has to leave a wall between. It
  clears the channel by 1.47 mm. It is
  not a box: it has the jig's rail profile, so the jig slides in the way it
  slides into a Joy-Con. Two straight steps, 9.90 mm for the flange and
  7.90 for the tongue. It goes in upside
  down, which buries the 9.90 chamber and leaves a 7.90 mouth at the open
  underside — 0.61 mm of lip a side against a 9.09 flange, so too wide
  to fall out, and the shoulder stops it lifting. One bump on each wall near
  the mouth keeps it from working its way out. This is the whole reason the
  case is 11.9 mm and not 7.5 — a 4 mm jig has to go somewhere.

  **The mouth is flared**, because of the first print: it opens out by 0.45 mm
  a side over the first 2.5 mm (`JIG_FLARE`), so the jig finds the rails
  instead of having to arrive on them.
- **Nothing done to the lid** beyond the window. The cable runs underneath,
  so the lid needs no pass-through and no wire channel, and keeps its full
  2 mm.

## Jig fit

The profile is `JIG_FLANGE_W` / `JIG_TONGUE_W` = 9.90 / 7.90 — the jig plus
0.4 mm a side. Straight steps, deliberately not following the tongue's taper:
the extra slack up there costs nothing.

**It was 9.70 / 7.70 and that is a press fit.** Those are `RCM_Holder_v1`'s own
numbers, 0.3 mm a side, and they are right for what that model is: a tray, open
at the top, that the jig is dropped into. This is a horizontal rail, printed,
and three separate things eat the same 0.3 mm —

- the mouth is a **first layer** and elephant-foots inwards,
- the flange chamber's roof is a **bridge** and sags down into it,
- the ledge the flange rides on is an **overhang** and droops.

— which is why the first print went in under force and then had to be fought
back out. The vertical was worse than the width: 0.20 mm of roof clearance and
0.08 mm under the flange, against sag and droop of about that much. It is now
`JIG_ROOF` = 0.30 over the tip and `JIG_DROP` = 0.25 under the flange.

Everything else comes off `JIG_PROFILE` — how deep the slot is, how far down
the step sits, how much the floor has to grow, how tall the case ends up. So
the two widths are the only numbers to touch: rattles, lower them; will not go
in, raise them. `JIG_TONGUE_W` is also the mouth, so it is what the retention
check measures — 8.09 is the most it can be and still leave 0.5 mm of lip
against the 9.09 flange. `JIG_DETENT` is how hard it clicks, and the clearance
eats it: at 9.70 it left 0.2 mm a side of real interference, which is a lot to
shove a 4 mm rail past, and at 9.90 it leaves 0.1. It should click, not lock.

The step height is worth a word. It is derived, not typed: it goes `JIG_DROP`
below the last height at which the jig is still wider than the tongue slot,
which is where its flange ends. Put it even 0.1 mm high and the 9.09 flange
fouls the 7.90 tongue slot, which shows up only as a jig that will not go in.

The script checks the profile against the jig's measured outline at every
height, then slides the profile through the finished slot at three positions —
and then does it again **0.3 mm off centre, 0.25 mm up and both at once**. That
last one is the check the first print would have failed: the nominal position
fitting is also true of a press fit, and what matters is whether there is room
to be wrong by as much as a printer is wrong by.

## Pictures

`build.py` draws them itself — there is no CAD application in the loop, and
nothing to install beyond the Python packages below.

The section comes from matplotlib and carries a scale, so it can be measured
off. The two 3-D views come from a z-buffer rasteriser in `render()`, about
sixty lines of numpy. That is there rather than matplotlib's 3-D because
mplot3d sorts faces by centroid, and every interesting view here has parts
interpenetrating — case, board, header, jig — where centroid sorting draws
nonsense. Per-pixel depth gets it right.

The Pico, its connector, the header and the jumper cap are stand-ins built
from datasheet dimensions, not scans: they are there to show what has to clear
what, not to portray your board.

Drawing is most of the runtime. `./build.py --fast` skips it.

## Printing

Two parts: `base.stl` and `lid.stl`. Both print in the orientation they are
saved in.

0.4 mm nozzle, 0.2 mm layers, no supports. Both parts print in the orientation
they are saved in. Neither the jig slot nor the cable duct needs support: the
duct is open at the top, and the jig slot opens at the bed as a 7.90 mm slit
with one 1 mm ledge per side and a 9.90 mm bridge over it.

Three settings matter more here than usual, because the geometry cannot fix
any of them:

- **Top solid layers, 5 rather than 3, and infill 25% or more.** The inside of
  the base has several floors at different heights — the cavity at 0, the two
  channels at −4.2, the jig slot's roof — and every one of them is a *top
  surface* the slicer has to close over infill. Three layers over 15% infill is
  what makes them look chewed. Ironing on top surfaces helps further.
- **Elephant-foot compensation on, 0.1–0.2 mm.** Both parts care, for opposite
  reasons. On the base it is the jig slot's mouth: that 7.90 mm slit is a first
  layer, and what squashes out of it is clearance the jig needed. On the lid it
  is the moat: 1.2 mm of it, with letters on one side and the face on the other,
  both spreading into it.
- **A clean first layer on the lid**, not a squashed one. Its outer face,
  lettering and all, is layer one. There is nothing to gain from extra squish
  here — the face is 26 × 56 mm of flat contact.

The moat is a bridge, but a 1.2 mm one, and it is over in a single layer. There
is nothing to set for it.

## Regenerating

```
pip install trimesh manifold3d rtree numpy scipy matplotlib pillow
python3 build.py
```

No CAD application, and no downloads. The donor case is carried inside
`build.py` at the bottom as delta-coded LZMA in base85: 43 kB against 1.1 MB
of STL, coordinates kept to a micron. To swap it, `./build.py --pack that.stl`
and paste what it prints over `DONOR_MESH`.

The jig is **not** a mesh in here. It is `JIG_PROFILE`, 21 rows of half-width
against height taken off its rail section at every place the section changes
and nowhere else, plus `JIG_LEN`. That is all the slot needs, and it means the
only thing this file carries of anyone else's is the case it is a remix of.
Faithful to ±0.04 mm, finer than a caliper on a printed part resolves.

Everything downstream follows from the table on its own: slot depth, where the
step sits, how far the floor grows, how tall the case ends up. To fit a
different jig, measure yours and retype those rows.

One consequence worth stating: the slide-through check now runs the *measured
profile* through the slot rather than a donor mesh. It still catches every
geometric mistake — it caught the step height and the clearances — but it
cannot catch a jig whose real section differs from the table. Measure carefully.

Every dimension is measured off those meshes, so the script also self-checks:
watertightness,
an unchanged footprint, at least 0.5 mm of material in every column under the
board, that no piece of the marking is finer than `NOZZLE` (an erosion by
half a bead — whatever vanishes is a feature the printer cannot lay down), a clear path for the jumper, a clear run for the cable from outside the
end wall to pin 39, room to drop that cable in from above, clearance between
the cable and the lid's rim, that the lid's tongue misses the base and beds
into the cable, and that the hold-down ribs miss the base and land on the
board. For the jig it does the real thing: puts
the jig's profile in the slot at three positions along the slide, then four
more off centre and off the roof, and checks that not one of its corners ends
up inside plastic. It exits non-zero if any check fails.
