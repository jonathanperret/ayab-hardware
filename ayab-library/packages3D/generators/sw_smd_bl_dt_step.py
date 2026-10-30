"""sw_smd_bl_dt_step.py OUT.step  -- SHOU HAN BL-DT thumb wheel switch (LCSC C53223909) as a coloured STEP,
built with CadQuery from the manufacturer's drawing and LCSC's photos (toothed ring lever over a stainless cover plate) (datasheet rev B00, 2020-05-28): 14.20 wheel diameter,
12.34 overall length, 11.90 base width, 2.50 overall height, 1.65 wheel thickness, 2.16 handle tab,
pegs dia 1.05 at 5.00 pitch, terminals 2.50 pitch / 10.80 span.
Frame: KiCad footprint SW-SMD_BL-DT (origin between the pegs' row and the body), x right, y = -footprint y
(the wheel protrudes towards +y), z up from the PCB top.   pip install cadquery"""
import sys, cadquery as cq

DARK, LEVER, METAL = (26, 26, 26), (40, 40, 40), (200, 200, 205)
# Vertical layout (z, from the PCB): the body stands on its 0.25 terminals (front elevation: the feet hang
# below the 2.50 body), housing 0.25..2.50, cover plate 2.50..2.65 with the pressed chevron 0.10 proud, lever
# ring 0.92..2.57 (1.65 thick; the elevation shows its ends 0.67..2.07 above the body's underside), the
# lever's arm and wings on the plate.
FEET = 0.25
H, LEVER_Z, HOUSING_Z, PLATE_Z0, PLATE_T = FEET + 2.50, FEET + 0.67, FEET + 2.25, FEET + 2.25, 0.15
# Plan (model x right, y towards the wheel; footprint origin): the 14.20 teeth circle is centred 0.28 above the
# A terminals' line (its top is 6.65 above the A pads' top edge), the lever's inner edge is a circle centred
# lower (the lever is 1.75 wide at the top, narrow at its ends), the ring ends are cut at y 4.0.
CX, CY, R_OUT = 0.0, 2.60, 7.10
IN_CY, IN_R = 0.60, 7.35
Y_END, Y_BOT, Y_TAB = 4.0, -2.30, 10.04     # ring ends, base edge (12.34 overall to the tab top), tab top
TEETH, TOOTH = 50, 0.25
R_HOUSING, Y_SHOULDER, W_BASE = 5.30, 3.40, 11.90
import math

def half_disc(r, h, cy):
    return (cq.Workplane('XY').circle(r).extrude(h)
            .intersect(cq.Workplane('XY').box(2 * r + 1, r + 1, h, centered=(True, False, False)))).translate((CX, cy, 0))

def body():
    """A: nylon base, 11.90 wide up to the shoulders, then the half disc inside the lever ring."""
    base = cq.Workplane('XY').box(W_BASE, Y_SHOULDER - Y_BOT, HOUSING_Z - FEET, centered=(True, False, False)).translate((0, Y_BOT, 0))
    housing = base.union(half_disc(R_HOUSING, HOUSING_Z - FEET, CY)).translate((0, 0, FEET))
    pegs = cq.Workplane('XY').pushPoints([(-2.5, 1.32), (2.5, 1.32)]).circle(0.5).extrude(-0.8).translate((0, 0, FEET))
    return housing.union(pegs)

def cover():
    """E: stainless cover: a rectangle over the base and a flat arc (r 8.2 about y -2.1) reaching y 6.1 at the
    centre, with the pressed V in the middle."""
    rect = cq.Workplane('XY').box(11.10, 4.5 - Y_BOT, PLATE_T, centered=(True, False, False)).translate((0, Y_BOT, 0))
    arc = (cq.Workplane('XY').circle(8.2).extrude(PLATE_T).translate((0, -2.1, 0))
           .intersect(cq.Workplane('XY').box(11.10, 2.0, PLATE_T, centered=(True, False, False)).translate((0, 4.3, 0))))
    c = rect.union(arc)
    rib = (cq.Workplane('XY').polyline([(-3.3, 4.1), (0, 5.75), (3.3, 4.1), (3.3, 4.6), (0, 6.25), (-3.3, 4.6)]).close()
           .extrude(0.10).translate((0, 0, PLATE_T)))
    return c.union(rib).translate((0, 0, PLATE_Z0))

def lever():
    """F: toothed ring (outer r 7.10 about y 2.6, inner edge r 7.35 about y 0.6, ends cut at y 4.0), the 2.16
    tab at the top, and on the plate the arm block and the two wings down to the ring's ends."""
    t = 1.65
    ring = (cq.Workplane('XY').circle(R_OUT).extrude(t).translate((CX, CY, 0))
            .cut(cq.Workplane('XY').circle(IN_R).extrude(t).translate((CX, IN_CY, 0)))
            .intersect(cq.Workplane('XY').box(2 * R_OUT + 1, R_OUT + 3, t, centered=(True, False, False)).translate((0, Y_END, 0))))
    pts = [(CX + R_OUT * math.cos(a), CY + R_OUT * math.sin(a)) for a in [2 * math.pi * i / TEETH for i in range(TEETH)] if CY + R_OUT * math.sin(a) > Y_END + 0.3]
    ring = ring.cut(cq.Workplane('XY').pushPoints(pts).circle(TOOTH).extrude(t))
    tab = cq.Workplane('XY').box(2.16, Y_TAB - (CY + R_OUT) + 0.4, t, centered=(True, False, False)).translate((CX, CY + R_OUT - 0.4, 0))
    top_z = PLATE_Z0 + PLATE_T; ht = 0.10
    arm = cq.Workplane('XY').polyline([(-1.95, 8.2), (1.95, 8.2), (1.65, 6.8), (-1.65, 6.8)]).close().extrude(ht).translate((0, 0, top_z - LEVER_Z))
    wings = [cq.Workplane('XY').polyline([(sx * 1.9, 8.3), (sx * 5.8, 4.1), (sx * 6.3, 4.6), (sx * 2.4, 7.7)][::sx]).close()
             .extrude(ht).translate((0, 0, top_z - LEVER_Z)) for sx in (-1, 1)]   # counter-clockwise outlines
    # kept as separate solids: OCC's fuse drops the ring when the thin wings are added
    return [w.translate((0, 0, LEVER_Z)) for w in (ring.union(tab).union(arm), wings[0], wings[1])]

def springs():
    """The two return springs between the housing and the ring, by the ring's ends."""
    bars = [cq.Workplane('XY').box(1.8, 0.3, 0.9, centered=(True, True, False))
            .rotate((0, 0, 0), (0, 0, 1), sx * 40).translate((sx * 4.6, 5.1, FEET + 0.9)) for sx in (-1, 1)]
    sp = bars[0].union(bars[1])
    return sp

def terminals():
    """Five terminals, 0.25 thick under the body; b and d have 0.90 feet reaching out below the base edge."""
    t = cq.Workplane('XY').pushPoints([(-5.4, 2.32), (5.4, 2.32)]).rect(1.6, 1.6).extrude(FEET)
    t = t.union(cq.Workplane('XY').pushPoints([(-2.5, -2.32), (0, -2.32), (2.5, -2.32)]).rect(1.9, 1.9).extrude(FEET))
    return t

asm = cq.Assembly(name='SW-SMD_BL-DT')
asm.add(body(), name='body', color=cq.Color(*[c / 255 for c in DARK]))
asm.add(cover(), name='cover', color=cq.Color(*[c / 255 for c in METAL]))
asm.add(springs(), name='springs', color=cq.Color(*[c / 255 for c in METAL]))
for i, part in enumerate(lever()):
    asm.add(part, name='lever%d' % i, color=cq.Color(*[c / 255 for c in LEVER]))
asm.add(terminals(), name='terminals', color=cq.Color(*[c / 255 for c in METAL]))
asm.save(sys.argv[1], exportType='STEP')
print(sys.argv[1])
