# Build kh910.pretty footprints and the .kicad_pcb from the tracer geometry. Run with KiCad's python.
import json, sys, os, math, uuid
import pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import footprints

GEOM, OUTDIR, PROJ = sys.argv[1], sys.argv[2], sys.argv[3]
g = json.load(open(GEOM)); netmap = json.load(open(os.path.join(OUTDIR, 'netmap.json')))
symmap = json.load(open(os.path.join(OUTDIR, 'symmap.json')))
pads = g['pads']; labels = g['labels']
LIB = os.path.join(OUTDIR, 'kh910.pretty'); os.makedirs(LIB, exist_ok=True)
PINMAP = {'VR301': {1: '1', 2: '3', 3: '2'}}

# ------------------------------------------------------------- net of every pad (incl. vias)
par = {k: k for k in pads}
def f(a):
    while par[a] != a: par[a] = par[par[a]]; a = par[a]
    return a
for l in g['links']: par[f(l['a'])] = f(l['b'])
padpin = {}
for pt in g['parts']:
    for i, pid in enumerate(pt['pins']): padpin[pid] = (pt['ref'], PINMAP.get(pt['ref'], {}).get(i + 1, str(i + 1)))
HAR = {**{c: ('J1', str(i + 1)) for i, c in enumerate('ABCDEFGHI')}, **{c: ('J2', str(i + 1)) for i, c in enumerate('JKLMNOP')}}
for k, lab in labels.items():
    if lab.startswith('pad ') and lab[4] in HAR: padpin[k] = HAR[lab[4]]
groupnet = {}
for k, rp in padpin.items():
    n = netmap.get('%s.%s' % rp)
    if n: groupnet[f(k)] = n
padnet = {k: groupnet.get(f(k), '') for k in pads}

# ------------------------------------------------------------- footprint geometry
def procrustes(meas, ideal):
    """rigid fit of ideal points onto measured ones; returns transformed ideal points"""
    n = len(meas); mx = sum(p[0] for p in meas) / n; my = sum(p[1] for p in meas) / n
    ix = sum(p[0] for p in ideal) / n; iy = sum(p[1] for p in ideal) / n
    sxx = sum((a[0] - ix) * (b[0] - mx) + (a[1] - iy) * (b[1] - my) for a, b in zip(ideal, meas))
    sxy = sum((a[0] - ix) * (b[1] - my) - (a[1] - iy) * (b[0] - mx) for a, b in zip(ideal, meas))
    th = math.atan2(sxy, sxx); c, s = math.cos(th), math.sin(th)
    return [(mx + c * (a[0] - ix) - s * (a[1] - iy), my + s * (a[0] - ix) + c * (a[1] - iy)) for a in ideal], th
PADSPEC = {'IC': (1.5, 1.5, 0.8), 'R': (1.6, 1.6, 0.8), 'D': (1.6, 1.6, 0.8), 'VR': (1.9, 1.9, 1.0), 'PI': (1.4, 1.4, 0.8),
           'CH': (1.6, 1.6, 0.8), 'J': (2.2, 2.2, 1.1)}
parts = []   # (ref, [(padnum, x, y)], kind, angle)
for pt in g['parts']:
    ref = pt['ref']; meas = [tuple(pads[p]) for p in pt['pins']]
    ang = 0.0
    if ref.startswith('IC'):
        n = len(meas); h = n // 2
        ideal = [(0, k * 2.54) for k in range(h)] + [(7.62, (h - 1 - k) * 2.54) for k in range(h)]
        meas, ang = procrustes(meas, ideal)
    if ref in footprints.CUSTOM:
        def clus(vals):
            out = list(vals)
            for i, v in enumerate(vals):
                grp = [w for w in vals if abs(w - v) < 1.2]; out[i] = sum(grp) / len(grp)
            return out
        xs_, ys_ = clus([m[0] for m in meas]), clus([m[1] for m in meas])
        meas = list(zip(xs_, ys_))
        if ref == 'VR301': meas[2] = ((meas[0][0] + meas[1][0]) / 2, meas[2][1])
    nums = [PINMAP.get(ref, {}).get(i + 1, str(i + 1)) for i in range(len(meas))]
    kind = next(k for k in ('IC', 'VR', 'PI', 'CH', 'R', 'D') if ref.startswith(k))
    parts.append((ref, list(zip(nums, [m[0] for m in meas], [m[1] for m in meas])), kind, ang, pt['pins']))
for jref, letters in (('J1', 'ABCDEFGHI'), ('J2', 'JKLMNOP')):
    ids = [next(k for k, v in labels.items() if v.startswith('pad ' + c)) for c in letters]
    parts.append((jref, [(str(i + 1), pads[k][0], pads[k][1]) for i, k in enumerate(ids)], 'J', 0.0, ids))
padpos = {}  # tracer pad id -> final board position (mm)
MEAS = {k: tuple(v) for k, v in pads.items()}
for ref, pl, kind, ang, ids in parts:
    for (num, x, y), pid in zip(pl, ids): padpos[pid] = (x, y)

def fp_text(ref, pl, kind, ang):
    cx = sum(p[1] for p in pl) / len(pl); cy = sum(p[2] for p in pl) / len(pl)
    w, h, dr = PADSPEC[kind]
    L = [f'(footprint "{ref}" (version 20240108) (generator "kh910_build") (layer "F.Cu")',
         f'  (descr "{ref}: pad positions measured from the KH-910 right sensor board photos")',
         f'  (property "Reference" "{ref}" (at 0 {-max(abs(p[2]-cy) for p in pl)-1.6:.3f} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
         f'  (property "Value" "{ref}" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1) (thickness 0.15))))',
         '  (attr through_hole)']
    loc = [(n, x - cx, y - cy) for n, x, y in pl]
    for n, x, y in loc:
        shape = 'rect' if (n == '1' and kind in ('IC', 'J')) else 'circle'
        L.append(f'  (pad "{n}" thru_hole {shape} (at {x:.3f} {y:.3f}) (size {w} {h}) (drill {dr}) (layers "*.Cu" "*.Mask"))')
    xs = [p[1] for p in loc]; ys = [p[2] for p in loc]
    if kind == 'IC':        # body outline along the rotated rows
        c, s = math.cos(ang), math.sin(ang); hw, hh = 2.6, (max(abs(v) for v in ys) if abs(c) > 0.7 else max(abs(v) for v in xs)) + 1.3
        corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        R = lambda p: (c * p[0] - s * p[1], s * p[0] + c * p[1])
        cs = [R(p) for p in corners]
        for a, b in zip(cs, cs[1:] + cs[:1]):
            L.append(f'  (fp_line (start {a[0]:.3f} {a[1]:.3f}) (end {b[0]:.3f} {b[1]:.3f}) (stroke (width 0.15) (type solid)) (layer "F.SilkS"))')
    elif len(loc) == 2:     # two-pin part: body line between pads
        (_, x1, y1), (_, x2, y2) = loc; d = math.hypot(x2 - x1, y2 - y1)
        if d > 4.0:
            ux, uy = (x2 - x1) / d, (y2 - y1) / d; px, py = -uy * 0.9, ux * 0.9; a0, a1 = 1.4, d - 1.4
            q = [(x1 + ux * a0 + px, y1 + uy * a0 + py), (x1 + ux * a1 + px, y1 + uy * a1 + py), (x1 + ux * a1 - px, y1 + uy * a1 - py), (x1 + ux * a0 - px, y1 + uy * a0 - py)]
            for a, b in zip(q, q[1:] + q[:1]):
                L.append(f'  (fp_line (start {a[0]:.3f} {a[1]:.3f}) (end {b[0]:.3f} {b[1]:.3f}) (stroke (width 0.15) (type solid)) (layer "F.SilkS"))')
        else:               # upright part: body circle on pad 1
            L.append(f'  (fp_circle (center {x1:.3f} {y1:.3f}) (end {x1+1.25:.3f} {y1:.3f}) (stroke (width 0.15) (type solid)) (fill none) (layer "F.SilkS"))')
    else:                   # box around the pads
        m = 1.6; x0, x1_, y0, y1_ = min(xs) - m, max(xs) + m, min(ys) - m, max(ys) + m
        L.append(f'  (fp_rect (start {x0:.3f} {y0:.3f}) (end {x1_:.3f} {y1_:.3f}) (stroke (width 0.15) (type solid)) (fill none) (layer "F.SilkS"))')
    L.append(')')
    return '\n'.join(L) + '\n', (cx, cy)
centres = {}
for f_ in os.listdir(LIB):
    if f_.endswith('.kicad_mod'): os.remove(os.path.join(LIB, f_))
for ref, pl, kind, ang, ids in parts:
    txt, c = fp_text(ref, pl, kind, ang); centres[ref] = c
    if footprints.choose(ref, [(x, y) for _, x, y in pl])[0] == 'kh910':
        open(os.path.join(LIB, ref + '.kicad_mod'), 'w').write(txt)
JPFP = '''(footprint "SolderJumper_open" (version 20240108) (generator "kh910_build") (layer "B.Cu")
  (descr "open solder jumper between two neighbouring THT pads (solder side)")
  (property "Reference" "JP" (at 0 -1.6 0) (layer "B.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12)) (justify mirror)))
  (property "Value" "open" (at 0 1.6 0) (layer "B.Fab") (hide yes) (effects (font (size 0.8 0.8) (thickness 0.12)) (justify mirror)))
  (attr smd)
  (pad "1" smd rect (at -0.65 0) (size 1 1.4) (layers "B.Cu" "B.Mask"))
  (pad "2" smd rect (at 0.65 0) (size 1 1.4) (layers "B.Cu" "B.Mask"))
)
'''
open(os.path.join(LIB, 'SolderJumper_open.kicad_mod'), 'w').write(JPFP)

# ------------------------------------------------------------- board
board = pcbnew.CreateEmptyBoard()
MM = pcbnew.FromMM
V = lambda p: pcbnew.VECTOR2I(MM(p[0]), MM(p[1]))
nets = {}
def net(name):
    if not name: return None
    if name not in nets:
        ni = pcbnew.NETINFO_ITEM(board, name); board.Add(ni); nets[name] = ni
    return nets[name]
for n in sorted(set(netmap.values())): net(n)
# outline
ol = g['outline']
for a, b in zip(ol, ol[1:] + ol[:1]):
    sh = pcbnew.PCB_SHAPE(board); sh.SetShape(pcbnew.SHAPE_T_SEGMENT); sh.SetStart(V(a)); sh.SetEnd(V(b))
    sh.SetLayer(pcbnew.Edge_Cuts); sh.SetWidth(MM(0.1)); board.Add(sh)
# footprints
class _IO:
    @staticmethod
    def FootprintLoad(lib, name): return pcbnew.FootprintLoad(lib, name)
io = _IO()
FPCHOICE = {}
for ref, pl, kind, ang, ids in parts:
    libn, fpn = footprints.choose(ref, [(x, y) for _, x, y in pl]); FPCHOICE[ref] = f'{libn}:{fpn}'
    if libn == 'kh910':
        fp = io.FootprintLoad(LIB, ref); fp.SetPosition(V(centres[ref]))
    else:
        fp = io.FootprintLoad(os.path.join(footprints.LIBDIR, libn + '.pretty'), fpn)
        meas = {n: (x, y) for n, x, y in pl}; best = None
        for rot in (0, 90, 180, 270):
            fp.SetOrientationDegrees(rot); fp.SetPosition(V((0, 0)))
            loc = {pd.GetNumber(): (pcbnew.ToMM(pd.GetPosition().x), pcbnew.ToMM(pd.GetPosition().y)) for pd in fp.Pads()}
            ks = [n for n in meas if n in loc]
            off = (sum(meas[n][0] - loc[n][0] for n in ks) / len(ks), sum(meas[n][1] - loc[n][1] for n in ks) / len(ks))
            err = sum(math.dist(meas[n], (loc[n][0] + off[0], loc[n][1] + off[1])) for n in ks)
            if best is None or err < best[0]: best = (err, rot, off)
        fp.SetOrientationDegrees(best[1]); fp.SetPosition(V(best[2]))
    fp.SetReference(ref); fp.SetFPID(pcbnew.LIB_ID(libn, fpn)); fp.SetValue(symmap['values'].get(ref, ref))
    # tracks must end on the final pad positions
    pnum = {pd.GetNumber(): (pcbnew.ToMM(pd.GetPosition().x), pcbnew.ToMM(pd.GetPosition().y)) for pd in fp.Pads()}
    for (n, _, _), pid in zip(pl, ids):
        if n in pnum: padpos[pid] = pnum[n]
    if ref in symmap['sym']: fp.SetPath(pcbnew.KIID_PATH('/' + symmap['sym'][ref]))
    board.Add(fp)
    for pad in fp.Pads():
        n = netmap.get(f'{ref}.{pad.GetNumber()}')
        if n: pad.SetNet(net(n))
for j in g['jumpers']:
    a, b = padpos[j['a']], padpos[j['b']]
    fp = io.FootprintLoad(LIB, 'SolderJumper_open'); fp.SetReference(j['ref']); fp.SetFPID(pcbnew.LIB_ID('kh910', 'SolderJumper_open')); fp.SetValue('open')
    if j['ref'] in symmap['sym']: fp.SetPath(pcbnew.KIID_PATH('/' + symmap['sym'][j['ref']]))
    fp.SetPosition(V(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)))
    fp.SetOrientationDegrees(-math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])))
    board.Add(fp)
    for pad in fp.Pads():
        n = netmap.get(f"{j['ref']}.{pad.GetNumber()}")
        if n: pad.SetNet(net(n))
    # short tracks from the jumper pads to the resistor pads
    for pad in fp.Pads():
        tgt = a if pad.GetNumber() == '1' else b
        t = pcbnew.PCB_TRACK(board); t.SetStart(pad.GetPosition()); t.SetEnd(V(tgt)); t.SetWidth(MM(0.6)); t.SetLayer(pcbnew.B_Cu)
        if pad.GetNet(): t.SetNet(pad.GetNet())
        board.Add(t)
# vias
inpart = set(padpos)
for k, p in pads.items():
    if k in inpart: continue
    v = pcbnew.PCB_VIA(board); v.SetPosition(V(p)); v.SetDrill(MM(0.7)); v.SetWidth(MM(1.4))
    if padnet[k]: v.SetNet(net(padnet[k]))
    board.Add(v); padpos[k] = tuple(p)

# ------------------------------------------------------------- tracks with rounded corners
def width(n): return 0.8 if n in ('+5V', 'GND') else 0.45
def add_seg(a, b, lay, ni, w):
    if math.dist(a, b) < 1e-3: return
    t = pcbnew.PCB_TRACK(board); t.SetStart(V(a)); t.SetEnd(V(b)); t.SetWidth(MM(w)); t.SetLayer(lay)
    if ni: t.SetNet(ni)
    board.Add(t)
def add_arc(a, m, b, lay, ni, w):
    t = pcbnew.PCB_ARC(board); t.SetStart(V(a)); t.SetMid(V(m)); t.SetEnd(V(b)); t.SetWidth(MM(w)); t.SetLayer(lay)
    if ni: t.SetNet(ni)
    board.Add(t)
# ---- obstacle model (other-net copper), used to keep clearance
CLR = 0.27                                    # target clearance (a little above the 0.25 mm rule)
padrad = {}
for fp in board.GetFootprints():
    for pd in fp.Pads():
        q = (pcbnew.ToMM(pd.GetPosition().x), pcbnew.ToMM(pd.GetPosition().y))
        for pid, pp in padpos.items():
            if math.dist(pp, q) < 0.05: padrad[pid] = max(pcbnew.ToMM(pd.GetSize(pcbnew.F_Cu).x), pcbnew.ToMM(pd.GetSize(pcbnew.F_Cu).y)) / 2
for k in pads:
    if k not in padrad: padrad[k] = 0.7     # vias
def seg_dist(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]; L2 = vx * vx + vy * vy
    t = 0 if L2 == 0 else max(0, min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2))
    return math.hypot(a[0] + t * vx - p[0], a[1] + t * vy - p[1])
def seg_seg(a, b, c, d):
    return min(seg_dist(a, c, d), seg_dist(b, c, d), seg_dist(c, a, b), seg_dist(d, a, b)) if not _cross(a, b, c, d) else 0.0
def _cross(a, b, c, d):
    def o(p, q, r): return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return (o(a, b, c) * o(a, b, d) < 0) and (o(c, d, a) * o(c, d, b) < 0)
LINKS = []
def drag(pts_mid, a, b):
    """move the drawn corners along with their end pads (pads moved onto library footprints); effect fades over 5 mm"""
    da = (padpos[a][0] - MEAS[a][0], padpos[a][1] - MEAS[a][1]); db = (padpos[b][0] - MEAS[b][0], padpos[b][1] - MEAS[b][1])
    full = [MEAS[a]] + pts_mid + [MEAS[b]]
    cum = [0.0]
    for i in range(1, len(full)): cum.append(cum[-1] + math.dist(full[i - 1], full[i]))
    for end, dd, sgn in ((a, da, 1), (b, db, -1)):
        if math.hypot(*dd) > 0.3:
            P0 = full[0] if sgn == 1 else full[-1]; P1 = full[1] if sgn == 1 else full[-2]; L_ = math.dist(P0, P1)
            if L_ > 4.0:
                q = (P0[0] + (P1[0] - P0[0]) * 2.5 / L_, P0[1] + (P1[1] - P0[1]) * 2.5 / L_)
                if sgn == 1: pts_mid = [q] + pts_mid; full = [full[0], q] + full[1:]
                else: pts_mid = pts_mid + [q]; full = full[:-1] + [q, full[-1]]
    cum = [0.0]
    for i in range(1, len(full)): cum.append(cum[-1] + math.dist(full[i - 1], full[i]))
    out = []
    for i, q in enumerate(pts_mid, start=1):
        wa = max(0.0, 1 - cum[i] / 5.0); wb = max(0.0, 1 - (cum[-1] - cum[i]) / 5.0)
        out.append((q[0] + da[0] * wa + db[0] * wb, q[1] + da[1] * wa + db[1] * wb))
    return out
for l in g['links']:
    if not l['layer']: continue
    n = padnet.get(l['a']) or padnet.get(l['b'])
    raw = [tuple(q) for q in l['pts']]
    raw = [q for i_, q in enumerate(raw) if i_ == 0 or math.dist(q, raw[i_ - 1]) > 0.05]
    mid = raw if l.get('board_exact') else drag(raw, l['a'], l['b'])
    LINKS.append(dict(a=l['a'], b=l['b'], layer=l['layer'], net=n, w=l.get('board_width') or width(n), status=l['status'], idx=l.get('idx'), exact=bool(l.get('board_exact')),
                      pts=[padpos[l['a']]] + mid + [padpos[l['b']]]))
def violations(Lk):
    """(kind, obstacle point/segment, segment index) for other-net copper closer than allowed to link Lk"""
    out = []; hw = Lk['w'] / 2
    for k, pos in padpos.items():
        if padnet.get(k) == Lk['net'] and Lk['net']: continue
        for i in range(len(Lk['pts']) - 1):
            if seg_dist(pos, Lk['pts'][i], Lk['pts'][i + 1]) < padrad[k] + hw + CLR - 1e-6: out.append(('pad', pos, i, padrad[k]))
    for O in LINKS:
        if O is Lk or O['layer'] != Lk['layer'] or (O['net'] == Lk['net'] and Lk['net']): continue
        need = hw + O['w'] / 2 + CLR
        for i in range(len(Lk['pts']) - 1):
            for j in range(len(O['pts']) - 1):
                if seg_seg(Lk['pts'][i], Lk['pts'][i + 1], O['pts'][j], O['pts'][j + 1]) < need - 1e-6: out.append(('trk', O, i, j))
    return out

# ---- 1. inferred (unsure) links that collide: maze-route them around everything else
import heapq
def blocked_fn(Lk):
    hw = Lk['w'] / 2; obs_p = []; obs_s = []
    for k, pos in padpos.items():
        if padnet.get(k) == Lk['net'] and Lk['net']: continue
        obs_p.append((pos, padrad[k] + hw + CLR))
    for O in LINKS:
        if O is Lk or O['layer'] != Lk['layer'] or (O['net'] == Lk['net'] and Lk['net']): continue
        for j in range(len(O['pts']) - 1): obs_s.append((O['pts'][j], O['pts'][j + 1], O['w'] / 2 + hw + CLR))
    def bad(p):
        if not (0.6 < p[0] < BW - 0.6 and 0.6 < p[1] < BH - 0.6): return True
        for c, r in obs_p:
            if abs(c[0] - p[0]) < r and abs(c[1] - p[1]) < r and math.hypot(c[0] - p[0], c[1] - p[1]) < r: return True
        for a_, b_, r in obs_s:
            if seg_dist(p, a_, b_) < r: return True
        return False
    def seg_ok(a_, b_):
        n = max(2, int(math.dist(a_, b_) / 0.1))
        return all(not bad((a_[0] + (b_[0] - a_[0]) * t / n, a_[1] + (b_[1] - a_[1]) * t / n)) for t in range(1, n))
    return bad, seg_ok
xs = [q[0] for q in g['outline']]; ys = [q[1] for q in g['outline']]; BW, BH = max(xs), max(ys)
def route(Lk, res=0.2, hug=None):
    bad, seg_ok = blocked_fn(Lk)
    A_, B_ = Lk['pts'][0], Lk['pts'][-1]
    to_g = lambda p: (round(p[0] / res), round(p[1] / res)); to_m = lambda c: (c[0] * res, c[1] * res)
    sa, sb = to_g(A_), to_g(B_)
    if hug:
        hx = [to_g(q)[0] for q in hug]; hy = [to_g(q)[1] for q in hug]; m_ = int(2.4 / res)
        lo = (min(hx) - m_, min(hy) - m_); hi = (max(hx) + m_, max(hy) + m_)
    else:
        lo = (min(sa[0], sb[0]) - 40, min(sa[1], sb[1]) - 40); hi = (max(sa[0], sb[0]) + 40, max(sa[1], sb[1]) + 40)
    near_end = lambda c: math.dist(to_m(c), A_) < 0.3 or math.dist(to_m(c), B_) < 0.3
    cache = {}
    def free(c):
        if c not in cache: cache[c] = near_end(c) or not bad(to_m(c))
        return cache[c]
    D8 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    pq = [(0, 0, sa, None)]; came = {}; cost = {(sa, None): 0}
    while pq:
        f, gc, c, d = heapq.heappop(pq)
        if c == sb:
            path = [c]; key = (c, d)
            while key in came: key = came[key]; path.append(key[0])
            path = [to_m(q) for q in reversed(path)]; path[0] = A_; path[-1] = B_
            # straighten: keep only corners needed for clearance
            out = [path[0]]; i = 0
            while i < len(path) - 1:
                j = len(path) - 1
                while j > i + 1 and not (seg_ok(path[i], path[j]) and not violations(dict(Lk, pts=[path[i], path[j]]))): j -= 1
                out.append(path[j]); i = j
            return out
        for dx, dy in D8:
            nc = (c[0] + dx, c[1] + dy)
            if not (lo[0] <= nc[0] <= hi[0] and lo[1] <= nc[1] <= hi[1]) or not free(nc): continue
            step = math.hypot(dx, dy) + (0.6 if d and d != (dx, dy) else 0)
            if hug: step += 6.0 * min(seg_dist(to_m(nc), hug[k], hug[k + 1]) for k in range(len(hug) - 1))
            ng = gc + step; key = (nc, (dx, dy))
            if ng < cost.get(key, 1e18):
                cost[key] = ng; came[key] = (c, d)
                heapq.heappush(pq, (ng + math.hypot(sb[0] - nc[0], sb[1] - nc[1]), ng, nc, (dx, dy)))
    return None
rerouted = []
for _pass in range(2):
    for Lk in LINKS:
        if Lk['status'] == 'proposed' and violations(Lk):
            r_ = route(Lk)
            if r_ and not [v for v in violations(dict(Lk, pts=r_))]: Lk['pts'] = r_; rerouted.append((Lk['a'], Lk['b'])); continue
            # the hidden copper's real route is unknown: join the first pad to the nearest reachable copper of the same net
            # keep the end that has no other connection (else it would be left floating)
            others = lambda e: sum(1 for O in LINKS if O is not Lk and e in (O['a'], O['b']))
            keep = Lk['a'] if others(Lk['a']) <= others(Lk['b']) else Lk['b']
            start = padpos[keep]
            # pads of the same net that are NOT already connected to 'keep' without this link
            comp = {keep}; grow = True
            while grow:
                grow = False
                for O in LINKS:
                    if O is Lk: continue
                    if (O['a'] in comp) != (O['b'] in comp): comp |= {O['a'], O['b']}; grow = True
            cands = [padpos[k] for k in padpos if padnet.get(k) == Lk['net'] and k not in comp]
            cands.sort(key=lambda q: math.dist(q, start))
            for q in cands[:15]:
                trial = dict(Lk, pts=[start, q]); r_ = route(trial)
                if r_ and not violations(dict(Lk, pts=r_)): Lk['pts'] = r_; Lk['retarget'] = True; rerouted.append((Lk['a'], 'nearest')); break
nudged = 0
# ---- 2. tracks grazing another net's pad: add one detour corner, kept only if it creates no new conflict
for Lk in LINKS:
    for _try in range(3):
        v = [x for x in violations(Lk) if x[0] == 'pad']
        if not v: break
        kind, c, i, prad = v[0]; a_, b_ = Lk['pts'][i], Lk['pts'][i + 1]
        vx, vy = b_[0] - a_[0], b_[1] - a_[1]; L2 = vx * vx + vy * vy or 1
        t = max(0.1, min(0.9, ((c[0] - a_[0]) * vx + (c[1] - a_[1]) * vy) / L2))
        q = (a_[0] + t * vx, a_[1] + t * vy); dx, dy = q[0] - c[0], q[1] - c[1]; dl = math.hypot(dx, dy)
        if dl < 1e-6: dx, dy, dl = -vy, vx, math.sqrt(L2)
        need = prad + Lk['w'] / 2 + CLR + 0.05
        before = len(violations(Lk)); old = list(Lk['pts'])
        Lk['pts'].insert(i + 1, (c[0] + dx / dl * need, c[1] + dy / dl * need))
        if len(violations(Lk)) >= before: Lk['pts'] = old; break
        nudged += 1
for _pass in range(4):
    for Lk in LINKS:
        if Lk.get('exact'): continue
        for v_ in violations(Lk)[:3]:
            if v_[0] == 'trk': kind, O, i, j = v_; need = Lk['w'] / 2 + O['w'] / 2 + CLR + 0.05; seg = (O['pts'][j], O['pts'][j + 1])
            else: kind, c0, i, prad = v_; O = Lk; need = prad + Lk['w'] / 2 + CLR + 0.05; seg = (c0, c0)
            for vi in (i, i + 1):
                if vi in (0, len(Lk['pts']) - 1): continue
                p_ = Lk['pts'][vi]; dist = seg_dist(p_, *seg)
                if dist >= need: continue
                vx, vy = seg[1][0] - seg[0][0], seg[1][1] - seg[0][1]; L2 = vx * vx + vy * vy or 1
                t = max(0, min(1, ((p_[0] - seg[0][0]) * vx + (p_[1] - seg[0][1]) * vy) / L2)); c = (seg[0][0] + t * vx, seg[0][1] + t * vy)
                dx, dy = p_[0] - c[0], p_[1] - c[1]; dl = math.hypot(dx, dy) or 1e-6
                before = len(violations(Lk)) + (len(violations(O)) if O is not Lk else 0); old = Lk['pts'][vi]
                Lk['pts'][vi] = (c[0] + dx / dl * need, c[1] + dy / dl * need)
                if len(violations(Lk)) + (len(violations(O)) if O is not Lk else 0) >= before: Lk['pts'][vi] = old
                else: nudged += 1
FIXED = {}; FIXW = {}
if os.environ.get('KH_FIX'):
    wants = [L.get('idx') for L in LINKS if violations(L) and not L.get('exact')] if os.environ['KH_FIX'] == 'auto' else [int(x) for x in os.environ['KH_FIX'].split(',')]
    print('repairing links', wants)
    for want in wants:
        Lk = next(L for L in LINKS if L.get('idx') == want)
        for v_ in violations(Lk):
            print('link', want, 'seg', v_[2], v_[0], (round(v_[1][0], 2), round(v_[1][1], 2)) if v_[0] == 'pad' else (v_[1].get('idx'), v_[1]['net']))
        if not violations(Lk): continue
        r_ = route(Lk, res=0.1, hug=list(Lk['pts']))
        if r_ is None or violations(dict(Lk, pts=r_)): r_ = route(Lk, res=0.1)
        if (r_ is None or violations(dict(Lk, pts=r_))) and Lk['w'] > 0.45:
            w0 = Lk['w']; Lk['w'] = 0.45
            r_ = route(Lk, res=0.1, hug=list(Lk['pts']))
            if r_ is None or violations(dict(Lk, pts=r_)): r_ = route(Lk, res=0.1)
            if r_ and not violations(dict(Lk, pts=r_)): FIXW[want] = 0.45
            else: Lk['w'] = w0
        if r_ and not violations(dict(Lk, pts=r_)): Lk['pts'] = r_; FIXED[want] = r_[1:-1]
        else:
            print('could not fix link', want, 'route', None if r_ is None else len(r_), [ (v[0], v[2]) for v in violations(dict(Lk, pts=r_))] if r_ else '')
            bad, _ = blocked_fn(Lk); print('   endpoint blocked?', bad(Lk['pts'][0]), bad(Lk['pts'][-1]), [tuple(round(c,2) for c in Lk['pts'][0]), tuple(round(c,2) for c in Lk['pts'][-1])])
    json.dump({'pts': FIXED, 'w': FIXW}, open(os.environ['KH_FIX_OUT'], 'w'))
# ---- 3. tracks with the largest corner radius that keeps clearance
def arc_ok(Lk, pts_arc):
    hw = Lk['w'] / 2
    for k, pos in padpos.items():
        if padnet.get(k) == Lk['net'] and Lk['net']: continue
        for p in pts_arc:
            if math.dist(p, pos) < padrad[k] + hw + CLR: return False
    for O in LINKS:
        if O is Lk or O['layer'] != Lk['layer'] or (O['net'] == Lk['net'] and Lk['net']): continue
        for p in pts_arc:
            for j in range(len(O['pts']) - 1):
                if seg_dist(p, O['pts'][j], O['pts'][j + 1]) < hw + O['w'] / 2 + CLR: return False
    return True
narc = 0
def dedupe(pts):
    out = [pts[0]]
    for q in pts[1:]:
        if math.dist(q, out[-1]) > 0.05: out.append(q)
    if len(out) == 1: out.append(pts[-1])
    out[-1] = pts[-1]
    return out
for Lk in LINKS: Lk['pts'] = dedupe(Lk['pts'])
for Lk in LINKS:
    pts = Lk['pts']; lay = pcbnew.F_Cu if Lk['layer'] == 'f' else pcbnew.B_Cu
    ni = net(Lk['net']); w = Lk['w']; cur = pts[0]
    for i in range(1, len(pts) - 1):
        A, B, C = pts[i - 1], pts[i], pts[i + 1]
        la, lc = math.dist(A, B), math.dist(B, C)
        if la < 1e-6 or lc < 1e-6: continue
        u = ((A[0] - B[0]) / la, (A[1] - B[1]) / la); v = ((C[0] - B[0]) / lc, (C[1] - B[1]) / lc)
        th = math.acos(max(-1.0, min(1.0, u[0] * v[0] + u[1] * v[1])))
        done = False
        if th < math.radians(172):
            for R_ in (2.5, 1.6, 1.0, 0.6, 0.35):
                t = min(R_ / math.tan(th / 2), 0.45 * la, 0.45 * lc); r = t * math.tan(th / 2)
                T1 = (B[0] + u[0] * t, B[1] + u[1] * t); T2 = (B[0] + v[0] * t, B[1] + v[1] * t)
                bx, by = u[0] + v[0], u[1] + v[1]; bl = math.hypot(bx, by); bx, by = bx / bl, by / bl
                d = r / math.sin(th / 2); O_ = (B[0] + bx * d, B[1] + by * d); M = (O_[0] - bx * r, O_[1] - by * r)
                a0 = math.atan2(T1[1] - O_[1], T1[0] - O_[0]); a1 = math.atan2(T2[1] - O_[1], T2[0] - O_[0])
                da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
                samples = [(O_[0] + r * math.cos(a0 + da * k / 8), O_[1] + r * math.sin(a0 + da * k / 8)) for k in range(9)]
                if arc_ok(Lk, samples):
                    add_seg(cur, T1, lay, ni, w); add_arc(T1, M, T2, lay, ni, w); narc += 1; cur = T2; done = True; break
        if not done: add_seg(cur, B, lay, ni, w); cur = B
    add_seg(cur, pts[-1], lay, ni, w)
remaining = sum(1 for Lk in LINKS if violations(Lk))
if os.environ.get('KH_DEBUG'):
    json.dump(dict(links=[dict(a=L['a'], b=L['b'], layer=L['layer'], net=L['net'], w=L['w'], status=L['status'], pts=L['pts']) for L in LINKS],
                   pads={k: [padpos[k][0], padpos[k][1], padrad.get(k, 0.7), padnet.get(k, '')] for k in padpos}), open(os.environ['KH_DEBUG'], 'w'))
print('rerouted', len(rerouted), 'nudges', nudged, 'links still too close', remaining)

# texts
for txt, pos, lay in (('BP-111025-7  (KH-910 right sensor, reconstruction)', (46, 44.2), pcbnew.F_SilkS),):
    tx = pcbnew.PCB_TEXT(board); tx.SetText(txt); tx.SetPosition(V(pos)); tx.SetLayer(lay)
    tx.SetTextSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0))); tx.SetTextThickness(MM(0.15)); board.Add(tx)
path = os.path.join(OUTDIR, PROJ + '.kicad_pcb')
board.Save(path)
print('footprints', len(parts) + len(g['jumpers']), 'tracks', sum(1 for _ in board.GetTracks()), 'arcs', narc, 'nets', len(nets))
