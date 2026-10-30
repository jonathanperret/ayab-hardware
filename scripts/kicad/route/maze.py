"""Small 2-layer grid A* router on top of pcbnew (0.1 mm grid). Runs inside the KiCad container.
Board outline and keep-outs come from the board (pcb/boardgeom.py); clearance 0.2 mm, vias 0.6/0.3 mm.

maze.py BOARD gnd [REF:PAD ...]        connect isolated SMD GND pads to a new GND via (F.Cu path)
maze.py BOARD pads REF:PAD REF:PAD [W] route a track of width W (mm) between two pads of the same net
maze.py BOARD rip X1 Y1 X2 Y2 NET W [UNPROTECT|-] [PROTECTED_NET ...]
                                       route NET between two points, ripping up other nets' tracks
                                       in the way (except protected nets); ripped nets must be rerouted
maze.py BOARD stitch [STEP]            add GND stitching vias on a STEP-mm grid where there is room
maze.py BOARD fixdrc DRC_REPORT [W]    try to route every 'unconnected_items' pair of the DRC report
"""
import pcbnew, sys, math, heapq
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pcb'))
from boardgeom import BoardGeom
b = pcbnew.LoadBoard(sys.argv[1]); mm, MM = pcbnew.ToMM, pcbnew.FromMM
GEOM = BoardGeom(b)
G = 0.1; CLR = 0.2; VIA_D, VIA_DR = 0.6, 0.3
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)

class Grid2:
    def __init__(self, ny, nx):
        self.nx = nx; self.a = bytearray(ny * nx)
    def __getitem__(self, k):
        return self.a[k[0] * self.nx + k[1]] != 0
    def __setitem__(self, k, v):
        self.a[k[0] * self.nx + k[1]] = 1 if v else 0

class Grid3:
    def __init__(self, nl, ny, nx):
        self.nx, self.ny = nx, ny; self.a = bytearray(nl * ny * nx)
    def __getitem__(self, k):
        return self.a[(k[0] * self.ny + k[1]) * self.nx + k[2]] != 0
    def __setitem__(self, k, v):
        self.a[(k[0] * self.ny + k[1]) * self.nx + k[2]] = 1 if v else 0

def board_ok(x, y, m):
    """Inside the board outline and outside track keep-outs, with margin m (mm)."""
    return GEOM.ok(x, y, m)

def items_near(x0, y0, x1, y1):
    box = pcbnew.BOX2I(pcbnew.VECTOR2I(MM(x0), MM(y0)), pcbnew.VECTOR2L(MM(x1 - x0), MM(y1 - y0)))
    pads = [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetBoundingBox().Intersects(box)]
    tracks = [t for t in b.GetTracks() if t.GetBoundingBox().Intersects(box)]
    return pads, tracks

def build(netcode, x0, y0, x1, y1, w, rippable=None):
    """blocked[layer, iy, ix] for a track of width w of net netcode; viaok[iy, ix]."""
    nx, ny = int((x1 - x0) / G) + 1, int((y1 - y0) / G) + 1
    blk = Grid3(2, ny, nx); vblk = Grid2(ny, nx)
    pads, tracks = items_near(x0 - 1, y0 - 1, x1 + 1, y1 + 1)
    acc_t, acc_v = MM(w / 2 + CLR), MM(VIA_D / 2 + CLR)
    soft = {}; reg = []
    def mark(it, li, hit_layers, foreign):
        acc_t, acc_v = cur_acc[0], cur_acc[1]
        if rippable is not None and foreign and rippable(it):
            reg.append(it); key = len(reg) - 1
            bb = it.GetBoundingBox(); m = VIA_D / 2 + CLR + 0.1
            ix0 = max(0, int((mm(bb.GetLeft()) - m - x0) / G)); ix1 = min(nx - 1, int((mm(bb.GetRight()) + m - x0) / G) + 1)
            iy0 = max(0, int((mm(bb.GetTop()) - m - y0) / G)); iy1 = min(ny - 1, int((mm(bb.GetBottom()) + m - y0) / G) + 1)
            for iy in range(iy0, iy1 + 1):
                for ix in range(ix0, ix1 + 1):
                    p = pcbnew.VECTOR2I(MM(x0 + ix * G), MM(y0 + iy * G))
                    for L in hit_layers:
                        if it.HitTest(p, acc_t):
                            soft.setdefault((L, iy, ix), set()).add(key)
                    if it.HitTest(p, acc_v):
                        soft.setdefault(('v', iy, ix), set()).add(key)
            return
        bb = it.GetBoundingBox(); m = VIA_D / 2 + CLR + 0.1
        ix0 = max(0, int((mm(bb.GetLeft()) - m - x0) / G)); ix1 = min(nx - 1, int((mm(bb.GetRight()) + m - x0) / G) + 1)
        iy0 = max(0, int((mm(bb.GetTop()) - m - y0) / G)); iy1 = min(ny - 1, int((mm(bb.GetBottom()) + m - y0) / G) + 1)
        for iy in range(iy0, iy1 + 1):
            for ix in range(ix0, ix1 + 1):
                p = pcbnew.VECTOR2I(MM(x0 + ix * G), MM(y0 + iy * G))
                if foreign:
                    for L in hit_layers:
                        if not blk[L, iy, ix] and it.HitTest(p, acc_t):
                            blk[L, iy, ix] = True
                if not vblk[iy, ix] and (foreign or li == 'hole') and it.HitTest(p, acc_v):
                    vblk[iy, ix] = True
    acc_t0, acc_v0 = acc_t, acc_v
    cur_acc = [acc_t0, acc_v0]
    for p in pads:
        foreign = p.GetNetCode() != netcode or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH
        cur_acc[:] = [acc_t0 + MM(0.1), acc_v0 + MM(0.1)] if p.HasHole() else [acc_t0, acc_v0]
        hl = [i for i, L in enumerate(LAYERS) if p.IsOnLayer(L)]
        if foreign:
            mark(p, None, hl, True)
        elif p.HasHole():
            mark(p, 'hole', [], False)      # own-net PTH: no via on top of it
    cur_acc[:] = [acc_t0, acc_v0]
    for t in tracks:
        foreign = t.GetNetCode() != netcode
        if t.GetClass() == 'PCB_VIA':
            if foreign:
                mark(t, None, [0, 1], True)
            else:
                mark(t, 'hole', [], False)
        else:
            if foreign:
                mark(t, None, [0 if t.GetLayer() == pcbnew.F_Cu else 1], True)
    for iy in range(ny):
        for ix in range(nx):
            x, y = x0 + ix * G, y0 + iy * G
            if not board_ok(x, y, 0.5 + w / 2):
                blk[0, iy, ix] = True; blk[1, iy, ix] = True
            if not board_ok(x, y, 0.5 + VIA_D / 2):
                vblk[iy, ix] = True
    viaok = Grid2(ny, nx)
    for iy in range(ny):
        for ix in range(nx):
            viaok[iy, ix] = not (vblk[iy, ix] or blk[0, iy, ix] or blk[1, iy, ix])
    build.soft = soft; build.reg = reg
    return blk, viaok, nx, ny

def astar(blk, viaok, starts, goal, h, nx, ny, via_cost=12, soft=None, soft_cost=40):
    D = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    dist, prev, pq = {}, {}, []
    for s in starts:
        dist[s] = 0; heapq.heappush(pq, (h(s), 0, s))
    while pq:
        f, g, cur = heapq.heappop(pq)
        if g > dist.get(cur, 1e9):
            continue
        if goal(cur):
            path = [cur]
            while cur in prev:
                cur = prev[cur]; path.append(cur)
            return path[::-1]
        L, iy, ix = cur
        nbrs = []
        for dx, dy, c in D:
            jx, jy = ix + dx, iy + dy
            if 0 <= jx < nx and 0 <= jy < ny and not blk[L, jy, jx]:
                if dx and dy and (blk[L, iy, jx] or blk[L, jy, ix]):
                    continue
                nbrs.append(((L, jy, jx), c))
        if viaok[iy, ix]:
            nbrs.append(((1 - L, iy, ix), via_cost))
        for n, c in nbrs:
            if soft:
                if n[0] != L and ('v', n[1], n[2]) in soft:
                    c += soft_cost
                elif (n[0], n[1], n[2]) in soft and (L, iy, ix) not in soft:
                    c += soft_cost
                elif (n[0], n[1], n[2]) in soft:
                    c += 2
            ng = g + c
            if ng < dist.get(n, 1e9):
                dist[n] = ng; prev[n] = cur; heapq.heappush(pq, (ng + h(n), ng, n))
    return None

def emit(path, x0, y0, net, w, end_via=False):
    """turn a cell path into tracks/vias (merging straight runs)."""
    pt = lambda c: pcbnew.VECTOR2I(MM(x0 + c[2] * G), MM(y0 + c[1] * G))
    segs, i = [], 0
    run = [path[0]]
    def flush(run):
        if len(run) < 2:
            return
        pts = [run[0]]
        for a, c, d in zip(run, run[1:], run[2:]):
            if (c[1] - a[1], c[2] - a[2]) != (d[1] - c[1], d[2] - c[2]):
                pts.append(c)
        pts.append(run[-1])
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b); t.SetStart(pt(a)); t.SetEnd(pt(c)); t.SetWidth(MM(w))
            t.SetLayer(LAYERS[a[0]]); t.SetNet(net); b.Add(t)
    def via(c):
        v = pcbnew.PCB_VIA(b); v.SetPosition(pt(c)); v.SetWidth(MM(VIA_D)); v.SetDrill(MM(VIA_DR)); v.SetNet(net); b.Add(v)
    for a, c in zip(path, path[1:]):
        if a[0] != c[0]:
            flush(run); via(a); run = [c]
        else:
            run.append(c)
    flush(run)
    if end_via:
        via(path[-1])

def cell(x, y, x0, y0):
    return (int(round((y - y0) / G)), int(round((x - x0) / G)))

mode = sys.argv[2]
if mode == 'gnd':
    gnd = b.FindNet('GND'); n = 0
    targets = [a.split(':') for a in sys.argv[3:]]
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() != gnd.GetNetCode() or pad.HasHole() or not pad.IsOnLayer(pcbnew.F_Cu):
                continue
            if targets and [fp.GetReference(), pad.GetNumber()] not in targets:
                continue
            px, py = mm(pad.GetPosition().x), mm(pad.GetPosition().y)
            if not targets and any(t.GetNetCode() == gnd.GetNetCode() and (t.GetClass() == 'PCB_VIA' or True) and
                                   (t.GetStart() == pad.GetPosition() or t.GetEnd() == pad.GetPosition()) for t in b.GetTracks()):
                continue
            w = 0.25
            x0, y0 = px - 4, py - 4
            blk, viaok, nx, ny = build(gnd.GetNetCode(), x0, y0, px + 4, py + 4, w)
            sy, sx = cell(px, py, x0, y0)
            # start cells: inside the pad itself (own copper), F.Cu only
            starts = []
            for iy in range(ny):
                for ix in range(nx):
                    if pad.HitTest(pcbnew.VECTOR2I(MM(x0 + ix * G), MM(y0 + iy * G)), 0):
                        blk[0, iy, ix] = False; starts.append((0, iy, ix))
            far = lambda c: math.hypot(c[1] - sy, c[2] - sx) * G
            goal = lambda c: c[0] == 0 and viaok[c[1], c[2]] and far(c) > 0.55 and not pad.HitTest(pcbnew.VECTOR2I(MM(x0 + c[2] * G), MM(y0 + c[1] * G)), MM(VIA_D / 2 + 0.05))
            # no layer change for this search: F.Cu only
            viaok_f = Grid2(ny, nx)
            path = astar(blk, viaok_f, starts, goal, lambda c: 0, nx, ny)
            if path:
                emit([(0, sy, sx)] + path[1:], x0, y0, gnd, w, end_via=True); n += 1
            else:
                print('no gnd path for', fp.GetReference(), pad.GetNumber())
    print('gnd fanouts', n)
elif mode == 'stitch':
    gnd = b.FindNet('GND'); step = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    x0, y0, x1, y1 = GEOM.bbox
    blk, viaok, nx, ny = build(gnd.GetNetCode(), x0, y0, x1, y1, 0.25)
    existing = [(mm(t.GetPosition().x), mm(t.GetPosition().y)) for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
    n = 0; k = int(round(step / G))
    for iy in range(0, ny, k):
        for ix in range(0, nx, k):
            # look for a free spot near the grid point
            for dy, dx in ((0, 0), (0, 3), (3, 0), (0, -3), (-3, 0), (3, 3), (-3, -3), (3, -3), (-3, 3)):
                jy, jx = iy + dy, ix + dx
                if 0 <= jy < ny and 0 <= jx < nx and viaok[jy, jx]:
                    x, y = x0 + jx * G, y0 + jy * G
                    if any(math.hypot(x - ex, y - ey) < 1.6 for ex, ey in existing):
                        break
                    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); v.SetWidth(MM(VIA_D)); v.SetDrill(MM(VIA_DR)); v.SetNet(gnd); b.Add(v)
                    existing.append((x, y)); n += 1
                    break
    print('stitching vias', n)
elif mode == 'fixdrc':
    import re
    rpt = open(sys.argv[3]).read()
    w = float(sys.argv[4]) if len(sys.argv) > 4 else 0.25
    blocks = [blk_ for blk_ in rpt.split('\n[') if blk_.startswith('unconnected_items')]
    def layers_at(netcode, x, y):
        p = pcbnew.VECTOR2I(MM(x), MM(y)); out = set()
        for fp in b.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetCode() == netcode and pad.HitTest(p, MM(0.01)):
                    out |= {i for i, L in enumerate(LAYERS) if pad.IsOnLayer(L)}
        for t in b.GetTracks():
            if t.GetNetCode() == netcode and t.HitTest(p, MM(0.01)):
                out |= {0, 1} if t.GetClass() == 'PCB_VIA' else {0 if t.GetLayer() == pcbnew.F_Cu else 1}
        return sorted(out)
    def route_pts(net, a, c, w, goal_layers=None):
        (ax, ay), (cx, cy) = a, c
        x0, y0 = min(ax, cx) - 5, min(ay, cy) - 5
        blk, viaok, nx, ny = build(net.GetNetCode(), x0, y0, max(ax, cx) + 5, max(ay, cy) + 5, w)
        sa, sc = cell(ax, ay, x0, y0), cell(cx, cy, x0, y0)
        La = layers_at(net.GetNetCode(), ax, ay) or [0]
        Lc = goal_layers or layers_at(net.GetNetCode(), cx, cy) or [0]
        for L in La: blk[(L,) + sa] = False
        for L in Lc: blk[(L,) + sc] = False
        path = astar(blk, viaok, [(L,) + sa for L in La], lambda q: (q[1], q[2]) == sc and q[0] in Lc,
                     lambda q: math.hypot(q[1] - sc[0], q[2] - sc[1]), nx, ny)
        if path:
            emit(path, x0, y0, net, w)
        return bool(path)
    done = 0
    for blk_txt in blocks:
        items = re.findall(r'@\(([\d.]+) mm, ([\d.]+) mm\): (.*)', blk_txt)
        pts = [(float(x), float(y), desc) for x, y, desc in items]
        netname = None
        for _, _, desc in pts:
            m = re.search(r'\[([^\]]+)\]', desc)
            if m: netname = m.group(1); break
        net = b.FindNet(netname)
        real = [(x, y) for x, y, desc in pts if not desc.startswith('Zone')]
        ok = False
        if len(real) == 2:
            ok = route_pts(net, real[0], real[1], w)
        elif len(real) == 1:
            vias = sorted(((mm(t.GetPosition().x), mm(t.GetPosition().y)) for t in b.GetTracks()
                           if t.GetClass() == 'PCB_VIA' and t.GetNetCode() == net.GetNetCode()), key=lambda v: math.dist(v, real[0]))
            for v in [v for v in vias if math.dist(v, real[0]) > 1.5][:6]:
                if route_pts(net, real[0], v, w, goal_layers=[0, 1]):
                    ok = True; break
        print(('fixed ' if ok else 'FAILED ') + str(netname) + ' ' + str(real))
        done += ok
    print('fixdrc', done, '/', len(blocks))
elif mode == 'rip':
    # rip x1 y1 x2 y2 NET width : route, ripping up signal tracks / plain GND vias in the way
    ax, ay, cx, cy = map(float, sys.argv[3:7]); net = b.FindNet(sys.argv[7]); w = float(sys.argv[8])
    # power nets are never ripped up; override with MAZE_PROTECTED_NETS="net1,net2,..."
    hard_nets = set(os.environ.get('MAZE_PROTECTED_NETS', '+15V,/Vout,/Vsol,Net-(U6-SW),+5V,+3.3V,Net-(D1-K),/USB2_VBUS,Net-(U9-SW)').split(','))
    hard_nets -= {sys.argv[9]} if len(sys.argv) > 9 and sys.argv[9] != '-' else set()
    hard_nets |= set(sys.argv[10:])
    def rippable(it):
        if it.GetClass() == 'PCB_VIA':
            return it.GetNetname() not in hard_nets
        if it.GetClass() in ('PCB_TRACK', 'PCB_ARC'):
            return it.GetNetname() not in hard_nets and it.GetNetname() != 'GND'
        return False
    x0, y0 = min(ax, cx) - 5, min(ay, cy) - 5
    blk, viaok, nx, ny = build(net.GetNetCode(), x0, y0, max(ax, cx) + 5, max(ay, cy) + 5, w, rippable)
    soft = build.soft
    for (L, iy, ix) in [k for k in soft if k[0] != 'v']:
        pass
    sa, sc = cell(ax, ay, x0, y0), cell(cx, cy, x0, y0)
    def lay(x, y):
        p = pcbnew.VECTOR2I(MM(x), MM(y)); out = set()
        for fp in b.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetCode() == net.GetNetCode() and pad.HitTest(p, MM(0.01)):
                    out |= {i for i, L in enumerate(LAYERS) if pad.IsOnLayer(L)}
        for t in b.GetTracks():
            if t.GetNetCode() == net.GetNetCode() and t.HitTest(p, MM(0.01)):
                out |= {0, 1} if t.GetClass() == 'PCB_VIA' else {0 if t.GetLayer() == pcbnew.F_Cu else 1}
        return sorted(out) or [0]
    La, Lc = lay(ax, ay), lay(cx, cy)
    for L in La: blk[(L,) + sa] = False
    for L in Lc: blk[(L,) + sc] = False
    # soft cells are passable: clear them from the hard grid if no hard item there
    # (build() did not mark rippable items as hard, so nothing to clear)
    via_ok_soft = Grid2(ny, nx)
    for iy in range(ny):
        for ix in range(nx):
            via_ok_soft[iy, ix] = viaok[iy, ix]
    path = astar(blk, via_ok_soft, [(L,) + sa for L in La], lambda q: (q[1], q[2]) == sc and q[0] in Lc,
                 lambda q: math.hypot(q[1] - sc[0], q[2] - sc[1]), nx, ny, soft=soft)
    if not path:
        print('no path even with rip-up')
    else:
        victims = set()
        for a, c in zip(path, path[1:]):
            victims |= soft.get(c, set())
            if a[0] != c[0]:
                victims |= soft.get(('v', a[1], a[2]), set())
        items = [build.reg[k] for k in victims]
        names = sorted({v.GetNetname() for v in items})
        for v in items:
            b.Remove(v)
        emit(path, x0, y0, net, w)
        print('routed with rip-up of', len(victims), 'items on nets', names)
elif mode == 'pads':
    (r1, p1), (r2, p2) = sys.argv[3].split(':'), sys.argv[4].split(':')
    w = float(sys.argv[5]) if len(sys.argv) > 5 else 0.25
    pa = [p for p in b.FindFootprintByReference(r1).Pads() if p.GetNumber() == p1][0]
    pb = [p for p in b.FindFootprintByReference(r2).Pads() if p.GetNumber() == p2][0]
    ax, ay, bx, by = mm(pa.GetPosition().x), mm(pa.GetPosition().y), mm(pb.GetPosition().x), mm(pb.GetPosition().y)
    x0, y0 = min(ax, bx) - 6, min(ay, by) - 6
    blk, viaok, nx, ny = build(pa.GetNetCode(), x0, y0, max(ax, bx) + 6, max(ay, by) + 6, w)
    sa, sb = cell(ax, ay, x0, y0), cell(bx, by, x0, y0)
    La = [i for i, L in enumerate(LAYERS) if pa.IsOnLayer(L)]; Lb = [i for i, L in enumerate(LAYERS) if pb.IsOnLayer(L)]
    for L in La: blk[(L,) + sa] = False
    for L in Lb: blk[(L,) + sb] = False
    path = astar(blk, viaok, [(L,) + sa for L in La], lambda c: (c[1], c[2]) == sb and c[0] in Lb,
                 lambda c: math.hypot(c[1] - sb[0], c[2] - sb[1]), nx, ny)
    if path:
        emit(path, x0, y0, pa.GetNet(), w); print('routed', r1, p1, '->', r2, p2, len(path), 'cells')
    else:
        print('no path')
pcbnew.SaveBoard(sys.argv[1], b)
