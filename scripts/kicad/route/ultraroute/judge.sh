#!/bin/bash
# judge.sh ROUTED.kicad_pcb OUTDIR -- KiCad's verdict on an ultraroute result: the GND pour put back on both copper
# layers (it is on B.Cu only while routing), zones refilled, DRC with every severity. Prints the counts.
set -e
IN=$(realpath "$1"); O=$(realpath -m "$2"); mkdir -p "$O"; chmod 777 "$O"
K=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/../kicad.sh; K=$(realpath "$K"); PCB=$(dirname "$K")/pcb
SRC=$(dirname "$IN"); B=$(basename "$IN" .kicad_pcb)
python3 - "$IN" "$O/j.kicad_pcb" <<'PY'
import sys, re
s = open(sys.argv[1]).read()
i = s.index('\t(zone\n\t\t(net "GND")'); j = s.index('\n\t)\n', i) + 3
z = s[i:j].replace('(layer "B.Cu")', '(layers "F.Cu" "B.Cu")', 1)
z = re.sub(r'\n\t\t\(filled_polygon\n.*?\n\t\t\)', '', z, flags=re.S)
open(sys.argv[2], 'w').write(s[:i] + z + s[j:])
PY
cp "$SRC/$B.kicad_pro" "$O/j.kicad_pro"; cp "$SRC/$B.kicad_dru" "$O/j.kicad_dru"
cp "$SRC"/fp-lib-table "$O/" 2>/dev/null || true
cd "$O"; KICAD_KEEP_PRO=1 "$K" sh -c "python3 $PCB/refill.py j.kicad_pcb && kicad-cli pcb drc --severity-all -o drc.rpt j.kicad_pcb" | grep Found
grep -o '^\[[a-z_]*\]' drc.rpt | sort | uniq -c
