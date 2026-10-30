"""Net naming and text fixes, applied to base.kicad_sch (the hand-drawn schematic) before layout.py (old coordinates)."""
import re, sys, uuid
from sx import *
t = open(sys.argv[1]).read()
_n = [0]
def U():
    _n[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "ayab-sr-esp32-prep-%d" % _n[0]))

def label(name, x, y, ang):
    j = 'left bottom' if ang == 0 else 'right bottom'
    return ('\t(label "%s"\n\t\t(at %g %g %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
            '\t\t\t(justify %s)\n\t\t)\n\t\t(uuid "%s")\n\t)\n') % (name, x, y, ang, j, U())

def is_wire(s, p, q):
    P = [tuple(map(float, m)) for m in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', s)]
    return head(s) == 'wire' and set(P) == {p, q}

LCSC = {'C2': 'C15849', 'R1': 'C23206', 'R2': 'C23186', 'R3': 'C23186', 'R7': 'C25819', 'R13': 'C25804',
        'D1': 'C8678', 'D2': 'C8678', 'J1': 'C165948', 'J2': 'C165948', 'J3': 'C20611695', 'U1': 'C42459160',
        'U2': 'C2687116', 'U3': 'C2913198', 'U4': 'C52140417', 'U5': 'C5248081', 'U8': 'C54411083', 'U10': 'C22365427'}

def set_lcsc(s, code):
    if '(property "LCSC" ' in s:
        return re.sub(r'\(property "LCSC" "[^"]*"', '(property "LCSC" "%s"' % code, s, count=1)
    at = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)', s)
    blk = ('\t\t(property "LCSC" "%s"\n\t\t\t(at %s %s 0)\n\t\t\t(hide yes)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n'
           '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n') % (code, at.group(1), at.group(2))
    i = s.index('\t\t(pin "')
    return s[:i] + blk + s[i:]

def set_field(s, name, x, y, ang, just):
    def f(m):
        body = m.group(0)
        body = re.sub(r'\(at [^)]*\)', '(at %g %g %d)' % (x, y, ang), body, count=1)
        body = re.sub(r'\n\t\t\t\t\(justify [^)]*\)', '', body)
        if just: body = body.replace('\n\t\t\t\t)\n\t\t\t)', '\n\t\t\t\t)\n\t\t\t\t(justify %s)\n\t\t\t)' % just, 1)
        return body
    return re.sub(r'\(property "%s" "[^"]*"\n.*?\n\t\t\)' % name, f, s, count=1, flags=re.S)

pwr = sorted(int(n) for n in re.findall(r'"#PWR0*(\d+)"', t))
next_pwr = pwr[-1] + 1
out = []; last = 0
for a, b in items(t):
    s = t[a:b]; h = head(s); out.append(t[last:a]); last = b
    # ALERT: cut the R11 junction -> Q1 gate link, name both sides
    if is_wire(s, (419.1, 137.16), (419.1, 134.62)): out.append('\x00'); continue
    if h == 'junction' and '(at 419.1 134.62)' in s: out.append('\x00'); continue
    # Buck5V -> +5V
    if h == 'label' and s.startswith('(label "Buck5V"'):
        if '(at 303.53 200.66' in s: out.append('\x00'); continue
        # replace D2's Buck5V label with a +5V power symbol pointing left
        tpl = re.search(r'\(symbol\n\t\t\(lib_id "power:\+5V"\).*?\n\t\)', t, re.S).group(0)
        ref = '#PWR%03d' % next_pwr
        p = re.sub(r'"#PWR\d+"', '"%s"' % ref, tpl)
        p = re.sub(r'\(uuid "[^"]+"\)', lambda m: '(uuid "%s")' % U(), p)
        p = re.sub(r'\n\t\t\(fields_autoplaced yes\)', '', p)
        p = re.sub(r'\(at [-\d.]+ [-\d.]+ \d+\)', '(at 123.19 81.28 0)', p)
        p = set_field(p, 'Value', 123.19, 77.47, 0, None)
        out.append(p); continue
    if h == 'symbol':
        r = re.search(r'\(property "Reference" "([^"]+)"', s).group(1)
        if r in LCSC:
            s = set_lcsc(s, LCSC[r])
        if r in ('H1', 'H2', 'H3'):
            s = s.replace('\n\t\t(in_bom yes)', '\n\t\t(in_bom no)', 1)   # mounting holes: no BOM line for JLCPCB
        if r == 'U5':
            # Hansheng HS91L02W2C01: same 38 x 12 mm 4-pin module outline as the ER-OLEDM0.91, stocked at JLCPCB
            s = s.replace('(property "Value" "ER_OLEDM0.91_1x-I2C"', '(property "Value" "HS91L02W2C01"')
            s = re.sub(r'\(property "Datasheet" "[^"]*"', '(property "Datasheet" "https://www.lcsc.com/datasheet/C5248081.pdf"', s, count=1)
            s = s.replace('(lib_id "Display_Graphic:ER_OLEDM0.91_1x-I2C")', '(lib_id "ayab-lib:OLED_128x32_I2C")')
            s = set_field(s, 'Reference', 203.2, 74.93, 0, 'left')
            s = set_field(s, 'Value', 203.2, 92.71, 0, 'left')
        if r == 'J14':
            # stock socket with staggered pads (friction-fit test header), kept in ayab-library
            s = s.replace('"Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical"', '"Library:PinSocket_1x08_P2.54mm_Vertical_Lock"')
        if r in ('RV1', 'RV2'):
            # local copy of the TC33X footprint with the silk clipped off the pads (JLCPCB 0.15 mm)
            s = s.replace('"Potentiometer_SMD:Potentiometer_Bourns_TC33X_Vertical"', '"Library:Potentiometer_Bourns_TC33X_Vertical"')
        if r == 'S1':
            s = set_field(s, 'Reference', 109.22, 160.02, 0, None)
            s = set_field(s, 'Value', 109.22, 162.56, 0, None)
        if r == 'U7':
            s = set_field(s, 'Reference', 359.41, 141.605, 0, 'left')
            s = set_field(s, 'Value', 359.41, 144.145, 0, 'left')
        if r in ('R15', 'R16', 'R17', 'R18'):
            x, y = map(float, re.search(r'\(at ([-\d.]+) ([-\d.]+)', s).groups())
            s = set_field(s, 'Reference', x - 0.635, y - 2.794, 90, 'left')
            s = set_field(s, 'Value', x + 0.635, y - 2.794, 90, 'right')
    if h == 'text' and s.startswith('(text "56k = 15V"'):
        s = s.replace('56k = 15V', 'R1 56k on CFG1: requests 15 V').replace('(size 0.762 0.762)', '(size 1.27 1.27)')
        s = s.replace('(at 134.62 124.46 0)', '(at 82.55 134.62 0)')
        s = s.replace('\t\t\t)\n\t\t)\n\t\t(uuid', '\t\t\t)\n\t\t\t(justify left)\n\t\t)\n\t\t(uuid', 1)
    if h == 'text' and s.startswith('(text "DP shorted'):
        s = s.replace('DP shorted to DM\\nto disable BC/QC\\nprotocols, only\\nPD is supported',
                      'DP shorted to DM: disables\\nBC/QC, only PD is supported')
        s = s.replace('(size 0.762 0.762)', '(size 1.27 1.27)').replace('(at 87.63 111.76 0)', '(at 82.55 129.54 0)')
        s = s.replace('\t\t\t)\n\t\t)\n\t\t(uuid', '\t\t\t)\n\t\t\t(justify left)\n\t\t)\n\t\t(uuid', 1)
    out.append(s)
out.append(t[last:])
body = re.sub(r'\n\t\x00', '', ''.join(out))
extra = (label('ALERT', 419.1, 134.62, 0) + label('ALERT', 419.1, 137.16, 180)
         + label('CMPREF', 392.43, 137.16, 0) + label('CFG1', 120.65, 107.95, 0))
# U5: display-looking symbol from ayab-lib instead of Display_Graphic:ER_OLEDM0.91_1x-I2C
i = body.index('\t\t(symbol "Display_Graphic:ER_OLEDM0.91_1x-I2C"'); d = 0; j = i
while True:
    d += {'(': 1, ')': -1}.get(body[j], 0)
    if d == 0 and body[j] == ')': break
    j += 1
body = body[:i] + open(__file__.rsplit('/', 1)[0] + '/oled_embedded.txt').read() + body[j + 1:]
# S1: thumb-wheel shaped symbol
sys.path.insert(0, __file__.rsplit('/', 1)[0]); import bldt
i, j = bldt.block(body, '\t\t(symbol "ayab-lib:BL-DT"'); body = body[:i] + bldt.redraw(body[i:j]) + body[j:]
# ERC: PWR_FLAGs on the undriven supply nets, no-connect marks on the unused ESP32 pins
lib = open(__file__.rsplit('/', 1)[0] + '/pwrflag_lib.txt').read()
i = body.index('\t\t(symbol "power:+15V"'); body = body[:i] + lib.lstrip('\t').join(['\t\t', '\n']) + body[i:]
tpl = re.search(r'\t\(symbol\n\t\t\(lib_id "power:\+5V"\).*?\n\t\)\n', body, re.S).group(0)
def flag(n, x, y):
    f = tpl.replace('"power:+5V"', '"power:PWR_FLAG"')
    f = re.sub(r'"#PWR\d+"', '"#FLG%02d"' % n, f)
    f = f.replace('(property "Value" "+5V"', '(property "Value" "PWR_FLAG"')
    f = re.sub(r'\(property "Description" [^\n]*', '(property "Description" "Special symbol for telling ERC where power comes from"', f)
    f = re.sub(r'\(uuid "[^"]+"\)', lambda m: '(uuid "%s")' % U(), f)
    f = re.sub(r'\n\t\t\(fields_autoplaced yes\)', '', f)
    f = re.sub(r'\(at [-\d.]+ [-\d.]+ \d+\)', '(at %g %g 0)' % (x, y), f)
    f = set_field(f, 'Reference', x, y - 1.905, 0, None)
    f = set_field(f, 'Value', x, y - 3.81, 0, None)
    return f
for n, (x, y) in enumerate([(90.17, 91.44), (49.53, 132.08), (295.91, 200.66), (152.4, 81.28)], 1):
    extra += flag(n, x, y)
extra += ('\t(wire\n\t\t(pts\n\t\t\t(xy 39.37 132.08) (xy 49.53 132.08)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n'
          '\t\t\t(type default)\n\t\t)\n\t\t(uuid "%s")\n\t)\n') % U()
for x, ys in ((137.16, (158.75, 161.29, 163.83, 166.37, 168.91, 181.61, 189.23)),
              (167.64, (161.29, 163.83, 166.37, 168.91, 176.53, 179.07, 181.61, 184.15, 186.69, 189.23, 191.77))):
    for y in ys:
        extra += '\t(no_connect\n\t\t(at %g %g)\n\t\t(uuid "%s")\n\t)\n' % (x, y, U())
i = body.index('\t(sheet_instances'); body = body[:i] + extra + body[i:]
open(sys.argv[2], 'w').write(body)
