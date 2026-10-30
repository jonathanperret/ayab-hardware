#!/bin/bash
# check.sh PROJECT_DIR [GIT_REF]  -- the checks to run before pushing a board change:
#   ERC and DRC (counts by violation type, full reports in $OUT), a pad-net check of the board
#   against the schematic netlist (pcb/padcheck.py), and with GIT_REF a connectivity comparison of
#   the schematic against that revision (netcmp.py: same pin sets per net, renames, changed parts).
# Exit status 1 if ERC/DRC has more violations of any type than PROJECT_DIR/check-baseline.txt (or the
# same file in this tools checkout, e.g. ayab-sr-esp32/check-baseline.txt) allows
# (lines "erc|drc TYPE COUNT"; without the file, any ERC/DRC error fails), unconnected items remain,
# the board does not match the schematic, or connectivity changed.
#   scripts/kicad/check.sh ayab-sr-esp32 HEAD~1
set -u
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
K="$REPO/scripts/kicad/kicad.sh"
PROJ=$(cd "$1" && pwd); NAME=$(basename "$(ls "$PROJ"/*.kicad_pro | head -1)" .kicad_pro)
OUT=${OUT:-/tmp/kicad-check/$NAME}; mkdir -p "$OUT"
fail=0
summary() { grep -o '^\[[a-z_]*\]' "$1" | sort | uniq -c | sed 's/^/    /'; }
BASE="$PROJ/check-baseline.txt"          # next to the project, else in the tools' checkout
[ -f "$BASE" ] || BASE="$REPO/$(basename "$PROJ")/check-baseline.txt"
over_baseline() {   # over_baseline erc|drc REPORT: 1 if a violation type exceeds the baseline
  local kind=$1 rpt=$2 bad=0
  if [ ! -f "$BASE" ]; then grep -q '; error' "$rpt" && return 0; return 1; fi
  while read -r n t; do
    t=${t#[}; t=${t%]}
    allowed=$(awk -v k="$kind" -v t="$t" '$1==k && $2==t {print $3}' "$BASE"); allowed=${allowed:-0}
    if [ "$n" -gt "$allowed" ]; then echo "    NEW: $kind $t $n (baseline $allowed)"; bad=1; fi
  done < <(grep -o '^\[[a-z_]*\]' "$rpt" | sort | uniq -c)
  [ $bad = 1 ]
}

cd "$PROJ"
"$K" kicad-cli sch erc --severity-all -o "$OUT/erc.rpt" "$NAME.kicad_sch" | grep -i 'found'
summary "$OUT/erc.rpt"; over_baseline erc "$OUT/erc.rpt" && fail=1
"$K" kicad-cli pcb drc --severity-all -o "$OUT/drc.rpt" "$NAME.kicad_pcb" | grep -i 'found'
summary "$OUT/drc.rpt"; over_baseline drc "$OUT/drc.rpt" && fail=1
grep -q 'Found [1-9][0-9]* unconnected' <("$K" kicad-cli pcb drc -o /dev/null "$NAME.kicad_pcb") && fail=1

"$K" kicad-cli sch export netlist -o "$OUT/netlist.net" "$NAME.kicad_sch" >/dev/null
echo "pad-net check:"; "$K" python3 "$REPO/scripts/kicad/pcb/padcheck.py" "$NAME.kicad_pcb" "$OUT/netlist.net" | sed 's/^/    /' || fail=1
[ "${PIPESTATUS[0]}" = 0 ] || fail=1

if [ $# -ge 2 ]; then
  REF=$2; TMP=$(mktemp -d); PREPO=$(git -C "$PROJ" rev-parse --show-toplevel); REL=${PROJ#$PREPO/}
  (cd "$PREPO" && git archive "$REF" | tar -x -C "$TMP")
  (cd "$TMP/$REL" && "$K" kicad-cli sch export netlist -o "$OUT/netlist_ref.net" "$NAME.kicad_sch" >/dev/null)
  rm -rf "$TMP"
  echo "connectivity vs $REF:"; python3 "$REPO/scripts/kicad/netcmp.py" "$OUT/netlist_ref.net" "$OUT/netlist.net" | sed 's/^/    /'
  [ "${PIPESTATUS[0]}" = 0 ] || fail=1
fi
echo "reports in $OUT"; [ $fail = 0 ] && echo "CHECKS OK" || echo "CHECKS FAILED"
exit $fail
