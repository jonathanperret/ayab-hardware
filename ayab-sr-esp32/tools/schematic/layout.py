"""Re-layout the schematic: move each group, redraw section frames, fix notes. Netlist untouched."""
import re, sys, uuid, json
from sx import *; from regions import sect
SRC, DST = sys.argv[1], sys.argv[2]
L = json.load(open(__file__.rsplit('/',1)[0] + '/targets.json'))
t = open(SRC).read()
G = 2.54
def rnd(v): return round(round(v / G) * G, 2)

skip = ('lib_symbols','sheet_instances','embedded_fonts','title_block','paper','version','generator','generator_version','uuid')
old_titles = ('5V Buck regulator','8V Buck regulator','Carriage connector','Current limiter','Test connector')
drop_wires = {((278.13,241.3),(278.13,246.38)), ((273.05,201.93),(273.05,200.66))}
drop_junct = {(273.05,200.66), (278.13,241.3)}
TEXT_FIX = {
 'Vsol_div = Vsol / 4': 'Vsol_div = Vsol x 10/57 (R7 47k / R8 10k)\\n  15 V -> 2.63 V',
}
# source bbox (min corner) per group, from item anchor points
pts_by = {}
spans = []
for a, b in items(t):
    s = t[a:b]; h = head(s)
    if h in skip: spans.append((a, b, None, s)); continue
    if h in ('wire', 'polyline'):
        P = [tuple(map(float, p)) for p in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', s)]
    else:
        P = [tuple(map(float, re.search(r'\((?:at|start) ([-\d.]+) ([-\d.]+)', s).groups()))]
    g = {sect(*p) for p in P}; assert len(g) == 1 and None not in g, (s[:80], g)
    g = g.pop()
    if h == 'rectangle': continue
    if h == 'text' and re.match(r'\(text "([^"]*)"', s).group(1) in old_titles: continue
    if h == 'wire' and tuple(P) in drop_wires: continue
    if h == 'junction' and P[0] in drop_junct: continue
    for p in P: pts_by.setdefault(g, []).append(p)
    spans.append((a, b, g, s))
off = {}
for g, P in pts_by.items():
    tx, ty = L['place'][g]
    off[g] = (rnd(tx - min(p[0] for p in P)), rnd(ty - min(p[1] for p in P)))

def shift(s, dx, dy):
    f = lambda m: '(%s %s %s' % (m.group(1), ('%.4f' % (float(m.group(2)) + dx)).rstrip('0').rstrip('.'),
                                ('%.4f' % (float(m.group(3)) + dy)).rstrip('0').rstrip('.'))
    return re.sub(r'\((at|xy|start|end) ([-\d.]+) ([-\d.]+)', f, s)

def fix(s, g):
    h = head(s)
    if h == 'text':
        for k, v in TEXT_FIX.items():
            if s.startswith('(text "' + k): s = s.replace(k, v, 1)
        if s.startswith('(text "Vout = 0.596'):
            s = re.sub(r'\(text "[^"]*"', lambda m: '(text "' + L['vout_note'] + '"', s, count=1)
        if s.startswith('(text "INA381A1'):
            s = re.sub(r'\(text "[^"]*"', lambda m: '(text "' + L['lim_note'] + '"', s, count=1)
    if h == 'symbol':
        ref = re.search(r'\(property "Reference" "([^"]+)"', s).group(1)
        if ref == 'Q1':
            s = re.sub(r'\n\t\t\(property "Sim\.(Device|Pins)" .*?\n\t\t\)', '', s, flags=re.S)
        if ref in ('H1', 'H2', 'H3'):
            s = re.sub(r'(\(property "Value" "MountingHole_Pad"\n\t\t\t\(at [^)]*\))', r'\1\n\t\t\t(hide yes)', s)
    return s

out = []; pos = 0
inserted = False
for a, b, g, s in spans:
    pass
# rebuild: keep text between items, replace items
res = []; last = 0
keep = {(a, b): (g, s) for a, b, g, s in spans}
for a, b in items(t):
    res.append(t[last:a]); last = b
    if (a, b) not in keep: res.append('\x00'); continue
    g, s = keep[(a, b)]
    if g: s = fix(shift(s, *off[g]), g)
    res.append(s)
res.append(t[last:])
body = ''.join(res)
body = re.sub(r'\n\t\x00', '', body)
body = body.replace('(paper "A3")', '(paper "A2")').replace('(date "2026-09-15")', '(date "%s")' % L['date'])

def rect(x0, y0, x1, y1):
    return ('\t(rectangle\n\t\t(start %g %g)\n\t\t(end %g %g)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
            '\t\t(fill\n\t\t\t(type none)\n\t\t)\n\t\t(uuid "%s")\n\t)\n') % (x0, y0, x1, y1, uuid.uuid5(uuid.NAMESPACE_URL, "ayab-sr-esp32-rect-%g-%g" % (x0, y0)))
def title(x, y, txt):
    return ('\t(text "%s"\n\t\t(exclude_from_sim no)\n\t\t(at %g %g 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 2.54 2.54)\n'
            '\t\t\t\t(thickness 0.508)\n\t\t\t\t(bold yes)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)\n') % (txt, x, y, uuid.uuid5(uuid.NAMESPACE_URL, "ayab-sr-esp32-frame-" + txt))
add = ''
for name, (x0, y0, x1, y1) in L['frames'].items():
    add += rect(x0, y0, x1, y1) + title(x0 + 2.54, y0 + 5.08, name)
i = body.index('\t(sheet_instances')
body = body[:i] + add + body[i:]
open(DST, 'w').write(body)
for g, o in sorted(off.items()): print(g, o)
