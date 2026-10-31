"""stretch.py IN OUT DY STATIC [--keep REF,REF] [--move-point X,Y ...]  -- grow a board along y by moving
everything outside a static region by DY (mm, + = down), stretching the tracks that cross its boundary.
Plain-text edit of the .kicad_pcb (runs on the host); zones are emptied: refill afterwards.

  STATIC   union of rectangles 'x0,y0,x1,y1;x0,y0,x1,y1' (board mm) that stay in place
  --keep   footprints that stay in place wherever they are (others move with their anchor)
  --move-point X,Y   an Edge.Cuts point inside STATIC that moves anyway (e.g. a cut-out corner)

Footprint-level zones (keep-outs) move with their footprint; board zones keep their outline except
points beyond the far edge (y > max of STATIC for DY > 0), which move so the pour still covers the board.
A track crossing a horizontal side of the boundary gets a vertical extension of DY (angles kept); one
crossing a vertical side cannot be stretched and is deleted (listed): reroute it (route/maze.py fixdrc)
and clean up with pcb/prune.py. Then: refill, DRC, check.sh.

  # ayab-sr-esp32: keep J3/U5/S1 and the top band, move the rest 6 mm down
  stretch.py in.kicad_pcb out.kicad_pcb 6 '0,0,122.6,53;0,0,300,38.6' --keep J3,U5,S1 \\
      --move-point 158.9,32.7 --move-point 164.5,32.7
"""
import argparse, re, sys, uuid

ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('dst'); ap.add_argument('dy', type=float); ap.add_argument('static')
ap.add_argument('--keep', default=''); ap.add_argument('--move-point', action='append', default=[])
A = ap.parse_args()
DY = A.dy
RECTS = [tuple(map(float, r.split(','))) for r in A.static.split(';') if r.strip()]
KEEP = set(filter(None, A.keep.split(',')))
MOVEPTS = [tuple(map(float, p.split(','))) for p in A.move_point]
FAR = max(r[3] for r in RECTS)


def static(x, y):
    return any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in RECTS)


def f(v):
    return ('%.6f' % v).rstrip('0').rstrip('.')


def sh(m):
    return '(%s %s %s' % (m.group(1), m.group(2), f(float(m.group(3)) + DY))


s = open(A.src).read()
head_end = s.index('\n\t(')
items, buf, d = [], '', 0
for line in s[head_end + 1:s.rindex(')')].split('\n'):
    buf += line + '\n'
    d += line.count('(') - line.count(')')
    if d == 0 and buf.strip():
        items.append(buf); buf = ''
assert buf.strip() == '', 'unbalanced item: ' + buf[:200]

res, nvert, deleted = [], 0, []
pt = r'\((start|end|mid|at|xy|center) ([-\d.]+) ([-\d.]+)'
for it in items:
    kind = re.match(r'\t\((\w+)', it).group(1)
    if kind == 'footprint':
        ref = re.search(r'\(property "Reference" "([^"]+)"', it).group(1)
        x, y = map(float, re.search(r'^\t\t\(at ([-\d.]+) ([-\d.]+)', it, re.M).groups())
        if ref in KEEP or (not KEEP and static(x, y)):
            res.append(it); continue
        it = re.sub(r'^(\t\t)\(at ([-\d.]+) ([-\d.]+)', lambda m: '%s(at %s %s' % (m.group(1), m.group(2), f(float(m.group(3)) + DY)), it, count=1, flags=re.M)
        it = re.sub(r'\(zone\n.*?\n\t\t\)\n', lambda z: re.sub(r'\((xy) ([-\d.]+) ([-\d.]+)', sh, z.group(0)), it, flags=re.S)
        res.append(it); continue
    if kind == 'via':
        x, y = map(float, re.search(r'\(at ([-\d.]+) ([-\d.]+)', it).groups())
        res.append(it if static(x, y) else re.sub(r'\((at) ([-\d.]+) ([-\d.]+)', sh, it, count=1)); continue
    if kind in ('segment', 'arc'):
        a = list(map(float, re.search(r'\(start ([-\d.]+) ([-\d.]+)', it).groups()))
        e = list(map(float, re.search(r'\(end ([-\d.]+) ([-\d.]+)', it).groups()))
        sa, se = static(*a), static(*e)
        if sa and se:
            res.append(it); continue
        if not sa and not se:
            res.append(re.sub(r'\((start|end|mid) ([-\d.]+) ([-\d.]+)', sh, it)); continue
        net = re.search(r'\(net "([^"]*)"', it).group(1)
        if kind == 'arc':
            deleted.append((net, a, e)); continue
        if not sa:
            a, e = e, a
        lo, hi = 0.0, 1.0
        for _ in range(60):
            t = (lo + hi) / 2
            if static(a[0] + (e[0] - a[0]) * t, a[1] + (e[1] - a[1]) * t): lo = t
            else: hi = t
        p = (a[0] + (e[0] - a[0]) * lo, a[1] + (e[1] - a[1]) * lo)
        # left the static region through a horizontal side when the point just outside is straight below/above
        horiz = static(p[0], p[1]) and not static(p[0], p[1] + (1e-4 if DY > 0 else -1e-4))
        if not horiz:
            deleted.append((net, a, e)); continue
        u0 = re.search(r'\(uuid "([^"]+)"', it).group(1)
        def seg(p1, p2, n):
            t = re.sub(r'\(start [-\d.]+ [-\d.]+\)', '(start %s %s)' % (f(p1[0]), f(p1[1])), it, count=1)
            t = re.sub(r'\(end [-\d.]+ [-\d.]+\)', '(end %s %s)' % (f(p2[0]), f(p2[1])), t, count=1)
            return re.sub(r'\(uuid "[^"]+"\)', '(uuid "%s")' % uuid.uuid5(uuid.NAMESPACE_URL, u0 + n), t, count=1)
        res += [seg(a, p, 'a'), seg(p, (p[0], p[1] + DY), 'v'), seg((p[0], p[1] + DY), (e[0], e[1] + DY), 'b')]
        nvert += 1; continue
    if kind.startswith('gr_') or kind in ('dimension', 'image', 'group'):
        lay = (re.search(r'\(layer "([^"]+)"', it) or [None, ''])[1]
        if lay == 'Edge.Cuts':
            def mv(m):
                x, y = float(m.group(2)), float(m.group(3))
                keep = static(x, y) and not any(abs(x - mx) < 0.01 and abs(y - my) < 0.01 for mx, my in MOVEPTS)
                return m.group(0) if keep else sh(m)
            res.append(re.sub(pt, mv, it)); continue
        xs = [(float(a), float(b)) for _, a, b in re.findall(pt, it)]
        res.append(it if lay.endswith('.User') or all(static(*q) for q in xs) else re.sub(pt, sh, it)); continue
    if kind == 'zone':
        it = re.sub(r'\n\t\t\(filled_polygon\n.*?\n\t\t\)', '', it, flags=re.S)
        it = re.sub(r'\((xy) ([-\d.]+) ([-\d.]+)', lambda m: sh(m) if (float(m.group(3)) > FAR) == (DY > 0) else m.group(0), it)
        res.append(it); continue
    res.append(it)
open(A.dst, 'w').write(s[:head_end + 1] + ''.join(res) + ')\n')
print('vertical extensions', nvert, file=sys.stderr)
for net, a, e in deleted:
    print('deleted (crosses a vertical side): %s %s -> %s' % (net, a, e), file=sys.stderr)
