#!/bin/bash
# production.sh PROJECT_DIR  -- regenerate PROJECT_DIR/production/ for JLCPCB from the board and schematic:
#   gerbers/ (board plot settings) + Excellon drill (PTH/NPTH separate, Gerber X2 maps), the Gerber zip,
#   PROJECT-pos.csv (pick and place, DNP excluded), PROJECT-bom.csv (grouped, with LCSC numbers) and
#   PROJECT-schematic.pdf, plus PROJECT-cpl-jlc.csv (JLCPCB CPL columns, FT Rotation/Position Offset
#   fields applied, see jlc/jlc_cpl.py). Gerbers only differ in dates when copper is unchanged.
set -e
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
K="$REPO/scripts/kicad/kicad.sh"
cd "$1"; NAME=$(basename "$(ls *.kicad_pro | head -1)" .kicad_pro)
mkdir -p production/gerbers; rm -f production/gerbers/*
"$K" sh -c "
kicad-cli pcb export gerbers --board-plot-params -o production/gerbers/ $NAME.kicad_pcb >/dev/null &&
kicad-cli pcb export drill --format excellon --excellon-separate-th --generate-map --map-format gerberx2 -o production/gerbers/ $NAME.kicad_pcb >/dev/null &&
kicad-cli pcb export pos --format csv --units mm --side both --exclude-dnp -o production/$NAME-pos.csv $NAME.kicad_pcb >/dev/null &&
kicad-cli sch export bom --fields 'Reference,Value,Footprint,LCSC,\${QUANTITY},\${DNP}' --labels 'Designator,Value,Footprint,LCSC,Qty,DNP' --group-by Value,Footprint,LCSC --ref-range-delimiter '' -o production/$NAME-bom.csv $NAME.kicad_sch >/dev/null &&
kicad-cli sch export pdf -o production/$NAME-schematic.pdf $NAME.kicad_sch >/dev/null"
(cd production/gerbers && rm -f ../$NAME-gerbers.zip && zip -q ../$NAME-gerbers.zip *)
python3 "$REPO/scripts/kicad/jlc/jlc_cpl.py" $NAME.kicad_pcb production/$NAME-pos.csv production/$NAME-cpl-jlc.csv
ls production production/gerbers
