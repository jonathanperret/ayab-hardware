"""joints.py BOARD -- pad joint widths (copper overlap measured across each track at the pad), GND pour pieces,
narrowest track per net class. Pads are tested on every copper layer they are on (IsOnLayer), not GetLayer."""
import math, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM; MM = pcbnew.FromMM
pads = [(fp.GetReference(), p) for fp in list(b.GetFootprints()) for p in fp.Pads() if not p.HasHole() or True]
tracks = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
bad = []; n = 0; best = {}
for t in tracks:
    w = mm(t.GetWidth()); lay = t.GetLayer(); a = t.GetStart(); e = t.GetEnd()
    dx, dy = mm(e.x - a.x), mm(e.y - a.y); L = math.hypot(dx, dy)
    if L == 0: continue
    ux, uy = dx / L, dy / L; px, py = -uy, ux
    tp = pcbnew.SHAPE_POLY_SET(); t.TransformShapeToPolygon(tp, lay, 0, MM(0.001), pcbnew.ERROR_INSIDE)
    for ref, p in pads:
        if p.GetNetname() != t.GetNetname() or not p.IsOnLayer(lay): continue
        if not (p.HitTest(a) or p.HitTest(e)) and not p.GetBoundingBox().Intersects(t.GetBoundingBox()): continue
        pp = pcbnew.SHAPE_POLY_SET(); p.TransformShapeToPolygon(pp, lay, 0, MM(0.001), pcbnew.ERROR_INSIDE)
        inter = pcbnew.SHAPE_POLY_SET(pp); inter.BooleanIntersection(tp)
        if inter.OutlineCount() == 0: continue
        # the joint: the track's copper inside the pad, measured across the track
        vals = []
        for oi in range(inter.OutlineCount()):
            o = inter.Outline(oi)
            for k in range(o.PointCount()):
                q = o.CPoint(k); vals.append(mm(q.x) * px + mm(q.y) * py)
        chord = max(vals) - min(vals); n += 1
        need = min(0.15, w) - 0.005
        key = (ref, p.GetNumber(), lay)
        best[key] = max(best.get(key, (-1, 0, ''))[:1] + (0,), (chord - need, chord, t.GetNetname()))[:3] if False else max(best.get(key, (-9, 0, '')), (chord - need, chord, t.GetNetname()))
bad = [(k, v) for k, v in best.items() if v[0] < 0]
print('pad joints (track/pad overlaps)', n, 'pads', len(best), 'pads whose best joint is under min(0.15 mm, track width):', len(bad))
for k, v in bad[:20]: print('  ', k[0], k[1], v[2], 'best chord %.3f' % v[1])
for z in b.Zones():
    if z.GetIsRuleArea(): continue
    for lay in (pcbnew.F_Cu, pcbnew.B_Cu):
        if z.IsOnLayer(lay):
            fp = z.GetFilledPolysList(lay)
            print('zone', z.GetNetname(), b.GetLayerName(lay), 'pieces', fp.OutlineCount(), 'area %.0f mm2' % (fp.Area() / 1e12))
cls = {}
for t in tracks:
    c = t.GetNetClassName(); cls.setdefault(c, []).append(mm(t.GetWidth()))
for c, ws in cls.items(): print('class', c, 'min %.3f' % min(ws), 'max %.3f' % max(ws), 'tracks', len(ws))
