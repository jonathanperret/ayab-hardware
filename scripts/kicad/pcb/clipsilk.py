"""clipsilk.py BOARD REF[,REF...] [--own] [--edge]  -- cut the footprints' silkscreen lines/arcs/rects
back to 0.15 mm from pads (JLCPCB). --own: only the footprint's own pads; --edge: also clip at the board
edge. Changed footprints no longer match their library: copy them into the project library.
Runs inside the KiCad container."""
import math, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
REFS = sys.argv[2].split(',')
OWN_ONLY = '--own' in sys.argv
EDGE = '--edge' in sys.argv
PAD_CL, EDGE_CL, STEP = 0.15, 0.1, 0.02
nm = pcbnew.FromMM
poly = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(poly, False)
ol = poly.Outline(0); E = [(ol.CPoint(i).x / 1e6, ol.CPoint(i).y / 1e6) for i in range(ol.PointCount())]
def dseg(p, a, c):
    vx, vy = c[0] - a[0], c[1] - a[1]; L = vx * vx + vy * vy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)
def inside_board(p, m):
    if not poly.Contains(pcbnew.VECTOR2I(nm(p[0]), nm(p[1]))): return False
    return min(dseg(p, E[i], E[(i + 1) % len(E)]) for i in range(len(E))) >= m
pads = {}
for fp in b.GetFootprints():
    if OWN_ONLY and fp.GetReference() not in REFS: continue
    for pd in fp.Pads():
        for L in (pcbnew.F_Cu, pcbnew.B_Cu):
            if pd.IsOnLayer(L): pads.setdefault(L, []).append(pd.GetEffectiveShape(L))
def ok(p, layer, w):
    cu = pcbnew.F_Cu if layer == pcbnew.F_SilkS else pcbnew.B_Cu
    v = pcbnew.VECTOR2I(nm(p[0]), nm(p[1]))
    if any(s.Collide(v, nm(PAD_CL + w / 2 + 0.01)) for s in pads.get(cu, [])): return False
    return inside_board(p, EDGE_CL + w / 2) if EDGE else True
def polyline_of(it):
    st = it.GetShape()
    if st == pcbnew.SHAPE_T_SEGMENT:
        return [[(it.GetStart().x / 1e6, it.GetStart().y / 1e6), (it.GetEnd().x / 1e6, it.GetEnd().y / 1e6)]]
    if st == pcbnew.SHAPE_T_RECTANGLE:
        c = [(x / 1e6, y / 1e6) for x, y in ((it.GetStart().x, it.GetStart().y), (it.GetEnd().x, it.GetStart().y), (it.GetEnd().x, it.GetEnd().y), (it.GetStart().x, it.GetEnd().y))]
        return [[c[i], c[(i + 1) % 4]] for i in range(4)]
    if st == pcbnew.SHAPE_T_ARC:
        cx, cy = it.GetCenter().x / 1e6, it.GetCenter().y / 1e6; r = it.GetRadius() / 1e6
        a0 = math.atan2(it.GetStart().y / 1e6 - cy, it.GetStart().x / 1e6 - cx)
        a1 = math.atan2(it.GetEnd().y / 1e6 - cy, it.GetEnd().x / 1e6 - cx)
        sweep = it.GetArcAngle().AsRadians()
        n = max(8, int(abs(sweep) * r / 0.2))
        return [[(cx + r * math.cos(a0 + sweep * k / n), cy + r * math.sin(a0 + sweep * k / n)) for k in range(n + 1)]]
    return None
changed = 0
for fp in b.GetFootprints():
    if fp.GetReference() not in REFS: continue
    for it in list(fp.GraphicalItems()):
        if it.GetClass() != 'PCB_SHAPE' or it.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS): continue
        pls = polyline_of(it)
        if pls is None: continue
        w = it.GetWidth() / 1e6
        runs, bad = [], False
        for pl in pls:
            cur = []
            for a, c in zip(pl, pl[1:]):
                n = max(1, int(math.hypot(c[0] - a[0], c[1] - a[1]) / STEP))
                for k in range(n + 1):
                    if k == 0 and cur: continue
                    p = (a[0] + (c[0] - a[0]) * k / n, a[1] + (c[1] - a[1]) * k / n)
                    if ok(p, it.GetLayer(), w): cur.append(p)
                    else:
                        bad = True
                        if len(cur) > 1: runs.append(cur)
                        cur = []
                # keep corners as polyline vertices
            if len(cur) > 1: runs.append(cur)
        if not bad: continue
        changed += 1
        for run in runs:
            # simplify the sampled run back to straight pieces (keep points where direction changes)
            pts = [run[0]]
            for i in range(1, len(run) - 1):
                (x0, y0), (x1, y1), (x2, y2) = pts[-1], run[i], run[i + 1]
                if abs((x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1)) > 1e-6: pts.append(run[i])
            pts.append(run[-1])
            for p0, p1 in zip(pts, pts[1:]):
                if math.hypot(p1[0] - p0[0], p1[1] - p0[1]) < 0.1: continue
                s = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_SEGMENT)
                s.SetLayer(it.GetLayer()); s.SetWidth(it.GetWidth())
                s.SetStart(pcbnew.VECTOR2I(nm(p0[0]), nm(p0[1]))); s.SetEnd(pcbnew.VECTOR2I(nm(p1[0]), nm(p1[1])))
                fp.Add(s)
        fp.Remove(it)
b.Save(sys.argv[1])
print('clipped', changed)
