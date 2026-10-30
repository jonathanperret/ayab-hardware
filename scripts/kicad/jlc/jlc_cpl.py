#!/usr/bin/env python3
"""jlc_cpl.py BOARD.kicad_pcb POS.csv OUT.csv  -- turn kicad-cli's pick-and-place CSV into JLCPCB's CPL
format (Designator, Mid X, Mid Y, Layer, Rotation), applying the per-footprint corrections used by the
Fabrication Toolkit plugin (same fields as silverreed-firmware's shield):
  "FT Rotation Offset"  degrees added to the KiCad rotation (JLCPCB's reel orientation differs for
                        some packages)
  "FT Position Offset"  "dx,dy" mm in the footprint's own frame (rotated with the footprint)
Set those fields on the symbol (they reach the board via update_pcb.py) after checking the placement
preview in JLCPCB's order page. Runs on the host (plain Python)."""
import csv, math, re, sys

pcb = open(sys.argv[1], encoding='utf-8').read()
off = {}
for m in re.finditer(r'\n\t\(footprint "', pcb):
    blk = pcb[m.start():pcb.find('\n\t)\n', m.start() + 2)]
    ref = re.search(r'\(property "Reference" "([^"]+)"', blk).group(1)
    rot = re.search(r'\(property "FT Rotation Offset" "([^"]*)"', blk)
    pos = re.search(r'\(property "FT Position Offset" "([^"]*)"', blk)
    off[ref] = (float(rot.group(1)) if rot and rot.group(1).strip() else 0.0,
                tuple(float(v) for v in pos.group(1).split(',')) if pos and pos.group(1).strip() else (0.0, 0.0))
rows = list(csv.DictReader(open(sys.argv[2], encoding='utf-8')))
with open(sys.argv[3], 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
    n = 0
    for r in rows:
        ref = r['Ref']; rot = float(r['Rot']); x, y = float(r['PosX']), float(r['PosY'])
        drot, (dx, dy) = off.get(ref, (0.0, (0.0, 0.0)))
        if dx or dy:   # pos CSV has y up; offsets are in footprint coordinates (y down), rotated with it
            a = math.radians(rot)
            x += dx * math.cos(a) + dy * math.sin(a)
            y += dx * math.sin(a) - dy * math.cos(a)
        if drot or dx or dy:
            n += 1
        w.writerow([ref, '%.4f' % x, '%.4f' % y, 'Top' if r['Side'] == 'top' else 'Bottom', '%g' % ((rot + drot) % 360)])
print('%d placements, %d with JLCPCB corrections' % (len(rows), n))
