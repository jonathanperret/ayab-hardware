#!/bin/bash
# regen.sh [WORKDIR] [--full|--iso] [--install]  -- rebuild the enclosure outputs and check the fit:
#   bottom.stl / lid.stl (print orientation, in enclosure/), tray/lid in board coordinates, the board
#   and every placed component as STL from KiCad (pick-and-place refs), then tools/fitcheck.py
#   ("no collision" expected). --iso: one isometric render; --full: all stills, sections and the
#   turntable / exploded animations. --install copies the renders into enclosure/renders/.
# Needs openscad + xvfb-run (headless OpenGL), ffmpeg, python3 numpy/pillow and the KiCad -full image.
set -e
E=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); P=$(dirname "$E"); REPO=$(cd "$P/.." && pwd)
W=$(realpath -m "${1:-/tmp/enclosure-work}"); MODE=--iso; INSTALL=
for a in "$@"; do case $a in --full) MODE=--full;; --iso) MODE=--iso;; --install) INSTALL=1;; esac; done
mkdir -p "$W/comp"; rm -f "$W"/comp/*.stl
cd "$E"
openscad -q -D 'part="tray_print"' -o bottom.stl ayab-sr-esp32-enclosure.scad
openscad -q -D 'part="lid_print"' -o lid.stl ayab-sr-esp32-enclosure.scad
openscad -q -D 'part="tray"' -o "$W/tray_asm.stl" ayab-sr-esp32-enclosure.scad
openscad -q -D 'part="lid"' -o "$W/lid_asm.stl" ayab-sr-esp32-enclosure.scad
REFS=$(awk -F, 'NR>1 {gsub(/"/,"",$1); print $1}' "$P/production/ayab-sr-esp32-pos.csv" | tr '\n' ' ')
cd "$P"
KICAD_IMAGE=mirror.gcr.io/kicad/kicad:10.0.7-full "$REPO/scripts/kicad/kicad.sh" sh -c "
 kicad-cli pcb export glb --no-dnp --subst-models -f --user-origin 0x0mm -o $W/board.glb ayab-sr-esp32.kicad_pcb >/dev/null 2>&1;
 kicad-cli pcb export stl --subst-models -f --user-origin 0x0mm --board-only -o $W/pcb_only.stl ayab-sr-esp32.kicad_pcb >/dev/null 2>&1;
 for r in $REFS; do kicad-cli pcb export stl --subst-models -f --user-origin 0x0mm --no-board-body --component-filter \$r -o $W/comp/\$r.stl ayab-sr-esp32.kicad_pcb >/dev/null 2>&1; done"
cd "$E/tools"; mkdir -p "$W/renders"
python3 fitcheck.py "$W" > "$W/fitcheck.txt" 2>&1 || true
tail -1 "$W/fitcheck.txt"
if [ $MODE = --full ]; then
  python3 sections.py "$W"
  python3 quick_render.py "$W" "$W/renders" --anim
else
  python3 quick_render.py "$W" "$W/renders" --iso
fi
[ -n "$INSTALL" ] && cp "$W"/renders/* "$E/renders/"
echo "work dir: $W"
