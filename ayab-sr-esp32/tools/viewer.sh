#!/bin/bash
# viewer.sh  -- refresh the three.js page's models in ayab-sr-esp32/viewer/: board.glb (kicad-cli GLB
# export, KiCad coordinates in metres, -full image for the 3D models), tray.stl / lid.stl (OpenSCAD, in
# board coordinates) and the PARTS table in index.html (from production/ayab-sr-esp32-bom.csv, so run
# production.sh first). Run from the design checkout:  ../tooling/ayab-sr-esp32/tools/viewer.sh
set -e
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
P=$(git rev-parse --show-toplevel)/ayab-sr-esp32; V=$P/viewer
cd "$P/enclosure"
openscad -q -D 'part="tray"' -o "$V/tray.stl" ayab-sr-esp32-enclosure.scad
openscad -q -D 'part="lid"' -o "$V/lid.stl" ayab-sr-esp32-enclosure.scad
cd "$P"
KICAD_IMAGE=mirror.gcr.io/kicad/kicad:10.0.7-full "$REPO/scripts/kicad/kicad.sh" kicad-cli pcb export glb \
  --no-dnp --subst-models -f --user-origin 0x0mm -o "$V/board.glb" ayab-sr-esp32.kicad_pcb 2>&1 | grep -v "couldn't be created" || true
python3 - "$P/production/ayab-sr-esp32-bom.csv" "$V/index.html" <<'PY'
import csv, json, re, sys
m = {}
for r in csv.DictReader(open(sys.argv[1])):
    for d in r['Designator'].split(','): m[d] = [r['Value'], r['LCSC']]
m.setdefault('J14', ['8-pin socket (debug)', '—']); m.setdefault('J4', ['2-pin header', '—'])
m.setdefault('U5', ['HS91L02W2C01 (fitted at assembly)', 'C5248081'])   # not in the JLCPCB BOM
s = open(sys.argv[2], encoding='utf-8').read()
s = re.sub(r'const PARTS = \{.*?\};', lambda _: 'const PARTS = %s;' % json.dumps(m, separators=(',', ':'), ensure_ascii=False), s, count=1)
open(sys.argv[2], 'w', encoding='utf-8').write(s)
PY
ls -la "$V"
