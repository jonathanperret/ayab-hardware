#!/bin/bash
# render_board.sh PROJECT_DIR OUT_DIR [--anim]  -- KiCad 3D renders of the board: top.png, bottom.png,
# iso_front.png, iso_back.png (high quality, raytraced); with --anim also a 24-frame turntable (GIF + MP4, needs ffmpeg
# and python3-pil on the host). Uses the -full KiCad image (3D models).
set -e
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
export KICAD_IMAGE=${KICAD_IMAGE:-mirror.gcr.io/kicad/kicad:10.0.7-full}
K="$REPO/scripts/kicad/kicad.sh"
O=$(mkdir -p "$2" && cd "$2" && pwd)   # OUT_DIR relative to the caller, not to PROJECT_DIR
cd "$1"; NAME=$(basename "$(ls *.kicad_pro | head -1)" .kicad_pro); FR=$(mktemp -d)
R="kicad-cli pcb render --background opaque"
"$K" sh -c "
$R --quality high --side top -w 1600 -h 1200 -o $O/top.png $NAME.kicad_pcb >/dev/null &
$R --quality high --side bottom -w 1600 -h 1200 -o $O/bottom.png $NAME.kicad_pcb >/dev/null &
$R --quality high --perspective --floor --rotate '-55,0,-30' -w 1600 -h 1100 -o $O/iso_front.png $NAME.kicad_pcb >/dev/null &
$R --quality high --perspective --floor --rotate '-55,0,150' -w 1600 -h 1100 -o $O/iso_back.png $NAME.kicad_pcb >/dev/null &
wait"
[ "$3" = "--anim" ] || { ls "$O"; exit 0; }
"$K" sh -c "for i in \$(seq 0 23); do $R --quality basic --perspective --rotate \"-58,0,\$((i*15))\" --zoom 0.9 -w 640 -h 480 -o $FR/\$(printf %03d \$i).png $NAME.kicad_pcb >/dev/null; done"
python3 - "$FR" "$O" <<'PY'
import glob, sys
from PIL import Image
fr = [Image.open(f).convert('RGB').quantize(colors=160, method=Image.Quantize.MEDIANCUT) for f in sorted(glob.glob(sys.argv[1] + '/*.png'))]
fr[0].save(sys.argv[2] + '/board_turntable.gif', save_all=True, append_images=fr[1:], duration=120, loop=0, optimize=True)
PY
ffmpeg -y -loglevel error -framerate 8 -i "$FR/%03d.png" -vf 'scale=640:-2' -pix_fmt yuv420p -c:v libx264 -crf 22 -movflags +faststart "$O/board_turntable.mp4"
rm -rf "$FR"; ls "$O"
