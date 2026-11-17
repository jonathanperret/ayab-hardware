# Convert the schemdraw drawing (../../schematic/draw_schematic.py) into a KiCad schematic with the same layout:
# every resistor, op-amp, diode, LED, phototransistor, wire, junction, power symbol, flag and text lands where it was drawn.
# Usage: python svg_to_kicad_sch.py <project dir> <project name> [swap.json]
#   swap.json (optional): list of references of two-pin parts whose pin numbering must be reversed (written by check_sch.py)
import sys, os, re, math, json, uuid
import matplotlib; matplotlib.use('Agg')
import schemdraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import libsym

PROJDIR, PROJ = sys.argv[1], sys.argv[2]
SWAP = set(json.load(open(sys.argv[3]))) if len(sys.argv) > 3 and os.path.exists(sys.argv[3]) else set()
SCHEMDRAW_SCRIPT = os.path.join(HERE, '..', '..', 'schematic', 'draw_schematic.py')

# ------------------------------------------------------------------ capture the drawings
SHEETS = []
_exit = schemdraw.Drawing.__exit__
def _capture(self, *a):
    SHEETS.append(self); return _exit(self, *a)
schemdraw.Drawing.__exit__ = _capture
tmp = os.path.join(PROJDIR, '.schemdraw_tmp'); os.makedirs(tmp, exist_ok=True)
_argv = sys.argv; sys.argv = ['draw', tmp]
_stdout = sys.stdout; sys.stdout = open(os.devnull, 'w')
exec(compile(open(SCHEMDRAW_SCRIPT).read(), SCHEMDRAW_SCRIPT, 'exec'), {'__name__': '__main__'})
sys.stdout = _stdout; sys.argv = _argv
for f in os.listdir(tmp): os.remove(os.path.join(tmp, f))
os.rmdir(tmp)
hall, optical, enc, power = SHEETS[:4]

K = 5.08 / 1.24                      # mm per schemdraw unit: op-amp input spacing = KiCad's 5.08 mm
GRID = 0.635
def snap(v): return round(round(v / GRID) * GRID, 4)
U = lambda: str(uuid.uuid4())
R2 = lambda v: round(v, 4)
out, libs = [], {}
UNITS = {'IC303B': ('Amplifier_Operational:LM358', 'IC303', 2), 'IC302A': ('Comparator:LM339', 'IC302', 1),
         'IC302B': ('Comparator:LM339', 'IC302', 2), 'IC302C': ('Comparator:LM339', 'IC302', 4), 'IC302D': ('Comparator:LM339', 'IC302', 3),
         'IC301B': ('Amplifier_Operational:LM324', 'IC301', 2), 'IC301C': ('Amplifier_Operational:LM324', 'IC301', 3),
         'IC301D': ('Amplifier_Operational:LM324', 'IC301', 4)}
VALUES = {'IC301': 'µPC324C', 'IC302': 'µPC339C', 'IC303': 'µPC358C'}
HAR = {'A': 'OPT_A', 'B': 'OPT_B', 'C': 'EOL_R', 'D': 'HALL_D', 'E': 'ENC_C', 'F': 'ENC_B', 'G': 'ENC_A',
       'J': 'OPT_SIG', 'N': 'HALL_N', 'P': 'HALL_P'}
GREY, BLUE, RED = '#8a8a8a', '#1f5fbf', '#d02020'
def rgb(c):
    c = {'black': '#000000'}.get(c, c or '#000000'); return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))

# ------------------------------------------------------------------ library symbols
for lid in ('Comparator:LM339', 'Amplifier_Operational:LM324', 'Amplifier_Operational:LM358', 'power:+5V', 'power:GND', 'power:PWR_FLAG',
            'Connector_Generic:Conn_01x09', 'Connector_Generic:Conn_01x07'):
    lib, name = lid.split(':'); libs[lid] = libsym.get(lib, name)
def S(v): return f'{v:.4f}'.rstrip('0').rstrip('.')
def poly(pts, fill='none', w=0.254):
    return '(polyline (pts ' + ' '.join(f'(xy {S(x)} {S(y)})' for x, y in pts) + f') (stroke (width {w}) (type default)) (fill (type {fill})))'
def pin(num, x, y, ang=0, name='~', length=0, typ='passive'):
    return (f'(pin {typ} line (at {S(x)} {S(y)} {ang}) (length {length}) (name "{name}" (effects (font (size 1.0 1.0)))) '
            f'(number "{num}" (effects (font (size 1.0 1.0)))))')
def custom(name, body, pins, ref='X', hide_names=True, extra_units=None):
    """single- or multi-unit custom symbol; body/pins in lib coordinates (y up)"""
    units = extra_units or {1: (body, pins)}
    txt = (f'(symbol "kh910:{name}" (pin_numbers (hide yes)) (pin_names (offset 0) (hide yes)) (exclude_from_sim no) (in_bom yes) (on_board yes)\n'
           f' (property "Reference" "{ref}" (at 0 2.54 0) (effects (font (size 1.27 1.27))))\n'
           f' (property "Value" "{name}" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))\n'
           f' (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
           f' (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
           f' (property "Description" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n')
    for u, (b, p) in units.items():
        txt += f' (symbol "{name}_{u}_1" {" ".join(b)} {" ".join(p)})\n'
    txt += ')'
    libs['kh910:' + name] = (txt, None)
    return 'kh910:' + name
def zigzag(L):
    """horizontal resistor of total length L (mm), pins at the ends"""
    zl = min(L * 0.7, 4.6); n = 6; x0 = -zl / 2; a = 0.75
    pts = [(-L / 2, 0), (x0, 0)] + [(x0 + zl * (i + 0.5) / n, a * (1 if i % 2 == 0 else -1)) for i in range(n)] + [(zl / 2, 0), (L / 2, 0)]
    return [poly(pts)]
def R_sym(L):
    name = f'R_{int(round(L * 100))}'
    if 'kh910:' + name not in libs: custom(name, zigzag(L), [pin('1', -L / 2, 0, 0, length=0.635), pin('2', L / 2, 0, 180, length=0.635)], 'R')
    return 'kh910:' + name
def D_sym(L):
    name = f'D_{int(round(L * 100))}'
    if 'kh910:' + name not in libs:
        h = 1.0
        b = [poly([(-L / 2, 0), (L / 2, 0)]), poly([(h, h), (h, -h), (-h, 0), (h, h)], 'outline'), poly([(-h, h), (-h, -h)])]
        custom(name, b, [pin('1', -L / 2, 0, 0, length=0.635), pin('2', L / 2, 0, 180, length=0.635)], 'D')    # pin 1 = cathode (left)
    return 'kh910:' + name
def SJ_sym(L):
    name = f'SJ_{int(round(L * 100))}'
    if 'kh910:' + name not in libs:
        b = [f'(circle (center {S(-L/2)} 0) (radius 0.45) (stroke (width 0.254) (type default)) (fill (type none)))',
             f'(circle (center {S(L/2)} 0) (radius 0.45) (stroke (width 0.254) (type default)) (fill (type none)))']
        custom(name, b, [pin('1', -L / 2, 0, 0, length=0.3175), pin('2', L / 2, 0, 180, length=0.3175)], 'JP')
    return 'kh910:' + name
TP = custom('TP2', ['(circle (center 0 0) (radius 0.45) (stroke (width 0.254) (type default)) (fill (type none)))'],
            [pin('1', 0, 0), pin('2', 0, 0)], 'CH')

# ------------------------------------------------------------------ placement helpers
SYMU = {}
_fpm = os.path.join(PROJDIR, 'fpmap.json')
FPMAP = json.load(open(_fpm)) if os.path.exists(_fpm) else {}
def emit_symbol(lib_id, ref, unit, at, ang=0, mirror=None, value=None, fields=None, hidden=False):
    x, y = at
    su = SYMU.setdefault(ref, U()) if (unit == 1 and not ref.startswith('#')) else U()
    mir = f' (mirror {mirror})' if mirror else ''
    fr, fv = fields or ((x, y - 3.2, 0), (x, y + 3.2, 0))
    hide = ' (hide yes)'
    rtxt = (f'  (property "Reference" "{ref}" (at {R2(fr[0])} {R2(fr[1])} {fr[2]}) (effects (font (size 1.27 1.27)){hide if hidden else ""}))\n'
            f'  (property "Value" "{value or ref}" (at {R2(fv[0])} {R2(fv[1])} {fv[2]}) (effects (font (size 1.27 1.27)){hide if (hidden or value is None) else ""}))\n'
            f'  (property "Footprint" "{"" if ref.startswith("#") else FPMAP.get(ref, "kh910:" + ref)}" (at {R2(x)} {R2(y)} 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            f'  (property "Datasheet" "" (at {R2(x)} {R2(y)} 0) (effects (font (size 1.27 1.27)) (hide yes)))\n')
    out.append(f'(symbol (lib_id "{lib_id}") (at {R2(x)} {R2(y)} {ang}){mir} (unit {unit}) (exclude_from_sim no) (in_bom {"no" if ref.startswith("#") else "yes"}) '
               f'(on_board {"no" if ref.startswith("#") else "yes"}) (dnp no) (uuid "{su}")\n{rtxt}'
               f'  (instances (project "{PROJ}" (path "/{ROOT}" (reference "{ref}") (unit {unit}))))\n)')
def wire(a, b):
    if abs(a[0] - b[0]) < 1e-4 and abs(a[1] - b[1]) < 1e-4: return
    out.append(f'(wire (pts (xy {R2(a[0])} {R2(a[1])}) (xy {R2(b[0])} {R2(b[1])})) (stroke (width 0) (type default)) (uuid "{U()}"))')
def gline(a, b, color, dash):
    r, g, bb = rgb(color)
    out.append(f'(polyline (pts (xy {R2(a[0])} {R2(a[1])}) (xy {R2(b[0])} {R2(b[1])})) (stroke (width 0.2) (type {"dash" if dash else "solid"}) (color {r} {g} {bb} 1)) (uuid "{U()}"))')
def junction(p): out.append(f'(junction (at {R2(p[0])} {R2(p[1])}) (diameter 0) (color 0 0 0 0) (uuid "{U()}"))')
def noconn(p): out.append(f'(no_connect (at {R2(p[0])} {R2(p[1])}) (uuid "{U()}"))')
def text(t, p, color='black', size=1.27, bold=False, halign='left', valign='center'):
    r, g, b = rgb(color); t = t.replace('"', '\\"').replace('\n', '\\n')
    j = ' (justify %s%s)' % (halign if halign != 'center' else '', '' if valign == 'center' else ' ' + valign)
    j = j if j.strip() != '(justify )' else ''
    out.append(f'(text "{t}" (exclude_from_sim no) (at {R2(p[0])} {R2(p[1])} 0) (effects (font (size {size} {size}){" bold" if bold else ""} (color {r} {g} {b} 1)){j}) (uuid "{U()}"))')
def glabel(name, p, ang):
    j = {0: 'left', 180: 'right', 90: 'left', 270: 'right'}[ang]
    out.append(f'(global_label "{name}" (shape passive) (at {R2(p[0])} {R2(p[1])} {ang}) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {j})) (uuid "{U()}"))')
pwrn = [0]
def power(net, p, flag=False):
    pwrn[0] += 1
    emit_symbol(f'power:{net}', f'#PWR{pwrn[0]:03d}' if not flag else f'#FLG{pwrn[0]:03d}', 1, p, 0, value=net if not flag else 'PWR_FLAG',
                fields=((p[0], p[1] + 3, 0), (p[0], p[1] - (3.5 if net == '+5V' else -3.5), 0)), hidden=False)
    out[-1] = re.sub(r'(\(property "Reference" "#[^"]*" .*?\(effects \(font \(size 1.27 1.27\)\))', r'\1 (hide yes)', out[-1], count=1)
def rot(lx, ly, ang):
    a = math.radians(ang); return lx * math.cos(a) - ly * math.sin(a), lx * math.sin(a) + ly * math.cos(a)

# ------------------------------------------------------------------ convert one drawing
pi_led = [('PI1', 1, '4', '6'), ('PI1', 3, '3', '5'), ('PI2', 1, '4', '3')]
pi_q = [('PI1', 2, '8', '2'), ('PI1', 4, '8', '1'), ('PI2', 2, '1', '2')]
def convert(d, ox, oy, sheet):
    M = lambda p: (snap(ox + float(p[0]) * K), snap(oy - float(p[1]) * K))
    MT = lambda p: (ox + float(p[0]) * K, oy - float(p[1]) * K)
    els = list(d.elements)
    labels = [(e, e._userlabels[0].label if e._userlabels else '') for e in els if type(e).__name__ == 'Label']
    def near_label(p, maxd=3.0, pred=lambda t: True):
        best = None
        for e, t in labels:
            q = e.absanchors['xy']; dd = math.hypot(q[0] - p[0], q[1] - p[1])
            if dd < maxd and pred(t) and (best is None or dd < best[0]): best = (dd, e, t)
        return best
    consumed = set()
    leds = [e for e in els if type(e).__name__ == 'LED']; qs = [e for e in els if type(e).__name__ == 'NpnPhoto']
    opdots = [e for e in els if type(e).__name__ == 'Dot' and e.params.get('open')]
    jp_pairs = []
    for e in opdots:
        if id(e) in consumed: continue
        p = e.absanchors['center']
        nl = near_label(p, 1.4, lambda t: t.startswith('JP'))
        if nl:
            mate = min((o for o in opdots if o is not e and id(o) not in consumed and abs(o.absanchors['center'][1] - p[1]) < 0.01),
                       key=lambda o: abs(o.absanchors['center'][0] - p[0]), default=None)
            if mate is not None and abs(mate.absanchors['center'][0] - p[0]) < 1.5:
                a, b = sorted([e, mate], key=lambda o: o.absanchors['center'][0])
                jp_pairs.append((nl[2], a, b, nl[1])); consumed |= {id(a), id(b), id(nl[1])}
    for e in els:
        tn = type(e).__name__; A = e.absanchors; col = e.params.get('color') or 'black'; ls = e.params.get('ls') or '-'
        lab = e._userlabels[0].label if e._userlabels else ''
        if id(e) in consumed: continue
        if tn == 'Line':
            a, b = M(A['start']), M(A['end'])
            if ls in ('--', ':'): gline(a, b, col, True)
            else: wire(a, b)
        elif tn.startswith('Resistor'):
            a, b = M(A['start']), M(A['end']); Lfull = math.dist(a, b)
            ang = round(math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0]))) % 360
            c = (round((a[0] + b[0]) / 2, 5), round((a[1] + b[1]) / 2, 5))
            L = min(5.08, round(Lfull / 1.27) * 1.27 if Lfull >= 1.27 else Lfull)
            ux, uy = (b[0] - a[0]) / Lfull, (b[1] - a[1]) / Lfull
            p1 = (round(c[0] - ux * L / 2, 4), round(c[1] - uy * L / 2, 4)); p2 = (round(c[0] + ux * L / 2, 4), round(c[1] + uy * L / 2, 4))
            wire(a, p1); wire(p2, b)
            if lab.split()[0] in SWAP: ang = (ang + 180) % 360
            vertical = abs(math.sin(math.radians(ang))) > 0.5
            ul = e._userlabels[0]; loc = ul.loc or 'top'
            # put the reference where schemdraw put it
            if vertical: fp = (c[0] + 1.6, c[1], 0)
            else: fp = (c[0], c[1] + (-1.9 if loc == 'top' else 2.1), 0)
            words = lab.split(None, 1)
            emit_symbol(R_sym(L), words[0], 1, c, round(ang, 3), value='R', fields=(fp, fp))
            out[-1] = out[-1].replace('(property "Value" "R"', '(property "Value" "R"', 1)
            # value hidden, reference shown; any extra words (e.g. "hysteresis") become text
            out[-1] = re.sub(r'(\(property "Value" "R" .*?\(effects \(font \(size 1.27 1.27\)\))', r'\1 (hide yes)', out[-1], count=1)
            if fp[0] != c[0] or True:
                hj = 'left' if (vertical and fp[0] > c[0]) else ('right' if vertical else 'center')
                out[-1] = out[-1].replace(f'(property "Reference" "{words[0]}" (at {R2(fp[0])} {R2(fp[1])} 0) (effects (font (size 1.27 1.27))',
                                          f'(property "Reference" "{words[0]}" (at {R2(fp[0])} {R2(fp[1])} 0) (effects (font (size 1.27 1.27)) (justify {hj})' if hj != 'center' else
                                          f'(property "Reference" "{words[0]}" (at {R2(fp[0])} {R2(fp[1])} 0) (effects (font (size 1.27 1.27))', 1)
            if len(words) > 1:
                text(words[1], (fp[0] + 2.0 + 0.9 * len(words[0]) if not vertical else fp[0], fp[1] + (0 if not vertical else 1.8)), 'black', 1.27,
                     halign='left' if not vertical else ('left' if fp[0] > c[0] else 'right'))
        elif tn.startswith('Potentiometer'):
            a, b, t = M(A['start']), M(A['end']), M(A['tap'])
            L = math.dist(a, b); c0 = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            ang0 = round(math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0]))) % 360
            tl = rot(t[0] - c0[0], -(t[1] - c0[1]), -ang0); tap_off = -tl[1]
            name = 'POT'
            if 'kh910:POT' not in libs:
                body = zigzag(L) + [poly([(round(tl[0], 4), round(tl[1], 4)), (0, -1.0)]), poly([(-0.45, -1.6), (0, -1.0), (0.45, -1.6)], 'none')]
                # local frame: horizontal start(-L/2)..end(+L/2); tap below (y negative)
                custom('POT', body, [pin('3', -L / 2, 0), pin('1', L / 2, 0), pin('2', round(tl[0], 4), round(tl[1], 4))], 'VR')
            c = c0; ang = ang0
            # with ang=90 (start at bottom), local -y (tap side) maps to display -x: matches schemdraw's tap on the left
            emit_symbol('kh910:POT', 'VR301', 1, c, round(ang, 3), value='VR', fields=((c[0] + 2.0, c[1], 0), (c[0] + 2.0, c[1] + 2.5, 0)))
            out[-1] = out[-1].replace('(property "Reference" "VR301" (at', '(property "Reference" "VR301" (at', 1)
        elif tn == 'Diode':
            a, b = M(A['start']), M(A['end'])
            if not e.params.get('reverse'): a, b = b, a            # make 'a' the cathode
            Lfull = math.dist(a, b); ang = round(math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0]))) % 360
            c = (round((a[0] + b[0]) / 2, 5), round((a[1] + b[1]) / 2, 5)); L = min(3.81, Lfull)
            ux, uy = (b[0] - a[0]) / Lfull, (b[1] - a[1]) / Lfull
            wire(a, (round(c[0] - ux * L / 2, 4), round(c[1] - uy * L / 2, 4))); wire((round(c[0] + ux * L / 2, 4), round(c[1] + uy * L / 2, 4)), b)
            emit_symbol(D_sym(L), lab or 'D301', 1, c, round(ang, 3), value='D', fields=((c[0], c[1] - 2.2, 0), (c[0], c[1] + 2.2, 0)))
            out[-1] = re.sub(r'(\(property "Value" "D" .*?\(effects \(font \(size 1.27 1.27\)\))', r'\1 (hide yes)', out[-1], count=1)
        elif tn == 'Opamp':
            nm = near_label(A['center'], 1.0, lambda t: t.split('\n')[0] in UNITS)
            consumed.add(id(nm[1])) if nm else None
            key = nm[2].split('\n')[0]; lid, ref, unit = UNITS[key]
            c = M(A['center']); plus_top = A['in2'][1] > A['in1'][1]
            mirror = None if plus_top else 'x'
            emit_symbol(lid, ref, unit, c, 0, mirror, VALUES[ref], fields=((c[0] - 1.6, c[1], 0), (c[0] - 1.6, c[1] + 1.6, 0)))
            out[-1] = re.sub(r'(\(property "Value" .*?\(effects \(font \(size 1.27 1.27\)\))', r'\1 (hide yes)', out[-1], count=1)
            out[-1] = out[-1].replace('(effects (font (size 1.27 1.27)))', '(effects (font (size 1.0 1.0)))', 1)
            pins = {p[1]: (p[2], p[3]) for p in libs[lid][1][unit]}
            def kp(name):
                lx, ly = pins[name]; ly = -ly if mirror == 'x' else ly; return (c[0] + lx, c[1] - ly)
            for an, pn in (('in1', '-'), ('in2', '+'), ('out', '')):
                a0 = M(A[an]); p1 = kp(pn); mid = (a0[0], p1[1])
                wire(a0, mid); wire(mid, p1)
        elif tn == 'LED':
            ref, unit, an, ca = pi_led[leds.index(e)]
            a, b = M(A['start']), M(A['end']); L = math.dist(a, b)
            nm = f'PI_{ref}'
            emit_symbol(f'kh910:{nm}', ref, unit, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), 0, value=None,
                        fields=(((a[0] + b[0]) / 2 - 6, a[1], 0), ((a[0] + b[0]) / 2, a[1], 0)), hidden=True)
            LED_L[(ref, unit)] = L
        elif tn == 'NpnPhoto':
            ref, unit, cn, en = pi_q[qs.index(e)]
            emit_symbol(f'kh910:PI_{ref}', ref, unit, M(A['base']), 0, value=None, hidden=True)
            bq = M(A['base']); QGEOM[(ref, unit)] = {k: (round(M(A[k])[0] - bq[0], 4), round(bq[1] - M(A[k])[1], 4)) for k in ('collector', 'emitter')}
        elif tn == 'Dot':
            p = M(A['center'])
            if not e.params.get('open'): junction(p); continue
            nl = near_label(A['center'], 2.0, lambda t: (len(t) > 2 and t[0] in HAR and t[1] == ' ') or t.startswith('CH301') or t.startswith('J '))
            if nl and nl[2].startswith('CH301'):
                emit_symbol(TP, 'CH301', 1, p, 0, value='test point', fields=((p[0] + 1.5, p[1] - 1.6, 0), (p[0] + 1.5, p[1] + 1.6, 0)))
                out[-1] = out[-1].replace('(property "Reference" "CH301" (at', '(property "Reference" "CH301" (at', 1)
                consumed.add(id(nl[1]))
            elif nl:
                letter = nl[2][0]; net = HAR[letter]
                q = nl[1].absanchors['xy']; left = q[0] < A['center'][0]
                glabel(net, p, 180 if left else 0)
                # keep the descriptive text, moved past the label
                consumed.add(id(nl[1]))
                rest = nl[2][1:].strip(); off = 2.6 + 1.05 * len(net)
                if rest: text(f'{letter} {rest}', (p[0] - off, p[1]) if left else (p[0] + off, p[1]), BLUE, 1.27, halign='right' if left else 'left')
            else:
                print('open dot without role at', A['center'], file=sys.stderr)
        elif tn == 'Ground': power('GND', M(A['start']))
        elif tn == 'Vdd': power('+5V', M(A['start']))
        elif tn == 'Tag':
            p = M(A['start']); th = (e.transform.theta or 0) % 360
            glabel(lab, p, 180 if abs(th - 180) < 1 else 0)
        elif tn == 'Label':
            if id(e) in consumed: continue
            t = lab; p = MT(A['xy']); col = col
            if re.fullmatch(r'\d+', t.strip()): continue                       # pin numbers: KiCad shows its own
            if col == BLUE and len(t) <= 3: continue                            # interrupter pin roles: in the symbol
            if 'µPC' in t: continue
            fs = e._userlabels[0].fontsize or 11
            size = 2.2 if fs >= 14 else (1.0 if fs <= 10 else 1.27)
            ha = e._userlabels[0].halign or 'center'
            text(t, p, col, size, bold=fs >= 14, halign=ha)
        else:
            print('skipped', tn, file=sys.stderr)
    for name, a, b, lbl in jp_pairs:
        pa, pb = M(a.absanchors['center']), M(b.absanchors['center']); L = math.dist(pa, pb)
        ang = 180 if name not in SWAP else 0          # pin 1 on the right (R32x side), pin 2 on the left (emitter side)
        emit_symbol(SJ_sym(L), name, 1, ((pa[0] + pb[0]) / 2, pa[1]), ang, value='open', fields=(((pa[0] + pb[0]) / 2, pa[1] + 2.0, 0), ((pa[0] + pb[0]) / 2, pa[1] + 3.6, 0)))
        out[-1] = out[-1].replace(f'(property "Value" "open"', f'(property "Value" "open"', 1)
LED_L, QGEOM = {}, {}

ROOT = U()
# sheet origins on an A3 landscape page (mm); schemdraw y up, KiCad y down
def place(d, x_left, y_top):
    bb = d.get_bbox(); return x_left - bb.xmin * K, y_top + bb.ymax * K
convert(hall, *place(hall, 14, 14), 'hall')
convert(optical, *place(optical, 14, 14 + (hall.get_bbox().ymax - hall.get_bbox().ymin) * K + 6), 'optical')
convert(enc, *place(enc, 140, 14), 'enc')

# ------------------------------------------------------------------ interrupter symbols (geometry taken from the drawing)
def led_body(L):
    return [poly([(-0.9, 0.45), (0.9, 0.45), (0, -0.45), (-0.9, 0.45)], 'outline'), poly([(-0.9, -0.45), (0.9, -0.45)]),
            poly([(0, L / 2), (0, 0.45)]), poly([(0, -0.45), (0, -L / 2)]),
            poly([(1.3, 0.3), (2.2, -0.4)]), poly([(1.3, -0.4), (2.2, -1.1)])]
def q_body(cg):
    cx, cy = cg['collector']; ex, ey = cg['emitter']
    return [poly([(0, 1.2), (0, -1.2)], w=0.3), poly([(0, 0.45), (cx, cy - 0.9), (cx, cy)]), poly([(0, -0.45), (ex, ey + 0.9), (ex, ey)]),
            poly([(ex - 0.55, ey + 1.35), (ex, ey + 0.9), (ex - 0.25, ey + 1.6)], 'outline'),
            poly([(-2.2, 1.6), (-0.9, 0.6)]), poly([(-2.2, 0.8), (-0.9, -0.2)])]
def led_unit(ref, unit, an, ca, na, nk):
    L = LED_L[(ref, unit)]; return (led_body(L), [pin(an, 0, L / 2, name=na), pin(ca, 0, -L / 2, name=nk)])
def q_unit(ref, unit, cn, en, ne):
    g = QGEOM[(ref, unit)]; return (q_body(g), [pin(cn, *g['collector'], name='C'), pin(en, *g['emitter'], name=ne)])
custom('PI_PI1', None, None, 'PI', extra_units={
    1: led_unit('PI1', 1, '4', '6', 'A2', 'K2'), 2: q_unit('PI1', 2, '8', '2', 'E2'),
    3: led_unit('PI1', 3, '3', '5', 'A1', 'K1'), 4: q_unit('PI1', 4, '8', '1', 'E1'),
    5: ([], [pin('7', 0, 0, name='NC', typ='no_connect')])})
custom('PI_PI2', None, None, 'PI', extra_units={
    1: led_unit('PI2', 1, '4', '3', 'A', 'K'), 2: q_unit('PI2', 2, '1', '2', 'E')})

# ------------------------------------------------------------------ connectors, supplies, unused units (replaces the text-only fourth sheet)
FLAGGED = set()
bx, by = 140, 118
text('Connectors, power, jumpers', (bx, by), 'black', 2.2, bold=True)
def connector(lid, ref, x, y, nets, value):
    emit_symbol(lid, ref, 1, (x, y), 0, value=value, fields=((x, y - 15, 0), (x, y + 15, 0)))
    for num, nm, px, py, pa, ln in libs[lid][1][1]:
        p = (x + px, y - py); net = nets.get(num)
        e = (p[0] - 3.81, p[1]); wire(p, e)
        if net in ('+5V', 'GND'):
            q = (e[0] - 2.54, e[1]); wire(e, q); power(net, q)
            out[-1] = out[-1].replace(f'(at {R2(q[0])} {R2(q[1])} 0)', f'(at {R2(q[0])} {R2(q[1])} {90 if net == "+5V" else 270})', 1)
            out[-1] = re.sub(r'\(property "Value" "([^"]*)" \(at [-0-9. ]+ 0\)', lambda m: f'(property "Value" "{m.group(1)}" (at {R2(q[0] - 5.5)} {R2(q[1])} 0)', out[-1], count=1)
            pass
        elif net: glabel(net, e, 180)
        else: noconn(p)
connector('Connector_Generic:Conn_01x09', 'J1', bx + 30, by + 22,
          {'1': 'OPT_A', '2': 'OPT_B', '3': 'EOL_R', '4': 'HALL_D', '5': 'ENC_C', '6': 'ENC_B', '7': 'ENC_A', '8': 'GND', '9': '+5V'}, 'S-5 harness')
connector('Connector_Generic:Conn_01x07', 'J2', bx + 30, by + 52,
          {'1': 'OPT_SIG', '2': 'GND', '3': '+5V', '4': '+5V', '5': 'HALL_N', '6': 'GND', '7': 'HALL_P'}, 'sensor harness')
text('J1 = top harness pads A..I (pin 1 = A) → S-5 → AYAB\nJ2 = bottom harness pads J..P:\noptical board J K L, hall board M N O P', (bx + 40, by + 7), GREY, 1.0)
# supplies
for i, (lid, ref, unit, vp, gp) in enumerate([('Amplifier_Operational:LM324', 'IC301', 5, '4', '11'), ('Comparator:LM339', 'IC302', 5, '3', '12'),
                                              ('Amplifier_Operational:LM358', 'IC303', 3, '8', '4')]):
    x, y = bx + 72 + i * 20, by + 26
    emit_symbol(lid, ref, unit, (x, y), 0, value=VALUES[ref], fields=((x + 3, y - 2, 0), (x + 3, y + 2, 0)))
    pins = {p[0]: (p[2], p[3]) for p in libs[lid][1][unit]}
    for num, net in ((vp, '+5V'), (gp, 'GND')):
        lx, ly = pins[num]; power(net, (x + lx, y - ly))
# power flags: one per supply net
for i, net in enumerate(('+5V', 'GND')):
    q = (bx + 72 + 60 + i * 10, by + 26 + (0 if net == '+5V' else 6))
    power(net, q); power('PWR_FLAG', q, flag=True)
    out[-1] = out[-1].replace(f'(at {R2(q[0])} {R2(q[1])} 0)', f'(at {R2(q[0])} {R2(q[1])} 180)' if net == '+5V' else f'(at {R2(q[0])} {R2(q[1])} 0)', 1)
# unused sections
for i, (lid, ref, unit) in enumerate([('Amplifier_Operational:LM324', 'IC301', 1), ('Amplifier_Operational:LM358', 'IC303', 1)]):
    x, y = bx + 76 + i * 30, by + 50
    emit_symbol(lid, ref, unit, (x, y), 0, value=VALUES[ref] + ' (unused)', fields=((x, y - 6, 0), (x, y + 6, 0)))
    for p in libs[lid][1][unit]: noconn((x + p[2], y - p[3]))
emit_symbol('kh910:PI_PI1', 'PI1', 5, (bx + 128, by + 50), 0, value=None, hidden=True); noconn((bx + 128, by + 50)); text('PI1 pin 7 (NC)', (bx + 130, by + 50), GREY, 1.0)
text('Still to confirm: links drawn under parts (beep list in README), D301 orientation, resistor values', (14, 196), GREY, 1.27)

# ------------------------------------------------------------------ write
used = sorted(libs)
def libtext(k):
    t = libs[k][0]
    if k.startswith('kh910:'): return t
    return t
open(os.path.join(PROJDIR, 'kh910.kicad_sym'), 'w').write(
    '(kicad_symbol_lib (version 20231120) (generator "kh910_build")\n' + '\n'.join(libs[k][0].replace('(symbol "kh910:', '(symbol "', 1) for k in used if k.startswith('kh910:')) + '\n)\n')
sch = (f'(kicad_sch (version 20231120) (generator "eeschema") (generator_version "8.0") (uuid "{ROOT}") (paper "A4")\n'
       f'(title_block (title "KH-910 right sensor board BP-111025-7 / PCB-E-144") (comment 1 "reverse-engineered from photos and continuity checks; see README beep list"))\n'
       '(lib_symbols\n' + '\n'.join(libtext(k) for k in used) + '\n)\n' + '\n'.join(out) + '\n(sheet_instances (path "/" (page "1")))\n)\n')
open(os.path.join(PROJDIR, PROJ + '.kicad_sch'), 'w').write(sch)
json.dump({'root': ROOT, 'sym': SYMU}, open(os.path.join(PROJDIR, 'symmap.json'), 'w'), indent=1)
print('kicad schematic written:', len(out), 'items')
