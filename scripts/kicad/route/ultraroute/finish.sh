#!/bin/bash
# finish.sh JUDGE_DIR OUTDIR  -- the release board from a judged seed: GND stitching vias (3 mm grid), dangling
# copper removed (pcb/prune.py, then DRC-reported dangling vias), every track and via unlocked, refill, DRC with
# every severity, pad-joint / pour-piece / width report (joints.py). Copy OUTDIR's board and rules into the project.
# Then (UR_POST=1, the default) octofix.py makes every segment 0/45/90 degrees where DRC allows (only short pad
# entries keep an angle) and octo.py --fix merges the collinear pieces, followed by a last refill, DRC and report.
set -e
J=$(realpath "$1"); O=$(realpath -m "$2"); mkdir -p "$O"; chmod 777 "$O"
H=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd); K=$(realpath "$H/../../kicad.sh"); R=$(realpath "$H/.."); PCB=$(realpath "$H/../../pcb")
N=board
cp "$J/j.kicad_pcb" "$O/$N.kicad_pcb"; cp "$J/j.kicad_pro" "$O/$N.kicad_pro"; cp "$J/j.kicad_dru" "$O/$N.kicad_dru"; cp "$J"/fp-lib-table "$O/" 2>/dev/null || true
cd "$O"; KICAD_KEEP_PRO=1 "$K" sh -c "python3 $R/maze.py $N.kicad_pcb stitch 3.0 && python3 $PCB/refill.py $N.kicad_pcb && \
  kicad-cli pcb drc --severity-all -o d1.rpt $N.kicad_pcb >/dev/null; python3 $PCB/prune.py $N.kicad_pcb; \
  python3 $R/rm_dangling.py $N.kicad_pcb d1.rpt; python3 $R/lock.py $N.kicad_pcb unlock; python3 $PCB/refill.py $N.kicad_pcb; \
  kicad-cli pcb drc --severity-all -o drc.rpt $N.kicad_pcb | grep Found; python3 $H/joints.py $N.kicad_pcb"
grep -o '^\[[a-z_]*\]' drc.rpt | sort | uniq -c
if [ "${UR_POST:-1}" = 1 ]; then
  python3 "$H/octofix.py" "$O" 6 0.3
  python3 "$H/octo.py" "$O/$N.kicad_pcb" --fix
  KICAD_KEEP_PRO=1 "$K" sh -c "python3 $PCB/refill.py $N.kicad_pcb && kicad-cli pcb drc --severity-all -o drc.rpt $N.kicad_pcb | grep Found; python3 $H/joints.py $N.kicad_pcb"
  grep -o '^\[[a-z_]*\]' drc.rpt | sort | uniq -c
  python3 "$H/octo.py" "$O/$N.kicad_pcb"
fi
