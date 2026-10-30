"""placeref.py BOARD REF[,REF...]  -- move each reference label to the nearest spot clear of pads
(0.17 mm), silkscreen (0.12 mm), other labels, courtyards (if possible) and the board edge (0.3 mm);
tries the current angle, then +90 deg. Runs inside the KiCad container."""
import math, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
REFS = sys.argv[2].split(',')
PADM, SILKM, EDGEM = 0.17, 0.12, 0.3
mm = lambda v: v / 1e6
poly = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(poly, False)
ol = poly.Outline(0); E = [(mm(ol.CPoint(i).x), mm(ol.CPoint(i).y)) for i in range(ol.PointCount())]
def dseg(p, a, c):
    vx, vy = c[0] - a[0], c[1] - a[1]; L = vx * vx + vy * vy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)
def rect_of(bb): return (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))
def overlap(r, q, m): return not (r[2] + m <= q[0] or q[2] + m <= r[0] or r[3] + m <= q[1] or q[3] + m <= r[1])
def seg_hits_rect(a, c, r, m):
    x0, y0, x1, y1 = r[0] - m, r[1] - m, r[2] + m, r[3] + m
    t0, t1 = 0.0, 1.0; dx, dy = c[0] - a[0], c[1] - a[1]
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0: return False
        else:
            t = q / p
            if p < 0: t0 = max(t0, t)
            else: t1 = min(t1, t)
            if t0 > t1: return False
    return True
pads, segs, texts, crt = [], [], [], []
for fp in b.GetFootprints():
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    if cy.OutlineCount(): crt.append(rect_of(cy.BBox()))
    for pd in fp.Pads():
        if pd.IsOnLayer(pcbnew.F_Cu): pads.append(rect_of(pd.GetBoundingBox()))
    for it in fp.GraphicalItems():
        if it.GetLayer() != pcbnew.F_SilkS: continue
        if it.GetClass() == 'PCB_SHAPE':
            st = it.GetShape()
            if st == pcbnew.SHAPE_T_SEGMENT:
                segs.append(((mm(it.GetStart().x), mm(it.GetStart().y)), (mm(it.GetEnd().x), mm(it.GetEnd().y))))
            elif st == pcbnew.SHAPE_T_RECTANGLE:
                c = [(mm(it.GetStart().x), mm(it.GetStart().y)), (mm(it.GetEnd().x), mm(it.GetStart().y)), (mm(it.GetEnd().x), mm(it.GetEnd().y)), (mm(it.GetStart().x), mm(it.GetEnd().y))]
                segs += [(c[i], c[(i + 1) % 4]) for i in range(4)]
            else:
                r = rect_of(it.GetBoundingBox()); segs += [((r[0], r[1]), (r[2], r[1])), ((r[2], r[1]), (r[2], r[3])), ((r[2], r[3]), (r[0], r[3])), ((r[0], r[3]), (r[0], r[1]))]
        elif it.IsVisible():
            texts.append((fp.GetReference() + ':t', rect_of(it.GetBoundingBox())))
    for f in (fp.Reference(), fp.Value()):
        if f.IsVisible() and f.GetLayer() == pcbnew.F_SilkS: texts.append((fp.GetReference() + (':ref' if f is fp.Reference() else ':val'), rect_of(f.GetBoundingBox())))
for it in b.GetDrawings():
    if it.GetLayer() == pcbnew.F_SilkS: texts.append(('board', rect_of(it.GetBoundingBox())))
def clear(r, own, strict):
    if strict and any(overlap(r, q, 0) for q in crt): return False
    if any(overlap(r, p, PADM) for p in pads): return False
    if any(seg_hits_rect(a, c, r, SILKM) for a, c in segs): return False
    if any(overlap(r, q, SILKM) for k, q in texts if k != own): return False
    for x, y in ((r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])):
        if not poly.Contains(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6))): return False
        if min(dseg((x, y), E[i], E[(i + 1) % len(E)]) for i in range(len(E))) < EDGEM: return False
    return True
for fp in b.GetFootprints():
    ref = fp.GetReference()
    if ref not in REFS: continue
    f = fp.Reference(); p0 = f.GetPosition(); c0 = fp.GetPosition(); a0 = f.GetTextAngleDegrees()
    best = None
    for strict in (True, False):
      if best: break
      for ang in (a0, (a0 + 90) % 180):
        f.SetTextAngleDegrees(ang)
        for rad in [k * 0.25 for k in range(0, 41)]:
            for k in range(max(1, int(rad * 8))):
                a = 2 * math.pi * k / max(1, int(rad * 8))
                pos = pcbnew.VECTOR2I(int(c0.x + rad * 1e6 * math.cos(a)), int(c0.y + rad * 1e6 * math.sin(a)))
                f.SetPosition(pos)
                r = rect_of(f.GetBoundingBox())
                if clear(r, ref + ':ref', strict):
                    d = math.hypot(mm(pos.x - c0.x), mm(pos.y - c0.y)) + (0.5 if ang != a0 else 0)
                    if best is None or d < best[0]: best = (d, pos, ang)
            if best and rad > best[0] + 0.5: break
    if best:
        f.SetTextAngleDegrees(best[2]); f.SetPosition(best[1])
        texts = [(k, q) for k, q in texts if k != ref + ':ref'] + [(ref + ':ref', rect_of(f.GetBoundingBox()))]
        print(ref, 'moved', round(mm(best[1].x), 2), round(mm(best[1].y), 2), best[2], 'strict' if strict else 'loose')
    else:
        f.SetPosition(p0); print(ref, 'NO SPOT')
b.Save(sys.argv[1])
