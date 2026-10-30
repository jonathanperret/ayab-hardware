#!/usr/bin/env python3
"""fixed_trims.py IN.kicad_sch [OUT]  -- replace the trimmers by fixed JLCPCB basic resistors (run by
build.sh after layout.py, final coordinates):
  RV1 (U6 fallback voltage) -> R24 3.3k: Vout = 0.596 V x (R4 + R24 + R5) / (R24 + R5) = 8.05 V
  RV2 (INA381 threshold)    -> R25 10k + R26 7.5k between R9 and R23 (R23 and its GND move down):
                               CMPREF = 3.3 V x (R26 + R23) / (R9 + R25 + R26 + R23) = 0.90 V = 0.90 A
and update the two design notes. Idempotent: does nothing once RV1/RV2 are gone."""
import re, sys, uuid
from sx import items, head
src = sys.argv[1]; dst = sys.argv[2] if len(sys.argv) > 2 else src
t = open(src, encoding='utf-8').read()
if '"Reference" "RV1"' not in t:
    open(dst, 'w', encoding='utf-8').write(t); sys.exit(0)
U = lambda k: str(uuid.uuid5(uuid.NAMESPACE_URL, 'ayab-sr-esp32-fixed-trims-' + k))

def sym(ref):
    for a, b in items(t):
        s = t[a:b]
        if head(s) == 'symbol' and '(property "Reference" "%s"' % ref in s:
            return a, b

def shift(s, dy):   # move every (at x y ...) in a symbol block down by dy
    return re.sub(r'\(at ([-\d.]+) ([-\d.]+)', lambda m: '(at %s %s' % (m[1], '%g' % round(float(m[2]) + dy, 4)), s)

a, b = sym('R23'); r23 = t[a:b]
def resistor(ref, value, lcsc, y):   # R23's block (Device:R, 0 deg, x 245.11) as template
    s = shift(r23, y - 181.61).replace('"R23"', '"%s"' % ref)
    s = re.sub(r'\(property "Value" "[^"]*"', '(property "Value" "%s"' % value, s)
    s = re.sub(r'\(property "LCSC" "[^"]*"', '(property "LCSC" "%s"' % lcsc, s)
    n = [0]
    def nu(m):
        n[0] += 1
        return '(uuid "%s")' % U('%s-%d' % (ref, n[0]))
    return re.sub(r'\(uuid "[^"]+"\)', nu, s)

def wire(x1, y1, x2, y2):
    return ('(wire\n\t\t(pts\n\t\t\t(xy %g %g) (xy %g %g)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n'
            '\t\t)\n\t\t(uuid "%s")\n\t)') % (x1, y1, x2, y2, U('w%g,%g,%g,%g' % (x1, y1, x2, y2)))

def pts(s):
    return [tuple(map(float, p)) for p in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', s)]

out = []; last = 0
for a, b in items(t):
    s = t[a:b]; h = head(s); out.append(t[last:a]); last = b
    ref = re.search(r'\(property "Reference" "([^"]+)"', s) if h == 'symbol' else None
    ref = ref and ref[1]
    if ref == 'RV1':   # same pin positions: pin 1 (167.64) at FB, pin 2 (175.26) at R5
        s = shift(resistor('R24', '3.3k', 'C22978', 181.61), 0)
        s = re.sub(r'\(at 245\.11 ', '(at 100.33 ', s).replace('(at 247.65 ', '(at 102.87 ').replace('(at 246.888 ', '(at 102.108 ')
        s = shift(s, 171.45 - 181.61)
    elif ref == 'RV2':
        r25 = resistor('R25', '10k', 'C25804', 172.72)   # fields left of the body, clear of the CMPREF wire
        r25 = r25.replace('(at 247.65 ', '(at 243.84 ').replace('(justify left)', '(justify right)')
        s = r25 + '\n\t' + resistor('R26', '7.5k', 'C23234', 181.61)
    elif ref in ('R23', '#PWR033'):
        s = shift(s, 7.62)
    elif h == 'wire' and set(pts(s)) in ({(104.14, 171.45), (104.14, 166.37)}, {(104.14, 166.37), (100.33, 166.37)},
                                        {(250.19, 172.72), (248.92, 172.72)}):
        s = '\x00'   # RV1 wiper loop, RV2 wiper wire
    elif h == 'wire' and set(pts(s)) == {(250.19, 154.94), (250.19, 172.72)}:
        s = s.replace('(xy 250.19 172.72)', '(xy 250.19 176.53)') + '\n\t' + wire(250.19, 176.53, 245.11, 176.53)
    elif h == 'junction' and '(at 100.33 166.37)' in s:
        s = s.replace('(at 100.33 166.37)', '(at 245.11 176.53)')   # CMPREF tee between R25 and R26
    elif h == 'text' and s.startswith('(text "Vout = 0.596'):
        s = re.sub(r'\(text "[^"]*"', lambda m: '(text "Vout = 0.596 * (R24+R5+R4) / (R24+R5)\\n'
                   '  = 0.596 * (3.3+4.7+100) / (3.3+4.7) = 8.05V\\n'
                   '  (0.9 A in a 7 ohm solenoid = 6.3 V, plus the carriage\\n'
                   '  Darlington VCE and the DIN cable: ~8 V)\\n'
                   'Default: Q1 on holds FB low, Vout ~ VIN (~15 V bypass)\\n'
                   'Overcurrent: Q1 off, U6 regulates at 8 V"', s)
    elif h == 'text' and s.startswith('(text "INA381A1 (amplifier'):
        s = re.sub(r'Threshold \(RV2\):[^"]*"', lambda m: 'Threshold: R9 82k / R25 10k / R26 7.5k / R23 27k\\n'
                   '  CMPREF = 3.3 * 34.5 / 126.5 = 0.90 V, i.e. 0.90 A\\n'
                   '  (keep CMPREF > V_HYS or ALERT never releases)"', s).replace('at the RV1 setpoint', 'at 8 V')
    out.append(s)
out.append(t[last:])
t = ''.join(out)
t = re.sub(r'\n\t\x00', '', t)
open(dst, 'w', encoding='utf-8').write(t)
print('%s: RV1 -> R24, RV2 -> R25 + R26' % dst)
