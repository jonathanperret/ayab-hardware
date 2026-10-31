"""sw_smd_bl_dt_step.py OUT.step  -- SHOU HAN BL-DT thumb wheel switch (LCSC C53223909) as a coloured STEP,
built with CadQuery from the manufacturer's drawing (datasheet rev B00, 2020-05-28) read to scale.

All five views of the drawing share one scale (12.34, 11.90, 2.16, 6.65, 3.40, 5.00, 10.80, 2.50 and 1.65
all agree within 0.05 mm); the ring is drawn 14.6 wide although its dimension says 14.20 and the drawing is
followed. Coordinates are those of the KiCad footprint SW-SMD_BL-DT with y flipped (model y = -footprint y,
towards the wheel), z up from the PCB; the pegs are at (+-2.5, 1.32).   pip install cadquery"""
import sys, math, cadquery as cq

DARK, LEVER, METAL = (26, 26, 26), (45, 45, 45), (200, 200, 205)
Y_BASE, X_BASE = -2.80, 5.95          # base front edge, half width (11.90)
Z_HOUSING, Z_TOP = 2.30, 2.50         # housing top, cover plate top (2.50 overall)
Z_RING0, Z_RING1 = 0.60, 2.25         # lever ring (1.65), below the cover's top
RC = (0.0, 1.95)                      # ring centre
R_ROOT, R_TIP, R_IN = 7.07, 7.42, 6.47
TEETH = 50
Y_END = 2.90                          # ring ends, cut level
Y_TAB = 9.54                          # tab top (12.34 from the base edge)
COVER_C, COVER_R = (0.0, 1.29), 5.00  # the cover's top edge (and the housing's central part)
LEV_C, LEV_R = (0.0, 1.19), 6.40      # inner edge of the lever's wide top part
PEG_Y, PEG_X, PEG_D, PEG_H = 1.32, 2.50, 0.90, 0.50
# the cover's side features (from the LCSC photo, positions given by the user): two tabs folding down
# into the body and a flat bump between them
TAB_T = 0.15
GAP = 0.01                            # clearance kept between the parts: no two solids touch
TAB_BOT, BUMP = (-1.80, -0.80), (-0.10, 1.10)
# top tab: folds down along the cover's edge between these two points (marked by the user on the drawing),
# goes down through the body and folds under it like the bottom tab
TAB_FOLD = ((3.63, 4.56), (4.60, 3.98))

def disc(c, r, z0, z1):
    return cq.Workplane('XY').circle(r).extrude(z1 - z0).translate((c[0], c[1], z0))
def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane('XY').box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))
def poly(pts, z0, z1):
    return cq.Workplane('XY').polyline(pts).close().extrude(z1 - z0).translate((0, 0, z0))

# the lever's arm: seen in both plan views between the cover's edge and the lever's arc, its sides
# continue under the cover into the body (how far is not drawn: down to y 5.0 here); its top runs into
# the wide part
ARM = [(-2.20, 7.30), (-2.20, 8.00), (2.20, 8.00), (2.20, 7.30), (1.37, 5.00), (-1.37, 5.00)]

def lever_inner():
    """Inner edge of the lever's wide top part, left to right: V notch, arc r 6.40 about (0, 1.19), V notch."""
    n = 16; a1 = math.asin(2.2 / LEV_R)
    return ([(-3.75, 7.22), (-2.80, 6.97)] + [(LEV_R * math.sin(-a1 + 2 * a1 * i / n), LEV_C[1] + LEV_R * math.cos(-a1 + 2 * a1 * i / n))
            for i in range(n + 1)] + [(2.80, 6.97), (3.75, 7.22)])

def top_tab(sx, d0, d1, z0, z1, ext=0.0):
    """Strip along the top tab's fold line, from d0 to d1 inwards (towards the cover's centre) of it, lengthened
    by ext at both ends; side sx."""
    (x1, y1), (x2, y2) = TAB_FOLD
    n = math.hypot(x2 - x1, y2 - y1); ux, uy = (x2 - x1) / n, (y2 - y1) / n
    x1, y1, x2, y2 = x1 - ux * ext, y1 - uy * ext, x2 + ux * ext, y2 + uy * ext
    nx, ny = -uy, ux   # unit normal, inwards
    if nx * x1 + ny * (y1 - COVER_C[1]) > 0:
        nx, ny = -nx, -ny
    p = [(x1 + nx * d0, y1 + ny * d0), (x2 + nx * d0, y2 + ny * d0), (x2 + nx * d1, y2 + ny * d1), (x1 + nx * d1, y1 + ny * d1)]
    if p[0][0] * 0 + (p[1][0] - p[0][0]) * (p[3][1] - p[0][1]) - (p[1][1] - p[0][1]) * (p[3][0] - p[0][0]) < 0:
        p.reverse()
    pts = [(sx * x, y) for x, y in p]
    if sx < 0:
        pts.reverse()
    return poly(pts, z0, z1)

def outline(y0):
    """The cover's outline, also the body's above its base (the bottom view draws the body's edge on the cover's
    arc): straight sides from y0, a curved edge round the springs up to the hooks, then the arc r 5."""
    side = [(5.45, 2.40), (5.27, 3.00), (5.00, 3.50), (4.45, 3.85), (3.95, 4.10), (3.35, 4.30), (3.10, 4.50)]   # read off the drawing
    x_top = 3.10; a0 = math.atan2(math.sqrt(COVER_R ** 2 - x_top ** 2), x_top); n = 24
    pts = [(-5.45, y0), (5.45, y0)] + side
    pts += [(COVER_R * math.cos(a0 + (math.pi - 2 * a0) * i / n), COVER_C[1] + COVER_R * math.sin(a0 + (math.pi - 2 * a0) * i / n)) for i in range(0, n + 1)]
    return pts + [(-x, y) for x, y in reversed(side)]

def housing():
    """A: base slab and side walls (11.90 wide to y 1.2, 11.30 above to y 2.4), then the cover's outline (the
    bottom view draws the body's edge on the cover's arc), less the lever's arm; the two pegs (0.90, 0.50 below)."""
    zt = Z_HOUSING - GAP   # below the cover
    h = box(-X_BASE, X_BASE, Y_BASE, 1.20, 0, zt)
    h = h.union(box(-5.65, 5.65, 1.0, 2.40, 0, zt))
    h = h.union(poly(outline(1.0), 0, zt))
    h = h.cut(cq.Workplane('XY').polyline(ARM).close().offset2D(GAP, 'intersection').extrude(Z_RING1 - Z_RING0 + 2 * GAP)
              .translate((0, 0, Z_RING0 - GAP)))
    for sx in (-1, 1):
        def bx(x0, x1, y0, y1, z0, z1): return box(min(sx * x0, sx * x1), max(sx * x0, sx * x1), y0, y1, z0, z1)
        g0, g1 = TAB_BOT[0] - GAP, TAB_BOT[1] + GAP
        h = h.cut(bx(X_BASE - TAB_T - GAP, X_BASE + 0.1, g0, g1, 0, Z_HOUSING))   # groove down the side
        h = h.cut(bx(X_BASE - 0.55 - GAP, X_BASE + 0.1, g0, g1, 0, TAB_T + GAP))  # recess underneath
        h = h.union(top_tab(sx, 0, 0.6, 0, zt))      # the body reaches out to the top tab's fold line
        h = h.cut(top_tab(sx, -0.1, TAB_T + GAP, 0, Z_HOUSING, GAP))      # groove for the top tab
        h = h.cut(top_tab(sx, -0.1, 0.55 + GAP, 0, TAB_T + GAP, GAP))     # recess underneath
        h = h.union(disc((sx * PEG_X, PEG_Y), PEG_D / 2, -PEG_H, 0))
    return h

def cover():
    """E: stainless cover: straight sides, a curved edge round the springs up to the hooks, then the arc;
    the pressed V is recessed 0.08."""
    c = poly(outline(Y_BASE + 0.05), Z_HOUSING, Z_TOP)
    # the V: flat centre then arms at 29.7 deg, rounded ends at x +-2.85
    k = math.tan(math.radians(29.6))
    top = [(-2.85, 4.95 - k * 1.35 + 0.0), (-0.85, 5.70 - 0.0), (0.85, 5.70), (2.85, 4.95 - k * 1.35)]
    def arm_outline():
        t = [(-0.9, 5.70), (0.9, 5.70), (1.5, 4.95), (2.85, 4.95 - k * 1.35), (2.85, 4.27 - k * 1.35), (1.5, 4.27), (0.75, 4.70),
             (-0.75, 4.70), (-1.5, 4.27), (-2.85, 4.27 - k * 1.35), (-2.85, 4.95 - k * 1.35), (-1.5, 4.95)]
        return t
    v = poly(arm_outline(), Z_TOP - 0.08, Z_TOP)
    for sx in (-1, 1):
        v = v.union(disc((sx * 2.85, (4.95 + 4.27) / 2 - k * 1.35), 0.34, Z_TOP - 0.08, Z_TOP))
    c = c.cut(v)
    T = TAB_T
    for sx in (-1, 1):
        def bx(x0, x1, y0, y1, z0, z1): return box(min(sx * x0, sx * x1), max(sx * x0, sx * x1), y0, y1, z0, z1)
        # bottom tab (y -1.8..-0.8): out to the body's edge, down its side in a groove, folded under the body
        c = c.union(bx(5.40, X_BASE, *TAB_BOT, Z_HOUSING, Z_TOP))
        c = c.union(bx(X_BASE - T, X_BASE, *TAB_BOT, T, Z_HOUSING))
        c = c.union(bx(X_BASE - 0.55, X_BASE, *TAB_BOT, 0, T))
        # bump (y -0.1..1.1): flat, out to the body's edge, rounded corners
        c = c.union(bx(5.40, X_BASE - 0.25, *BUMP, Z_HOUSING, Z_TOP))
        for yc in (BUMP[0] + 0.25, BUMP[1] - 0.25):
            c = c.union(disc((sx * (X_BASE - 0.25), yc), 0.25, Z_HOUSING, Z_TOP))
        c = c.union(bx(X_BASE - 0.25, X_BASE, BUMP[0] + 0.25, BUMP[1] - 0.25, Z_HOUSING, Z_TOP))
        # top tab: down from the cover's edge along the fold line, through the body, folded under it
        c = c.union(top_tab(sx, 0, 0.6, Z_HOUSING, Z_TOP))   # the cover's edge reaches the fold line here
        c = c.union(top_tab(sx, 0, T, T, Z_HOUSING))
        c = c.union(top_tab(sx, 0, 0.55, 0, T))
    return c

def lever():
    """F: toothed ring around the housing, its ends cut level at y 2.90, a wide top part whose inner edge is
    an arc with a V notch on each side, the 2.16 tab, and the arm reaching in to the cover's edge."""
    t = (Z_RING0, Z_RING1)
    # scalloped edge: bumps reaching R_TIP and hollows down to R_ROOT, alternating at the tooth pitch
    r_mid = (R_ROOT + R_TIP) / 2; pitch = 2 * math.pi / TEETH; rb = 0.26
    ring = disc(RC, r_mid, *t).cut(disc(RC, R_IN, *t))
    for i in range(-TEETH // 2, TEETH // 2 + 1):
        a = math.pi / 2 + i * pitch
        ring = ring.union(disc((RC[0] + (R_TIP - rb) * math.cos(a), RC[1] + (R_TIP - rb) * math.sin(a)), rb, *t))
        a += pitch / 2
        ring = ring.cut(disc((RC[0] + (R_ROOT + rb) * math.cos(a), RC[1] + (R_ROOT + rb) * math.sin(a)), rb, *t))
    ring = ring.intersect(box(-8, 8, Y_END, 10, *t))
    # wide top part: from the inner edge (V notch + arc) out to the ring
    wide = poly(lever_inner() + [(3.75, 9.0), (-3.75, 9.0)], *t).intersect(disc(RC, R_ROOT, *t))
    tab = box(-1.05, 1.05, RC[1] + R_ROOT - 0.3, Y_TAB, *t)
    arm = poly(ARM, *t)
    ends = [box(sx * 6.30 if sx > 0 else -7.30, 7.30 if sx > 0 else -6.30, Y_END, Y_END + 0.55, *t) for sx in (-1, 1)]   # square outer corners
    return ring.union(wide).union(tab).union(arm).union(ends[0]).union(ends[1])

def springs(g=0.0):
    """The two return springs, between the cover's diagonal edge and the housing arc (grown by g: their room)."""
    s = None
    for sx in (-1, 1):
        a = math.atan2(4.25 - 2.40, sx * (4.75 - 5.40))
        bar = (cq.Workplane('XY').box(math.hypot(0.65, 1.85) + 2 * g, 0.30 + 2 * g, 0.70 + 2 * g).rotate((0, 0, 0), (0, 0, 1), math.degrees(a))
               .translate((sx * (4.75 + 5.40) / 2, (4.25 + 2.40) / 2, 1.2)))
        s = bar if s is None else s.union(bar)
    return s

def terminals(g=0.0):
    """b, c, d: 1.6 wide, from the base edge 1.5 in; a: 1.3 x 1.3 by the ring ends; 0.15 thick at the bottom
    (grown by g: their room)."""
    t = None
    for x in (-2.5, 0.0, 2.5):
        b = box(x - 0.8 - g, x + 0.8 + g, Y_BASE - g, Y_BASE + 1.5 + g, -g, 0.15 + g); t = b if t is None else t.union(b)
    for sx in (-1, 1):
        t = t.union(box(min(sx * 4.30, sx * 5.60) - g, max(sx * 4.30, sx * 5.60) + g, 1.80 - g, 3.10 + g, -g, 0.15 + g))
    return t

if __name__ == '__main__':
    asm = cq.Assembly(name='SW-SMD_BL-DT')
    asm.add(housing().cut(springs(GAP)).cut(terminals(GAP)), name='housing', color=cq.Color(*[c / 255 for c in DARK]))
    asm.add(cover(), name='cover', color=cq.Color(*[c / 255 for c in METAL]))
    asm.add(springs(), name='springs', color=cq.Color(*[c / 255 for c in METAL]))
    asm.add(lever(), name='lever', color=cq.Color(*[c / 255 for c in LEVER]))
    asm.add(terminals(), name='terminals', color=cq.Color(*[c / 255 for c in METAL]))
    asm.save(sys.argv[1], exportType='STEP')
    print(sys.argv[1])
