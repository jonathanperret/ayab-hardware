#!/bin/bash
# build.sh [OUT.kicad_sch]  -- rebuild ayab-sr-esp32.kicad_sch from base.kicad_sch (the last revision
# drawn by hand, commit fd659d8 of the original history) by script: prep.py (net labels, power flags, field/LCSC/value edits, symbol
# graphics), then layout.py (moves each block into its titled A2 section, frames, notes), then jlc_rot.py
# (JLCPCB rotation offsets), then fixed_trims.py (RV1/RV2 replaced by fixed resistors).
# The output must equal the committed schematic; to change the sheet, change these scripts and rebuild,
# or edit the .kicad_sch directly and keep the scripts as history. Default OUT: the project schematic.
set -e
H=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd); P=$(cd "$H/../.." && pwd)
OUT=${1:-$P/ayab-sr-esp32.kicad_sch}; TMP=$(mktemp -d)
cp "$H/base.kicad_sch" "$TMP/base.kicad_sch"
python3 "$H/prep.py" "$TMP/base.kicad_sch" "$TMP/prep.kicad_sch"
python3 "$H/layout.py" "$TMP/prep.kicad_sch" "$OUT" > /dev/null
python3 "$H/jlc_rot.py" "$OUT" > /dev/null
python3 "$H/fixed_trims.py" "$OUT" > /dev/null
rm -rf "$TMP"; echo "wrote $OUT"
