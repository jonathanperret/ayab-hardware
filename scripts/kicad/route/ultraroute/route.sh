#!/bin/bash
# route.sh PROJECT_DIR WORKDIR [SEED...]  -- re-route a board from bare pads with ultraroute, Boardroom phase-7 style:
#   1. WORKDIR/in: the project copied, then the board's tools/ultraroute/prep.py (bare copper, fixed parts locked,
#      GND pour on B.Cu only as the soft plane, edge strips, width rules, strict DRC) and preroute.py (short critical
#      links from pad positions, rule areas); a GND via at every SMD ground pad (route/maze.py gnd), all locked; refill
#   2. one governed ultraroute run per seed (nice 15, 1 thread, --timeout 240, timeout backstop, 8 GB ceiling),
#      each judged by KiCad (judge.sh: F.Cu pour back, refill, DRC all severities)
#   3. pick a seed (the first clean one unless you choose), then finish.sh makes the release board
# UR_RECIPE = the router's stage flags (default: ultraroute's default recipe minus --tighten, so the copper keeps
#   the grid router's 0/45/90-degree geometry instead of being pulled taut at any angle; set UR_RECIPE="--recipe
#   default" for that). --diff-pairs is left out too: its coupled pairs are laid at any angle, which octofix.py cannot
#   turn into 45-degree corners without moving their ends (USB here is full-speed only and short, so it needs no
#   coupling). finish.sh then runs octofix.py (UR_POST=1, the default).
# ULTRAROUTE = the router binary (built from https://github.com/sequoia-hope/ultraroute: cargo build --release
#   -p ultraroute -p kicad-text, in core/). Seeds default to 0 1 2. Never deletes anything outside WORKDIR.
set -e
P=$(realpath "$1"); W=$(realpath -m "$2"); shift 2; SEEDS=${*:-0 1 2}
H=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd); K=$(realpath "$H/../../kicad.sh"); R=$(realpath "$H/..")
UR=${ULTRAROUTE:?set ULTRAROUTE to the ultraroute binary}
RECIPE=${UR_RECIPE:---negotiate --rip-up --rip-boxed --prefanout --escape-room --diff-pairs --shove-plough region --shove-reach 0.5 --shove-repair 20 --shove-ties --guard-ties --shove-passes 60 --shove-patience 8}
TOOLS=$(realpath "$H/../../../../$(basename "$P")/tools/ultraroute")
NAME=$(basename "$(ls "$P"/*.kicad_pro | head -1)" .kicad_pro)
mkdir -p "$W/in"; chmod 777 "$W" "$W/in"
for f in "$P/$NAME".kicad_{pcb,pro,dru,sch} "$P"/fp-lib-table "$P"/sym-lib-table; do cp "$f" "$W/in/"; done
sed -i "s#\${KIPRJMOD}/..#$(dirname "$P")#" "$W/in/fp-lib-table" "$W/in/sym-lib-table"
python3 "$TOOLS/prep.py" "$W/in"
python3 "$TOOLS/preroute.py" "$W/in"       # before the pad vias, so they keep off the pre-routes
( cd "$W/in" && KICAD_KEEP_PRO=1 "$K" sh -c "python3 $R/maze.py $NAME.kicad_pcb gnd && python3 $R/lock.py $NAME.kicad_pcb lock" )
( cd "$W/in" && KICAD_KEEP_PRO=1 "$K" python3 "$R/../pcb/refill.py" $NAME.kicad_pcb )
for sd in $SEEDS; do
  B=$W/s$sd; cp "$W/in/$NAME.kicad_pro" $B.kicad_pro; cp "$W/in/$NAME.kicad_dru" $B.kicad_dru; cp "$W/in/fp-lib-table" "$W/"
  ( ulimit -v 8000000; nice -n 15 timeout 360 "$UR" route "$W/in/$NAME.kicad_pcb" -o $B.kicad_pcb $RECIPE --strip \
      --pour-cost 3 --seed $sd --threads 1 --timeout 240 --uuid-seed 1 --stats $B.json ) > $B.log 2>&1 || true
  echo "seed $sd: $(grep -o 'routed [0-9]* more, [0-9]* failed, [0-9]* open, [0-9.]* s' $B.log | tail -1) | $("$H/judge.sh" $B.kicad_pcb $W/j$sd 2>&1 | tr '\n' ' ') | necks: $(grep -c '^neck: [^K]' $B.log || true)"
done
echo "next: $H/finish.sh $W/j<SEED> $W/final"
