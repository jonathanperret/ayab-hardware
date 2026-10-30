"""sw_smd_bl_dt_step.py OUT.step  -- SHOU HAN BL-DT thumb wheel switch (LCSC C53223909) as a coloured STEP,
built with CadQuery from the manufacturer's drawing and LCSC's photos (toothed ring lever over a stainless cover plate) (datasheet rev B00, 2020-05-28): 14.20 wheel diameter,
12.34 overall length, 11.90 base width, 2.50 overall height, 1.65 wheel thickness, 2.16 handle tab,
pegs dia 1.05 at 5.00 pitch, terminals 2.50 pitch / 10.80 span.
Frame: KiCad footprint SW-SMD_BL-DT (origin between the pegs' row and the body), x right, y = -footprint y
(the wheel protrudes towards +y), z up from the PCB top.   pip install cadquery"""
import sys, cadquery as cq

DARK, LEVER, METAL = (26, 26, 26), (40, 40, 40), (200, 200, 205)
H, LEVER_T, PLATE_T = 2.50, 1.65, 0.25    # overall height, toothed ring thickness, stainless cover on top
LEVER_Z = 0.40                            # ring from 0.40 to 2.05; the cover plate is the highest surface
R_OUT, R_IN, R_HOUSING, R_PLATE, TEETH, TOOTH = 7.10, 6.20, 5.60, 5.95, 60, 0.30
CX, CY = 0.0, 1.87                        # lever axis: rim top 6.65 above the A terminals (y 2.32), r 7.10
Y_BOT = CY + R_OUT - 11.90                # base edge: 12.34 overall less the 0.44 handle tab -> -2.93
import math

def d_shape(r, y0, h, w=11.90):
    """Rectangle from y0 up to the axis, then a half disc of radius r (the housing outline), height h."""
    rect = cq.Workplane('XY').box(w, CY - y0, h, centered=(True, False, False)).translate((0, y0, 0))
    disc = (cq.Workplane('XY').circle(r).extrude(h)
            .intersect(cq.Workplane('XY').box(2 * r + 1, r + 1, h, centered=(True, False, False)))).translate((CX, CY, 0))
    return rect.union(disc)

def body():
    housing = d_shape(R_HOUSING, Y_BOT, H - PLATE_T)
    floor = d_shape(R_IN, Y_BOT, LEVER_Z)                                      # under the ring: the hidden arms
    pegs = cq.Workplane('XY').pushPoints([(-2.5, 1.32), (2.5, 1.32)]).circle(0.5).extrude(-0.8)
    return housing.union(floor).union(pegs)

def cover():
    """Stainless cover plate E: the top surface, slightly wider than the housing."""
    return d_shape(R_PLATE, Y_BOT + 0.2, PLATE_T).translate((0, 0, H - PLATE_T))

def lever():
    """F: the toothed ring around the housing, below the cover, with its two ends running down the sides
    (photo); it rocks 24 deg each way (B/D) and presses in (C)."""
    ring = (cq.Workplane('XY').circle(R_OUT).circle(R_IN).extrude(LEVER_T)
            .intersect(cq.Workplane('XY').box(2 * R_OUT + 1, R_OUT + 1, LEVER_T, centered=(True, False, False))))
    pts = [(R_OUT * math.cos(a), R_OUT * math.sin(a)) for a in [math.pi * i / TEETH * 2 for i in range(TEETH)] if math.sin(a) > -0.01]
    ring = ring.cut(cq.Workplane('XY').pushPoints(pts).circle(TOOTH).extrude(LEVER_T))
    legs = cq.Workplane('XY').pushPoints([(-(R_IN + R_OUT) / 2, -1.7), ((R_IN + R_OUT) / 2, -1.7)]).rect(R_OUT - R_IN, 3.4).extrude(LEVER_T)
    tab = cq.Workplane('XY').box(2.16, 0.44 + 0.5, LEVER_T, centered=(True, False, False)).translate((0, R_OUT - 0.5, 0))
    return ring.union(legs).union(tab).translate((CX, CY, LEVER_Z))

def terminals():
    t = cq.Workplane('XY').pushPoints([(-5.4, 2.32), (5.4, 2.32)]).rect(1.6, 1.6).extrude(0.25)
    t = t.union(cq.Workplane('XY').pushPoints([(-2.5, -2.32), (0, -2.32), (2.5, -2.32)]).rect(1.9, 1.9).extrude(0.25))
    return t

asm = cq.Assembly(name='SW-SMD_BL-DT')
asm.add(body(), name='body', color=cq.Color(*[c / 255 for c in DARK]))
asm.add(cover(), name='cover', color=cq.Color(*[c / 255 for c in METAL]))
asm.add(lever(), name='lever', color=cq.Color(*[c / 255 for c in LEVER]))
asm.add(terminals(), name='terminals', color=cq.Color(*[c / 255 for c in METAL]))
asm.save(sys.argv[1], exportType='STEP')
print(sys.argv[1])
