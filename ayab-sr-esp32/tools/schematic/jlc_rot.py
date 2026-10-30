#!/usr/bin/env python3
"""jlc_rot.py IN.kicad_sch|IN.kicad_pcb [OUT]  -- set the "FT Rotation Offset" field (read by
scripts/kicad/jlc/jlc_cpl.py) on the parts whose JLCPCB reel orientation differs from KiCad's, as seen
in the JLCPCB placement preview (2026-10-30 order): adds the field after the symbol's/footprint's last
property, or updates it. Run on the schematic by build.sh; run once on the board by hand."""
import re, sys, uuid
OFF = {'U1': '-90', 'U2': '-90', 'U4': '-90', 'U7': '-90', 'U8': '-90', 'U6': '-90', 'U9': '-90',
       'U10': '180', 'Q1': '180'}
src = sys.argv[1]; dst = sys.argv[2] if len(sys.argv) > 2 else src
s = open(src, encoding='utf-8').read()
sch = src.endswith('.kicad_sch')

def close(t, i):   # index just past the first s-expression starting at or after t[i]
    d = 0
    for j in range(t.index('(', i), len(t)):
        d += {'(': 1, ')': -1}.get(t[j], 0)
        if d == 0:
            return j + 1

edits = []
for m in re.finditer(r'\n\t\(symbol\n' if sch else r'\n\t\(footprint "', s):
    st = m.start() + 1; en = close(s, st); b = s[st:en]
    r = re.search(r'\(property "Reference" "([^"]+)"', b)
    if not r or r.group(1) not in OFF:
        continue
    v = OFF[r.group(1)]
    if '"FT Rotation Offset"' in b:
        nb = re.sub(r'\(property "FT Rotation Offset" "[^"]*"', '(property "FT Rotation Offset" "%s"' % v, b)
    else:
        at = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)', b)
        if sch:
            p = ('(property "FT Rotation Offset" "%s"\n\t\t\t(at %s %s 0)\n\t\t\t(hide yes)\n\t\t\t(show_name no)\n'
                 '\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
                 '\t\t\t\t)\n\t\t\t)\n\t\t)') % (v, at.group(1), at.group(2))
        else:
            p = ('(property "FT Rotation Offset" "%s"\n\t\t\t(at 0 0 0)\n\t\t\t(unlocked yes)\n\t\t\t(layer "F.Fab")\n'
                 '\t\t\t(hide yes)\n\t\t\t(uuid "%s")\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1 1)\n'
                 '\t\t\t\t\t(thickness 0.15)\n\t\t\t\t)\n\t\t\t)\n\t\t)') % (v, uuid.uuid4())
        last = [x.start() + 1 for x in re.finditer(r'\n\t\t\(property ', b)][-1]
        pe = close(b, last)
        nb = b[:pe] + '\n\t\t' + p + b[pe:]
    edits.append((st, en, nb))
for st, en, nb in sorted(edits, reverse=True):
    s = s[:st] + nb + s[en:]
open(dst, 'w', encoding='utf-8').write(s)
print('%s: %d parts' % (dst, len(edits)))
