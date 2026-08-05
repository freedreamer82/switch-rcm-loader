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

Assembled: 26 × 56 × 11.7 mm — of which 4.20 mm is the jig slot under the
floor. The case itself is 7.5 mm.

## What changed from the original

- **Floor closed.** The two GPIO slots in the underside are sealed from below.
  What was left inside as a 1.4 mm channel for soldered pin tails turned out
  not to be enough — printed and tried, and solder on the pads bottoms out on
  it. The pin 1-20 row is now sunk to **3.2 mm** (`TAIL_Z`), which there is
  room for because the jig slot lowered the floor under it; the pin 21-40 row
  is the cable duct, deeper still. No need to clip tails any more.
- **Jumper window**, 4.2 × 9 mm, over pins 18-19-20 only. The 3-pin header
  and its cap come out through the top; the cap sits on the outside of the
  lid with about 4 mm of pin to grip.
- **SW / PC engraved** beside the window, 0.6 mm deep, each word joined to the
  pair of pins it means by a leader with a kink in it. Which way round comes
  from the firmware, not from taste: `MODE_PIN` is GP14 on pin 19, pin 18 is
  GND and pin 20 is GP15. Cap on 18-19 pulls GP14 down and the board comes up
  as a host — that pair is the Switch. Cap on 19-20 leaves GP14 on its
  pull-up: device, so that pair is the PC.

  The letters are a stroke font drawn in `build.py`, not typeset: seven glyphs
  is not worth a font dependency.

  **This is sized for the nozzle, not for the drawing.** The first version had
  a 0.45 mm stroke at 2.4 mm cap height and printed as *nothing* — a groove
  narrower than the nozzle is a groove the slicer omits. Everything is now
  1.0 mm or wider at 3.8 mm cap height, and `NOZZLE` (0.60) is what it is all
  judged against. Two side effects worth knowing: the P's bowl sits at 0.35 of
  the cap height rather than half, because a half-height bowl leaves 0.5 mm of
  raised material inside it and a 0.6 nozzle turns that to mush; and the words
  are SW and PC rather than SWITCH and PC, because at a stroke this printer can
  render, SWITCH needs 20 mm of lid and there are 17.7 between the window and
  the lip.
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
  clears the channel by 1.57 mm. It is
  not a box: it has the jig's rail profile, so the jig slides in the way it
  slides into a Joy-Con. Two straight steps, 9.70 mm for the flange and
  7.70 for the tongue, copied from `RCM_Holder_v1.stl`. It goes in upside
  down, which buries the 9.70 chamber and leaves a 7.70 mouth at the open
  underside — 0.71 mm of lip a side against a 9.09 flange, so too wide
  to fall out, and the shoulder stops it lifting. One bump on each wall near
  the mouth keeps it from working its way out. This is the whole reason the
  case is 11.8 mm and not 7.5 — a 4 mm jig has to go somewhere.
- **Nothing done to the lid** beyond the window. The cable runs underneath,
  so the lid needs no pass-through and no wire channel, and keeps its full
  2 mm.

## Jig fit

The profile is `JIG_FLANGE_W` / `JIG_TONGUE_W` = 9.70 / 7.70, lifted from
`RCM_Holder_v1.stl` — that model is drawn 10×, and at 1/10 its pocket is
exactly the jig plus 0.3 mm a side. Straight steps, deliberately not
following the tongue's taper: the extra slack up there costs nothing.

Everything else comes off the jig mesh at `JIG_SRC`
(`Joycon_Jig_triforce.stl`, 9.09 × 20.00 × 4.00 mm) — how deep the slot is,
how far down the step sits, how much the floor has to grow, how tall the case
ends up. So the two widths are the only numbers to touch: rattles, lower
them; will not go in, raise them. `JIG_DETENT` is how hard it clicks, and
0.3 mm of it is eaten by the flange clearance.

The step height is worth a word. It is derived, not typed: `silhouette()`
finds where the jig's flange ends and the step goes just below it. Put the
step even 0.1 mm high and the 9.09 flange fouls the 7.70 tongue slot, which
shows up only as a jig that will not go in. The script checks the profile
against the jig's measured outline at every height and then slides the actual
mesh through the finished slot, so that mistake cannot ship.

## Pictures

`build.py` draws them itself — there is no CAD application in the loop, and
nothing to install beyond the four Python packages below.

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

As the source model: 0.4 mm nozzle, 0.2 mm layers, no supports. Both parts
print in the orientation they are saved in. The thinnest new feature is the
0.6 mm skin over the closed GPIO slots. Neither the jig slot nor the cable
duct needs support: the duct is open at the top, and the jig slot opens at
the bed as a 7.70 mm slit with one 1 mm ledge per side and a 9.70 mm bridge
over it.

## Regenerating

```
pip install trimesh manifold3d rtree numpy matplotlib pillow
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
board, that no piece of the engraving is finer than `NOZZLE` (an erosion by
half a bead — whatever vanishes is a feature the printer cannot lay down), a clear path for the jumper, a clear run for the cable from outside the
end wall to pin 39, room to drop that cable in from above, clearance between
the cable and the lid's rim, that the lid's tongue misses the base and beds
into the cable, and that the hold-down ribs miss the base and land on the
board. For the jig it does the real thing: puts
the jig mesh in the slot at three positions along the slide and checks that
not one of its 3188 vertices ends up inside plastic. It exits non-zero if any
check fails.
