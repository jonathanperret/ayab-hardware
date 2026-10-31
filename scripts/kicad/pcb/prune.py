"""prune.py BOARD [NET,NET...]  -- remove dangling track chains and orphan vias in one run (no DRC loop).
A segment is dangling when one of its ends touches nothing of its net on its layer: another
segment's copper, a via, a pad, or a filled zone of the net (zones are not refilled here: refill
first); a via is an orphan when it touches no pad, no zone and at most one segment.
Repeats until nothing changes, so a chain of short segments left after cutting a connection goes in
one call (route/rm_dangling.py removes one segment per DRC pass). With NETS, only those nets.
Runs inside the KiCad container. Plain coordinates are read before any change (KiCad 10's swig
objects get corrupted when reused after board edits)."""
import math, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
NETS = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
TOL = 0.002   # mm


def mm(v):
    return pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)


# snapshot: tracks as plain tuples, pads as (net, layer set, hit-test object)
items = []
for t in b.GetTracks():
    net = t.GetNetname()
    if NETS is not None and net not in NETS:
        continue
    if t.GetClass() == 'PCB_VIA':
        items.append(dict(obj=t, via=True, net=net, p=mm(t.GetPosition()), vr=pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2))
    elif t.GetClass() == 'PCB_ARC':   # never removed, but other tracks may end on it (two chords via its mid point)
        a, m, e = mm(t.GetStart()), mm(t.GetMid()), mm(t.GetEnd())
        for p0, p1 in ((a, m), (m, e)):
            items.append(dict(obj=None, via=False, net=net, a=p0, b=p1, layer=t.GetLayer(), w=pcbnew.ToMM(t.GetWidth())))
    elif t.GetClass() == 'PCB_TRACK':
        items.append(dict(obj=t, via=False, net=net, a=mm(t.GetStart()), b=mm(t.GetEnd()), layer=t.GetLayer(),
                          w=pcbnew.ToMM(t.GetWidth())))
# ends that sit in a filled zone of their net count as connected (looked up before any change)
zones = [(z.GetNetname(), z) for z in b.Zones() if not z.GetIsRuleArea()]
def zoned(net):
    return any(n == net for n, z in zones)
def in_zone(net, pt, layers):
    v = pcbnew.VECTOR2I(pcbnew.FromMM(pt[0]), pcbnew.FromMM(pt[1]))
    return any(n == net and z.HitTestFilledArea(l, v) for n, z in zones for l in layers)
for it in items:
    if it['via']:
        it['zone'] = in_zone(it['net'], it['p'], (pcbnew.F_Cu, pcbnew.B_Cu))
    else:
        it['za'] = in_zone(it['net'], it['a'], (it['layer'],)); it['zb'] = in_zone(it['net'], it['b'], (it['layer'],))
pads = []   # (net, layers, bounding box in mm): a box test is enough to tell 'ends on a pad'
for fp in b.GetFootprints():
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        pads.append((p.GetNetname(), [l for l in (pcbnew.F_Cu, pcbnew.B_Cu) if p.IsOnLayer(l)],
                     (pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))))


def on_pad(net, pt, layer=None, m=0.0):
    x, y = pt; m += TOL
    return any(n == net and (layer is None or layer in ls) and bx[0] - m <= x <= bx[2] + m and bx[1] - m <= y <= bx[3] + m
               for n, ls, bx in pads)


def dist_seg(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def touched(pt, layer, net, me, alive, other):
    """copper of 'me' around its end pt overlaps something of its net; a track only counts if it is closer
    to pt than to my other end, or touches pt exactly (a short segment otherwise 'touches' its own neighbour)"""
    for it in alive:
        if it is me or it['net'] != net:
            continue
        if it['via']:
            if math.dist(it['p'], pt) < TOL + it['vr'] + me['w'] / 2:
                return True
        elif it['layer'] == layer:
            d = dist_seg(pt, it['a'], it['b'])
            if d < TOL or (d < TOL + (it['w'] + me['w']) / 2 and d < dist_seg(other, it['a'], it['b']) - TOL):
                return True
    return on_pad(net, pt, layer, me['w'] / 2)


alive = list(items); removed = []
while True:
    rm = []
    for it in alive:
        if it['via']:
            n = sum(1 for u in alive if not u['via'] and u['net'] == it['net']
                    and min(math.dist(u['a'], it['p']), math.dist(u['b'], it['p'])) < TOL + it['vr'])
            # one track only is still fine when the net has a zone (the via may reach it on the other layer)
            if (n == 0 or (n == 1 and not zoned(it['net']))) and not it['zone'] and not on_pad(it['net'], it['p']):
                rm.append(it)
        elif it['obj'] is not None and ((not it['za'] and not touched(it['a'], it['layer'], it['net'], it, alive, it['b'])) or
                                        (not it['zb'] and not touched(it['b'], it['layer'], it['net'], it, alive, it['a']))):
            rm.append(it)
    if not rm:
        break
    ids = set(map(id, rm)); alive = [it for it in alive if id(it) not in ids]; removed += rm
for it in removed:
    b.Remove(it['obj'])
print('pruned', len(removed), 'items')
pcbnew.SaveBoard(sys.argv[1], b)
