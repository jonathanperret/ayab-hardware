#!/bin/bash
# route.sh BOARD.kicad_pcb WORKDIR CONFIG  -- autoroute a placed board in WORKDIR (the input board is not
# modified; the result is WORKDIR/r.kicad_pcb, copy it back yourself after checking it):
#   pass A  Freerouting on the power nets only ($POWER_NETS), imported as-is
#   fixups  maze.py pad-to-pad routes ($PRE_ROUTES), GND fan-out vias for SMD pads (import_fanout.py,
#           maze.py gnd), then every existing track is locked
#   pass B  Freerouting on everything else (power classes narrowed to $PASS_B_WIDTHS so they fit)
#   finish  session added on top of the locked tracks (ses_add.py), edge keep-out removed, GND stitching
#           vias every $STITCH mm, zones refilled, dangling vias removed, remaining DRC unconnected pairs
#           routed by maze.py fixdrc; final DRC summary in WORKDIR/drc_final.rpt
# CONFIG is a shell file setting POWER_NETS, PRE_ROUTES ("REF:PAD REF:PAD WIDTH;..."), PASS_B_WIDTHS
# ("Class=um,..."), PASS_A_PASSES, PASS_B_PASSES, STITCH. See ayab-sr-esp32/tools/route.conf.
# Needs Java + Freerouting (scripts/setup-kicad.sh) and the KiCad container.
set -e
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
T="$REPO/scripts/kicad"; K="$T/kicad.sh"
BOARD=$(realpath "$1"); W=$(realpath -m "$2"); source "$3"
JAR=${FREEROUTING_JAR:-$HOME/.cache/kicad-tools/freerouting-2.5.0.jar}
JAVA=${FREEROUTING_JAVA:-$(ls /usr/lib/jvm/java-25-*/bin/java 2>/dev/null | head -1)}; JAVA=${JAVA:-java}   # Freerouting 2.5 needs Java 25
FR="timeout ${FR_TIMEOUT:-2400} $JAVA -Djava.awt.headless=true -jar $JAR --gui.enabled=false --usage_and_diagnostic_data.disable_analytics=true"
PRO=$(ls "$(dirname "$BOARD")"/*.kicad_pro | head -1)
mkdir -p "$W"; cd "$W"
pro() { cp "$PRO" "$1.kicad_pro"; }    # net classes live in the project file
cp "$BOARD" w.kicad_pcb; pro w
cp "$(dirname "$BOARD")"/fp-lib-table "$(dirname "$BOARD")"/sym-lib-table . 2>/dev/null || true

"$K" sh -c "python3 $T/route/edge_keepout.py w.kicad_pcb add && python3 $T/route/export_dsn.py w.kicad_pcb full.dsn"
python3 "$T/route/prep_dsn.py" full.dsn
python3 "$T/route/filter_dsn.py" full.dsn passA.dsn keep "$POWER_NETS"
$FR -de passA.dsn -do passA.ses -mp ${PASS_A_PASSES:-60} > frA.log 2>&1 || true
echo "pass A: $(grep -o 'final score.*violations)' frA.log || echo 'see frA.log')"

cp w.kicad_pcb a.kicad_pcb; pro a
CMDS="python3 $T/route/import_ses.py a.kicad_pcb passA.ses"
IFS=';' read -ra PR <<< "${PRE_ROUTES:-}"
for r in "${PR[@]}"; do [ -n "${r// }" ] && CMDS="$CMDS && python3 $T/route/maze.py a.kicad_pcb pads $r"; done
CMDS="$CMDS && (python3 $T/route/import_fanout.py a.kicad_pcb - > fanout.log 2>&1; true) && python3 $T/route/maze.py a.kicad_pcb gnd"
CMDS="$CMDS && python3 $T/route/lock.py a.kicad_pcb lock && python3 $T/route/export_dsn.py a.kicad_pcb passB.dsn"
"$K" sh -c "$CMDS"
python3 "$T/route/prep_dsn.py" passB.dsn
[ -n "${PASS_B_WIDTHS:-}" ] && python3 "$T/route/filter_dsn.py" passB.dsn passB.dsn width "$PASS_B_WIDTHS"
$FR -de passB.dsn -do passB.ses -mp ${PASS_B_PASSES:-150} > frB.log 2>&1 || true
echo "pass B: $(grep -o 'final score.*violations)' frB.log || echo 'see frB.log')"
awk '/could not be routed/{f=1} f' frB.log | grep -v 'INFO\|pass #\|JAVA' | tail -12 || true

cp a.kicad_pcb r.kicad_pcb; pro r
"$K" sh -c "python3 $T/route/ses_add.py r.kicad_pcb passB.ses && python3 $T/route/lock.py r.kicad_pcb unlock \
 && python3 $T/route/edge_keepout.py r.kicad_pcb remove && python3 $T/route/maze.py r.kicad_pcb stitch ${STITCH:-3.0} \
 && python3 $T/pcb/refill.py r.kicad_pcb && kicad-cli pcb drc -o drc_r0.rpt r.kicad_pcb >/dev/null \
 && python3 $T/route/rm_dangling.py r.kicad_pcb drc_r0.rpt && python3 $T/pcb/refill.py r.kicad_pcb \
 && kicad-cli pcb drc -o drc_r1.rpt r.kicad_pcb >/dev/null && python3 $T/route/maze.py r.kicad_pcb fixdrc drc_r1.rpt 0.25 \
 && python3 $T/pcb/refill.py r.kicad_pcb && kicad-cli pcb drc --severity-all -o drc_final.rpt r.kicad_pcb"
grep -o '^\[[a-z_]*\]' drc_final.rpt | sort | uniq -c
echo "result: $W/r.kicad_pcb"
