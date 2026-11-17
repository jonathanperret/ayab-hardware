#!/bin/sh
# Regenerate the KiCad project from ../../tracer/state.json and ../../schematic/draw_schematic.py.
# Needs a python3 with numpy, scipy and schemdraw (set PYTHON=...); the PCB steps use KiCad's bundled python.
set -e
HERE=$(cd "$(dirname "$0")" && pwd); PROJ=$HERE/..; ROOT=$PROJ/..; TMP=$(mktemp -d)
KICAD=/Applications/KiCad/KiCad.app/Contents
KPY=$KICAD/Frameworks/Python.framework/Versions/3.9/bin/python3.9
CLI=$KICAD/MacOS/kicad-cli
PY=${PYTHON:-python3}
NAME=kh910_right_sensor
"$PY" "$HERE/geom.py" "$ROOT" "$TMP/geom.json"
python3 "$HERE/make_fpmap.py" "$TMP/geom.json" "$PROJ"
# 1. schematic: same drawing as the SVG sheets; solve two-pin part orientation against the tracer, redraw, re-check
"$PY" "$HERE/svg_to_kicad_sch.py" "$PROJ" $NAME
"$CLI" sch export netlist --format kicadsexpr -o "$TMP/net.net" "$PROJ/$NAME.kicad_sch" >/dev/null
python3 "$HERE/check_sch.py" "$ROOT/tracer/state.json" "$TMP/net.net" "$TMP/swap.json" >/dev/null
"$PY" "$HERE/svg_to_kicad_sch.py" "$PROJ" $NAME "$TMP/swap.json"
"$CLI" sch export netlist --format kicadsexpr -o "$TMP/net.net" "$PROJ/$NAME.kicad_sch" >/dev/null
python3 "$HERE/check_sch.py" "$ROOT/tracer/state.json" "$TMP/net.net" "$TMP/swap2.json"
python3 "$HERE/netmap_from_sch.py" "$TMP/net.net" "$PROJ"
"$CLI" sch erc --exit-code-violations --severity-error -o "$PROJ/erc_report.txt" "$PROJ/$NAME.kicad_sch" >/dev/null && echo "ERC: no errors" || echo "ERC: see erc_report.txt"
# 2. PCB from the tracer geometry, nets named as in the schematic
"$KPY" "$HERE/build_pcb.py" "$TMP/geom.json" "$PROJ" $NAME 2>&1 | grep -v "assert\|wxApp" || true
"$CLI" pcb drc --schematic-parity -o "$TMP/drc.txt" "$PROJ/$NAME.kicad_pcb" >/dev/null || true
"$KPY" "$HERE/fix_unconnected.py" "$PROJ/$NAME.kicad_pcb" "$TMP/drc.txt" 2>&1 | grep -v "assert\|wxApp" || true
"$CLI" pcb drc --schematic-parity -o "$PROJ/drc_report.txt" "$PROJ/$NAME.kicad_pcb" >/dev/null || true
grep -E "Found" "$PROJ/drc_report.txt"
rm -rf "$TMP"
