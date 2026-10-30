#!/bin/bash
# kicad.sh CMD [ARGS...]  -- run a command (kicad-cli, python3 with pcbnew, sh -c ...) in the KiCad 10
# Docker image, with the repository and /tmp mounted at the same paths and the current directory kept.
#
#   scripts/kicad/kicad.sh kicad-cli pcb drc -o /tmp/drc.rpt ayab-sr-esp32/ayab-sr-esp32.kicad_pcb
#   scripts/kicad/kicad.sh python3 scripts/kicad/pcb/padcheck.py BOARD NETLIST
#   KICAD_IMAGE=mirror.gcr.io/kicad/kicad:10.0.7-full scripts/kicad/kicad.sh kicad-cli pcb render ...
#
# kicad-cli rewrites the .kicad_pro files it opens and leaves ~*.lck lock files behind: the .kicad_pro
# files are restored afterwards (set KICAD_KEEP_PRO=1 to keep its changes) and lock files removed.
# The swig "memory leak" noise of the pcbnew bindings is filtered out.
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
IMAGE=${KICAD_IMAGE:-mirror.gcr.io/kicad/kicad:10.0.7}
docker info >/dev/null 2>&1 || "$REPO/scripts/setup-kicad.sh" --start-docker >&2 || exit 1

WORK=$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || echo "$PWD")
SNAP=$(mktemp -d)
[ -z "$KICAD_KEEP_PRO" ] && (cd "$WORK" && find . -name '*.kicad_pro' -not -path './.git/*' -exec cp --parents {} "$SNAP" \;)

# the tools' checkout, and the checkout being worked on if different (e.g. tooling worktree vs design branch)
MOUNTS=(-v "$REPO:$REPO" -v /tmp:/tmp)
case "$WORK/" in "$REPO/"*|/tmp/*) ;; *) MOUNTS+=(-v "$WORK:$WORK") ;; esac
docker run --rm -u 0 -e HOME=/home/kicad -e TMPDIR=/var/tmp "${MOUNTS[@]}" -w "$PWD" "$IMAGE" "$@" 2>&1 \
  | { grep -v --line-buffered 'swig/python detected a memory leak\|no destructor found\|^Debug:\|^[0-9:]*: Debug:' || true; }
status=${PIPESTATUS[0]}

[ -z "$KICAD_KEEP_PRO" ] && (cd "$SNAP" && find . -name '*.kicad_pro' -exec cp {} "$WORK/{}" \;)
rm -rf "$SNAP"
find "$WORK" -name '~*.lck' -not -path '*/.git/*' -delete
exit $status
