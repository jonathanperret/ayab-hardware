"""traces_json.py BOARD.kicad_pcb OUT.json  -- copper tracks and vias of a 2-layer board as compact JSON
for the 3D viewer (KiCad's GLB copper is 35 um thick and disappears under the soldermask):
  {"F": [[x1, y1, x2, y2, w], ...], "B": [...], "V": [[x, y, d, drill], ...]}   (board mm, true widths)
Arcs are split into chords (<= 10 deg). Plain-text parse, runs on the host."""
import json, math, re, sys

s = open(sys.argv[1]).read()
out = {'F': [], 'B': [], 'V': []}
r3 = lambda v: round(v, 3)


def num(pat, body):
    return [float(v) for v in re.search(pat, body).groups()]


for kind, body in re.findall(r'\n\t\((segment|arc|via)\n(.*?)\n\t\)', s, re.S):
    if kind == 'via':
        x, y = num(r'\(at ([-\d.]+) ([-\d.]+)', body)
        d, = num(r'\(size ([\d.]+)', body); h, = num(r'\(drill ([\d.]+)', body)
        out['V'].append([r3(x), r3(y), r3(d), r3(h)]); continue
    lay = re.search(r'\(layer "([FB])\.Cu"\)', body)
    if not lay:
        continue
    w, = num(r'\(width ([\d.]+)', body)
    a = num(r'\(start ([-\d.]+) ([-\d.]+)', body); e = num(r'\(end ([-\d.]+) ([-\d.]+)', body)
    pts = [a, e]
    if kind == 'arc':
        m = num(r'\(mid ([-\d.]+) ([-\d.]+)', body)
        (ax, ay), (mx, my), (ex, ey) = a, m, e
        dd = 2 * (ax * (my - ey) + mx * (ey - ay) + ex * (ay - my))
        if abs(dd) > 1e-9:
            cx = ((ax * ax + ay * ay) * (my - ey) + (mx * mx + my * my) * (ey - ay) + (ex * ex + ey * ey) * (ay - my)) / dd
            cy = ((ax * ax + ay * ay) * (ex - mx) + (mx * mx + my * my) * (ax - ex) + (ex * ex + ey * ey) * (mx - ax)) / dd
            R = math.hypot(ax - cx, ay - cy)
            t0, tm, t1 = (math.atan2(p[1] - cy, p[0] - cx) for p in (a, m, e))
            # sweep from t0 to t1 through tm
            def norm(t): return (t - t0) % (2 * math.pi)
            sweep = norm(t1) if norm(tm) < norm(t1) else norm(t1) - 2 * math.pi
            n = max(2, int(abs(sweep) / math.radians(10)) + 1)
            pts = [[cx + R * math.cos(t0 + sweep * i / n), cy + R * math.sin(t0 + sweep * i / n)] for i in range(n + 1)]
    for p, q in zip(pts, pts[1:]):
        out[lay.group(1)].append([r3(p[0]), r3(p[1]), r3(q[0]), r3(q[1]), r3(w)])
json.dump(out, open(sys.argv[2], 'w'), separators=(',', ':'))
print('traces: F %d, B %d, vias %d' % (len(out['F']), len(out['B']), len(out['V'])), file=sys.stderr)
