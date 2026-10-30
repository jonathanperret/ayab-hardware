"""sw_smd_bl_dt_step.py OUT.step  -- SHOU HAN BL-DT thumb wheel switch (LCSC C53223909) as a coloured STEP,
built with CadQuery from the manufacturer's drawing (datasheet rev B00, 2020-05-28): 14.20 wheel diameter,
12.34 overall length, 11.90 base width, 2.50 overall height, 1.65 wheel thickness, 2.16 handle tab,
pegs dia 1.05 at 5.00 pitch, terminals 2.50 pitch / 10.80 span.
Frame: KiCad footprint SW-SMD_BL-DT (origin between the pegs' row and the body), x right, y = -footprint y
(the wheel protrudes towards +y), z up from the PCB top.   pip install cadquery"""
import sys, cadquery as cq

DARK, GREY, METAL = (26, 26, 26), (160, 160, 160), (205, 205, 205)
H, WHEEL_T = 2.50, 1.65                  # overall height, wheel thickness
BASE_Z = H - WHEEL_T                     # 0.85: housing under the wheel
R_WHEEL, R_HUB, TEETH, TOOTH = 7.10, 6.60, 60, 0.30
CX, CY = 0.0, 1.87                       # wheel axis: rim top 6.65 above the A terminals (y 2.32), r 7.10
Y_BOT = CY + R_WHEEL - 11.90             # base edge: 12.34 overall less the 0.44 handle tab -> -2.93

def half_disc(r, h):   # the part of a disc of radius r on the +y side of the wheel axis
    return (cq.Workplane('XY').circle(r).extrude(h)
            .intersect(cq.Workplane('XY').box(2 * r + 1, r + 1, h, centered=(True, False, False))))

def body():
    base = cq.Workplane('XY').box(11.90, CY + 0.3 - Y_BOT, BASE_Z, centered=(True, False, False)).translate((0, Y_BOT, 0))
    hub = half_disc(R_HUB, BASE_Z).translate((CX, CY, 0))                 # housing floor under the wheel
    rim = (cq.Workplane('XY').circle(R_HUB + 0.35).circle(R_HUB).extrude(H)
           .intersect(cq.Workplane('XY').box(2 * R_HUB + 2, 2.0, H, centered=(True, False, False)).translate((0, -1.0, 0)))
           .translate((CX, CY, 0)))                                       # the two "ears" holding the wheel
    pegs = cq.Workplane('XY').pushPoints([(-2.5, 1.32), (2.5, 1.32)]).circle(0.5).extrude(-0.8)
    return base.union(hub).union(rim).union(pegs)

def wheel():
    """A half-disc lever: it rocks 24 deg each way about the axis (B/D) and presses in (C)."""
    import math
    w = half_disc(R_WHEEL, WHEEL_T)
    pts = [(R_WHEEL * math.cos(a), R_WHEEL * math.sin(a)) for a in [math.pi * i / TEETH * 2 for i in range(TEETH)] if math.sin(a) > -0.01]
    w = w.cut(cq.Workplane('XY').pushPoints(pts).circle(TOOTH).extrude(WHEEL_T))
    w = w.union(cq.Workplane('XY').box(2 * R_HUB - 1.0, 1.5, WHEEL_T, centered=(True, False, False)).translate((0, -1.5, 0)))  # pivot, inside the housing
    w = w.union(cq.Workplane('XY').box(2.16, 0.44 + 0.3, WHEEL_T, centered=(True, False, False)).translate((0, R_WHEEL - 0.3, 0)))  # 2.16 handle tab
    return w.translate((CX, CY, BASE_Z))

def terminals():
    t = cq.Workplane('XY').pushPoints([(-5.4, 2.32), (5.4, 2.32)]).rect(1.6, 1.6).extrude(0.25)
    t = t.union(cq.Workplane('XY').pushPoints([(-2.5, -2.32), (0, -2.32), (2.5, -2.32)]).rect(1.9, 1.9).extrude(0.25))
    return t

asm = cq.Assembly(name='SW-SMD_BL-DT')
asm.add(body(), name='body', color=cq.Color(*[c / 255 for c in DARK]))
asm.add(wheel(), name='wheel', color=cq.Color(*[c / 255 for c in GREY]))
asm.add(terminals(), name='terminals', color=cq.Color(*[c / 255 for c in METAL]))
asm.save(sys.argv[1], exportType='STEP')
print(sys.argv[1])
