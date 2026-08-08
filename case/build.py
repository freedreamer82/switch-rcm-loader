#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
#
# pico-rcm case: builds base.stl and lid.stl, and draws the
# section that documents them. A remix of "Raspberry Pi Pico Case (1 & 2,
# Wireless)" by nmattia, printables.com/model/1368704, released CC0.
#
# The stock case is kept as-is - snap fit, USB mouth, LED window, BOOTSEL
# flexure. Five changes turn it into an RCM dongle case:
#
#   1  the two GPIO slots in the floor are closed from below. A 0.6 mm skin
#      seals them; the remaining 1.4 mm stays as an internal channel so
#      soldered pin tails still have somewhere to go.
#   2  a window in the lid over pins 18-19-20 only, so the 3-pin header and
#      its jumper cap come out through the top.
#   3  a 4.5 mm cable pass-through at the end OPPOSITE the Pico's own USB.
#   4  a shallow channel in the lid's inner face along the pin 21-40 row, so
#      the power wires can run from VSYS/GND down to that pass-through.
#   6  a tongue on the lid that plugs the cable notch, beds down on the cable
#      and holds it in the duct, plus four ribs that hold the board down.
#   5  a rail slot under the floor for the Joy-Con jig, opening at the same
#      end as the cable. It is the negative of the jig's own cross-section,
#      so the jig slides in the way it slides into a Joy-Con and the profile
#      itself holds it. This is what makes the case 11.8 mm instead of 7.5 -
#      there is nowhere else for a 4 mm jig to go.
#
# Everything is measured off the source mesh, nothing is redrawn.
#
#   ./build.py            writes base.stl, lid.stl and the pictures
#   ./build.py --fast     skips the pictures, which are most of the runtime
#
# Coordinates: both halves are centred on x and y. The board lies in the
# x/y plane, 26 mm across (x), 56 mm long (y). The Pico's USB is at +y.
# The lid is a separate print; assembled it is rotate(180 deg about x) then
# lifted, i.e.  assembled = (x, -y, 3.55 - z).

import sys, pathlib, base64
import numpy as np
import trimesh
from trimesh.creation import box, cylinder

OUT = pathlib.Path(__file__).resolve().parent

# Both input meshes are carried at the bottom of this file rather than read
# off disk, so the script is the whole build and nothing has to be downloaded
# to run it. See pack()/unpack() for the format.

# ------------------------------------------------------------ measurements
# Taken from the source mesh, not guessed.
SLOT_X0, SLOT_X1 = 7.47, 10.47   # the GPIO slots in the floor
SLOT_Y = 25.95                   # they run the full length of the cavity
CAV_X, CAV_Y = 11.0, 25.95       # inner faces of the cavity walls
FLOOR_Z0 = -2.0                  # underside of the base
JOINT_Z = 3.05                   # outside seam, in base coordinates
LID_FLIP_Z = 3.55                # z_base = LID_FLIP_Z - z_lid

PAD_X = 9.0                      # centre of the castellation row
SKIN = 0.6                       # unused: see make_base note 1

# The stock castellation channel is 1.4 mm deep, and a printed board with
# solder on the pads touches its floor. There is room to sink it now that the
# jig slot has lowered the floor, so it goes down to the same level as the
# cable duct on the other side - one internal surface fewer for the slicer to
# make a mess of, and more room for pin tails while we are at it.
TAIL_Z = -4.2

# Nothing held the board down: the donor's locating pegs stop at z = 1.28,
# which is 0.28 mm above a 1 mm board - enough to locate it, nothing to keep
# it there, and 2.55 mm of clear air above. These are ribs on the lid that
# land on the board. Thin on purpose: if the print comes out over size a
# 0.9 mm blade deforms rather than holding the lid off its snap.
#
# Where they land took two goes. At |x| = 9.5 all four sat on the castellated
# pads - the pad copper runs from the board edge to about 2.4 mm in, so
# anything past |x| = 8.1 is on it - and one of them sat on pin 40, a pad
# away from where the power cable gets soldered. At |x| = 7.0 they are inboard
# of the copper and outboard of everything in the middle of the board.
#
# The y values are pad mid-gaps, but do not read anything into that: a rib is
# 3.6 mm long and the pad pitch is 2.54, so it crosses a pad centre wherever
# it is put. What keeps it off the copper is the x, and only the x.
#
# The y is mine, and constrained: the locating pegs occupy y +-22.45 to +-24.45
# so a rib cannot sit on the mounting hole itself, the BOOTSEL flexure owns
# y 8.5 to 17.9, the LED hole 20.9 to 22.5, and the jumper window everything
# below -17 on the -x side. What is left is these four. The lid is checked for
# solidity around each one, which is what caught the flexure.
# Three plain blades - x, y, length. Nothing wraps anything and nothing is
# squeezed in: a land built round the locating peg was tried and thrown out,
# because a ring only has to be 0.1 mm oversize to stop seating, and a fourth
# blade in the only bare gap left on the +y half - a two-millimetre window at
# y +11 to +12 - was dropped rather than contrived. Better a support that is
# not there than one in a place it does not belong.
#
# So the USB half of the board is held by its two locating pegs and by the
# connector sitting in the case mouth, and these three do the rest. The board
# scan is what says there is nowhere better: the -x/+y quadrant has no room at
# all, because the BOOTSEL flexure owns y 8.5 to 17.9 of the lid and the LED
# hole 20.9 to 22.5.
HOLD_RIBS = ((5.7, -20.0, 3.6),
             (-5.5, -20.0, 3.6),
             (-5.5, -5.5, 3.6))
HOLD_CLEAR = 0.80                # how far a rib must stay from any opening
HOLD_W = 0.9                     # blade thickness
BOARD_TOP = 1.0
HOLD_BITE = 0.10                 # how far a rib presses into the board

# Window over pins 18-19-20. The 20 pads are centred on the board, so
# pin 20 sits at y = -24.13 and pin 18 at -19.05; the window spans from the
# end wall to just short of pin 17.
WIN_Y0, WIN_Y1 = -CAV_Y, -17.0
WIN_X0, WIN_X1 = -CAV_X, -6.8    # flush with the wall, 4.2 mm wide
WIN_R = 0.8                      # corner radius

# The power cable is soldered to the underside of the board, so it runs
# UNDER it, not over: a duct sunk into the floor on the pin 21-40 row,
# because VSYS and GND are pins 39 and 38. It replaces the stock 1.4 mm
# castellation channel on that side and is deeper than it, which there is
# room for now that the jig slot has lowered the floor.
#
# The entry is a notch, not a hole, and that is the whole point: the cable
# is already soldered to the board, and the USB-A plug on its far end will
# not thread through anything a dongle can afford. So the wall is open from
# the duct right up to the top of the base and the cable drops in from
# above. The duct floor then has to sit low enough that a 4 mm cable clears
# the lid's rim on the way down, or the lid would need notching too.
CABLE_X = PAD_X                  # over the pin 21-40 pads, mirrored below
CABLE_W = 4.0                    # across the duct
CABLE_D = 3.0                    # the cable itself, over the jacket
CABLE_Z0 = -CABLE_D - 0.2        # duct floor: the cable has to end up BELOW
                                 # the cavity floor or it lifts the board
CABLE_Z1 = 0.05                  # duct roof under the board is the board
CABLE_SLOT_TOP = JOINT_Z + 0.05  # the notch, open to the top of the base
CABLE_END = CAV_Y - 1.0          # how far up the board the duct reaches
LID_RIM_Z = 0.5                  # lowest the lid reaches at the end wall
CABLE_CLAMP = 0.20               # how far the tongue beds into the cable
TONGUE_WRAP = 1.2                # how far its skirts reach past the crown

# Outer profile of the case, measured off the source: a 26 x 56 rounded
# rectangle, corner radius 2.5. The tray below the floor repeats it exactly.
OUT_W, OUT_L, OUT_R = 26.0, 56.0, 2.5

# The jig is a table of dimensions, not somebody else's model: width against
# height off its own rail section, taken every place the section changes and
# nowhere else. Faithful to +-0.04 mm, which is finer than a caliper on a
# printed part resolves. Length and height come from the same measurement.
#
# JIG_LEN is along the slot, JIG_PROFILE is the cross-section, symmetric to
# 0.008 mm and so stored as full widths about the centre.
JIG_LEN = 20.00
JIG_PROFILE = (
    (0.00, 8.69),                # break on the bottom edge of the flange
    (0.02, 8.87),
    (0.10, 9.04),
    (0.18, 9.09),
    (1.60, 9.09),                # the flange, straight
    (1.70, 9.04),
    (1.78, 8.90),
    (1.80, 8.70),                # break on the top edge of the flange
    (1.82, 7.33),                # the shoulder: as good as vertical
    (1.86, 7.22),
    (1.94, 7.12),
    (2.50, 7.10),                # the tongue, straight
    (2.70, 7.02),
    (2.80, 6.90),
    (2.90, 6.70),
    (2.96, 6.49),
    (2.98, 6.38),
    (3.00, 6.10),                # roundover into the taper
    (3.20, 5.94),
    (3.60, 5.62),
    (4.00, 5.30),                # the tip
)

# The slot's own profile is two straight steps, 9.70 for the flange and 7.70
# for the tongue - the jig plus 0.3 a side, the fit RCM_Holder_v1 uses.
# Straight, not following the tongue's taper: the extra slack up there costs
# nothing and it prints and measures better than a contour.
#
# It goes in upside down, which is what retains it: the 9.70 chamber ends up
# buried and the mouth at the open underside is only 7.70, narrower than the
# 9.09 flange.
JIG_X = -1.0                     # off centre, but only just: the cable duct
                                 # wants one side of the floor and the
                                 # deepened pin-tail channel the other, and
                                 # the slot has to leave a wall between
JIG_FLANGE_W = 9.70              # RCM_Holder_v1.stl, scaled 1/10
JIG_TONGUE_W = 7.70
JIG_ROOF = 0.20                  # slack over the tip
JIG_LEAD = 0.5                   # slack at the far end of the slot

# Two bumps in the flange chamber, a few mm inside the mouth. They are what
# stops the jig sliding straight back out: the slot is horizontal and open at
# one end, and 0.3 mm a side of clearance does not hold anything by friction.
# The donor holder needs none because it is a tray open at the top, where
# gravity does the job. Set to 0 for no bumps at all.
JIG_DETENT = 0.5                 # 0.3 of it is taken up by the clearance,
                                 # leaving 0.2 a side of real interference

# Everything else about the jig follows from the table, and has to: put the
# step even 0.1 mm high and the 9.09 flange fouls the 7.70 tongue slot, which
# shows up only as a jig that will not go in.
JIG_FLANGE = max(w for _, w in JIG_PROFILE)          # 9.09
JIG_HEIGHT = max(z for z, _ in JIG_PROFILE)          # 4.00
TRAY = JIG_HEIGHT + JIG_ROOF                         # how far the floor grows
JIG_STEP_Z = max(z for z, w in JIG_PROFILE
                 if w > (JIG_FLANGE_W + JIG_TONGUE_W) / 2) + 0.1
JIG_FLANGE_H = JIG_ROOF + JIG_STEP_Z

MESH_GRID = 1000                 # coordinates are stored to 0.001 mm


def pack(mesh):
    """Encode a mesh as the base85 text this file carries.

    Quantise to a micron, delta-code both arrays in the order they already
    have, then LZMA. Sorting the vertices first sounds like it ought to help
    and makes it 70% bigger: the order the modeller emitted them in already
    has the locality the delta coder wants.
    """
    import lzma, struct
    m = mesh.copy()
    m.merge_vertices()
    v = np.round(np.asarray(m.vertices) * MESH_GRID).astype(np.int64)
    f = np.asarray(m.faces).astype(np.int64)
    zero = np.zeros((1, 3), np.int64)
    body = (np.diff(v, axis=0, prepend=zero).astype(np.int32).tobytes() +
            np.diff(f, axis=0, prepend=zero).astype(np.int32).tobytes())
    blob = lzma.compress(struct.pack("<II", len(v), len(f)) + body,
                         preset=9 | lzma.PRESET_EXTREME)
    return base64.b85encode(blob).decode()


def unpack(text):
    import lzma, struct
    raw = lzma.decompress(base64.b85decode(text))
    nv, nf = struct.unpack("<II", raw[:8])
    a = np.frombuffer(raw[8:8 + nv * 12], np.int32).reshape(nv, 3)
    b = np.frombuffer(raw[8 + nv * 12:], np.int32).reshape(nf, 3)
    return trimesh.Trimesh(np.cumsum(a.astype(np.int64), axis=0) / MESH_GRID,
                           np.cumsum(b.astype(np.int64), axis=0),
                           process=False)


# What stands on top of a Pico, measured off a scan of the board and reduced to
# a table - a 1 mm grid of the tallest thing in each cell, '.' for bare board.
# Rows run from the USB end down, columns from the pin 1-20 edge across. It is
# deliberately conservative: a cell is marked if a component touches any part
# of it, so the keep-out is slightly larger than the truth.
#
# This replaces a hand-written list of component boxes that was wrong twice,
# once by 2 mm. It is measurements, not somebody's model.
BOARD_KEEPOUT = (
    '......333333333......', '......333333333......',
    '......333333333......', '......333333333......',
    '...111333333333.1....', '...111...111...111...',
    '.......11....11111...', '.......11...111111...',
    '............111.1....', '.....2222..1111222...',
    '.....3333..1111222...', '.....3333..1111222...',
    '.....3333...111222...', '.....3333...111......',
    '.....2222............', '..............1111...',
    '.....11.......1111...', '....1111......1111...',
    '....1111........11...', '....1111........11...',
    '....1111.111111111...', '.........111111111...',
    '......1111111111.....', '.....11111111111.....',
    '......111111111......', '......111111111111...',
    '.....1111111111111...', '.....11111111111.....',
    '......111111111......', '......11111111.......',
    '..........11.........', '..........11.........',
    '........111..........', '......11111..........',
    '.....111111..........', '.....11111...........',
    '.....................', '.....................',
    '.....................', '.....................',
    '.....................', '.....................',
    '.....................', '.....................',
    '.....................', '.....................',
    '.....................', '.....................',
    '.....................', '.....................',
    '.....................',
)


def board_clear(x0, x1, y0, y1):
    """Is every cell of BOARD_KEEPOUT under this footprint bare board?"""
    for j, row in enumerate(BOARD_KEEPOUT):
        cy0, cy1 = 24.5 - j, 25.5 - j
        if cy1 <= y0 or cy0 >= y1:
            continue
        for i, ch in enumerate(row):
            cx0, cx1 = -10.5 + i, -9.5 + i
            if cx1 > x0 and cx0 < x1 and ch != '.':
                return False, (cx0 + 0.5, cy0 + 0.5, ch)
    return True, None


def rrect(x0, x1, y0, y1, z0, z1, r):
    """Rounded rectangular prism, inscribed in the given box."""
    parts = []
    for cx in (x0 + r, x1 - r):
        for cy in (y0 + r, y1 - r):
            c = cylinder(radius=r, height=z1 - z0, sections=32)
            c.apply_translation([cx, cy, (z0 + z1) / 2])
            parts.append(c)
    return trimesh.util.concatenate(parts).convex_hull


def prism(w, l, r, z0, z1):
    """Rounded rectangular prism centred on the origin. Convex."""
    return rrect(-w / 2, w / 2, -l / 2, l / 2, z0, z1, r)


def slab(x0, x1, y0, y1, z0, z1):
    x0, x1 = sorted((x0, x1))
    b = box(extents=[x1 - x0, y1 - y0, z1 - z0])
    b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return b


def tube(x, z, y0, y1, d):
    """Cylinder with its axis along y."""
    c = cylinder(radius=d / 2, height=y1 - y0, sections=64)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    c.apply_translation([x, (y0 + y1) / 2, z])
    return c


def U(a, *rest):
    return trimesh.boolean.union([a, *rest], engine='manifold')


def D(a, *rest):
    return trimesh.boolean.difference([a, *rest], engine='manifold')


def jig_solid():
    """The jig, built from JIG_PROFILE: a prism the length of the slot.

    Not a copy of the real part - the real one is hollowed out and has a
    triforce through the top - but its outline is what the slot has to
    clear, and the outline is exactly what was measured.

    Symmetric about JIG_X, sitting in the slot upside down: the profile's
    z = 0 face, which is the bottom of the flange, ends up against the roof.
    """
    zs = np.array([p[0] for p in JIG_PROFILE])
    ws = np.array([p[1] for p in JIG_PROFILE])
    top = FLOOR_Z0 - JIG_ROOF                # where the flange's face lands
    n = len(zs)
    V = np.empty((4 * n, 3))
    for i, (z, w) in enumerate(zip(zs, ws)):
        for k, (x, y) in enumerate(((-w / 2, 0.0), (w / 2, 0.0),
                                    (w / 2, JIG_LEN), (-w / 2, JIG_LEN))):
            V[4 * i + k] = [JIG_X + x, y, top - z]
    F = []
    for i in range(n - 1):
        a, b = 4 * i, 4 * (i + 1)
        F += [[a + 0, a + 1, b + 1], [a + 0, b + 1, b + 0],
              [a + 3, b + 2, a + 2], [a + 3, b + 3, b + 2],
              [a + 1, a + 2, b + 2], [a + 1, b + 2, b + 1],
              [a + 0, b + 0, b + 3], [a + 0, b + 3, a + 3]]
    t = 4 * (n - 1)
    F += [[0, 3, 2], [0, 2, 1], [t, t + 1, t + 2], [t, t + 2, t + 3]]
    m = trimesh.Trimesh(V, np.array(F), process=True)
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    m.fix_normals()
    if not m.is_volume:
        sys.exit('the jig profile did not close into a solid')
    return m


def jig_slot():
    """Two-step rail slot, upside down, opening at the end face.

    Roof flush with the original underside, mouth on the new bottom face.
    Starts 1 mm outside the end wall so the mouth is a clean cut, and runs
    deep enough that the jig sits flush with the face rather than proud of
    it - the depth that matters is measured from the face, not from y0.
    """
    y0 = -OUT_L / 2 - 1.0
    y1 = -OUT_L / 2 + JIG_LEN + JIG_LEAD
    step = FLOOR_Z0 - JIG_FLANGE_H
    return U(rrect(JIG_X - JIG_FLANGE_W / 2, JIG_X + JIG_FLANGE_W / 2,
                   y0, y1, step, FLOOR_Z0 + 0.01, 0.4),
             rrect(JIG_X - JIG_TONGUE_W / 2, JIG_X + JIG_TONGUE_W / 2,
                   y0, y1, FLOOR_Z0 - TRAY - 0.2, step + 0.01, 0.4))


def load():
    m = unpack(DONOR_MESH)
    bodies = m.split(only_watertight=False)
    if len(bodies) != 2:
        sys.exit('expected 2 bodies in the donor mesh, found %d' % len(bodies))
    # Taller volume is the base (it has walls all round); order is stable but
    # do not rely on it.
    bodies = sorted(bodies, key=lambda b: b.volume, reverse=True)
    lid, base = bodies[0], bodies[1]
    for b in (lid, base):
        c = b.bounds.mean(axis=0)
        b.apply_translation([-c[0], -c[1], 0])
    return lid, base


def make_base(src):
    out = src

    # 1. The donor's two GPIO slots need closing, but not by plugging them:
    #    both are cut deeper further down - the pin-tail channel on one side,
    #    the cable duct on the other - and what seals the floor underneath
    #    both is the jig tray's own skirt. A 0.6 mm plug used to go in here
    #    and every bit of it was removed again by those later cuts. It was
    #    doing nothing but adding a coplanar face for the slicer to trip on.

    # 5. Jig tray. The floor grows downwards by TRAY, keeping the same
    #    profile; the hull of two rounded prisms gives the new bottom the
    #    same 0.8 mm break the original edges have.
    zb = FLOOR_Z0 - TRAY
    c = 0.8
    out = U(out, trimesh.util.concatenate([
        prism(OUT_W - 2 * c, OUT_L - 2 * c, OUT_R - c, zb, zb + 0.01),
        prism(OUT_W, OUT_L, OUT_R, zb + c, FLOOR_Z0),
    ]).convex_hull)

    #    The stock bottom edge is filleted, so the old underside is ~1 mm
    #    narrower than the profile. Left alone that fillet becomes a groove
    #    running round the case at the tray joint, and an undercut to print.
    #    Squaring it off with a ring restores a straight side wall; the ring
    #    stops short of the channels and of the USB mouth so neither closes.
    out = U(out, D(prism(OUT_W, OUT_L, OUT_R, FLOOR_Z0, -0.3),
                   prism(OUT_W - 3, OUT_L - 3, OUT_R - 1.5, FLOOR_Z0 - 0.1, -0.2),
                   slab(-6.0, 6.0, 26.0, 29.0, FLOOR_Z0 - 0.1, -0.2)))

    # 2b. Sink the pin-tail channel on the pin 1-20 row. The jig slot is
    #     1.6 mm clear of it in x, which is the whole reason JIG_X moved.
    out = D(out, slab(-SLOT_X1 - 0.05, -SLOT_X0 + 0.05, -CAV_Y, CAV_Y,
                      TAIL_Z, 0.05))

    # 3. Cable entry and the duct it feeds, in one cut: a slot through the
    #    end wall that carries on under the board. Open upwards into the
    #    cavity for its whole length, so the only thing to bridge is the
    #    2 mm of wall above the entry itself.
    cw = CABLE_W / 2
    out = D(out, rrect(CABLE_X - cw, CABLE_X + cw,
                       -OUT_L / 2 - 1.0, CABLE_END, CABLE_Z0, CABLE_Z1, 1.0),
                 slab(CABLE_X - cw, CABLE_X + cw,
                      -OUT_L / 2 - 1.0, -CAV_Y + 0.45, CABLE_Z0,
                      CABLE_SLOT_TOP))

    #    The rail slot, opening at the cable end. Both openings are in that
    #    face but 2 mm apart in z, so they never meet.
    out = D(out, jig_slot())

    #    One bump on each flange wall, a few mm inside the mouth: the jig
    #    clicks past them and stops working its way out in a pocket.
    fw = JIG_FLANGE_W / 2
    for s in (-1, 1) if JIG_DETENT > 0 else ():
        d = cylinder(radius=1.2, height=JIG_FLANGE_H - 0.4, sections=32)
        d.apply_translation([JIG_X + s * (fw + 1.2 - JIG_DETENT),
                             -OUT_L / 2 + 4.0, FLOOR_Z0 - JIG_FLANGE_H / 2])
        out = U(out, d)
    return out


# ------------------------------------------------------------------ marking
# A stroke font, drawn rather than typeset: only seven glyphs are needed and
# pulling in a font library to engrave two words is not worth it. Each glyph
# is polylines in a 0..1 box, stroked with round-ended capsules so the joins
# come out clean.
GLYPHS = {
    # The P's bowl is deliberately shallow: at a 1 mm stroke and this cap
    # height a half-height bowl leaves 0.5 mm of raised material inside it,
    # which a 0.6 nozzle turns to mush. At 0.35 it leaves 1.47 mm.
    'P': [[(0, 0), (0, 1), (1, 1), (1, .35), (0, .35)]],
    'C': [[(1, 1), (0, 1), (0, 0), (1, 0)]],
    'S': [[(1, 1), (0, 1), (0, .5), (1, .5), (1, 0), (0, 0)]],
    'W': [[(0, 1), (.2, 0), (.5, .65), (.8, 0), (1, 1)]],
    'I': [[(.5, 1), (.5, 0)]],
    'T': [[(0, 1), (1, 1)], [(.5, 1), (.5, 0)]],
    'H': [[(0, 1), (0, 0)], [(1, 1), (1, 0)], [(0, .5), (1, .5)]],
}

# RAISED letters in a sunken field, not engraved strokes - and that is the
# whole point, not a style choice. The lid prints outer-face-down, so anything
# cut into that face is a hole in the first layers: first-layer squash closes
# it and the perimeters round a 1 mm slot smear together. Printed at 0.45 mm
# stroke it came out as nothing, and at 1.0 mm it was still unreadable.
#
# This way round, the letters are solid material standing on the glass, which
# is the one thing an FDM printer does perfectly, and the contrast comes from
# the 0.6 mm field sunk around them. The letters are pillars off the field
# floor, so they are not loose islands either.
#
# The W needs its own width, which is why GLYPH_W exists. Its legs pass within
# 0.331 of the glyph width of each other, so at a 1 mm stroke a 3 mm cell puts
# them 0.0 apart - they merge into a blob. 5.2 mm leaves 0.72, clear of a bead.
# Nothing else in SW or PC is dense enough to care. Two letters, or nothing legible.
TEXT_H = 4.40                    # cap height
TEXT_W = 3.00                    # glyph width
TEXT_GAP = 1.70                  # between glyphs: it has to clear a stroke
                                 # plus a bead, or adjacent letters merge
TEXT_STROKE = 1.00
TEXT_DEPTH = 0.60                # how deep it is cut into the 2 mm plate
GLYPH_W = {'W': 5.2}             # cells that need to be wider than TEXT_W
TEXT_X = -1.8                    # where the words start
TICK_X = (-6.6, -5.2)            # the leader, pointing at the pin gap
LEAD_X = -3.6                    # where it stops: LEAD_GAP short of the word
LEAD_GAP = 0.8                   # daylight between leader and lettering
LABELS = (('SW', -20.32, -15.7),  # mark, the pin gap it means, where it sits
          ('PC', -22.86, -22.9))

# The sunken field, derived from the labels rather than typed in. Two goes at
# typing it went wrong the same way: the strokes are drawn as capsules, so a
# letter reaches half a stroke past its nominal cap height, and the margin
# that looked like 1.0 mm was really 0.5 - narrower than a bead, and the check
# threw it out. FIELD_MARGIN is the real clearance round the lettering.
FIELD_MARGIN = 1.0
FIELD_LEFT = -7.2                # runs into the jumper window on purpose, so
                                 # the leaders reach the pins


def word_width(text):
    return (sum(GLYPH_W.get(c, TEXT_W) for c in text)
            + TEXT_GAP * (len(text) - 1))


def field_box():
    reach = TEXT_H / 2 + TEXT_STROKE / 2
    x1 = (TEXT_X + max(word_width(w) for w, _, _ in LABELS)
          + TEXT_STROKE / 2 + FIELD_MARGIN)
    mids = [m for _, _, m in LABELS]
    return (FIELD_LEFT, x1,
            min(mids) - reach - FIELD_MARGIN, max(mids) + reach + FIELD_MARGIN)

# What the printer can actually resolve. Every cut and every raised sliver in
# the marking is checked against this.
NOZZLE = 0.60


def capsule(p0, p1, w, z0, z1):
    """Round-ended stroke from p0 to p1 in the x/y plane."""
    parts = []
    for x, y in (p0, p1):
        c = cylinder(radius=w / 2, height=z1 - z0, sections=16)
        c.apply_translation([x, y, (z0 + z1) / 2])
        parts.append(c)
    return trimesh.util.concatenate(parts).convex_hull


def label(text, tick_y, y_mid, z0, z1):
    """The word, and the leader that says which pair of pins it means."""
    parts = [capsule((TICK_X[0], tick_y), (TICK_X[1], tick_y),
                     TEXT_STROKE, z0, z1),
             capsule((TICK_X[1], tick_y), (LEAD_X, y_mid),
                     TEXT_STROKE, z0, z1)]
    x = TEXT_X
    for ch in text:
        w = GLYPH_W.get(ch, TEXT_W)
        for poly in GLYPHS[ch]:
            for a, b in zip(poly[:-1], poly[1:]):
                parts.append(capsule(
                    (x + a[0] * w, y_mid + (a[1] - .5) * TEXT_H),
                    (x + b[0] * w, y_mid + (b[1] - .5) * TEXT_H),
                    TEXT_STROKE, z0, z1))
        x += w + TEXT_GAP
    return U(*parts)


def to_lid(mesh):
    """Move a solid from assembled coordinates into the lid's own.

    The lid's transform is an involution - a half turn about x and a lift -
    so the same operation serves both ways.
    """
    m = mesh.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    m.apply_translation([0, 0, LID_FLIP_Z])
    return m


def cable_tongue():
    """The lid's own plug for the cable notch, in assembled coordinates.

    This replaces the separate gland. A loose plug in a straight slot cannot
    be locked without a flexure, and a 4 mm slot has no room for one - the
    tooth-in-a-pocket it was tried with does not hold. Growing the same shape
    off the lid solves it by not being a separate part: the lid's snap is what
    retains it, there is nothing to lose, and it prints for free.

    It descends into the notch until it meets the cable, and its underside is
    the cable's own radius less CABLE_CLAMP, so it beds down on it rather than
    resting on the crown. That is the strain relief.
    """
    x0, x1 = CABLE_X - CABLE_W / 2 + 0.05, CABLE_X + CABLE_W / 2 - 0.05
    axis = CABLE_Z0 + CABLE_D / 2
    body = slab(x0, x1, -OUT_L / 2 + 0.05, -CAV_Y - 0.05,
                axis + CABLE_D / 2 - TONGUE_WRAP, JOINT_Z + 0.05)
    return D(body, tube(CABLE_X, axis, -OUT_L / 2 - 2.0, -CAV_Y + 1.0,
                        CABLE_D - 2 * CABLE_CLAMP))


def hold_feet():
    """Footprints of the hold-down blades: x0, x1, y0, y1."""
    return [(x - HOLD_W / 2, x + HOLD_W / 2, y - L / 2, y + L / 2)
            for x, y, L in HOLD_RIBS]


def hold_ribs():
    """Blades on the lid that hold the board down, assembled coords."""
    z0, z1 = BOARD_TOP - HOLD_BITE, LID_FLIP_Z + 0.05
    return U(*[slab(x0, x1, y0, y1, z0, z1) for x0, x1, y0, y1 in hold_feet()])


def marking():
    """PC and SWITCH beside the jumper window, in assembled coordinates.

    Built the right way round on the finished case and then pushed back
    through the lid's own transform, which is the only way to be sure the
    letters are not mirrored: the lid gets flipped to be fitted.

    Which is which comes from the firmware. MODE_PIN is GP14, pin 19; pin 18
    is GND and pin 20 is GP15, left floating. Cap on 18-19 pulls GP14 down
    and the board comes up as a host, so that pair is the Switch. Cap on
    19-20 leaves GP14 on its pull-up: device, so that pair is the PC.
    """
    top = LID_FLIP_Z + 2.0           # outer face of the lid, assembled
    strokes = U(*[label(w, tick, mid, top - TEXT_DEPTH - 0.05, top + 0.05)
                  for w, tick, mid in LABELS])
    # Sink the field, keep the letters. The field runs into the jumper window
    # on its left, which is what makes the leaders reach the pins.
    field = rrect(*field_box(), top - TEXT_DEPTH, top + 0.05, 1.2)
    art = D(field, strokes)
    art.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    art.apply_translation([0, 0, LID_FLIP_Z])
    return art


def make_lid(src):
    out = src

    # 2. Window over the 18-19-20 header. Lid y is mirrored relative to the
    #    assembled case, hence the sign flip.
    out = D(out, rrect(WIN_X0, WIN_X1, -WIN_Y1, -WIN_Y0, -2.1, 0.6, WIN_R))

    #    Nothing else: the cable runs under the board, so the lid needs no
    #    pass-through and no wire channel, and keeps its full 2 mm.

    # 7. PC / SWITCH engraved beside the window, so the jumper position is
    #    not something to remember.
    out = D(out, marking())

    # 8. The cable tongue, and ribs to hold the board down. Both are built
    #    in assembled coordinates and pushed back through the lid's own
    #    transform - the only way to be sure of the handedness.
    out = U(out, to_lid(cable_tongue()), to_lid(hold_ribs()))
    return out


# ----------------------------------------------------------------- preview
# A z-buffer rasteriser, sixty lines of numpy. The alternative was keeping a
# CAD application around just to draw two pictures, or using matplotlib's
# 3-D, which sorts faces by centroid and therefore draws nonsense wherever
# parts interpenetrate - which here is everywhere: case, board, header, jig.
# Per-pixel depth gets it right instead.

def pin_y(n):
    return 24.13 - (n - 1) * 2.54              # pin 1 sits at +24.13


def components():
    """What stands on top of the board, as boxes.

    Datasheet dimensions and a photograph, NOT a verified layout: treat it as
    what the hold-down ribs are checked against, not as proof. The ribs sit at
    |x| = 7.0, inboard of the pad copper and outboard of all of this, which is
    the argument that actually matters - none of it reaches past |x| = 6.
    """
    return [
        (slab(-3.75, 3.75, 20.6, 26.5, 1.0, 3.6), 'micro-USB'),
        (slab(-3.5, 3.5, -3.5, 3.5, 1.0, 1.9), 'RP2040'),
        (slab(-2.5, 2.5, 5.0, 9.0, 1.0, 1.7), 'flash'),
        (slab(1.5, 4.5, 15.0, 18.0, 1.0, 2.5), 'boost inductor'),
        # Taken off the donor's own flexure cut, which is real evidence for
        # where the button is - the box that was here before was a guess, it
        # was 2 mm out, and a rib landed on the flexure because of it.
        (slab(-7.9, -1.1, 8.5, 17.9, 1.0, 2.0), 'BOOTSEL and its flexure'),
        (slab(-PAD_X - 1.27, -PAD_X + 1.27, pin_y(20) - 1.27,
              pin_y(20) + 6.35, 1.0, 3.54), 'header on 18-19-20'),
    ]


def stand_ins():
    """The Pico, its header and the jumper cap, for the preview."""
    out = [(slab(-10.5, 10.5, -25.5, 25.5, 0.0, BOARD_TOP), (0.10, 0.42, 0.23))]
    out += [(m, (0.17, 0.17, 0.17)) for m, _ in components()]
    for n in (18, 19, 20):
        out.append((slab(-PAD_X - 0.32, -PAD_X + 0.32, pin_y(n) - 0.32,
                         pin_y(n) + 0.32, 0.0, 10.5), (0.79, 0.64, 0.15)))
    out.append((slab(-PAD_X - 2.0, -PAD_X + 2.0, pin_y(19) - 2.6,
                     pin_y(19) + 2.6, LID_FLIP_Z + 2.0, LID_FLIP_Z + 7.6),
                (0.12, 0.31, 0.85)))
    out.append((tube(CABLE_X, CABLE_Z0 + CABLE_D / 2, -29.0, CABLE_END,
                     CABLE_D), (0.13, 0.13, 0.13)))
    return out


def render(items, path, eye, target, up=(0, 0, 1), size=(1400, 900), ss=2):
    """Flat-shaded z-buffer render. items is [(mesh, rgb), ...]."""
    from PIL import Image
    w, h = size[0] * ss, size[1] * ss
    eye, target, up = (np.array(v, float) for v in (eye, target, up))
    fwd = target - eye
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, up)
    right /= np.linalg.norm(right)
    cam = np.stack([right, np.cross(right, fwd), -fwd])   # world -> camera

    pts = [np.asarray(m.vertices) for m, _ in items]
    depth = np.full((h, w), np.inf)
    rgb = np.zeros((h, w, 3), np.float32)
    rgb[:] = (0.97, 0.97, 0.96)

    # Fit: the scale is bounded by HALF the frame in each axis, separately.
    # Using the whole of the smaller dimension put the part off the edge.
    allv = (np.vstack(pts) - eye) @ cam.T
    rx = np.abs(allv[:, 0] / -allv[:, 2]).max()
    ry = np.abs(allv[:, 1] / -allv[:, 2]).max()
    f = min(0.46 * w / rx, 0.46 * h / ry)
    light = np.array([0.35, 0.45, 0.82])
    light /= np.linalg.norm(light)

    for (mesh, colour), v in zip(items, pts):
        c = (v - eye) @ cam.T
        z = -c[:, 2]
        sx = w / 2 + f * c[:, 0] / z
        sy = h / 2 - f * c[:, 1] / z
        tri = np.asarray(mesh.faces)
        n = np.asarray(mesh.face_normals)
        shade = 0.35 + 0.65 * np.clip(n @ light, 0, 1)
        px, py, pz = sx[tri], sy[tri], z[tri]
        area = ((px[:, 1] - px[:, 0]) * (py[:, 2] - py[:, 0]) -
                (px[:, 2] - px[:, 0]) * (py[:, 1] - py[:, 0]))
        for i in np.nonzero(area < -1e-9)[0]:
            x0, x1 = int(max(px[i].min(), 0)), int(min(px[i].max() + 2, w))
            y0, y1 = int(max(py[i].min(), 0)), int(min(py[i].max() + 2, h))
            if x1 <= x0 or y1 <= y0:
                continue
            gy, gx = np.mgrid[y0:y1, x0:x1]
            ax, ay, d = px[i], py[i], area[i]
            b0 = ((ax[1] - gx) * (ay[2] - gy) - (ax[2] - gx) * (ay[1] - gy)) / d
            b1 = ((ax[2] - gx) * (ay[0] - gy) - (ax[0] - gx) * (ay[2] - gy)) / d
            b2 = 1.0 - b0 - b1
            inside = (b0 >= 0) & (b1 >= 0) & (b2 >= 0)
            if not inside.any():
                continue
            zz = b0 * pz[i][0] + b1 * pz[i][1] + b2 * pz[i][2]
            hit = inside & (zz < depth[y0:y1, x0:x1])
            if not hit.any():
                continue
            depth[y0:y1, x0:x1][hit] = zz[hit]
            rgb[y0:y1, x0:x1][hit] = np.array(colour) * shade[i]

    img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
    img.resize(size, Image.LANCZOS).save(path)


def previews(base, lid_a):
    shell = (0.91, 0.89, 0.84)
    jig = jig_solid()
    jig.apply_translation([0, -OUT_L / 2 - jig.bounds[0][1], 0])

    # Viewed from -x, so that +x runs left to right and the lid's lettering
    # reads the right way round.
    render([(base, shell), (lid_a, shell), (jig, (0.75, 0.22, 0.17))],
           OUT / 'preview.png', eye=(-44, -66, 46), target=(0, 0, 2))

    up_lid = lid_a.copy()
    up_lid.apply_translation([0, 0, 13.0])
    out_jig = jig.copy()
    out_jig.apply_translation([0, -15.0, -3.0])
    render([(base, shell), (up_lid, shell),
            (out_jig, (0.75, 0.22, 0.17))] + stand_ins(),
           OUT / 'preview-open.png', eye=(-38, -64, 44), target=(0, -4, 4))


def draw_section(base, path, y=-20.0):
    """Cross-section through the jig slot, with the jig's outline on it.

    Drawn here rather than in a CAD application so the one tool that builds
    the geometry is also the one that documents it - and so the drawing
    carries a scale, which a shaded render does not.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    seg = trimesh.intersections.mesh_plane(base, [0, 1, 0], [0, y, 0])
    fig, ax = plt.subplots(figsize=(11, 4.2), dpi=130)
    for a, b in seg[:, :, [0, 2]]:
        ax.plot([a[0], b[0]], [a[1], b[1]], color='#37474f', lw=1.4,
                solid_capstyle='round')

    top = FLOOR_Z0 - JIG_ROOF
    ring = ([(JIG_X + w / 2, top - z) for z, w in JIG_PROFILE] +
            [(JIG_X - w / 2, top - z) for z, w in reversed(JIG_PROFILE)])
    ax.add_patch(Polygon(ring, closed=True, facecolor='#e57373',
                         edgecolor='#b71c1c', lw=0.8, zorder=3))
    ax.annotate('jig', (JIG_X, top - 2.0), color='#7f0000', ha='center',
                va='center', fontsize=9, zorder=4)

    ax.set_aspect('equal')
    ax.set_xlabel('x  [mm]')
    ax.set_ylabel('z  [mm]')
    ax.set_title('section at y = %.1f mm - jig rail slot, cable duct and'
                 ' pin-tail channel' % y, fontsize=10)
    ax.grid(True, lw=0.3, color='#b0bec5')
    ax.set_xticks(np.arange(-13, 13.1, 2))
    ax.set_yticks(np.arange(-7, 3.1, 1))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def report(name, mesh, ref):
    ok = mesh.is_watertight and mesh.is_winding_consistent
    print('%-16s %6.2f x %6.2f x %6.2f   vol %8.1f mm3   watertight %s'
          % (name, *mesh.extents, mesh.volume, ok))
    if ref is not None:
        # z is allowed to move - the base grows a tray downwards - but the
        # footprint must still be the source's, or the halves stop matching.
        d = np.abs(mesh.bounds[:, :2] - ref.bounds[:, :2]).max()
        print('%-16s footprint drift vs source: %.3f mm' % ('', d))
        ok &= d < 0.01
    return ok


def main():
    lid_src, base_src = load()

    base = make_base(base_src)
    lid = make_lid(lid_src)

    good = True
    good &= report('base', base, base_src)
    good &= report('lid', lid, lid_src)

    # Nothing under the board may see daylight. Both the cable duct and the
    # jig slot are holes in the floor now, so this cannot be a single plane
    # probe any more: walk the whole column under each point of the cavity
    # and demand some material somewhere below it.
    xs = np.arange(-10.4, 10.5, 0.4)
    ys = np.arange(-25.5, 25.6, 0.8)
    zs = np.arange(base.bounds[0][2] + 0.05, -0.1, 0.1)
    thin = []
    for x in xs:
        for y in ys:
            col = base.contains(np.column_stack([np.full(zs.size, x),
                                                 np.full(zs.size, y), zs]))
            if col.sum() * 0.1 < 0.5:
                thin.append((x, y, col.sum() * 0.1))
    print('floor: %d of %d columns under 0.5 mm of material (want 0)'
          % (len(thin), len(xs) * len(ys)))
    if thin:
        print('       worst:', ' '.join('(%.1f,%.1f)=%.1f' % t for t in thin[:6]))
    good &= not thin

    # The window must clear the pad row and the three pins.
    for pin, y in ((20, -24.13), (19, -21.59), (18, -19.05)):
        inside = (WIN_X0 < -PAD_X < WIN_X1) and (WIN_Y0 < y < WIN_Y1)
        print('pin %d at y=%+6.2f inside window: %s' % (pin, y, inside))
        good &= inside

    # Nothing may block a jumper leaving pin 19 through the lid, and nothing
    # may block the cable leaving through the end wall.
    lid_a = lid.copy()
    lid_a.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    lid_a.apply_translation([0, 0, LID_FLIP_Z])

    def solid(p):
        return base.contains(p) | lid_a.contains(p)

    zs = np.arange(1.2, 7.0, 0.1)
    blocked = solid(np.column_stack([np.full(zs.size, -PAD_X),
                                     np.full(zs.size, -21.59), zs])).sum()
    print('jumper path over pin 19: %d blocked samples (want 0)' % blocked)
    good &= blocked == 0

    # The cable has to get from outside the end wall to under the board
    # without climbing over it: one clear run at duct height.
    zc = (CABLE_Z0 + CABLE_Z1) / 2
    ys = np.arange(-28.5, CABLE_END - 0.5, 0.1)
    blocked = base.contains(np.column_stack([np.full(ys.size, CABLE_X), ys,
                                             np.full(ys.size, zc)])).sum()
    print('cable duct, wall to pin 39: %d blocked samples (want 0)' % blocked)
    good &= blocked == 0

    # The duct must stay under the board, or it is not a duct.
    print('duct top %.2f mm vs board underside 0.00 mm' % CABLE_Z1)
    good &= CABLE_Z1 <= 0.1

    # Put the real jig in the real slot and slide it the whole way in.
    # Anything the profile got wrong shows up as a jig vertex ending up
    # inside the plastic. The source jig mesh is not watertight, so this
    # tests its vertices rather than booleaning with it - on a convex
    # cross-section the vertices are the extremes anyway. The detent is
    # meant to touch, so vertices beside it do not count.
    j = jig_solid()
    det_y = -OUT_L / 2 + 4.0
    for stop in (0.0, 4.0, 10.0):
        v = j.vertices + [0, -OUT_L / 2 - stop - j.bounds[0][1], 0]
        hit = base.contains(v) & (np.abs(v[:, 1] - det_y) > 2.5)
        print('jig %4.1f mm out: %d of %d profile corners in the plastic'
              ' (want 0)' % (stop, hit.sum(), len(v)))
        good &= hit.sum() == 0

    # The two straight steps have to clear the jig's real outline at every
    # height, taper and all. This is what would catch a wrong scale factor
    # on the donor holder, or a different jig.
    worst = 99.0
    for z, w in JIG_PROFILE:
        want = JIG_FLANGE_W if z <= JIG_STEP_Z else JIG_TONGUE_W
        worst = min(worst, (want - w) / 2)
    print('two-step profile vs jig outline: %.2f mm clearance at the tightest'
          % worst)
    good &= worst >= 0.15

    # The cable is already soldered, so it has to be able to drop into the
    # duct from above with the lid off: one clear column through the wall.
    zc = np.arange(CABLE_Z0 + 0.2, CABLE_SLOT_TOP, 0.05)
    blocked = base.contains(np.column_stack([np.full(zc.size, CABLE_X),
                                             np.full(zc.size, -27.0), zc])).sum()
    print('cable lay-in at the wall: %d blocked samples (want 0)' % blocked)
    good &= blocked == 0

    # ...and once it is in, the lid must close over it, not onto it.
    print('%.1f mm cable tops out at %+.2f mm; lid rim %+.2f, board seat 0.00'
          % (CABLE_D, CABLE_Z0 + CABLE_D, LID_RIM_Z))
    good &= CABLE_Z0 + CABLE_D <= min(LID_RIM_Z, 0.0)

    # The lid's tongue has to sit in the notch without touching the base, and
    # has to bed into the cable rather than rest on it.
    tongue = cable_tongue()
    hit = trimesh.boolean.intersection([tongue, base], engine='manifold').volume
    print('lid tongue vs base: %.3f mm3 interference (want < 0.05)' % hit)
    good &= hit < 0.05
    cable = tube(CABLE_X, CABLE_Z0 + CABLE_D / 2, -OUT_L / 2 - 1.0,
                 CABLE_END, CABLE_D)
    grip = trimesh.boolean.intersection([tongue, cable], engine='manifold').volume
    print('lid tongue bed into the cable: %.2f mm3 (%.2f mm deep)'
          % (grip, CABLE_CLAMP))
    good &= 0.2 < grip < 8.0

    # And the ribs have to land on the board, not on the walls or the pegs.
    ribs = hold_ribs()
    hit = trimesh.boolean.intersection([ribs, base], engine='manifold').volume
    print('hold-down ribs vs base: %.3f mm3 interference (want < 0.05)' % hit)
    good &= hit < 0.05
    board = slab(-10.5, 10.5, -25.5, 25.5, 0.0, BOARD_TOP)
    bite = trimesh.boolean.intersection([ribs, board], engine='manifold').volume
    print('hold-down ribs bite on the board: %.2f mm3 over %d ribs'
          % (bite, len(HOLD_RIBS)))
    good &= bite > 0.5 * HOLD_W * HOLD_BITE * sum(L for _, _, L in HOLD_RIBS)

    # ...and nothing that stands on the board may be under one. This is the
    # check that took a board scan to get right: the hand-written component
    # boxes it replaces were wrong twice, once by 2 mm, and put a rib on the
    # BOOTSEL flexure. BOARD_KEEPOUT is measured and conservative.
    feet = hold_feet()
    bad = []
    for f in feet:
        ok, where = board_clear(*f)
        if not ok:
            bad.append((f, where))
    print('contact feet on bare board: %d of %d' % (len(feet) - len(bad), len(feet)))
    for f, (cx, cy, ch) in bad:
        print('   ON A COMPONENT: foot x %.1f..%.1f y %.1f..%.1f hits a %s mm'
              ' tall part at (%.1f, %.1f)' % (f[0], f[1], f[2], f[3], ch, cx, cy))
    good &= not bad

    # And the one that matters most, because the list of components is a guess
    # and this is not: each rib's footprint is grown by HOLD_CLEAR and the lid
    # has to be solid over the whole of it. No list of openings to keep up to
    # date - if the lid has a hole there, this finds it. It is what catches a
    # rib on the BOOTSEL flexure, which is a spring: it would hold nothing
    # down and would jam the button.
    step = 0.1
    mid = LID_FLIP_Z + 1.0                       # mid-plate, above any recess
    bad = []
    for fx0, fx1, fy0, fy1 in feet:
        gx = np.arange(fx0 - HOLD_CLEAR, fx1 + HOLD_CLEAR, step)
        gy = np.arange(fy0 - HOLD_CLEAR, fy1 + HOLD_CLEAR, step)
        X, Y = np.meshgrid(gx, gy, indexing='ij')
        holes = (~lid_a.contains(np.column_stack([
            X.ravel(), Y.ravel(), np.full(X.size, mid)]))).sum()
        if holes:
            bad.append(((fx0 + fx1) / 2, (fy0 + fy1) / 2, holes * step * step))
    print('contact feet with an opening in the lid within %.1f mm: %d of %d'
          % (HOLD_CLEAR, len(bad), len(feet)))
    # Printed in board terms so it can be checked against a real Pico with a
    # rule, which is the only way this gets settled: the component list here
    # is a guess and has been wrong twice.
    for x, y, a in bad:
        print('   TOO CLOSE TO A HOLE: (%+.1f, %+.2f), %.1f mm2 of it' % (x, y, a))
    good &= not bad

    print('   where they land, measured on the board:')
    for fx0, fx1, fy0, fy1 in feet:
        print('     %.1f-%.1f mm in from the %s edge,'
              '  %.1f-%.1f mm from the USB end'
              % (10.5 - max(abs(fx0), abs(fx1)), 10.5 - min(abs(fx0), abs(fx1)),
                 'pin 1-20' if fx0 < 0 else 'pin 21-40',
                 25.5 - fy1, 25.5 - fy0))
    # The engraving is the one feature a nozzle can silently swallow - the
    # first version had a 0.45 mm stroke and printed as nothing at all - so it
    # is measured on the finished lid rather than trusted.
    #
    # Run lengths along scan lines do not work for this: a line that clips the
    # corner of a stroke gives a one-sample run and the test cries wolf. The
    # question is morphological. Erode each region by half a nozzle: whatever
    # disappears is a feature the printer cannot lay down, so every connected
    # piece of groove and every raised island between strokes has to survive.
    from scipy import ndimage
    top = LID_FLIP_Z + 2.0
    step = 0.08
    xs = np.arange(-7.4, 4.6, step)
    ys = np.arange(-27.2, -14.8, step)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    solid = lid_a.contains(np.column_stack([
        X.ravel(), Y.ravel(),
        np.full(X.size, top - TEXT_DEPTH / 2)])).reshape(X.shape)

    r = int(round(NOZZLE / 2 / step))
    k = np.hypot(*np.mgrid[-r:r + 1, -r:r + 1]) <= r + 0.01
    # Per-piece erosion is not enough: it clears a thin neck inside an
    # otherwise fat region, and there was a 0.5 mm one between the W and the
    # edge of the field. So this is an OPENING - erode then dilate - and what
    # the opening removes is what the nozzle cannot lay down, neck or island.
    worst = 0.0
    edge = np.zeros_like(solid)               # the sampling border erodes too,
    edge[r + 1:-r - 1, r + 1:-r - 1] = True   # so its losses do not count
    for name, region in (('sunken field', ~solid), ('raised letters', solid)):
        opened = ndimage.binary_dilation(
            ndimage.binary_erosion(region, k, border_value=1), k)
        lost = region & ~opened & edge
        lab, n = ndimage.label(lost)
        blobs = sorted(((lab == i).sum() * step * step,
                        X[lab == i].mean(), Y[lab == i].mean())
                       for i in range(1, n + 1))[::-1]
        big = blobs[0] if blobs else (0.0, 0, 0)
        worst = max(worst, big[0])
        print('marking, %-14s: %.2f mm2 lost to a %.2f mm nozzle, worst patch'
              ' %.2f mm2' % (name, lost.sum() * step * step, NOZZLE, big[0]))
        if big[0] > 0.30:
            print('     TOO FINE around (%+.2f, %+.2f)' % (big[1], big[2]))
    good &= worst <= 0.30

    # Probe the field, not a letter: the letters now stand at full height.
    zs = np.arange(top - 1.2, top - 0.005, 0.01)
    col = lid_a.contains(np.column_stack([
        np.full(zs.size, field_box()[1] - 0.5), np.full(zs.size, -21.0), zs]))
    print('marking depth: %.2f mm into a 2.00 mm plate' % ((~col).sum() * 0.01))
    good &= (~col).sum() * 0.01 >= TEXT_DEPTH - 0.05

    # Retention. The whole point of railing the jig instead of boxing it is
    # that the mouth is narrower than the flange, so it cannot drop out of
    # the open underside. Measure the mouth rather than trust the profile:
    # a convex hull of the outline silently replaces that shoulder with a
    # ramp, which fits just as well and holds nothing.
    xs = np.arange(JIG_X - 7.0, JIG_X + 7.001, 0.02)
    def slot_width(z):
        free = xs[~base.contains(np.column_stack([xs, np.full(xs.size, -20.0),
                                                  np.full(xs.size, z)]))]
        free = free[np.abs(free - JIG_X) < 6.5]
        return free.max() - free.min() if len(free) else 0.0
    mouth = slot_width(base.bounds[0][2] + 0.3)
    throat = min(slot_width(z) for z in
                 np.arange(base.bounds[0][2] + 0.2, FLOOR_Z0 - 1.6, 0.1))
    print('slot mouth %.2f mm, narrowest %.2f mm, jig flange %.2f mm'
          '  -> %.2f mm of lip a side' % (mouth, throat, JIG_FLANGE,
                                          (JIG_FLANGE - throat) / 2))
    good &= (JIG_FLANGE - throat) / 2 >= 0.5

    print('assembled: %.1f x %.1f x %.1f mm'
          % (OUT_W, OUT_L, lid_a.bounds[1][2] - base.bounds[0][2]))

    lid.export(OUT / 'lid.stl')
    base.export(OUT / 'base.stl')
    if '--fast' in sys.argv:
        print('wrote base.stl, lid.stl (--fast: no pictures)')
    else:
        draw_section(base, OUT / 'section.png')
        previews(base, lid_a)
        print('wrote base.stl, lid.stl, section.png, preview*.png')
    return 0 if good else 1


# --------------------------------------------------------------- the meshes
# Down here because they are 70 kB of noise, and because nothing above them
# needs them until main() runs.
#
# The only one is DONOR_MESH: "Raspberry Pi Pico Case (1 & 2, Wireless)" by
# nmattia, printables.com/model/1368704, CC0. Two bodies, lid and base. The
# jig is not in here - it is a table of dimensions further up, because that is
# all the slot needs, and dimensions are nobody's property.
#
# To swap it:  ./build.py --pack path/to.stl   and paste the result.

DONOR_MESH = (
    '{Wp48S^xk9=GL@E0stWa8~^|S5YJf5<@a-k{apYxihLN}DnJ>n4}5jaqEM*EXe-{iHYxC-#7'
    '5`7P?G68*ZQc*%;qBK^L;-HCZns;pTOQ&lN7gw5&kq!`j#o2!s_E?>jr>b=#$O&;N=ib_^@4'
    'BGgJMltZQehK}92FvW;Ub(%RI#Vjq-%UUWmcM?m=<mxs=R%`(iFQ)*J<HnKoC5B|+*efKsG?'
    '$$S#_%3PR4cZ6zk(k^`m<v1ILj2Futh6{&?kTe_{K_-cOvzH0!x-r$epTfU-R)8+TgYwxX$j'
    't+@;Za;4{5q%b;+%)puBwN8Mgo@M6*F9KGvn}Aw$@R#$6$Hm>|k^t1)xhI!3IvyC)~ZKJjO&'
    '<g@-(BDf8HU3dL~R>|7N?NFU)cyc*goAgqUN{5rDC(@I4rK8lvalGSSwZh1lgFBBq;XcEcbE'
    'z?W$%xQ?6PC^8r@UAsQXYh|?H>%@@(E!1m$ZP4U}2}1pfcye8d2od=A(-=HbdbW>p?HAsEgl'
    'C#*QX^ZN+&hE@U`0y@rCu?0|uH2FvCx`cH)H4w<Qw<ulOc(hYF`%C($?1Dr?b@{IL_AxK@t-'
    'g?F(CZdUsK{8yEto(X@X^A-D$JK7ljv?tB_FX^1Gj|KaxS=%^>pl~vGxUhVz^5$NV}hmMIH_'
    'F1F`file2HIhd$%pr#@KBmE``QUPd!_YShEwei2GdhR_eeA|9W8w;9V8zTJ8VC#=#%!_4}{<'
    '(9Y(XE}&?1fQ$9SFHygQ93ix&=@P3^oRN2&1ggeJJYwnY`_!~b(z+`iRl*lC;)k^enrN9ZoZ'
    '>~UHOxqLfk+Oo_k|d1^vc)D7|CWM)+e4{PcGL(UQ?Gh+z0@q%zpMU%WlC+n+%a}Ahz&Ns57@'
    ';axy&fd4S;BL#6m^t{h1{yrG9*#Dpo=PQ0$%NdM(Uh(hP$`0Hb(dA3Snf)=i$)bAJS_!ySlj'
    ';Kn~7FzZy?F{!7HNb9i4kRU~xa>V!MWkz6lj8elr2wbEkV|V5_h$fsyv<w0%uyAwfTn(Og62'
    '-OeBRFA!WGk4;^<&O0{V2XiuZYgm&86-IV9GSV`d^Y>l2~L+Bo-j0^tFY<iT0A#TXk~i+#d3'
    'fhQ+a_ACF+RYY<IhMna<W)LrLe@8g2kKKBHL)-pK!8_ol`By@0ZnCUX&maxIh%xpc^xl6iq8'
    'n})4I3vh-xL{prC*{BXbS8F^Z_sOhI4@)#F69&>dFYQuJP42uMQsAuzt!NGT(F)aGtH18TnQ'
    'a=%Bxm$V5Ka0012zWbo#aq#fpjNZxK7Mup%%Ffsy60OA(OoxBMT@0))D(lHD@lLQU6{{&Ttn'
    'Le7nkB*ywF)aN10Iv6G6a<>v)wm6OjeB?;0E4cAtGbyZDF1;WHKp!~W#!Sovxco37~hT=z1='
    '7t=Pth*9%MpDMrpj}%7#c!)au+CH%6)07Y@k}JUrL3nLGsp-VU>87pQ!=ub!o=LSk^EaLl_D'
    'Ply(^j<Q9rm0#v!vdwm9LhevBpIi?0^{Qv}^2Mwpf-;6fc6Xpf(047FOoR?kbp<t*!+Z0SQ!'
    '1d7Shu~nF8Q%bRAukVtHzU><sNU0w_JN-T=?;@4xiLV2iswiB-n1CB>*R#>~#1j=6n{;d>;`'
    '(?_X+rx#T@++5Rp2=^{oio`#^`Fw1K}vfEOKLSRhip;N6GuUY01ljg}ZUS$|mWe2L_jt5DU;'
    '<M)lR4jGlye5*=hMr-+{MZBMc5XYXo5>q~Eo3jfpC0nvv(Olo#pMbap`k8L1|4QU5h}$3#$A'
    'Ok+E3$Xqb1$IS*=>fe?Cr5u7LWw?T?4C)JxKniyQoaU%Odk>}JS3iZt+_gn;G9{(JPo$+?SD'
    'B8cVPr=YdhyKbhJ_UH9P0PZv_dXDV)jzxur;@o{HbLc#6E^bijHc%Vpq|v>NgL=pQB3ClDXg'
    'pFcV@3wgrebs!hYc?#<Qa~iu#2!if|~GZ1<eFSUsnpQs|Qs{n6C{uoA4n|uWX$(9g#I>{Hl|'
    '|eRFg2nmYi`UrKP1?V6KZGN>3BgE%=d^78@cny$az5CaREg|@)0v5`*as{vrZAtk8WiE^OKG'
    '@H@8v{;{N8vIq>X7pn7j6G&kF4u^%sMtfmaMcYWq!KsCYI*oQ>%-gpB>CGO0wdVkI{(3mT7y'
    'y|gdoT$Kw%pK>9%x0#J0fK3p_{=KhrmR;<I3J*)YOUJC~V!ts!(GNf2Kq&`FU({YrPjG4dcZ'
    'Bnpy??=_oL=KGo-U5o$XDObAW@}d6Jx%P?=d1Y+Zk!WF{1X0<m*EpNlQBdvDp$%>W%z{M!z6'
    'l!d-UDG!#|JYM43jqrky7(xmM##P*YuTBS>C)qd-M5xsX4zNVuZ)XZ^Egnn4xr|GEj5%;_|}'
    '>8@6Q<*P{sF!Ge_=lsa|D8RwZQZF{5^A*46Vf$avqzAfk*WIY5x%`MMbi(o*Qr3z#MO^k3)J'
    'Ef`=BysF2$IXS9AWD;-Frvuai&d-Mu9s(q<yO^w7aIbUDS<=e4L1|YMGhv%r*j1W3Q}dg9TE'
    '~jaO9UvkG)xwf^LK_Xx>`?iPl+aPQcyheqXVFc8>+$%oYWUz3h<j1(&GIyf<xXp1pThw;FS;'
    'uv#q)&5woNTK7}tG+oS=p^)j!&D^26{UFwyG3UZSM-J!&m<b+6egS-f9JY2yLLUcH5ru8KuH'
    'OZNNgJ{$QqTmBuVK(ImgzgL2FndzwYA5|NO*@bq%u;TM%`0J{_+UPda2PlYiz!uxrR-sDd4!'
    'J?=h1-<lW4$;->sJI3Rjuy&ZJ{Ck$#4A2Pb}H;mOB4&Pg2gqWnY9>deKD0iVPWgXQy=U6z~p'
    '4Nmz_b{RNL`vvgHxH9{IS*AU%Vl`Ia}yo67R-)Vv47~W*4oT1$K$VusF6?;^VXjh2DJg*-X%'
    'urhj)@M+hSQq2*7@J@+t0L@hfYE(Lact9jbJmGTK*Su&C56s|Su(vJW88;yrF{N`<RB3%jeg'
    'CC9jV(AmWsHaCLZoVQM(c3ziO1E#Y&N+IMUCH6)VZux*tJr-f*l~ubFBleN6vV0}F^ClJB5t'
    'ftUpgSH8y}a87oDLYrHrgFuFn22L2kM>Z4{crJ)Sbwxza*%e$f$A#mMpQLXNtaqdxmxZWW3#'
    'OA6-uQQtMK3Ez_!yjH)9C@riQ7o<bVd=a$3(Y4L3T)`@S9In;Kb2^=&eNg?>@US2wF-b6krp'
    'Lc37x6k@mZb_u;+b7}ZsyA-nnGfXXw%YRD{AZ@69%(l@fq>-Lr645G5JSY!jz}?FCZB!Hv$C'
    'KTI%0y4TK0s@aA~Y;7RDfO*Ni9q>aM9q4Z!csuy<dW_fAoi&povgEYMWVYd5pq7Jnz85favz'
    'OhI7uBiK42P^N;;3DT$d)`vAK4kf^vM09T?g=5@g5`Yg+(7-qIJvA*Nav$nmVWo+UmLvbK>X'
    '6UhB&2*=A>T~xY&VVr+<hzHNRE6*F@I(C`NKe}K2qjK_gfFhxsY#R-WP6bi=-J~J2s$3z&cP'
    '7B2c!u^&Hk#uMEkj&zeU#meM(2(&ksvrf>733R~M09)bH7jC`O<aC2n%7VG;n2Lz!ij}IB{q'
    'njK43<Vq;`$|NpKOPksri;h4b=Y?eh9IIkY6y|W`a0}sGoMBXKeLnwW6<~U=d^EAp7M8sYi1'
    '>(BDdWd$7ilbgel{tNrM}G7yTl=s+%R>j+=O34L#p2{GS{o7#0zDvTY;8^NP<R8eX3!Q^Ixh'
    '709+!1C}`CCE6Cln&2H#7=-_k890H9b{rE5;Eu&tK3dc2c9hhq52vk362F!P5pJ*F<~It%s%'
    'P1sz$Ql5Nxq`8JUpE;&F2$uGJq2LpjZj1k0T_ZvLsW0tG4ao%qSjJwzutP9pW0y+iN%4XWsL'
    'fZ?(SfIWCDSH?YLxCYX=+aqMAJEZPtEldrPptD6px89T#P(_hfpK5@MG_1iFBrRyD<?|ib2j'
    'S~jr`mi}8q^Lz|P`2*3feBaO2CCUx8|0xy@mB)h_Y&y&<JIxKC!?Ymvj<9j@XOi5ENXhLTAH'
    '4B^pfkMf?c)DHd2%#R~Vm3LB_+Cvg@~;6Q0|kfSX@km5SlX0@F~_?H$SyK7GMa1Z`y@=h4f{'
    '&_4Mu&vQees)CccvT_mEFwVW76Uk`qbUqou>XSi^OU-yv=}YW%sBN2En_ww~Xims8)aum6lS'
    'Zw|B~e0c#?x2oobZb$5_K-Yvdl?HYwN<kfC2ociEr^aWlK+^0V2*w;jVT><8#WQL0{t+ZWlD'
    '!?x8)4+tNOhsP1~WV|!;kzL73`j(xnk^2k1w=&EYsT~aaiNvX{^%&+ho8*$`4#Cj&;n2nv!3'
    'M3Kho%vX&wYPt7a!@RVVn%qSdB4)Sv?bNp|9Zyiod(s+tsvEQY9IpX<xm6%h-*&XM~<KE+?('
    'Y?nyHW$@0l$LN3&KF_T$WTaEzXWJ1S`YpGHW_HArOzM+l_`O+cUW&*e!vLSWhP7>B*im_kM+'
    'AwKK+oH;C3A6x$G=$)4ujnh(OogdqM{#Q$Z2iJA`L|}pvBBeoV7_GD*p)M}shU4J+9f`N+hr'
    '4a2?=6o{9|3tdu5ZcyGn2C;^e~&%ml>%DgTG|mH*aZsNWmhXa*Cy+K8Ai5bSQ}7p+~Mfm&cw'
    '#>)0?Oz6k;!mychMHc#WOx1e1!vz$E8eZJV3cK>L#Ow}t1^HMd?GA~TiFFEup#uw-t3HYk)E'
    'FHz8r=SRebuBk~z-CT85Gi=!`^pYro5dhZ;4_?2VEeTGJ$xamj$^f5SIW?cBl*-Yh_jf{Wgo'
    'CVe(-lzOHpfhsG~C<NezNlRU73;YQF390Y>wQa|arEIQG-=V=|+!-(4o>|6#eWz_LlcR?h?p'
    '2}UtYonVY!Gj$>b;EvjuVh>ZcSF70Ch}8=a9=MWe8`m`#OpEl`A$DJ76A=7zF|mKfi+J)Q(6'
    '}fbn^15c$7KS|&nLcBg$j}lTAV05oLZ=0z#^5M{gs_|W2BgQjefy@EhUzN+_>ifKL3GCXb7M'
    'qz^mt9*Ud;W7LEDw{0+Mdc0($^!|9Mg^nx=Go~#CTfja{8T_pbdoACO@VJ;{k{--B~6Jacxn'
    'N;kaIUuSP8O!<UIiFmXW(}M=E{c#KW0m?DZ9nziCN!Y80)>zEr#K@1!<GFPb0~wGDZG`9v6q'
    'pzkapHjj^Yw5zT?aO|Ak=5d-AdE&`EeIwHF_)2TIz7)pL>Bvh7w?2=$J9ECIsy=c3_;r=^Sp'
    'f68?`0wVts)oFwplQ~)e8x|wnNx6U$f5PU$G0RTAMwz4+%!hp?yq(D-a!V$Qsnpuxz2*TLFk'
    'zv&^H4pZgNEd1LCHt0*Wu#bEoJb0q1mIZ)z*dL^z_<VRN01egb0PPp}i+m)Bvp?S+XdM8{$S'
    'R(ZS2hy3F<FNs}Kg+Ku+JOkx7cDKF3j*|b>!j`F_TWGP8ZH^QT*#<l8u*)6E0bItc?m^5TVV'
    'mBziYaycl^AT!WaFuNbnDd{ZoO*)H%3QMGD9szRx4A1j)^+lk;O|aGa7B_xMOoSP6hm$Sa%f'
    'U-!64_1$PeagClOS3@3(>>qZhC!_akrUc2QOd)zY<Tn;rGW_ajn}`B@8KM7B*G+nH9wHfANG'
    '&Z6gt-8z{5axE3jU-z>ux3@qC)$a@)?iWK@(?K%vxm7ViuYaD+)^_Wf4ZmYD(5)t`C#E)M!t'
    'Dq?XmjvUr&6!o*`I4zRV)PNhs?XqXkx_g)(ML}@ltCBMfEsXTa?6HpoAs*@E+`Nu7rpmWh>Q'
    'fw_?*i_C7+Xo;3l$E6<Mgphor9*#Lc!3EP4+QQq964#U>j#6atV!3Oq9eofA>OVxHVY6I`Bl'
    'wMj1=ZgaX=TrY#&^VWlV43X1+b`MtZ?_zig}2VE(-}y@K_1#_069b9iy|Q4?gSe_wbN)Ls2|'
    'L|MzOO!o;}iW{{;7ql4?TKJzQL6Ub`{o&FooZM#zDFyu)#E@IFeyrd-*g)R@=f{J^l!!dk{z'
    'EV0VzOHgY+s0e|+BRc7!B2!>mu4S9Je-SK9pmwsw%Lv&pFR_NpiyIi73n#WL3qSC0N(;j6l}'
    'K;|hRjnC_Lc;#C$)^!o{Ty{ZdSS7dVDHl?xZS-2u&GHzOV(IPz|_lyIMrqhJ#z7`VhuP%qwH'
    '6D>aHhKcSh@qRR$=$g)6EXu+FlR5}vl&1IwhhyHe+%yBF6gO_~JoKm6}l8VtUAYa2Mwm4W7U'
    'a36sQCs;8-40R)KEbT)t8J+*Ta^Nr8w7lan%n~ui@Hf*l*S~}_phV9QlKn=AR{-=0E8m7by2'
    'Z5KWMgyc!~O*6M~E&zq{;_rd7?&*EeY@-Q((!s~PvGY;PiGQ7e7OeR=IzXs4UUJ|zRE2S~wl'
    ';vK9)qC<B0#=ceY;w@!GYp8{PrU1pt0n|Rs4Rh+w;A@4tfj5gsmaksqAv1o)CrB_@!}nBk`p'
    'T0qALuP71L0t29Tq#jz&qTq!X^J46m5Znz^w4uEvy5c4Q_*=u6$E~#XrBnZ{b2qiDOZorXUu'
    '9mB!nO<(eUISoGxakStH6k#?$!W);8g+cTeRQH2V0fDw=28qrJoe^#ZPxoZaike7sM{k&N|^'
    'opS-e0gZ)d_xM_YPXSpF!7!*x2A%SeGe%(#CPpcq<X%~<9-uI?=b7(x}$mUlIkH^Iv>b^M+G'
    '9oPL&WZ#6DCU0Lwg{kp8j#sQ-cJ-ijZpz;+8gr_Msw^KKN9Vwd4(=s8wDuZnmB6ZfK{nbT}('
    'x$B@#_#fMT3;ZP0Sg#=Wg}ew=1^~x}#OCgKzwo*NfeH@@_vlv_LwwN3dQhVcc;7mo(Oi>9WJ'
    '-iUuNpE1jf@^bJOe<vruxXfS`2a8abFcCz$XtsR>0ct3b}*wUrUg@%tq2sa8piqamO#{$Pd4'
    'F4o-hN^LN9YMBahkxC^;<#3M~m``bWN#Lr}}U2Sme@Jym<0O81O&5<1=XLvOPGW2s2?)8eWw'
    '5`w-r>6)eZC#*U_yODt92xT+%yjv2Km3i8^tZJ_hLC$?V?9xFKr>n5&Z)Zi>I!8vpxf*ODta'
    '!=ow>TQzMOruFs|kH-&$c)$EqRBHRhLaJ^_xL%er1%sSbaRES(SFNGI}{ZcWaSdM8c;As>R='
    'enQ&|O<-B9(wQrzEY-@2@qt{|boTEnpEuq8-Ab?85%Ddd&@D%G@=qgOc?D?%n!5lonhsR3>x'
    '@Kvw}aRXhs?w+8gQRv_%Tl18;yuPkJVG_EHXav?~Kg64BD4BVp<7P(EoWn&_aHK4dh$)c7uX'
    'FNCkvEwuSEauxf4}HubIM-jl>G&`+13ahiOSxXDwIsXrwA(05y%k?%oYE4}haKWuO@+9t;H+'
    'Z3eGK|=}kreT5EBkF)-J+SEq?g1Y~nQgRf9#BJ^G>#wkp4893yPqc#`7%MH93lUc)oUnKHQq'
    'qd(0Mt<^WHDryJw{H<Cb24DTwrC7adp`cnFsNq$3ReE%g^h6{?n5C15HNv;X;^39vKE&LEm_'
    '|CV`I-EdY&W_L`4c~3FVB}Mk+*ZdcWS8iLdL$@7O(a^QRDWJX{+je)@Qw@2tW*4~CzU}?bjm'
    '+xh0mwz@XflE<t}%c_ljqpS;N#=nqmsF@fsYfCPCc^h98Owc=q<`3Vk~}p6L^4kSAvMIT(Cc'
    'SV?B0-Sp58bhD{YB`d)7^3;4$6hHC7sl&VzAh_#d;r22Rswco!WLC4|y%GFyK+dt3tl@{RH8'
    '(EG;$V>u)bP!>E+Emq%>WD1=B!B2sU3p^3Zc8hY2MqR9@7v+fb<bQLYCJlg{T?D?@04hs;{R'
    'O8Z_eUzuil7`r|FB776lF}sl6E(?-U=SVBjwn#UbL9?6cnb-Ah}m^@-NR`08j+a(3nkzK3yg'
    '-&@BTITeK+f9nZk!9A@!m5Wx#dQE7U`m@>RH;HF;GX`EeK6DjjCcxvFx}1uFXiX7J`Ru?%<P'
    '-VgsA?H`-%l1_atyrb=AXyhP&H5gV-KsSHy7hr-rn#5p?!{fIFPIzUac1~Na?s_Y51*8w6UU'
    'XcTV)(O$iXqlCJ`}zF9lZ2+*zu8f^0UYhNW&5W`?`#PXMITO{e27|Olwq(+ShU6YHDTw-56H'
    '9IcQ&XWu6y$ttb22(2#tvUVT@xfx_fz?vlQD2K-2p~wdA{zWru1ZXX&MYuvF5Ye`>qAET*@|'
    '-5_cvz>U&fvQ!DftD7Kpc|&?H?;Iu`klEoNBqPAXE^#`aUpB~N{Wcx+DC`FqG0<frP4)mViM'
    '<q&^C1fszVg}IsMO<^s)ms01KgH#2$0ksQAJ$w2~Sl*#K?`HJiLK=CES(qN6CnvRf!$p$tV)'
    '{Cz(XK1xjqJd{CAYW9a;i4L*)fKDkbzYu3mz@3;X;oUh~%f*d}%?~uvzthspvo0w>tHqEo%n'
    'jB#@_XX1RK;FMqiqSB3Q2s+vTT9;%qHn!bde*qJ<qt(~+pT~o+Rl9fMIDq(SZr63mX%Y14AE'
    'L4ZEtcmZ9lbUA)Z$hZ!i<skB5aL_na0KkLc6Ap}oJXhTK?@n}q>@8L%ACVPwJz-Z1y<ympO~'
    'hPHMxb^rx`cKuQYhQ;i7zhscu{SEU5?>${SJe0MD%kesWuWzDi^b4E}!$e};-5_PtN^@YgS0'
    'q^G&HyA-3lNyX{8K<3y+l>ZW49arKVR;mea?&;$m>^u6Vc}zpm#I(Hr7c*+-Qa6`7HgbHV=n'
    '`J6@D~~fJ32~>s|4h=l~TJV{U35|Fmzrrlu;QXqO2t3(MGf;!k<wL81%t|idd%#IVpgaON$)'
    'e3%#?|*5a0(jnv@wgkwm&7i1Yh;eRt%yNHmD@M|Ql(GT8j6uIo+({X?D02SSMbiIFUAnnmb8'
    'OdBA@ZNdk4}_~6+<jr)A)<-P<CRvFHl&5>99P@ZxvEs_lx5SPFMa{;$G#ul1sREK#FxR9^a{'
    '8nnp!4VNJWx3rjJ~o=J-Ao2S0YVmDe$0Nb;;csOnM{rtOsd1K~KKTGsJ`HlW+?Uu?0`2VDr!'
    'hMvtIbca>sH~ko`vYZf@taLwS*_3o>P+?S|HZU_;!mmYJkBfEqr^|frmsq^dQ8a^6=2oxN!r'
    'q#pNato7!7HJJ<v&kmZ+bW8fT7JNV<rABSNKGzq=LV7`i^vW3Lk^Zl_B~m579Atqy%&Mc5ZX'
    'NM4Thk(E41Us`_yPS5cem%3Pu4(JrAxURqms<IHAws@MT@>K4^rYA88d01bHxR~x8Gj=qALa'
    'NKb{ySU5oHWltmcE!&&BCzdTcoXvb@V;pZu_q%)yK0V>-VXpLS}+E6q)r<tyT4N(zS^_@-l9'
    'g{M5?=%lyqCogf(!ZK!XD}0{bbQfmGpbVv%3aMT*_;ZkX)x<_c(R{N<jKR>r`IOxCFV-Mc9-'
    'f3n(FAqF->6l5u2enA$#goiG>%hd^~ry7@m%Fyi$pi+?Y2=Tka<Bi1eky;Z?V)z6JWI<q*c}'
    'a+_O_~N;Z<9`Jq0+3d0c7v|V%mKHC001Y7Qq##BJ6Pdp6<|>Tua6cVXEUAEik1Si@Q29YT?y'
    'g<-S(@!?u0WThFCcIDY4iT7K#X5Fkphi2}Y)WvCC-4d_M76Qfpf=Iz{q0M!P%V$U+B^aHf}?'
    '<LeA)0#y<_JUD{Obi#SP!PO`{&|$QU!(JoJ!bNCuDazQ30|v4z#GduFnYyE8PY?|Y5ySg9P@'
    'RBQvNo0QJW6c(uz=$N{(7!(QOoi7>xyTMES_7L;7jWBZV;{J<?nM{%02bz?+K7z)7?p)whld'
    '9YjXDYC>`e2Z`ouI+<mf2;r11Cx9Rt1u4quKeHL$xF!mmM6zgQup@4Y7@a;}OCztsvWf=eC0'
    'cYP%B4s6s_OkJl27WJVe9^58jhDK>iu^g$Df0KG{6x)&W;KWc%!kllY<6*vZEW5MzsaaN!yS'
    'V3klPU1W!8|XaH@^lUl(4=&&8gI~eeCvWGlx<5(||upsWR)aOgE<`el{IIgvNs>SF={RpS~P'
    'Mn~1E4>g&yoA;wTkN)>3b2LV#2TMG<uvJwri!4~UZZzneK9Q4|K;JrWJKKQPi8dn8r0IfS(w'
    '<EH|)hqrcDuk*R31?Jqc|4X|?MGSyeLT_oi;(f>JF*Z|x{&Wxn&c2m6u=YjsK&?+pi@iOo#y'
    '*^F7t&^44j@&eb{CBlzcQV?hR2$ira1nA=99!e!eJwB+~?pDucF_h~J>Qfp=kxyu@p1qHZ71'
    'CAc2Mdk2H|uKoc{C&cle4z3^wazj`T|KW%Kz0FbMK~wXyR>{(Fg&#aa2EeC|P;H^&BQn@KW!'
    'NiQ_B)&Ub22Hsrtsb7B~~u0Hu^bUP~*rVa`Tj5BUq%ynGOI{a$w&YI<l!f`u`BCj^;XsMAzk'
    'xJ`RT$~e1oHNFlA68=r{W%wT+DaS?aWH}v%b4>sf)EabLLdyC|Jqo&cg!ikn}40D0iJ28+&d'
    'sln-CWMMUtg>e-wAj>hPJo7Qw<)V#eg&AF3s(!|7p#6sIe8%2-X0PI5YXv{6VWvsYwfmz~=)'
    '+0t?i$fqQ6Wht|dui0-DSoKPg6iK7-c1)K$`cFW;w}M{R9X15yq4rA<VzauG^&3n?NK|vz)Z'
    'p^~#Ub!_))@WDIb)ws=5?Xvvl|w%@*u@0!CWwKkTT$IeHp`ziPB*|0m6y-h_u*4(vH*m7i%A'
    '<<1F~3Y}7VHz2gOhFTk+aD|^Ow5Okj3Ib^WxZgPOY<^BJJkUwscxpB&<h@DE#H_FoON}aK4U'
    'FI)6dsk`=!0vupW<(ll7G*x5s8e|>0W$8ab<$mmC8lC^=}+;0v|e73L<e9rh($Mo_ZgAxRRZ'
    '+90M0gcQf;dg4@NYaGi*<IUR|&%ApNw)r%SQ19F<A;z5wilEghwWTzB-){@hFieh7K+hB16U'
    'gAOG75%T!*-9nu<a>ev&tGEvimknR;n$@V!L1;x{guiHRk&`7z`Vhltzqt?I%21sH8Us+Ghx'
    'x-X3BKVlK7ziVQq;=XMv@)C48|oR+rjeK!ZdhY+`=sw-#l|>ul}@8B%)WgY!Ep!LG<&(R~m0'
    '_$kn#~Gx$D|3L4kO>hM%L5}Rm^l=lt>_we$qf67OZQk7ky1YluaQ!%&^HF$uB2;Ro<Tc#;Qz'
    '{c`}(W>vn?wFxR$@pExikUy#QrfobhSqm!o{R!9Duq$*J8{tSa6Au>uhpf2l9Bf~cU^+w*Aa'
    'CEyv}L0WDANsfXOTQI}qZj8RE#tXn{XX`17%}s>}@m(AacimRuK#BU+YH`Qf=Xk*1NPMaYU+'
    'COJ-WRom(KlNR{k6t_74ZS)L7fBW%@+9Fm(tj%SX*@iAsuWM}|jU@tX4zpe%g%qQH-stI-N3'
    'smvx*;`6Ty)qo!Gnm^e9#V6Ol3<UJ<d)-jgtq+f!${9rJI7fG4<c4;N@o~Qnn)lswh4pHeNn'
    'sdmVT1ZuP=&xpV9%w*f?jV|s<nC8Yxe02z+|R)<JLf0h<;^7eGL^q&9%?@(Jj)fncjU~M7h<'
    'M)l|jNkiOsYMaq$8_*Qdyf5ClbMg4yMLWUz?(fS4(W<%7qKINRn4yn>}HKT<{F)x|J(tVJ_#'
    'rzQUFV?Ikb@66=;xHNH}ddJ(wu$-IOHjDfh5)qh&CgXhre%2oA?Of&(e9v;Os&&F$_<LTgax'
    'uA@bmr1(=V3QJ-Z%{Q*T-$c&l{<j{6u!|nCKJ{~hPHTbF5Bfgmd&EC>M^}P^b%_vZQkBM5lh'
    'ZwoLWAHeA;UNdk+4P@;Vp(p-mFPDg8Nhy7g=yuspyW;gFrVIns`Za9s%wcG^4c6JU$rixx91'
    'iq=?geiN8jutVSG1gfz;xi^}kc>jzuLZsg6mz%&Ss7bT~8nM(I$;VbxwHJszjGiCIoJKmAC4'
    '-`k{Ie}~u_@dnAw7SZm>9jpqhcjdZ66HRA!$eXDgsis}>WRbtwNMfZEZhGET68#*Uc#8!DDy'
    's&;VDy8ZsfYjB)nl;e<U`0S3Qn))2?PtLp=!rV(T(hgn(QREwYQ@kV2UZIGUcIX@oa$v4K}H'
    '2aZo7#qat46AjC9BC`)>sZHhHA}sZRg<xrZJ{Z4xzE}ab!BckDwMrJ&2;7Pcz)BiePNaNt&Y'
    '1AL_TJ%KKsIScEJ03h{kC!~iu1Gg6oFD*n*x<Icuc@yY24*|714NSeU36O7%#W-1?!gBuH=n'
    '2E9w@l#JP%Vun3g4m22}%5j)p~hvP2>5C4Z}KE{nmQv6T%77xHi#FccAk4;4RHpY>I>A4^CP'
    'nkzIm&h|d(9axjKPW7vboUNBqq7x`<_rjZK`9vKX+1*;Pwu51Oh@nbA1b_}>JV~{<_Qc`i+u'
    'LC&uAevZS~5mV@M!p^y~+pxz){yXuacQkx?YC3uAg`R^VAO9bUtzz}I50iLpt`LJcjMIW}@|'
    'wwnC4QfKZTPR2%wSho|5kYkziF6G*5YgKAnNml6eM@3vJY+5GDtDUl#BNt(OFXJe$E-)o}KO'
    '?B`z-+!JZ*v$ixnaQ0`DKHHbL-9`-{{>wPfR_lR~nrI%(ln<01TtkYqbX?n{4IAuQF?3pXpI'
    '|Qd~K!;pJr_xK7Swh-&?I{SFYJmg0DGsj0bu?ON!-MWA1k1;9~eiNLqBX2!8#mTirroiTnN3'
    'nN!dbP-z-@H<7Sx0W4vE62Hf-1Or#{9rg8?hrmGvEqpKJRg7r7WH|VkaG?qSTGdq{AD*ShvU'
    '2q=2Zuu2Dj-f1(0CrX0vxh(b$)B7?%>_agE*_rAyv1_*2WWqCdawV3Zo0vGP;CkfOs$@()>+'
    'I|_ZU2G6wlcspQHV|9Dc%V#Xl+`8(lno&){%X41|!88M0aZ|Cy38x)}pN9r8mAZ+n`{SBr@P'
    '`EGdS2_2skVKaoR7#UwJ4$UFUtb;yrF)446Tq3-&)M=)TZ(=GQNxAa?Yx8atuuDJpDaZ&xDx'
    'VOs90MS{&s67_sFU3xI5l`ejs`sJbp~0%=*m*_?3-P~UJlp-{H~YfG|0&r9dM4-u;g_GZX#I'
    'xI>LL+1-bidonb!;Fakp=$$Tao+gJ7i}Dns$h=*E`ViOcHX9u<Uf)$Ifo>MP7}>hlrt4!m?a'
    'rU%mbKLO8H2%D|>y$6A)xHVz9cLl)S)i@%~4@x|yKz0())Xj}M~9F4z!Z`2_y+Ga4q9ApYOz'
    '<&VF0P7M;`HETCxGTobIDTmT_UZ2cLu1pHxqYUaIVRTJ*Ure*K8zH$^Z?WznLwL<dK)B8$;m'
    'ua|I^3MB6I)rut1S|rAc?j^sw{#+ZCO|wZc&U}6|aO)2ckq{<96bFfy`=NR2I?VfAKpNdk6w'
    '}w=@~fl$MDBTb8ha&~Mx=*sc+Ugrk=C><X!g!&vB&r$ntN$kD2(VaJiQzr04pu9(3TnPn^}d'
    'ENUxkEkWiKKCL3%y0+=$n+Az3iNc>Y+QrV)+{U_UK&K7VlOEI0U;pq$ixRRaJAoq*7E~6w#<'
    'e^EkNm;{bS9+`~wi(AR@XGG|V&h_=bgtY!DsI)7D*itK~l4_@6WP4FS3&jNq2~`0ZVxSnI%Q'
    'X+CZ{;`1%I=%J-kxL>)c5wLR~Y*%{ZV3CPGjw+lM8RA<&m-~4)3jIlAa@GmF(z)Vk0<{n#@{'
    'vu=mu3OYHhp3Zz_3ol@aq}8i9PqOZE*b#^+~?5H<c@ZF}oCz5Ef=aNwOMb#o3RPh|^m;|71D'
    'rvgeA4)a0nzmB~`*RQ<_^wd}wI3nUYs@V%02;)%NG4J4`_oyTK5LzIvw^*?B<@g+Ea@{>ysp'
    'y(In`=m2+RhLbw>LJnO-X*E1Eo5C7=2B)H<Xnmpz%Av1m|ANQ0(LGo^!5CxLkF_siHFS6u*6'
    'KUeKX<8#GOg9E!yWD%zSBNQS6cmeu)>Ef<wH%{`?YzPS6I)qXjn%n_VvSjX<&iA<N=OQ#r5o'
    'toPMitG&=?1=SG>#To~yzlgh#RsTT;I&%Y`R;)q5bX|{?V=bfQ%Vpf=x02pAR*!5+1?pLE^N'
    'kW{x%?i0lprboI?FHks<QTl<f(EDswS<H@rV*gO9>IB^4mqbgz{KB73F-+4Wiy2G0GzD9V%9'
    'U4hJl4@;m#&Yen5#(W5FyFV|u`yRUXz@k%(~{$eFzVmrD7`2uVPic5R*56$_v!4?&La+gU1W'
    'T%wY0_dL|kjkwekyC88-&~ellV>F&08}vR-mM@kJQ2i89z+f9OT!Nj%4r#)piE{vfmtxE;c9'
    'ebv5L%wNEbBFaNQef8=1XJbCnxF-NU({xGJ``<woh^_MqFb%QV%Lo$IS$U1`noolN%IEs~$O'
    'G`j7v0S<|W&dIeH#w?`#(jf->L-R=zp38Jzv_-R|$BH1av$vrz{N$?8&Ab<jhi?}_D+l34gH'
    'TfUSX1{;qmV0z(CnM06b$w?hJeHM)><#WO#T8~hBah!%{5T<DjEZ%1I3H@GC&wT42Bix-=lw'
    '(;pH;g$~z5k1|p-Omvepl!(Q7LQ^?Hv+s9j!s<~_;N%^2(ItkObN={TNmb2hzXaik|JTdenT'
    'yclzv5Fi6$t*q_LUS=%rNqqd4kxa{BF{4$x}B-d{UtI=j47`~;l51tKWUj3MyRk1ojC^J6&d'
    'Nvcm3hEu)T5hOBlnAeZ;8`-UYrq!ejnvND?)MLjKwQo?c5sLD#80yc_ckejXt%ffmceIsrC%'
    'ROzyCjr>+|u&5xL(Drq0_EW)1e+jIHYMIn6fpQ=eZ%pgjbuhgD)+SLl53&#U>fvc$%hWl()t'
    'm(EP#=g^F<5QZyK^$b6aOKSlIgZ`26qckomIgt9mB%_u#G!s<j;B*9IAC7WXvI>ehJgj{BL&'
    '|J^ydKJqz4BesF>$E2=4oC&N|&wz{%bsq8#jZrwSQd%1n59w*Q7lwn4nQ-da;_&FVGjtQCu%'
    'A`g8b!{^5Y+q@M2We>80W?mrYs65ArEA^4O7}75_$|e*{b+E6lQkc>TqQy<o9(@fIYiY;*yv'
    '9mPMp~}GFgQJ?3bZi%a*eprDm%%xixK<HAaEE&R=dKWm~?M^i$;!SCZkO1xI(IE-|F$F!i^w'
    'keFroOh=5}gj1Q5d!u}GJZ<fEf+kBZPLZpB9!Iz<2K5v}mNDeqbTA$SzEHW$Hv`)Gh3N8LE{'
    'LL--G#g>wI|apdTR*Z&cgcRlSYR6P;KjO(6x&RSx-5P=yY`1fO->;nf_$%n{Xk{5Pt-fS=@U'
    '_?HGF@(OaAtI7uba(S@%QHnk38e4}lD5Sr*Tq^3`nE{|?9=g@3}VlEXa?O?b+^b8&Nn9;$%_'
    '^*C=2TN2LY#b|3)890;VSF(t`n#COAS95%Dkms8v1Bg@w?R#sWv1dfqq-z=!iw8<%;Z){dO}'
    '|3h--ODh3{seS;~82?BCES#fgM?CL9~;W|4>&LB;PVyOrLY_X~}_4ia}B)vA12y;<Hz7A;F!'
    'TASNa0b|VRb&dMvY%zW8D-Y?<j%!`HOO3OIgI=JBI^bOHXE-Jif9I>ZihRz3R3)es(s@H%-v'
    '4We8yO|VQ9o7ihb<rmoQ%_EJ%K|y!eR$Ba+r)L^-b6W+%9;?Og^YS1oeU5&{01+@hq%2z9)8'
    '8a7}GA(|m>{+{};AQQnlk{QiVTi|qzl`qOaTx_E-Tx2Fo?V94vXE=67+Zg3#LLygzp;1mpx='
    '*t>Lr_0$tnPE5bP?m$Jn7wmPA#qjpmB@&N{e}pY8~Oq~4ZXm2WFh)9(T<fz72Vp)amIGy1jw'
    'qcZw%k&hlPV!w>zX;XLXvb8K}w=<g8@CJmRB*Lfkm26<-DnI>!VUvm-~c9~&v-LY);}V}&GE'
    'e68r33I=y49Bn2ps@fl`=&vQw-#G|pyC6|=Kz+HqC<)m8Ol4Z9fcr$Bl%E%snKmAh%MPEL(}'
    'It*U63B)?5-DS9UXb_+bPQ7YepfjfVFYj;mx+$*q2c?@*)&p1bG0poTot_=@{nj>nuZ^^3OP'
    '(|GPZnq~HDWtv^lpwa`fKm6WBnRu#X;4JI*X{qXB&(aZ#HKB9q1JFG^J0)GG#&)YfP_B9_ye'
    'ULQxiumqt+fczFCcq@rTTk_=BSM2DK>(xuO%i_?96g{Hnv!8uuGcH*=^C>3JHhM<Hk_t|>5-'
    'ROI^up*w(SVYRtvJ6+g}MEs34;uwy8vVj0haupcx;ksK_h9EWkVHQg_gC&p_|HnpWnJzuWt7'
    'dD)<Jp1Q+gKPo>N>OsYA#LTu(k@Z(8c<%Fp_5;TzOvpAtBjUy4eoY8LUlD!Gl(R2l;$jDWXo'
    'zU+(5(iHCIX3B%IEj%r9J3_i}!;Mux3;slrrT<{hd?wUS=6dq!u8N?*G%hx-z58Sq#BG^kD?'
    'p3Iu~3AFD&#(I2d&?J{IU+1wJWOkNN)(LfG%W6K#RjZMUZbg(~>J7MN%@VA9;3lzI9VY?6aq'
    'oTzZ$@ZxIj$7T>IMtKn2@-)7%`LJ&7cm=TbGrF@t%$xlRzj_S@*x2t7T5`xPNGvQbsZ^VI(;'
    '}wH2K?K31IXEyOUIlq5IRg2xM<EC^_2v-*hi#buaRe6CpjTkg)UyvNA;4<kjP~1AcdKL9;s&'
    '?1jIuvY9@xb2akx9&zLbV%-5X8#x+6qc~gm<;ZD9x*I92cLFUH@4SKgE?=NIC{`-$N<6ydtE'
    '3;~cQ{sm4HQj)yp>h=;n(pJ2A>#UlTF-Geq%sp0Wg!FNL(wK%faN0ki6)Pu0z&4l&&5$qu^M'
    'Twr1FhC4%oDRLQk#Offq^G9q2DeaRSv&YwB(W;nFJ8pu_yxt0&$8Aea7FVe1VsoVOFY#PO|^'
    '4VgrM06L5dJs}?r3>#>rt(`}Ul|gRx71P`2T++<AcHsn<3JMU7hrg*5HYtlj^}oIIOlnoxg~'
    '0iAJS8s;-LTBm>#>`*kM%WI}rVhVgS{YHA24+us!|rGJR8y5Wba&PKo=gz)mypZkJTzvcHa5'
    'Bbjw5xmR4Qi_Mkz1H$(fguBSHW6^5{uWg8GVk_%2K(ZC<Oj>3Z1eY~fbR{W#wG*Nn%Im=4%X'
    'z%W0+67$m&POq`J$}a_x&74fYQVyGadUfyf&+Jhg#4(OhidGIkVb^z1b&FgldyZ0(|Uh8^tj'
    'Bh0x2t)*1Vz`J7j?cLm~2ZgI<oefuJ!?Z`OGlE(~fnkehX-U+$t7voS#uZ)@wKyGX73;Ugsf'
    'UaM-TK5Vb>Z6BI^BkCK9wK{LO*~inMdc5lIt-2~r7vQU?yZ%ZibNQXjWct&+bVdd)u1)XgN~'
    'fSY8(^lYbDR!d3mh_gm_jl<)T_yaqz_l4M3}K^gRLw_qT86WwhyisO0s}jt!*c-Y32z0toRQ'
    'JwcsP--UnHMR>RU^pcU<_A?kHW!-8}TK@p_VRB#uaYTCfG6?sPgxc?MY=l-A@SBVeTo?xrxF'
    'I0>lOMw!ElG|$uGiQJ8BZR@qxMJ&PnXI=7*Sm98B^Y=xzdWa5KIF#gt71P@c)O$PD2q_p)*Y'
    'pY&hks53G>1zB;-bl*dD+PdSmd5JEH(h_j=q(4F#<N&vW9UfobUz7cl-Lm>NCCQ<Yt_Tu!D8'
    'gcRMGw{Bq8)aNR-qB(yvfJ-_X<dxH-uBx?3&^Rd8BF|B&IkN2PvgA_0VqjBW=ZHbI&D)#XJG'
    'ogA4&|#EW7o;TVBiTI|!7@lXHWgv(710sE$=loJ)ngJbmTY(CX;aYrV@EYw3|`2T``)Iky=o'
    '-eW1r!fEOibmB33NkInT`}5r&FYwIx9{1*!8eq{#Lo2x|dm6z}hFP|t5I2}Qj`8tvoO>7amg'
    'n$~k%)LZY~d59>Ig}<<r2snxa{_RQsKD@tOTIlwqXKwSNGx<8^@wBY8Ap?GV81x(mx%wr5-_'
    'D>Nl*W&E`$=k|4|}tkTg@i*(F-9c?EcjWIX+s%`@-B<-$})b7FPJuW&1AG@MnY+`|^s@%bba'
    '2oxT)dJo-3^4^-?_;GtNdbV0m+1S@Obik5iG?2;j}hHHbwKiBn%%9iBAV~fDH~`vxcQ{d9L;'
    'K7&KCe<igp>P2)>Qvy-Xby+Kz)i1`;hAJ%Ve&*FJy`X==k5UiCX6$%u6r@{!{u=Z04}a$0)E'
    ';*OUgAdSh48PB~g!R*m(#H5b3Ft;ks&Gm~koCi_-qGZNNPP~AjYsz-)VV>ALDv3I#n06N+(5'
    'Po`m3`zYj);qSZQyL35@&P9L}Qa!Ur2b<Knv4x?4?frgPgB<k(;BEO<u;>kbHuKn1D6F0kxf'
    'ESDtcHgjkd#Oy4@Bfc)}&F0HfN{#aak2f<o_+NRYy03K$;au8YI&kvdX4I~$i(gXmBf-lZWk'
    '4$PpDXyX?(No8et=H;~cWKy(1O{m2eix#H3m-yKSI-=_!UV**-_QE7XBhNZQCVb7L7x(HFCj'
    'ts#;krw_^rDT#hnbuH<a^Zc~;I%D^2XUCUn+eX(oESsL}R#4J0(3&<{j<HV|j7vyttDpkyTJ'
    'n^+oIsC49j)tw(=d7q3ymQN8_B?1jVS_fg)%H;8cx5b&+KMpHb6(Jn5G+jnx<KwiU2Jfy{fY'
    'CiJ_R2&M(e1S-o2YoZaeXo0F=UG0rdyO7*Wh1jctkF|sH@%38vhQT1*-&J9Rjz>+ZWDaYJff'
    'Jc;vU=5DvYyp0tCHMEhnkoL$mes)~r0Q$cwiOP2Gs)qU+egLPMPuS*~KxScsZ7xUgWWO38>3'
    'OLC0J)l(`ecr$Gp)wDr%4&QL5!}J~zg)Vnf!<uW1LJdky`=I_F;#ig46ASYaJ%^BnbIa)qqv'
    'G`y7D_<HcGNp`J=Tjxo;=fYGPu%4|+hw)5y1kGMfq`1qn)E$)F@sOqw9$bhpq$TQUdx<v68R'
    '3|*c1IN;VNu`K$zUrs~bIbr-LoSr~vt>v}gpmK{D3h1qTd8t5-Dmq+UUwJ_@tANmjB;qX?Y3'
    'QYkszb2kBl!GEH|~KjDo}WyYI#T+xjX8D!ts%{zjaM@MI*M^G9%O$ybes7MfsQIE>o~=z^e!'
    'xGuHUpqTWe|Z}LaWR^9h--yz|wfdUUnTHMdAti<iF&NXulL<0a9nAG_b@u4p(M5XDF?L*tJw'
    '{g(!9bNg9V^hyY4Q;Qm?3;J9hbSPIyHatc4mivLqd`yz1Xp`m%F?NR-bFOermECEh}#d4)&S'
    '>(>a*(M60qsu`XT<TA?2l~lgi-unf^9Zw@#m8Ea~g|;d($|k!DsWqvU<&YnMd7w1(2NZ@yKK'
    'CoUU37pDfmURb>xzo5ih<Al6KiPK5b{vT+=BgAUS*OPAdEOG^adAt;RC`2QH{=L}{OcFa2b!'
    'UW0q1EzT_iY$_OezE0a#`)@uD#t?Blsd~Hj%FD3h!YG7ElA&dMZ&&rV(Ud=ya@X&eIxnktoM'
    'sa8-L&OzWxG`4Afs-nCaa7XpSYFxP(5Xyuf03JNAbsKgqih~sEnfR!`W3$!q-j0VVx0y``{M'
    'Vk~(TLVVyT@TwxFLgL4xp7(z)=;xpR@hW4Q)faD1qG6c%8M_c&P3*YhL%xR0@G#4m`4Yq;Q;'
    '}a#JXt%FqC66^keibwcK0#Xlsq|fo?^{NJ0@D-jA)U4aqY{k&3mDCODEmyla7J`0Cx9l(dnh'
    'D)LQK^fZXw2;(akd}d!#o=;caON(5)_{L5?umdZ5ZD)R$Q8xE?)6EazqXvnD%HRblVfD_>;y'
    'V&LdE;vyd4<D;lU3ikm&BTv^x*uiuupwTal&m!tFwt3*152~<a$Kbdu7@xb{CE@asjx`{j?+'
    'Ps-tz4kJwTA=U_2no5(e6+iE0+9h<0%88}oRt-|b6P(^fqfxJmWxyQC(O<-S#7(sg3s2fMw>'
    'x>LbuIaCi@l8J&_cp30{FLbXU^c1T)IyVh*r2#W1%vqQzMhn14&%peHt_kdAasJ%9CQ-ZRj;'
    '*(7r72ndVaP|$oBAm_IsrVoK~glfYjkY&eXX6Xnc91co99QsuNFD8cp7s%Fchy-st{LN^^nY'
    '0}h)?urBC7fV%h>D#LS+bJAAh22*HG$LY$HQJN#RaW>SQ`>j8GCWV`WPT607Csv|V&9I~RUQ'
    '?-&k5ag10Jc$cbrK2#S|TqstjET$e9E8EIv^5CI^qaHLm)UW_2obvzX39ezeS^050Yv)(vNZ'
    '`hC&?Ks>|FAXxqJQs>+aJ+ZqUCalXekLc5Dkl2^aZKOQ|Jec2-~7@Axt6(O`=Z+>tkXWs=nG'
    '0Er|(*mp_c^xw-T{t!PmmvB^oWop<<~@b)!<{@Y*jDzbLOrn%YLe-r)Z)1nNQ~ui!@N{gNTq'
    'ZpQt%C#j4=S=Fbih0Uc2z{2h}R!x!6wte(k-~zB0%_9#MaMLBP`9ZW`!5r8v+BLn7B|)|~5T'
    '51-&$X-7H74nF#jQyE_&k&II1-k2Ch3b4yjkty0FZ;b1m6srfd59a&|6A1PPTij5EA<PgM*-'
    '}MiQW+2JH5V--O&9d=JYz(2#@rVr2CwfLh3u?=s-|QPeWB_2(IIOqTT{C0w>wf9AXux_c8C^'
    'UpKkcq`NGSqJ#Kp!$(WUY>DX-V3*a;g*9ioy{@tnN0DZDRT7OyxRRAUI_Z7l4494kXLKa&tM'
    'c4UUSkcGs6<P7~E733D;bnIyeuYKtmbjXK-BU@T%<-Gn{8S5lDVMKx(rx9ns^@2>gq*PO;?j'
    'mTMT1^sMk)#QSaIzZ`#bbXn7Tj8Q6~Bc`^o0hS6fGyf`GN$7P`m+`s|v8rQ7hlK93vsx@{5;'
    'T??M=vcx|)%moKMc(A@ul+pk6&gdeNGLxiR-n$RO6nGs5DiNcT4>{=kkc;*dKX@s-2$O2+a5'
    'qi&(BuHrE?S6yZ=6^Q5r{jxF{73;nngGw5^v|pIl}dIJg?C@x^|`MnQfIt=-BBYS|i2*ho&x'
    'Zw0aFOGe#zzyRABn=Tb^&wYsXfNY&SKJPZJ++tlGZ#LlbbRhq(~cOrlFeUZix$;s>Py;Ni5Y'
    'O8EXSV~3LOtjSXovQu`0coNf82RvC)b|P+gro8Fl7c&WZMdH<IBkT`b<y?{$mB#IE_I@Chmh'
    'HzC-!#9p{~mh0+%n?mN+UPkG8GviVp;{TurfjVluXu*eF;eWed3#Z`#(7|4roX4Vuac^_Q=g'
    'BGU-exIdti$V`#GvHcLO#E?&wHx*#js(x0hbdQT?e#=V@0w0h4-np+aE<VpO%Ep(JWt*?z2='
    'D35f87+5Ex?&k0LtHJ@>ROL8}`5N4e<%O(3xo=rvo4Lq8T&E5h#*88)WrG@sInme*SEA1y7f'
    'I{_<NVaHbYCf+EDM@cmYo%eDBwNoIdLK=`_QCgK+M=!$Pm5a#HIS~(Yv^iJBbiX}=_yQI~h>'
    '7ZLrnDeSx4}0<n1#AFz9838zN5yamYs}zExyYgRR=SmShS6XZGC(ofgii4vY?vZX<b6X&w&5'
    '(ErnOTPXjoet5V6)^s?Dj`MUoP*>h6s1*Xq2I?aUF1&WR{QV8~4pAd8Y#ls3f|dOD!n-Bphl'
    '_S&sFUk_lq@#|+s4WcL^r(T+25F$vbQgk)uWPS$t5y44pB9Pi&IqbhT@-uQ+02{tn)domnzM'
    'VUqfba_}jd~)>y&!q@0Z!h><F8#d8MxQt`QzBMK@(v>C<2GZ_#ZpjDY6uCD9Sl~Y7nU&028B'
    '?B4CHYRgM`dI!)v{GG`qlktc|AIa<A9y{4^i5&A?N!A)v=x~#4)S%iR8^;QVKpu8j3yyZn1j'
    'voG=6Vhq+^4vwp=|Lc%L5$nWQ0{h?>aPq$I)hxdN;#=;fVM>Oyslq4u(WnIT6%1Wpd_*;W85'
    '0Q#vZQ*2!+s2nj*f=>51ayjmBeGm+Y?96)hzFMlLuQCl;4Qg9L^{lmKgKYX4DB1p{!Ple1wq'
    'Cii0T=E=JFkVY1q_qgSAR0NE)A@+)>^KKx&G#)6u(~mi~jL#8l2P0Ym893*qJ`|9J{k`>^r>'
    '1LypaG(8qv}Q`fShe!*<Dn9-)J&z$F6%xemZa^ioEfH3uXAOD~=EdSbg-yl^80~^r>5K<v!G'
    'ra*J3E3;1??JWs|WS&h#zj1zBXV|tR2^L}x^3teD@^sEWzP&E$SvPe<tqq><3Mb7MOr~(}^V'
    '<-CCtHQ2!n<K@HdAvnlY97Khy-_}CtTj-*?5JmZg$_x%uoCFlhddF-ee&CY{ZRbPEYV2Y(@`'
    '7fX)Y>%fR&h(_!zqi{VUw_p1iNLSbpc=5CdL~I*2wmWz9a$WO0sUWesR>#J5;lo05!<C*%?!'
    's`d{a!7>_dFeQ5$08j`@OGPC+2ielWtjJR)gH^UUz@9NfkhfZO&#%vNEshV!C;{4xBie-GBE'
    '87BLvqrLCcz-3!UNF-vbZy6!#2idfk@AQ{IZo;og<FvBg<WgvAu<y9h6eN3;W8dfHL!X=C};'
    'h-;||kmmLUG&IK->xysN)U9mWmzzQgQ<d+PPX0*X(1uWC(x#!Q0$#pHT*n&BDgS|E3Y)QXUy'
    '|Tg(b3B;F%O9~K1T-rHP;y7DX=K#u4cB1&x>GaaCS!t=Q@)eTtB87X5l^B{N5osQOnKQ{K?W'
    'AApZ39bYFiCgO%SNwzxhjyo(Yb!Th+V$5rG*6*KZ@qH}hBmqe}ygD&Qdw_@d<CUv;WR{a5wt'
    'h~nK&JxQug>3V<(fG^dtSMC3SgBc<CGV{aMLn35XXRV}CoJalmHZ7*=E;wiNfU!&`p9>th70'
    '^mRG#4d;uR?TnCFmn&)&iJfp+}q5<v96IOWCN8>=R`5kh+a5R!_bf!pIUvV%}jYF%eX5J(<2'
    'Fn)6n&+;D%J&la=MTsaCF>ydOmH1+#|kg9$&7EAaoQGu#q+frHu&p|E`WxTVwlIR=8#wf9yC'
    'gtShe9YpPe*c&dWD>E^TRLu+PzUPv@?`O&Hr-z_LreH}P=b;jS!y#h|JlEb2Tm7iRWVMay6W'
    'aieFYJj4%Mci#oQd+^9nOt7^LU1mqRyI#vp(r1S*n<n)3uQPeMG$a@#6S4+k=1oLW-B8VLPy'
    'PGxNVdbM6XB<?IZorF`p7L+W!zp-UaVRGMmzCC^1`AC!oCRAjSb;cs#5I7K4+H=sT;tQk}kb'
    '~X61!D%?{HO2l&G=u!x6rn%zC&aS<7^{rwswTvlB8Y>orNxPxRk*$4<54?vtwfjrfoq8b9gK'
    ')_btghv^Ibj_DVAqugcfzPzC4je+ZQ9R;6zMlN!<6=k%R`4iVXru#Ux=Ykv4&2wwD}flKC3O'
    'VwyJocItBQ1ck{5Z1)y<W#LvDU#(Ob4kDZOp-%6x3NZZnhP&cxQ*v(SLa-Usq&dK!IN4CFCv'
    'Po;GnD2Oh0%w2MQTAFp8+St6O&PE0LC7J|(0sVC*A7p=8Z3u^3orv^o;%#~#5@$5|+e%R+Z<'
    '<}ZjG26w31X2y5=>j8&6>Wo3{!A?PCquC=%cX%qz&SJ{Tw^TL+kX(6q<}XRG3<A{$mvB~|p}'
    '(nZaM7EWko#ARweQfqE`F%sEtzar2g!8d&CSyi8B;_}+OX^LzyC=da5Vq<mU)tkaA*f2dhR8'
    'TIAb_5VtY-fh)z%0vC}7meb<||-auT7dzl^uk(Bz8_{7qf>XK`jx0h?s^>}zR^*+nOg7f%Q?'
    '~<&{h7oAzp1mH8k;q4<omts(%awg<Y9wi*C6D%PDA;C)mwKpc#x6KLRK|E22Q(Ir@KHCV6ts'
    'x{h_VGNY{AR~CQi@qgycRO!nL-K9POF(gVRx(IT~b}-%+Xx46;uc8$dX+-cxJrx4uu>XdHqi'
    'Qf)?c4vLuU_)j^xmQfdSlM_NE%}lr@@*Jy|`ty;7Pp`xQ1V3GN{tN0bTWk!k;h<8%=Cm~sbf'
    'cK{_4mbL-xHxYgL@aoWI;dd`)KSXoRxsnr?+Ut{Ah&!Kg_q`jeg7ITu4cFoGu@yZmabmJ+2U'
    '2v};C@%0P7OVe2I&@A**`Ku}UgWS%iXEBv3NT+)&hg!FKX(r)1dT;UpCDU^kfid#?ji0`wrB'
    'h@~Z?9q0S=7{N9bRV#Ri*Yr;v;!2=lpE*Z=@dHI?-prpDAATJ*~Ad6cl(E(!EVFnx_fEIQ?z'
    'msX^*%D6BO2TqQJ#r*2~2y`l0kH%o`7xC_Mcz)B@qaG$hgp1nZ9+F(H%Aj}=v=EiDUjgX#>j'
    'k}D$-!4p{D8&EzDsGP@-vsyDG?V4bi_i!9MH^`p?1EUi2Ponh7lsL3lw;mm!yLK-zq3K{7ot'
    't!Gibgcn=jgV@CAx{SF1`Y3NVFO5Aqc^*ap54)!wEzSC%a%>k`R|Jszmkf(fytJ;>KA_`qX7'
    '*ouL8p1Z?}r`eJN5^F&j>9Co}C#oy<+g+U^(oer|Lq3>J)@S&BFq5NQEYQh<l9h(`a=!Kb+O'
    'JHjq1~9WXSvkyzw}|$GR5R2AoKSx}U6)ujV8&sF4*Ze-<$}_<csr1rP;e1di`-0>vI5^p_PW'
    'Z^OQ^V+T&-b7MgO0x?3h)6=2iENp+}OHn@6S?uL;u|FQVzp!te2#dm||<XL>GlKr4EA8o*uz'
    '0PIrz4g~U-CI=@HEa=+%?}P38QV@;F3^ZhuS)PnthcNj{jF>-n(`(;YtMdv^VvEjbV#EoZY5'
    ';T6SH<g*WS#LHV;?XcXQA=r!NCNMsoJHnL6(#mOM!d1XtjrbFX#F9C^6{vy63b{)9{rjs$HZ'
    'Ey}DoBoP0fI^}3%y_I5a)E@*vO-7Zkh&2S>1$WO#fkw+I@{#5L@hb!_s@&~+Oe5%+xa-Hpxc'
    'CDXmv<yowRgXYA2aG&y!bD8b0gO6{;UH`gJFj;Og!~+;9ucSOlGeSqzV;P8<A9|Yx+v3FUNA'
    '{I0t6TQVHWEb)vK+59M^8X$K4FcbD>4bxwndK954SF_Gn~l+T<dHU$Jb4#pxHJAP(A8a?$lU'
    '(Xi?AU)(+2nJLE2fO(r!ogM=I-fn`#Y{GnwhYy|-8%3se17N;qgXV9d#9<!Tt0GYhv=SkJiM'
    'm7^0@mqd;f{Ain}O)2`PJ;mT!mXQWBx41r<C1qBMqigHa=c##W2qEJOejp-9MIDITgZ{_ttI'
    'JQJzGDqZlDXRYrA6f|&vw^k=f?S4uBMV1$A;O~A6t%6U$UAQEk8;y-mi6A{%v@v)dktKK&Of'
    '8`FCes5`Bwo(((W(lm~A~<_5cZxLq$7N+S&pE05{+NeXwlT-hAaW_cD>{-37bA;(sjN&BmAU'
    '#$r<o>c1eW47*Q{!xb7}E1@wfqeTL^oB77c0GYs;^@CO&^Tg;r2kN|KksqG2;5p){&S!Z*6<'
    't>|)AO|L4zdNc^vlR50jlM&419NA6RfbrPt&w<jTEUfs38(nrrzTKE%syCxhl{tA%Wy9NlY2'
    'F@Fgm&G(Yqc?6x2iW9Y&O=VC>EcKDh<MsYO4*C+rL+IsYp6-GBh1$BA3a20ImgiyHlu8sQu@'
    'FXj%>42dFtIi09~ux9Ex_!C+bMw>ZXj(yECr0l(f?+6PM6g=S&XS)8Y`tob!gEsB-Dg2e);G'
    'SYLwcr>(IhF5>3@1_;KfjIO?sKeAT@^b42qfvwod=#24EPHT!T}}pbmFMF5pKEAWbFj><JHV'
    'wYx}`adYqp;f36^5&xv>{rplEZ(9^wj}ojl__ah%S@MZ9xwn2aHQN}}G3R~T5Dq?*7jPJ-g0'
    'VDRI?jeyR~WrIg=Z)OD&#cO{o!Z*8i)!n8PzzrL$-cviYhha{`YoFp}>dR&AU#v3p>Ki$=8K'
    'tgO6)AV<0E=V5<*(AE6f)E|Df4}pfPB<05Oa9xh=ONQ%8kd<UJY%csloLjXTm9SjlI;7vmuY'
    '0Uw63RO1OQjLO=vJC1oBC^EQ{j#`9LBYCd6*x>z%%fH(Aa?uUt5M{pEmgcgdnSGNWGfQIna&'
    '8h~F!2yEGL&qaaoiTKLjNm>H`Zj%Lp^hOYe;yI^Uo_(9l-J}$(cG3sZ`1K}^iKb^!8vH0OKV'
    'XL*dF~X(dsQQ@L{Ot?2duraS`&<%l0>NX=OC9)*nF@AidQ)QZ45dpt)G795qA!JFC~~i##qX'
    't>~ed5=?Y*aP5>k7bsMk7N|F9x<~aOq8))4k;!<UPREQXv%0sB3f~1TqZK{9EQr?iArt(iqF'
    '~GDf8x8r;ZY;%Xs59ha$Fc^lTOZl6p0&fTC%`txQ}%VpA3_rp|Qt%OD@%NM$Ea=F1s)GyN!w'
    'N44QqPT^B9I^3-8Lybuo~X%H-{_KP=MM6?|RJP+}o4v`iZUSPL9{ql|{cLPY(0r8j!dCM$fE'
    'b}U&y#<<|quSx4y^q-g_!ubAo5|=}lbHC}<9|SJ8B+>P%=Sp;9tU@b&^1xI72??#5<{V?>qj'
    'PW=;P_!aMP+h^ACulzzoy9O`6TDb&xGD)eP>@7gM>N=D&D~Pm`A3u$H+vWa1~!l<P-M#*C3L'
    'qzDP=?%A!-cjs*+;9Vz?Jl8R&RKjXq^X>qjW3*ZV^yv=Jh(Ga#zC#5J#2Altk$t9BdBQwXLn'
    'hE~6Trq$Ot|SiD~i@-@=)#*><~}##5bhE7OI8Qvc<#sAgFm&JFkNkmZTUeDt4QE8DjLNLGmd'
    '?^@{M`K9jWDMxA9HM+n%2PTyo<P??^M<zkM8pO()iSbx#>C|#i{icyDd^jqJ0Xy2pBg|z(E3'
    '?kxzV}-M*Jx|^=1*2Eh!6C<D3ewm&r1-b1aSXbd&+!?ofnDLwV0M<a^v6o98vf;3P7?lk<F{'
    '#zfSjy?&$p&)1u_+mbzU)lXx;!D_^J2c%Pz9!Puen>35QM5DCMD0Kx|Z?@Ls{-ossps@XKC;'
    '`R|54YhE`rFpzLUF^6kA=~^xcFNpnJHo;jWhg^|Su4GQNas5p|6rd-E=<H(@4MWigQ>aMJ3i'
    'cU2VO1oP#QRCwqYcu;(&fcsSI(NMuovH@i2FT<6}2()<mF?sUL;n5KGJFACl9uQ_235c*cE{'
    'P3lD=)%#BFQkCpVkEC<>V|EFzhhe6bd##9PWrN0K+W9>EGnGrP*Lxsq&hDOL|zpis_KRhXi0'
    '4HGxDIWEqzUXR5m3=7QN*1<sJJig>iwv@AaX?Rf;1RlodLdSRw6a^8C-s{a#zYU4|2s*q6SC'
    '5*{`Kn65^c+!c%{~J!c>kQfyLGg8OhUA##v8BOs3)f0E$=%7D(fkqU?AeMQhaDHGF=>{Dttj'
    'MpifriX6k}jEk<mm?40A94AmZWh)nv>H`+Dq~BPVTuEj+qHoJuDzvl0cA*DhjN6QKXZ=OfxX'
    'DY=NY5^u1(^0h`djml13@cn=8$CkAlZ}$fxo(a4gCD%{c>1Rs*V;tUP>X2Ut#+r(9Li4e&@7'
    '#n%OakxLk38cA|8MQw};h19oJg2N40XUJF{=wf!o=1|MvM2^Xnx*aG})u+3-&h_wwU{37sAI'
    'pcuX0T)6=mmUmmSS|`h#-CZag5&OeRw=QAbpk$s`k0?0IW(b$nfC$N;5>$=bT>Kp);;eD=hM'
    'tyCqRn3rtG()mex)wE=TrBRGK+(lJ%|OEVbs1n2AC!(KHx9$IK(Ji;1kgR^Nq$vzwY^_!SBD'
    'rXG3gn5#Q({ek@bRApRvo&)|27S5&(H+MGLc@w0WMjfbxho<C<&Ljsp=S?0ZKV>@=K#^Im9o'
    'XAyPkH&5;3p@tfP1yUHCZz8UIuLIp(2%Bbc@TwdXYPo9`?os?ji;v#H^x8eNeh(bJWDV)TA#'
    'LSG#L*-D9`h?gZh~L&vvNg8J0$DVK?9hy@8%s9<26O)>~XOhpa@+rN2qvgW+WWs-HR98^8!s'
    'LU-4LuZZL;uU(LJA(lq+N4|RDKwnSa=jmWb$k_W<){8Fd{Oe0H)_g@KHI9zSNCI^uVJW7o{j'
    '9?V2rX|%f+p#<p4?v&pJuSD2NZJK~Q50)@?qnyHL+uq-0srn%sEZ4J`>kyh<s2q0n&`q-oTD'
    'KMV;vhgS0Zo&XL`FE<FYLL?@aE-0q?>jl6K^v;~NW&;0oA;ytP@mSs|AUk#U*bI>|ULuy0F~'
    '#`ur2zY(S7oIOwh2?+mb1Ctb=zX$mYs8G8}V(9dE%;VS?*&P%w+sAF8onG9wE#y7a^r)Qvc{'
    'omzmq0n#l?iMlZJ$orJ}K>>`(gw~v1@c;Xl!S++M#onAw8TG3enkm#=LIgR{i;c_o`=;i~ya'
    'fFSu$L!tU^}D53jRUC-Jk8jWUBky3BHV9lb38}g5h)B@{mSw>&|C6a_w^47@G(!grGri~f&7'
    'qN38YBXoo@ct5d~zERseexm;6?*)Xq9;MPNanMUmr6fs-C#quC9BULK0*(xzj8dmp~d2lf6^'
    '9dEi%5rH(6z1)+1m)AM%t`@AA2s)#FAUX$blh?DH>l$%vdkUy}1@r1{b?145-(fRY@4juEf`'
    'eX6G%02?52yTF(Jbz&pV1recJ?{-0)>-tKa|9MN3)ZR7x6gw^$ow-Z&CcxP8|I%`+NDsv8FK'
    '(pjte5sx!siA};LOv9+Ejr1kG|>%dX;L9LD(aZF%Iyd6EIccSGWLQ#OaxQ1%Fwm?VIDj8ahh'
    'N+G93LR^$=W*meGGk($nuO6sSm`TAi%Du4O`@2<sBolqbV0_#kKIWt99~BcknMu9qFFrklPT'
    '}8-AD%_&&j0C9`qKUrhMw-6~R0YS26N&AtDvzFlXNhG4V1YLje46=B&KosHk9`B-4_{BrS{7'
    'uhNNbj3RIi=4QA*Ke$}zeg0nOFl#Sng=Np091b(-o+Fcu)Ri+4O4Aoh=cy2wy-kpIxZaSQxy'
    '3e4Vsm&em9yF;p9760i-gg}NJm7a1l~m{uSG{1Aq<qT>;NpsEP!IeIaf7mV-+-kI)*Mb5lYb'
    'xp0zz)i8mIvEt#z#@0?c+Y7)FI<f*J==leeMAa%#2mz(qWsH@~5x5hGRY8;cuTIMfbm`sI=A'
    '4={Rp7Mv564k!)?QYM~;J?bwPO*t!C3qxjI(+?4E{&`UEE40GG}TuL$rTL_fi0aq@CBF*0D#'
    '24HPaFD$QR(}){lg%Fm=#lUzqyCryQc4NNPLVOZYLodh~7(FvOB_6PgU?oa~o+_Y7VRP(Ag3'
    'QAYNND)P*fSdp&jB)cN1*rGQL`~ZOKzTjj5aTsI9D^y=>tiv>3<C&;ipbp3sv;$%`%4|@4Ww'
    'llcNzkHSMPpZ|#>oFkg0~sbfhAM}?(pslJHi~iIIcsgF#&xrP3ye*$`twJ##!72lC|*l3`7$'
    '0HT)385LQbasz&9Jlx%Ls&*k?;5{KVP$uNVdPS;U8J!ZnH>qJ1uS2#uSt`{Xq7{bxQmUC(+#'
    'u$Ma{K@UhzNT#}=k1lzEUNBLWZt?&bIK~JD`6^TCLZueOqb$?;m;uyRDJd~`<6Gvo#aQ0J7*'
    'G44(8U{mBsdqIqFs?XAN(e>FOnA{6rLvq)tC^@n_!qa&hH|>_cXn7RX=AD4=J&hn${xF(-0;'
    'bbSF91WSn>jadpObhi~!V=DoOLc%^0U%?R)Ym4-Ghbxl|%+?48_2ueTzEnNgrZ`%YAZ3HkPP'
    'hhqj^d6le(yA{&#wNZ1ZJ>%#*Um218!frL8eF!ub8=uT8!7-&b!v9qfALn$go4fVy&UKEBh;'
    ';vr_z!6w;tPjFNLu7rThzcA~rj{JFVy1wYssc`)1g&r}960k)Ed{>)oECDMd|FeswcNkY&g?'
    'kyyz0zp=G9;-N})CKe+5O^5_EwX<h-pFl7w7P$nLnR(~vD4#G>9!qMy|)lZPOo{7QleX99w*'
    '6giKMe=n-#9EF}vdn_gI#PQ?$(cr{{3q{N|L>2GG!ERjlA{b6iv~q4tZZZ?koNFfdRCy{LPQ'
    '>jTPzMg*7^==hT`ycldkyu)8F|0N}Y;s1sy`$_5hj<Az9JCzF2h`5iwm2^?>J|+4~lqSvw2d'
    'fdt1^qU>d0}a`Xl5<A+Vmt_@|NgC%1i*{2PU-aSfZ-o*v`63!M#_<#|d3{4}cx+dmiH2v{UQ'
    '{UWcP!Dd>+=wn;DY#d=if0o;%gHQ*j+{MG9R<r7<uC!)%Zi6TeO-k-bb=E4=~cuaFC=5Dull'
    'Uy)$kNvma_RE^#h4|bvlwaJz**79a5)%Zg*@T<<3CC=J`bYEth{pCITDVt8dAmvEi)_pqxlI'
    '@`&DwolHF%_?C!VRn&6!JlDSHsm&D=6Pv1VDR=u!+nEJx5bxQy@YM?d1fb!@3i{#xVeSUv|0'
    'jbnO?aZ0C56h%J-+S&Z^OJ<6aAl9omJ~CImtDmJk$H5l+e)E{5gdT9tY1Aun=0{NTk*nyi1>'
    '>G_F)VlO+1SU8N`y{41rfd4yvHP~xHjmVY6zbbB-Rs{n|yPQrPAA_h9wL`sH%1g8e-my<Fa*'
    'Afy({JANS#RC*Y3@rnk@qV#*h7V*g8wyZiN@q0>2t^AVItn^yJAU|^m98GD>z;h=Wf^EHgy9'
    '@e(WGOXt<D{@yDgaFQL7j2k@O9zv(>`mPuc;ZmR!%-Pa=4VorD{8(b7Mbv#(!ut-?>R0<J}0'
    '~&^y4nqC!^9@25>L1KwkhYdu9r<A5B<yk_V--9orTV^WJ3iJu>-hv!P+RCpO;h05q%%XE@ob'
    '3f0&st+DVFoqdaO2z*5~2O|`EV_OVImFoh7gQ@Lg8sCp<uA*MGo>eX0hVwUjlN`W2eC-nIj#'
    'Y{A7sxjfK1%#~mL(<(aFAjLN%r;czR&!bD_uvonS8pC9QdbA>m~%mkl{fUvH0)!PQfa8d-P$'
    'DIg!TQVO8c(#>0sI{yzi*lVbM2xt`CfX4jklLAwl7aVtDnRtn3Dg4F9=+tmUXIHF;J3@K(24'
    '@*pFAgtjlVutvq$0U?erijn(*No^6t!teDY?oPP5WKqYPDPui%M!?W4H3S0uvXkW6IXOIpgb'
    'mGyYH~(Km?xMz1C`UH#Pr_A&^tiC@K;YjDqMqwAkhV@M<?KC<n6Q7CNRMlTUzlNjy(}nohjW'
    ')ja~l$H`kVhM4&W?69J-+8Av-)9=)&q_UcRnNE^~a?C#+7bvO80l#cgWa|qzmkBK!&F-MHrs'
    '8h4yn?9~kYQ2Vr(wj9si9r|%AcyKzVug^+{{E<)LZfZIs3nXBcH!L`UkD<`R-h-tbLzvfvnZ'
    'i8a;?@MWZU#HkxsZ8&o^b6(ieU^x)O6|IOD(9)?S`(p8d&E)dMHOKcL7i9|qa?LLxWT<5Gs5'
    'za1I0rj|xVqfU34lcMOX8Z;;nX9JeSPS^|Xiq=MX}{`9&z?Ud{3?ZujC)SB>5>w>Kn&#an!='
    'ap>iDM_P~l!Zx;<KCm<j)f=mhhon_OLI_6M=I3_<ze)EzI#I&eA(^S<xFluGQ^`Xc`AtOj1M'
    'fOVKC*u`Y*>C$_?uam$pwuE!6W+QQLr|V=vaulMQxmzF2PLRjJTETg^B)WQPDNUSM((}I>_%'
    '(w=47>e!7caT0R$i-u6#VKzJ!I6-)j=0>m@JP$bd_iQITV9Q063f;fJ)SW%#H+@@N8HmbyHo'
    'x^J~|nig81J_7S3@_;q5tre5O+uV4!9et@cFTD(OdWlA?RL@+pJ$FQdFQo8TlO*82*t6iY=t'
    '&}Yu)uVd#hbXsWj&yPBMy>8)!(EsFP$*OQ?)OWAxPWJ&v9-I37GF)T6CK<2Go%f!Z|=`zhM?'
    'D&&T5&U{<vt1f}=;uj$-RT%g%|xucAW;d?gHTj&_%%tnKco>!+k=(F(o=CDPCcv<m#>tJfMs'
    'b&pJI{HTDuZ*@FqSt+%ue;c(j#AQImS|7GC4u2UANntI>a)?e89Vvn)LQOMMTX^fCl%B16hK'
    '7rw-$MQFQ$;eg$mO7cGIt@ch-rpVPc?n-Y<t-LJVLB?3fDoN#VSPOouB{cg)Z-0Ua1Q8D`iq'
    '6p#TbgG$UVVjUO9EsYU_CNKNf~kd0IEjWNczlxSRD;)?F~g;CEob(Ek(-EMYF2)S8HfHqSj;'
    '*;RnRBup?kb9JgLUjgQ-peCkK8Vw8TM%M<5&t-4m1lUeRt5(W{XOWAC##m4g{E&?XW!<XUyT'
    ')(CUyQ^1A+(I#O%EX=EXfd3I9n<8yTtnM;2LkZ5$caBBf@SYL1{Qjm5ABRq@EM$1FMw;iV4p'
    'G-#2`zE<?dN8<vJoVrjDTP9#agczYuaqvR3W$8|fcgQa<nb7F;@tGYWV9^=(VG=<(f->bW!t'
    'RNK!q^!N=*$CYn=-6x1u)^Qt#TUENUOox!hwuZx;q7=$z0t68$j?{4}tuWDq;&!gcnrf^-~C'
    'U640c~vt$+&_Ysp_-)Z1ErPKdK#_P8k)`(Q#WAzQF!>Aa_Zwv^bi^=a~;rW=WJxkT>$iv~gk'
    'LM%CEmo*iu-|Sis}E(2U)@OQADC~~o!Z1}ysn#>tbx3nrj-AtG%*2$sd_kNim_e;;Nn<oaW4'
    '0p6cU6B;{X{2Vh*HIOL#DO2dl`Q?TWIZ|6|4cuG7Y=-=z}UB&XYG9tJxZ&}Bp;F+O<oKv@7C'
    'IMo;!q2^8n>|h2D%Y4s;n~obHJv4wS&B^6>Vn;u=xG4!lyR;oh6xS8ET5Uqi)o?6X64^w4RV'
    'V;vOjh1}irrP;6SlGuF3m>-Niv(;IO!x*TG}w8_^T~LOL^Xp4~!Hj8wiBWXHus%rxh>aarLD'
    'mQC(gxuvJEEh*J9F4WY!2l05%HHv|TZ6xMApW=Wt-*+dLZxGC;a_ij!&HKA%7><YOXpBiV?o'
    '8}ZExgFv6yVk`%5asV}%3C@TZ`&M;(o0$X`^`YkuO~}CoHK2kZF}h=Zw#^5T?BZXY9(6_`>Q'
    'nQo_j)}5^6#L%AYKDFjyrYrS#rq=Ly2hd5s4V41@LUku6io&!uvpsSe-XD@^G8=IkLla1rDF'
    '*83F14w8|=Vc~mn4qHraHc{lpRY-;wn8^M3emSeJ7*vyFvv~?ef6df;@1JNabcKk>WI~Et2W'
    '4YGe)aXLBpTZprY|>nqP+8P0Ki#nQ|_S8ZEb4<rvRrgEn{}sswAO5(&$@#HD-O0=GKNUt;s;'
    '87XPyxs1%92?ZEhp8P1L4FR>1tkJfJ}&Mep9C3D>8<G~w{#zZHsu``gv*dA#3_^C9k(%ZLa>'
    'Dk_fg=dSe&J}TNu$J5subUPbsH`V_8{`a>`LQ&d)ve(&s{&=D7saxJWHsfB1SR4^0bITOAZm'
    '3Z$JBuml?7LC!ZW{4CXOKj-2?HEpBlfK*;qsG!)ip(ds>#JoGTjBMubVUp4YlQX*LT#{?gwu'
    '8tJnO`MEEeC@dcKXfG`RT<Bl6lam5`4*2n^wcDsq+!-eH_F42U%VUDoR^NR|)p-&OfRZR|M3'
    '2|A!v<DUeRQ^}AC^rKHx!BK(Oi;~<1(JhzC)io07*3Ti5}1(A{{8i&YH@I(3|%pjn-ADXR}H'
    'v98z%Lu5lvjL1)JPP`yentquJ_nAjzZ*TD<hSh=L-En8B^u9pDz@~z!C`_~h~2~m~ak0b&W7'
    '4&tk_5lrOk8pbKaz{#Y#!accP?}QuRYFJc6&Lpgug|du5#ub*WWA=I@g%F}v>E}$^A7kQ<4('
    '5AD;cC8UCa5qJts|V5yV3!wtG9MW20+A5_E`3RP8Gg5b(|>>a%SI;K38|G&u#LmWVu<*p#E?'
    '1<Jy6F+C>+V>pQ@n|!!+fjZsUXlQ7_mm|4<E9<1qYZS(-mx{=MwtpOqTNpCK0VW>Iu0@S}qU'
    '(;GLK<V8G{A@|&0ty!dPvBpnsD?;BHmFyz+j&x0{AJ$B}{*I*}Ws5`~lDox&j8=+Gm$nFio%'
    'l=QV&Xg_KL7Tc9c1xQC%xg&^v9WSMO>d!4TZp!X<^*<K6;seoKgu?HL_-0X_%H5+&6?STy+C'
    '2mo5Vkjcc-RuzX7`7~9(fi{%&I!|Fm6Jzbs~1O`=ZS6u##SJ4cfZhx^w6vtla6;Q5Tb~wVwe'
    'HGM_|c>t2_@VF<Ek1PG4!*=7UFJZBz~$aa>TR<jeYo*~33DkBk^o`VuX=?tkE2srNQ82)G|B'
    ';(!i7V4;<!@KG!R?HUdF=ur&dJ#~f3O;vkxgKjsPW$FSFaBtrxE->h05i;;P88slSX!5k**z'
    'BY`uCUgzZs)+tlSUKl($D`lHNE6|(>fh$e?QLks^kI&Tl(l-qtS#MvHo8`hwA&D1)D0k?ky6'
    'JY+13Sbf)?`&FpAfE>)X;vy6H>nk^vmSd2E(LA5XJ>@?Vhzh5%}`Dh;?V8W!p2wBOIF}?$Ot'
    'B8?wQ%{TJhQT{2Z5V>;V$m_e^0K&78XD7oKEm&=3A7bd3NoVC^=dOG+$nadHAT}EncWWuckr'
    'g|(f+Q1W9QOs%#8!4(5gltp(9384)vA;_IYh$O!T$p<RKwP&n$-ETeDYW*MnS`oP<_ryj26z'
    '^9)qV7O6i9BbwxzM04tDvbKo$DbY)Pwn{RlI4nL8q94*z{pn-h3>BZ$w$%r22rHlEdcjBT3^'
    'rBo2HmO2jJMsC@?ai<gPPJ~(*$z(a2A6~;I36ZKu`y#<kawxo4%CboP{e`%xAEEJM3rgpTu~'
    'E-n0#<7a|-U;ijY6uAd8M#V*ZX0bwAO+6Gq2C!j|_&-MC;^yK9CPLWF^wG<rFYFe?{3E({Tp'
    'at&AfQ&QAUFUR<mSle-t43M+ojg9DQp)|G@&IItw|a;96pXSL`qg$aG=48yH@z8Du5bJwX8C'
    'Bfu}+x7);uq<Jb^>!T!<*lI`2E(gw!(Yo^t0TfBR|Ext5hw)JE<8mw(W}$CDHfN$2H&d!|ek'
    'XI(j&`y>pzjYJOHqevB`XDDZ^)Da!{y<hfa1_?GS<C;9ejCQ4<#*HggBK=To+k)Ap9yi1+>>'
    'jGvmQ^R>FD)u;u3@2rF$wkwm(&3}Y}g{;wa;mk6ASzD31k47>{7rAG`_4u36augU=q8>Y89`'
    '(^gE;D*Q#?Ut-!PGXC~ylGLY9#X`)48fj+b`(juJfx;{opf?QYCx2Q}o%TVe1msUurr)`En-'
    '%Yd%QS0z76|o%9U}hNKFlY2P(_^AN<*5E9z)Ihpnc#d9jiCXY0dwM&M*2hc2|RZYWGz16eBz'
    '*CXeo{OkmMPKfC=G1!5Z_@@mQ7T?tgK@(ivwaH5T)yMp0~ft&0h0AT2+6G9=Ku@+$!nn~HB$'
    'ZNFbB`JYg2?i;e$*M%ucr>M_w-ahdD-rI=NM)7k)KAwS1iSP~sbZOB&!f2>|_{0r;)*~T8qz'
    'dumH%H^<QxC;Z<q<YK>O;Q$Neg4YWhF&tlHLo$XgWCvLUKF@_uaKFznhyDd_1@PJ8BGltH0A'
    'V=CSUk1rD{_Jjj*~@5NO%QgQPO=d;IDvbsU2oj(DGH@hj@=g$RTFteuMXwG0u0`4>OqV;J+P'
    '}Q-4${KyefT&9_?2P~W<&$!2YmGut&{W7m7TWUjV>ATTL$s18C7F(?2^vUpN2Qv5G#pclk?G'
    'EkZuIh1{kb(8?3!#&a~%p8+ird<A@)lA`%+s%$w5B!B@(u!l5K;OBMfE?`QINOLF0r`6%)|O'
    'ZQf)d?+)Q*I;WCPIacvm?8&E^ukutNe0bz49%QEEy+70<k926N(u5n=PGXU9c!KLI^q-T#0='
    '9&U3g^|<<K8Dt+fuv8An2A;W7NpM&_m%4y__|>0XOnl);jf7%A52Mo}Uzmy&>7DqDhHc*mDu'
    'JY}j*N_u3C+vr%{Qk=0K)W6AYQp}H;S;cb{*Vt^3~ovvueY5B2!)qrn&usJ50UOw11>Qf{(>'
    '*4f&LM^A~B)-PRCWbdXlwIT%Qh^8YB2`aIxJ={|q4F#5-}V;r+&g%24C{G%mumX<gAqE6SZ~'
    '-mLK1m(^~17GzpASoMVXqfp5P*~atJYJT%-}W;JouB)+cUO={?q7so6;g-v9Tj%e0pFKYX1f'
    '!IY-ux;Ylv8|>h~wQt{`(KtiAF$=yLK+|D%(`L!{J`aD`iukbJZE$Ru6S{8Ipmi2eZZ<!;Lo'
    '9IlKu3zkO{(XPjQ0b%XHR-&?fcrx_)LqBGyb@~MM15~B$4UaBCOU0mH>E{df11tCWprt%!__'
    '3$`3ajU)%B_>CUhtdp+o(4TCpEPw*SZFxc^qO;G3+@GWLbrC=()q&I`LN6dNsTxaUd9O(PCS'
    'Y<?2d&SRtv$ZRco==q9Ke)OO0(TCsG-wyHY7PjvWDC1wDFq3QWm!SBYZF3+EYF=K_BJK(#>3'
    'f}!cU{BQK%4%x}AgnzR=Zmh<ZCcT1efs*x85UwL8m;|0_mRsd=;80zRF&#rH&U@&UamMa`@L'
    'DiH9^h3d<ljGhh(|53gH3$jMP|8kk<b5G1;jvkRF0p}VEp;>OaQvQSkK@~Pf+evFQpzDD@RK'
    '-NGBAMNR^tk^l_5**Y5{x5Rv6^lTK*1dxC=#U6lVaaQU3A7|&^!rC00-*k;|s&j_ZdN<q$^>'
    'Ig*G28<3&&vd=tcMT}_@C93ZFQ{#qlOV*@k{|2<9wcMxFJH#YNW{(k|(Zwv(~(NrgEL74@!T'
    'ft{TWYEL9D9rDz6te(Uj_{C4Or@ET{qzQ*VsvjFkikTo<S+||dJ%Br^ApyCKs=H{Z!<x$L92'
    '!Km~;HIIG1+a0TTmno~6(`*Yo-5GSV;7st~)#uCL+V;to5uI9HJ+e}za@U&4?{*y7CA=Jhe{'
    'fmbD3$7ue3l9vucY3R`g;eXlYy}`0$%c$Q+fPr+U;SLv>Sp>6gyK%EjG$oo_5|1P?M~q3*TA'
    'PD~?kE{2m?_@+lN<o1SEJ4_?mj&S7ri6*=O(BB3w;%;=S$p<%$IR@al`BmLSCWmFEMJxYDOu'
    'kY@;zKP-%V&kN^^URGJ|E(Se}M+;h6*_)2FI&;dv!%B(+<Y_k77TdlVoV+$5@sU*6}5>#E;H'
    'kd{G)X1rl!|V#_!YPC<MBXQT*u=8AYfYaj3q30;N?yD!LJUC0WT^9PV`IT#_y4T|ZM@CqgSr'
    '4e;1G2jrl|+rer#wUG1g4_v5n2-<T`Or%JaRQJ+GCZ;u4OpLO&?#7*AP2l!aR+RE}vZ8;4g@'
    '@*I<tbH;PvI7%!KX!=aCr{JfDNCW!=ZBjNO85%W?L}C(iyFw4Xu`L3Er0Y6=m+7vogMfWiBI'
    'oP1@){<VK}ZKHt&9GFHkyzjERk4-?x<TQ9~&5r0sQI>u9Mz1h!B4nQZA39&3#OAfAX92k}p1'
    'HIL{{J{)+VpKg@;t5(pCHHwc71Z>;R-#;grNGASLxfrt4<+4h4<mfge8EXPccBIs86b4&8F*'
    'IacjtCcgR5Flhs1dTX4E=HZesil|#X`mG^9Mv{`n}~|bxbW)oy<|Z<^pKAkhiso$f)YQLjR1'
    'Tf$`nSGVKUtUg1d7}RMT-Bgk(6L{1>u6y}6BVy*kbdy#x2VhZT4J{2G^S($>ffLZ~0sIJZ_K'
    '<dP8>IV(E>!4vg`XE+vfC4qma-M-8fQ~-+8BKjh#MP<vP(zUw_VBJUbFmU0w<q0cSC*vSP`P'
    '@b&N&jV2Myy6LaEgA7$M?SdxU?B^?Z<7QJN1WRf$Kvu!W_r64RCvl!a+7jvxf>wr8NQ*Mq{A'
    'Z5|q-H2t99L1%FxCUzAy&yY1u54IP_<8%gWnXYBStu{$Vi1h(81co8dQ($rsnf?muMxxTL0Z'
    'rujDzg7e!ndh}ULqSL-y&EpgG{(U&Cg3X*7zZY}ulf5Omh*i&vfdKncRk9UF#WWWp%lAO>Gk'
    'J(r-6n56$669y<@F>`ENnPpKL~z7v)ogNsh+lr}QOB6^{aAM?dV~I4B$H+S~1e+K%yxp#SHt'
    'GPZ*f^YJZ?g*egZ^_XrP=|PjtLI@Y1p?M|#e#Uk=ys<PUvT_I5zuM)e6AV{qHZ7615_9XQXC'
    'gCYyHHos-SUd!Ih*#RnpK_gCx<N7$WN&fT1Xa(kk6ioP`8UM`@#%wE;6U7;3B981DJctNO=-'
    'Pc_cc8k@IAo!a4n^LOkK%Fa+~&L#?6|gaB0-P<bs4eKVLoRp(Tj7@{F>H-@i?SMc1pTnw{(Q'
    'h~^9xY05afq5%-yBUHnu&#7XtG6P1y_O?&f)C;q)6g`FI3-k(k}#O65#dWckHpEi0jEXjD(M'
    'N+lBuUI%-!iN(ResIi3ea}hgJOVZ9-d)-Ky&*IXUm$5{6lfo%GD!KC<3tTZo$O0|SB=C_nms'
    'sHI>iwtb`%l)oz1ZKDeTOUTvK^@dy?_BG_VEh+y9-JL1VW2+Q^S{1f(^!>JcDzTht*Kw|Xrb'
    '&B~1i^Wm>*IiM2hNu|2J#l!nk0W`FU;mYCRiM0R@dQcQU^drP&b^}+#)9de%<7_+qBmy21MZ'
    '$_NJLVLI?c*bhuUs{VOD_AZA^<9M?J<#O*x8FI3&`I;qCFr)b6-6QmmT72=~X#kfpTl;K;s#'
    '?w%X;<KonhoK3zXrzR{F8F(#Q$Fr|j9^px-^bL9Zg2MrpU<U;m;?c7a736uZPr;OoVveLh*_'
    'afMB2#yJT(rWOVYF=qd9n@rk3pmzbxWbm))oLetBb;&P*tD6qIN9q*F-is%IV-C($5Y^t47V'
    'D;Hr6^fPaR7f}^$+u-<I$%KkfY8wAS&e1KE*J1HyQ^xpu*KWZFiDYd)STnlOq#07TX2#mH5*'
    'xtym@M<Y(DF$oC)?3F>|4`Xej)>EGSAId$MrkKTRO5(&z4^SICtU%KB#+#F{i{nr2*u5ZQqx'
    '#53CE5meeDaDG!*Ikdfb-jHXcRF+MyiPC%<qt*d9r(n+6Hg4bU`lMRGUEisUc>uReV<6W6eW'
    '&hU;%eBv<7}ceSnA+7(_#*RzlDSdT3RsS(^0&Aixg)c-?+us0cQ8OGj4#)eVpkGI&0L<A@O-'
    'mJoA4@?3wrTGv4!*=aLr%b+<YNc!S#ZF<I70Xh#92N6Dl=A37|3ihCSH9kLAtGM?9Ounqb&l'
    'B+iFo+Q3tCSk=%2m0KzGDtaHU>Wp{MO_wiazanBcv1bPEbu0Q(+hW4L3NFP?9$EeOtCLh#d#'
    'PSRYLeZ4ll?-e$TuLaU-Hu|!}TZnZ!lp?Mcw0ks-;fiLVn*6Uys$el=mOLg*@|&?-eG8O&U7'
    '+rtDJ(>-{&`BUvzUS+pot_I{TX1v*U`7l>Wsjdi|<a-^!3w<ufaOI>(lava}AwKBKVae;&~)'
    '~0AFX#yj;zJIx064Kgro#0=c^8iwcr9&Lh!8ajKjdU84!ZL@H4WTD-LghTndd9MVx}bCE6c>'
    '3!BG~HUG5m|GuuaAf^K`Hd6;>zY{WCY|@bdD&7c^QvTave2;t0V;?S!M`g*6wkx}<<R=kS`f'
    'l~Xp;^U*`3I4I^4&Yo)X<*f(Iu25b*{n8v}NUu~wDb6<%%Y&bc^Ut3hR(d`rlkpo_5Es5sUt'
    'u94M&n3d(^}nP0yROQ`@8do=3aD<OmRYRyKHR)UTH<|F-}%(g#NGzK<RX488;8$MH<abV?#p'
    '`--t9qFw)iun*kP1q<jeQ>o2ebFPJO;@#9m$YFjv3RZ(V6aEu^qn1Zr!waW@W6m?PQP7+aAl'
    'y<VkA|Kj##g*j)H}66@eCJ>=zDWuS9TX8%a-5O7HE-;EOY0H?9^_*ym5GV@rGt2WoYt)RvM7'
    'A>QpK`Rmx-~#4X^`!=j=+MDNnt<^WYoIuvI#L4?-+!%k<IOUl{?u{r0uUD`84WL2xu%1k6Pu'
    'fkK-DZj3kRu!{8ZzpD}E+!g`W(Y{tZL2)oC-UITR62`X$60la+N^CV0%Uj9MZfe>JAV|V`$A'
    '_Tl3gB@|XaSSygmyiz#tt&2s|2*J1(|nUq12dK!oHY3b2R_LN_0bSZ_619FHaiOl24?~AP#-'
    'ozroAcO(i0A;@n3citN2zjVYp@JbR{dnU&wLk9j%$qiYlqs}jUd@1P~$<Jta#<Eq@s=jX~Q!'
    'I7t4=otu7`d@E$beD?b0Q-OBuQ(Xj;o>Q<RI!%ur2?x_3+DEL*LV2W3eGkg()pd1Y)_-<1A4'
    '%2mKX<!d#hT1-voQsVnRkI>6ZGIqdQoan93uo+T@?*(m)FH^=jwm^$spA^$A?d32O)1Tn>l2'
    '2>q*raCV<95_ZWJo-WFHFVxnn>$Dm&E=A^_Wl<E2xs58bLTK~|^YKA~2yAylkXgs2Wqf{9bT'
    'z<+Gn_Cp+45oP<k>ZIW9oT(X$zcv>(t#D-Mo+^11~t~cUEX|&ap1RWj9HQ|1|)=8GL$5(kOp'
    'jp=(8+#1mN<K%@XUpxRleGGG;PBvPtX`Cr!;s`!teid>gz9?nuAB#X{P09?t<*R;$|$hBmQ$'
    ')PPb8jU%9_IKDck<H3!Tc9P*7O`-Tdwi=-GQV`Psl~gQlCWP+_hvhLca?B2@$G-;y!EN@_9>'
    'AgD~|w(u%h1AkV$V{`{h_l6XWV5HO8Fs*)0<hzqYeGVmC3nKI|~L(&&A4N~(DsJAOL51aLJ9'
    'XHvt_AZi!Inu47Ww4DiU=ky(OjW{k78=<9!&VyT3d(r_zEFLr$c7K_Zo{%xCcvG#!Tqc~<X!'
    'G=ifYV%``>SqnF^RC<1Cav%KiEtA&oVdZ=jdO=rdl`LAp}Bxv!C$%hx=|D#ORIIMD7O+79@='
    'kyawYcKH<)F8It!D$6?BKtE<`(lRafk>!VONZ}Du4Tk|~(lQ~cv1=<iW=f5;fTw#V%W7-W!d'
    'ZyM4bDA&)O}9<gYiWC*B1^d>uKYu|bAl$!a`?(NWYPJmx(N~XGq>7R?KOEhwbCQ^jq2zZu`h'
    'PCjxh-5#=l=!m}}~Nlq8jn<j+a(q-XJS?~>Cit}I%x`gogtX5u?~4_jaHOG|PM+-addfkt;z'
    '>Ra4L2s9M{I#V#de~WXi*kG~kv-)K<b1fzPW=ZwT{oSz_8<>U!jJ2>kb=4oN1}n81-6ihL6p'
    'Ny6E^?Xc6i2V)6C5P%%<zUxD2?;`<+#n=d~fzyLK~dLT*v^LHD1n9OR?$di<<^6_|xdDjMgq'
    'Bmvo{G-r}(MwYvH$xP0nM>@HZ%_yl~>j>b6z_enYd`99Yz%{f=(<UfnNL-D8=VdMUK+~((p9'
    '!6_S&g{5?&WPyw%oO9XugbobaO|`!d0*Kwbr?!JZu_fIfZ7pGC;(f85kmsmk~u2%v^ayqL`h'
    'W6ycm8Kgz>p6?r@buiyLozf{_<z!85lZwrxvem~So`jkay*gt9`^bml0i&f4ou8p1yhXm&%B'
    'kGdRG5DSH{zodG#_nfDrJkLsU@?a>X)P%C1Ww*XKI%1no5X{2(zQw00ZY_yu<|6^*T-jFaa~'
    '-P$`{}jq<y^E-Kz`_V)PxNqO^g0eX3@D-5=j|g<zDaIx*ML%{?;I0Kq;Z)llhfAt<lpvj)A!'
    '_Ee~*yB$h9RpkgGxm``h_oz_tHMS{1eUn*@8{X);4c^y4#`t{R~5q8Tl)iJHHJB3w1?CO6vq'
    '7<`v_-g5@+zaKmIOm49X1a_myP*}xdycEm25%WobNgkmjzeXr5axo5n4LTDlhtpuN(eYVq^q'
    '99nt3)~18}b8)I#O%deolDWe%tv4esdLcD~at@SqeVV$*`2jGG3+uI*Yd7Yx5@y{KFn5UGsp'
    'Ak}OL3G5Pm2KJ&C^yj1~PIMdj2;AEfha5iAo4h7?d(9~XNF)zQzvW?sLDA33X^y?cFDXov+7'
    'nW#xY+4gU@MwlG*+Y=xKQUqQD%cI_q)|`X7Osal*0v-gMql_D;XbR#QSzV?o*W?%dl@jIHRf'
    ';BN@<seFl^tdQ#%nn|-nNgDx&I#V7yS+s+?SF9o=>^w-8d(@<dKmH0gswE54d<ZL=S5i;nV_'
    'pV*as`8U>Y}ve2z_4ybrPH3bY+a{l4S)_OkRl5EriHQqbqu2Eo3XTe`a;8ncB-RTjk?06hZ0'
    '0Zch(ZYieLP7LvWl&g6%{5pjk3F%OJewqn@yG^%vWTC-&3f(2u0LT=3&!&zq_SI7Zd8<dJ=x'
    '!PB9(P~#v9&In1J#7}lqpIB(@axsJZ`K#OjnVcq`t{}9HzUIk9V8frVV_+=uRZa5ElPUaPf#'
    'OZLE}u?g)?NPUYc_NE!t<6YTORImet7iqmIbj>e_4#T7||O=2r$px67#l}($k-)mDWNakgVs'
    'AJ*Av)ito@PGD71SwR$|AMo7PXW4Ex~x!E5c{&$2Dl#oq@04ycn5>oj<BcZVgF5@akx>ml&W'
    'guCEuaizrk6-8$Otc*?Wz;9Wf^Z3qt*+DN_^-~x9Yq*8zV}JCcPa{eSZMp7Qi(sosC@a20fz'
    'JwIK>Mq_1U=1z<T@8V4oW&%1qEt+jgh4;c5D7gqGvY@Vx)W4DAvvwy$R(hfyut{!w6q9*2U!'
    'B)n!9*W?eC3>BsBC&uhcC1~_^BC-!N2tX(9W{rLShl$qX{C}>Yq=N1!hkTcyei&4I^OY%{kE'
    'v?+`gW#AN(bSJOnPjH%B1@6FC2(mhuKV*y3`Ng3`=X|-*r)ca$QlC&G5JFY!H+&%fhy6((o{'
    'o`O}3;4F!!~qj$UkfPYRNeB^>*ymWPM&vo?RL&n?I*~S-`Qa2gTk^a<vt+9WoJ1hPX#*JACl'
    'SUz8icx-OumVrzb(XDGe!{7~-8qTS!@q>t!#BgJL32%~WS(c}#db1<J<G(J&CU?5^60b)I~b'
    '%()PlcApc-?^p<F$A*Vpw=oNJK1B8Idb*!uh22{BxX=@2N#WtefyepZ<g28$pw4XF-Q8G7y@'
    '_7lwAD&Or2O--^olNd#EXUGHq+|S>|qEm4%)|$T(a-#o?=FyBg0H!lxrTxIV$j8*dVNi<r3D'
    '9V$RvE!e)f*4emqJg(|3zx8pFXRHWmGOsTK|V=wj=#O*w-F8y_LzB-wkRaY@(ofpQy$ggk|6'
    '`r%?jl7(s2$ip8B{kY2}rIjoh2X|>IM6QVir$5(h$-w%Zvi&F~dld;?YHw(&{hMLgW6JxdF*'
    'aUtI+2)A&h^~S5$pSHu{VV3~m>GPSM|0!<{~oQbs1^4D<ew-wXd#N|$#Cnr4!F%PbYMeOZc5'
    'J_;)XM&>0)a=pqi*<sS5PyvDtS1OwHXYih<KWF#7|UNXej42WtGQDYJy)+bqYm59RhPecwS!'
    'xO-Oh>}=xuEG@p0RF0*`Btb)nqZA-?(I!GgAJszWyZ%@l<}@t^hlpEx2aVDuU$XC}9;dDM0r'
    'q^YA&D&AM1Oy{F*W0}sL_+CN6D?V!O{i=5UJH^@Az=9veAG%?w#;@;H|GKKzOrmGRF)z4qvi'
    'T)F+>WY200ef$aAZ@jVo<R}3c-?4lG7)qNyYAFiP6v$s$zW><Y3TG7%Xgj@v}P4zAqB>=v*`'
    'l7k7a%fKlr=LKn{Shx+BKNWX%0`8Tq_}B}ZuM#q-Z)M7%6{OO1ZIO#BjEC)3fdBebUTk+Knh'
    'IRYD)dW`<_kYtb*Km2NkM6v_!IQmp_;)L&+Ie4Nxa<oQ5`xWud+C$XJM0#I_cAoo<oeve|l^'
    'afGY(&&=`SmYzBs%w&GgDaRObEVP%>p;EODTUXpIh1!st0=ab(?QIh|iY#v=Mbwixxq5Qs=R'
    '5Sckk<n(eKzm-!9nK#S^Ej1AR+b%yr8-O^ccb_82<wShw87FkKoQ6R>7)v3m}1Y!mjbwoX|@'
    '}Wj9NUWiZ)Ep}Sa#5$hN)APg2BsPEoa)wZp>l5K!#DC?iOJ>RW?0y_q>B~S_^n%LowT8>;$q'
    'PXWGfFYTbX4vq|OLx%MaUy{sOCjLR?HqY1_Zxh)y9l7gjOLR(#ak-?S=Isn+ghMV1PpS)jLl'
    'HcixJohqUs}_7SBy2x+$fP$IXSZ&X8hTVkX-S3C-Y@+&R2wPkD44$xGrMWD2{m#l!dPy9K6|'
    '7@4FT5nxca;q1^fV`h{x%u;H2gB<H7mU{pHRq&Gq0RKg&7)70rZtL`Lnaqy_c!_3@S83MJ8V'
    '0<9;fhNo6MK^`IY*l+{SIq&ZC>Czvq#mfoyD%^(c-dJLgrT%N(}*DktQndPLvokuVr(@MfYt'
    'X>qiMrK4kDjcs`~#sa&0te9{qsfEfzt9EQe{T{}ibGD$xRfV%yYM99XV-jkbthJ?j7>k|Vq2'
    '(c)*_yq}^b~)IT5d22^{^Pal=8Pq4Q0?g?wp$PQ>-hu>>0^1>MZrn8*>QTYA>F0RiRqsvSs?'
    'Ki<e?5p+*`ivX(%(6i#dpDmZDlcCsA-!?I_YuOsI)+5PK7BwiHWruK@iY-_<vK89-(%!6CkM'
    'bikuWVU7*5s93^Is~m^n+Y-k58%QFw_7U)Ucpp&^oLl0NVZTn0Yu0reXMd^7%nd}=-d$_nbj'
    'XsV&4LSQf;n^axn_n}aKF2MX6TShDDAT0Z+JR0<tV0WRX~3R`)Rm$zo`=8PzbVi@T|4BYs9>'
    '*YoLMH(d4_|`&I_K^L$YA$sY2#C;py<5X63gO)@xWtSv0usT4OjtjXGQkEU2)3BpxlLllD4m'
    'G2l)N?8RCw38Yd)M)xe4-;(LY8ES%JI>zC1V*)-qhxoyt^_g;!o5lhq9VSR`A$#CGG8)rs1%'
    'Sb$crN<lE1YC-gTC!{&His{G#cEC-Pc2+J_kP69Cmeoh+IYw;f2w{Ey(i2%QK65FB!N_=Ov9'
    '?S>+@8v2iwZqiwG<>g_)z33SuYX$QG*-)(OBzj?maH9gBfM><RfN|AMA`1A}c)PD;>LaK*$s'
    '5if@^DMk_qZou)ri1fycC=rCZfuu<wjF~W%0>&nM6qkjy?a~yF^LmD;JQM>wj|77z=`fAyLX'
    '#kvh){0A0B<J~ceSnr*|I5+$|B5D#LWYp5v6t*BG86^AY2i-E@jjd>EC<kI(wzPjYJG~4%j9'
    'dGBUjOhgyro4YEZX^jwExSq#>8$>(zh0#FRkw653$x;d7n6EztrV(_a2^X$2lB)R2V-^1LzZ'
    '|hTlL1b2-scj#R=LKj7{0SBnc7~J>Nh^lj5?09aPT0>U!$uEx<JE62%H55<}CK%fVQFqTnZb'
    'i_MM!dRC(pjDDGZ@{)}eP;BTdL>K~ARNO1%fiTRA4TJ4~%a!qdZV&;-Cj58_J!BEsOjYpf#~'
    'i2$dr+2P@eFvOnmi|uRMb-cg|emQN41+OY2-o(q{1p3g2&LIq<)Be(?50WEb{u=wvzdcI54p'
    'CT_5#zMI^N#b})xg6SFs-3o#jvU7_L-H;rrAhCZ{1$EKRrTNT)br)Yk7IOH8V^AF}HK<yEkQ'
    'ezE6jZJygB=5aDk-hE)Sd^(mn1)`+;C&p#9nKgb1p8ESmgrfXN79nZ#Xw+A`mHJ-79iHW^*K'
    '(1{Cs@dNy!^jPTXE_DObVOo`|2jf>N+}Q0Ym^IAUy0pkVygF-}#GTwWewZBfX${@yIm5ns&{'
    '8P?X5HWd}Q$QAj%DoK;OEYcuvQ}nNw#mm-`X4%^(M)@h`p3o+*?H6Z#REyTmOav|AyG5UgYb'
    '!YsYR;B?xA12BvQ8sXwa+3C+BG-AgTY!KU(0p>uzX3&GZl#>9PQokFd&%#Zdj}QH(Ks1g^;-'
    's+N(g+$Y$?m%njYulEwFcKl7W!IEFPUjo8+0q$8+5jcS{muL7;Z-BhXUAQzzlNU=%!VZuI%u'
    '!c<-Yg9nRWt0e_pNb!HBsgh;c%!F?Tno};0}(GvvmYSGy8e2RZlU5J&0;6SPNEUhk2G9LrO;'
    'A|3!tKw`p+BJY7>Nsmmz5OSF}2$z0JTU9emR>+LjWKc7|Aya2mlj)P5VA)>-{9(tWIW00000'
    '^vk>ZNh_~G00Ehh0`%?|Wc<)`vBYQl0ssI200dcD')


if __name__ == '__main__':
    if '--pack' in sys.argv:
        text = pack(trimesh.load(sys.argv[sys.argv.index('--pack') + 1]))
        for i in range(0, len(text), 72):
            print("    '" + text[i:i + 72] + "'")
        sys.exit(0)
    sys.exit(main())
