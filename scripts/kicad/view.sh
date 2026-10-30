#!/bin/bash
# view.sh FILE.kicad_sch|FILE.kicad_pcb OUT.png [LAYERS] [WIDTH_PX]  -- quick PNG for looking at a
# schematic (whole sheet) or board (LAYERS default F.Cu,F.Mask,F.Silkscreen,Edge.Cuts; use
# B.Cu,Edge.Cuts plus --mirror via VIEW_MIRROR=1 for the bottom). SVG export by kicad-cli, rasterised
# with rsvg-convert. Crop with ImageMagick afterwards if needed (convert OUT.png -crop WxH+X+Y ...).
set -e
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
K="$REPO/scripts/kicad/kicad.sh"
IN=$(realpath "$1"); OUT=$(realpath -m "$2"); W=${4:-2400}
TMP=$(mktemp -d); chmod 777 "$TMP"
cd "$(dirname "$IN")"
case "$IN" in
  *.kicad_sch) "$K" kicad-cli sch export svg -o "$TMP" "$(basename "$IN")" >/dev/null ;;
  *.kicad_pcb) "$K" kicad-cli pcb export svg --layers "${3:-F.Cu,F.Mask,F.Silkscreen,Edge.Cuts}" --mode-single \
                 ${VIEW_MIRROR:+--mirror} --exclude-drawing-sheet --fit-page-to-board -o "$TMP/out.svg" "$(basename "$IN")" >/dev/null ;;
esac
SVG=$(ls "$TMP"/*.svg | head -1)
rsvg-convert -w "$W" -b white -o "$OUT" "$SVG"
rm -rf "$TMP"
