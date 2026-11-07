"""octo.py BOARD [--fix] [--json OUT]  -- track geometry against the 0/45/90-degree style (plain text, host).
Reports the share of track length at multiples of 45 degrees, the off-45 segments (with whether an end
lies on a pad, i.e. an angle the pad position may force) and the collinear joints. --fix merges collinear
pieces of one net, layer and width that meet end to end with nothing else at the joint (no via, no third
track end, no pad), rewriting the file in place; it never moves copper, so DRC cannot get worse."""
import json, math, re, sys
from collections import defaultdict

P = sys.argv[1]; FIX = '--fix' in sys.argv
s = open(P).read()
SEG = re.compile(r'\n\t\(segment\n(.*?)\n\t\)', re.S)
segs = []
for m in SEG.finditer(s):
    b = m.group(1)
    a = tuple(map(float, re.search(r'\(start ([-\d.]+) ([-\d.]+)\)', b).groups()))
    e = tuple(map(float, re.search(r'\(end ([-\d.]+) ([-\d.]+)\)', b).groups()))
    segs.append(dict(span=m.span(), a=a, e=e, w=float(re.search(r'\(width ([\d.]+)', b).group(1)),
                     layer=re.search(r'\(layer "([^"]+)"', b).group(1), net=re.search(r'\(net "([^"]*)"', b).group(1),
                     body=b))
vias = [tuple(map(float, re.search(r'\(at ([-\d.]+) ([-\d.]+)', m.group(1)).groups()))
        for m in re.finditer(r'\n\t\(via\n(.*?)\n\t\)', s, re.S)]
# pad centres in board coordinates (footprint at + rotated pad at), with a rough half-size for "on pad"
pads = []
for m in re.finditer(r'\n\t\(footprint "[^"]*"\n(.*?)\n\t\)', s, re.S):
    b = m.group(1)
    fx, fy, *fr = map(float, re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)( [-\d.]+)?\)', b).group(0).split('(at ')[1].rstrip(')').split())
    ang = math.radians(fr[0]) if fr else 0.0
    for pm in re.finditer(r'\(pad "[^"]*" \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+)[^)]*\)\s*\(size ([\d.]+) ([\d.]+)\)', b):
        px, py, sx, sy = map(float, pm.groups())
        X = fx + px * math.cos(ang) + py * math.sin(ang); Y = fy - px * math.sin(ang) + py * math.cos(ang)
        pads.append((X, Y, max(sx, sy) / 2))
def on_pad(p):
    return any(math.hypot(p[0] - x, p[1] - y) <= r + 0.05 for x, y, r in pads)
def angle(sg):
    dx, dy = sg['e'][0] - sg['a'][0], sg['e'][1] - sg['a'][1]
    return math.degrees(math.atan2(dy, dx)) % 180
def off45(sg, tol=0.5):
    a = angle(sg); d = min(a % 45, 45 - a % 45)
    return d > tol
L = defaultdict(float); off = []
for sg in segs:
    l = math.dist(sg['a'], sg['e'])
    if l < 1e-6: continue
    if off45(sg):
        L['off'] += l
        off.append(dict(net=sg['net'], layer=sg['layer'], a=sg['a'], e=sg['e'], len=round(l, 3), angle=round(angle(sg), 1),
                        pad_end=on_pad(sg['a']) or on_pad(sg['e'])))
    else:
        L['45x'] += l
tot = L['45x'] + L['off']
off_free = [o for o in off if not o['pad_end']]
rep = dict(segments=len(segs), length_mm=round(tot, 1), share_45x=round(L['45x'] / tot, 4) if tot else 1,
           off45_segments=len(off), off45_len_mm=round(L['off'], 1), off45_at_pad=len(off) - len(off_free),
           off45_free=len(off_free))
# collinear joints: two pieces of one net/layer/width meeting end to end, collinear, nothing else there
def key(p): return (round(p[0], 4), round(p[1], 4))
ends = defaultdict(list)
for i, sg in enumerate(segs):
    ends[(key(sg['a']), sg['layer'])].append((i, 'a')); ends[(key(sg['e']), sg['layer'])].append((i, 'e'))
vset = {key(v) for v in vias}
merges = []
for (pt, layer), lst in ends.items():
    if len(lst) != 2 or pt in vset: continue
    (i, ei), (j, ej) = lst
    A, B = segs[i], segs[j]
    if A['net'] != B['net'] or abs(A['w'] - B['w']) > 1e-6 or on_pad(pt): continue
    oa = A['e'] if ei == 'a' else A['a']; ob = B['e'] if ej == 'a' else B['a']
    cross = (pt[0] - oa[0]) * (ob[1] - pt[1]) - (pt[1] - oa[1]) * (ob[0] - pt[0])
    if abs(cross) < 1e-6 and ((pt[0] - oa[0]) * (ob[0] - pt[0]) + (pt[1] - oa[1]) * (ob[1] - pt[1])) > 0:
        merges.append((i, j, oa, ob))
rep['collinear_joints'] = len(merges)
if FIX and merges:
    # merge chains: union-find over the joints, then one segment per chain from its two free ends
    parent = list(range(len(segs)))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i, j, _, _ in merges: parent[find(i)] = find(j)
    groups = defaultdict(list)
    for i, j, _, _ in merges:
        groups[find(i)]
    members = defaultdict(set)
    for i, j, _, _ in merges: members[find(i)].update((i, j))
    repl = {}; drop = set()
    for r, ms in members.items():
        cnt = defaultdict(int)
        for m_ in ms:
            cnt[key(segs[m_]['a'])] += 1; cnt[key(segs[m_]['e'])] += 1
        free = [p for p, c in cnt.items() if c == 1]
        if len(free) != 2: continue
        ms = sorted(ms); keep = ms[0]
        b = segs[keep]['body']
        b = re.sub(r'\(start [-\d.]+ [-\d.]+\)', '(start %s %s)' % free[0], b, count=1)
        b = re.sub(r'\(end [-\d.]+ [-\d.]+\)', '(end %s %s)' % free[1], b, count=1)
        repl[keep] = b; drop.update(ms[1:])
    out, pos = [], 0
    for i, sg in enumerate(segs):
        st, en = sg['span']
        out.append(s[pos:st])
        if i in drop: pass
        elif i in repl: out.append('\n\t(segment\n' + repl[i] + '\n\t)')
        else: out.append(s[st:en])
        pos = en
    out.append(s[pos:]); open(P, 'w').write(''.join(out))
    rep['merged_segments_removed'] = len(drop)
if '--json' in sys.argv:
    json.dump(dict(rep, off45=off), open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1)
print(' '.join('%s=%s' % kv for kv in rep.items()))
