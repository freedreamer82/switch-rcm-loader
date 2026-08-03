# Case

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
| `gland.stl` | cable gland, plugs the notch and grips the cable |
| `build.py` | regenerates all three from the source STL |
| `preview.png` | the assembled case |
| `preview-open.png` | lid lifted, board and header in place, jig and gland out |
| `section.png` | dimensioned cross-section |

Assembled: 26 × 56 × 11.7 mm — of which 4.20 mm is the jig slot under the
floor. The case itself is 7.5 mm.

## What changed from the original

- **Floor closed.** The two GPIO slots in the underside are sealed with a
  0.6 mm skin. The other 1.4 mm stays as an internal channel, so soldered pin
  tails still have somewhere to go — but clip them, 1.4 mm is all there is.
- **Jumper window**, 4.2 × 9 mm, over pins 18-19-20 only. The 3-pin header
  and its cap come out through the top; the cap sits on the outside of the
  lid with about 4 mm of pin to grip.
- **PC / SWITCH engraved** beside the window, 0.5 mm deep, each word joined to
  the pair of pins it means by a leader with a kink in it. Which way round
  comes from the firmware, not from taste: `MODE_PIN` is GP14 on pin 19,
  pin 18 is GND and pin 20 is GP15. Cap on 18-19 pulls GP14 down and the board
  comes up as a host — that pair is the Switch. Cap on 19-20 leaves GP14 on
  its pull-up: device, so that pair is the PC.

  The letters are a stroke font drawn in `build.py`, not typeset: seven glyphs
  is not worth a font dependency. Cap height is 2.4 mm because at 1.8 the bowl
  of the P came out 0.48 mm tall and would print closed — which is why the
  words are held apart from their pin gaps and reach them with a leader.
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
  it. The duct depth and the gland's cradle both follow. Getting it too big
  only loses the gland's grip; too small and the cable jacks the board off its
  seat, so the default is 4.0 — a full USB jacket. A charge-only cable is
  usually 3.0–3.5. Checked at 3.0, 3.6 and 4.0.
- **Cable gland**, `gland.stl`, printed separately. It plugs what is left of
  the notch above the cable: a foot the full thickness of the wall, a thinner
  blade above it that stops 0.05 mm short of the lid's rim, and a cradle
  underneath that squeezes the cable 0.2 mm a side.
  Its outer face is flush — it goes in from above, through the same opening
  the cable does, so it needs no lip to pinch and nothing protrudes. Drop the
  cable in, drop the gland on top of it, close the lid.

  It latches. Going in from above is what makes that possible: the direction
  it would escape in is not the direction it goes in, so a plain tooth locks
  it with no flexure anywhere. A 1 × 1.2 × 2.25 mm tooth on its left flank
  descends a pocket in the notch wall, and once seated the pocket's two faces
  stop it dead fore and aft — nudged 0.4 mm either way it runs 0.7 mm³ into
  plastic. Sideways the notch walls hold it, underneath is the cable, and the
  only way out is straight up, where the lid's skirt sits 0.05 mm over its
  top. Left flank only: the right one is inside the corner radius, and a
  pocket there would leave 0.1 mm of outer wall.

  Nothing latches it to the lid, deliberately. With the lid on it is already
  captive in all six directions, and with the lid off you want to be able to
  lift it out. A boss into the lid's skirt would only add a tolerance stack
  onto the snap fit, which is the most delicate thing about this case. What
  the gland's grip does need is the squeeze on the cable — the tooth stops the
  gland moving, but only friction stops the cable sliding through it, so
  `GLAND_PINCH` is set to bite 0.2 mm a side (0.88 mm³ of interference).
- **Jig rail slot** under the floor, opening at the same end as the cable and
  offset 3 mm off centre to leave that side of the floor to the duct. It is
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

Three parts: `base.stl`, `lid.stl`, `gland.stl`. All three print in the
orientation they are saved in.

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
board, a clear path for the jumper, a clear run for the cable from outside the
end wall to pin 39, room to drop that cable in from above, and clearance
between the cable and the lid's rim. For the jig it does the real thing: puts
the jig mesh in the slot at three positions along the slide and checks that
not one of its 3188 vertices ends up inside plastic. It exits non-zero if any
check fails.
