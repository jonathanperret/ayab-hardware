---
name: kicad-board-workflow
description: How to work on the KiCad 10 boards in this repo (ayab-sr-esp32 first) headless in a cloud container - environment setup, schematic and PCB edits by script, updating the PCB from the schematic, autorouting with Freerouting, the checks to run before every push, regenerating production files and renders, JLCPCB conventions and known KiCad 10 gotchas. Use for any change to a .kicad_sch, .kicad_pcb, production/ or enclosure file.
---

# KiCad board workflow (headless)

Working with the user: once a change is made and checked, offload the long mechanical tail
(production files, board renders, viewer, enclosure regen/fit check, commit and push) to a
background agent, and stay available for the next request instead of running it in the foreground.

Tools: `scripts/kicad/` (generic), `ayab-sr-esp32/tools/` (project), `ayab-sr-esp32/enclosure/tools/`.
Every script has a usage docstring at the top. "(container)" = runs in the KiCad image through
`scripts/kicad/kicad.sh`; the rest runs on the host.

## 1. Environment

The tooling lives on the `tooling` branch; design work happens on other branches. Check it out next
to the design checkout and point the tools at the design project:

    git worktree add ../tooling tooling
    ../tooling/scripts/kicad/check.sh ayab-sr-esp32 [GIT_REF]     # run from the design checkout

(`kicad.sh` mounts both checkouts; `check.sh` falls back to `ayab-sr-esp32/check-baseline.txt` here.)

    scripts/setup-kicad.sh            # once per container: Docker daemon, KiCad 10.0.7 images, Java 25,
                                      # Freerouting 2.5.0, OpenSCAD, xvfb, ffmpeg, rsvg-convert, numpy/pillow
    scripts/kicad/kicad.sh CMD ...    # run kicad-cli / python3 (pcbnew) in mirror.gcr.io/kicad/kicad:10.0.7

- KiCad is used from Docker, not installed: `kicad.sh` mounts the repo and /tmp at the same paths and
  keeps the current directory, so relative paths work. Use `KICAD_IMAGE=...:10.0.7-full` for 3D
  (renders, STL/GLB export). Pull from mirror.gcr.io: Docker Hub rate-limits.
- The Docker daemon has no systemd and dies every hour or so ("Cannot connect to the Docker daemon"):
  `kicad.sh` restarts it; or `scripts/setup-kicad.sh --start-docker`.
- `scripts/dependencies.sh` is the GitHub CI's native install (KiCad 9 PPA); not used here.
- Network allow-list needed: apt mirrors, mirror.gcr.io, repo1.maven.org; jlcpcb.com for prices.

## 2. Looking at things

    scripts/kicad/view.sh P/P.kicad_sch /tmp/sch.png          # whole sheet as PNG (rsvg-convert)
    scripts/kicad/view.sh P/P.kicad_pcb /tmp/top.png           # F.Cu+mask+silk+outline
    VIEW_MIRROR=1 scripts/kicad/view.sh P/P.kicad_pcb /tmp/b.png B.Cu,Edge.Cuts
    scripts/kicad/render_board.sh P P/renders [--anim]        # raytraced stills (minutes; --anim: turntable)
    ayab-sr-esp32/tools/viewer.sh                             # three.js page models (viewer/), seconds

Crop large PNGs with ImageMagick before viewing; show the user one view per change unless asked.

## 3. Editing the schematic (no GUI)

- `.kicad_sch` is an s-expression file; edit it with small Python scripts working on top-level items
  (`ayab-sr-esp32/tools/schematic/sx.py: items()` splits them). Keep uuids unique; derive new ones
  with uuid5 so reruns are deterministic.
- Symbol instance properties: field `(at ...)` is absolute, but its angle and justify are interpreted
  relative to the symbol's rotation (a 90-deg resistor's "horizontal" label has angle 90, and left/
  right justify swap). Check the PNG after every field move.
- Power symbols point up (supply) / down (GND). Every placed part needs an `LCSC` field (JLCPCB).
- ayab-sr-esp32's sheet is generated: `tools/schematic/build.sh` rebuilds it from tools/schematic/base.kicad_sch (the hand-drawn revision) with
  prep.py (labels, PWR_FLAGs, no-connects, fields, symbol graphics) and layout.py (A2 sections,
  regions.py + targets.json). The output must equal the committed file. Either extend those scripts
  and rebuild, or edit the .kicad_sch directly (then the scripts are only history).
- Library symbols live in `ayab-library/ayab-lib.kicad_sym`; the schematic embeds a copy
  (`lib_symbols`): change both, or ERC reports lib_symbol_mismatch.

## 4. Schematic -> PCB

    scripts/kicad/kicad.sh kicad-cli sch export netlist -o /tmp/n.net P.kicad_sch
    scripts/kicad/kicad.sh python3 scripts/kicad/pcb/update_pcb.py P.kicad_pcb /tmp/n.net   # (container)

Adds missing footprints (parked right of the board), updates values/fields/pad nets; reports
footprint swaps (do those by editing the footprint ID). Net renames need the same rename in the PCB
(text substitution of `(net "old")`, then refill zones). A pin moved off a net leaves its old tracks
on the old net: remove the track(s) touching the pad, then `pcb/prune.py BOARD NET,NET` (container)
takes the rest of the dangling chain in one call (`route/rm_dangling.py` removes one segment per
DRC pass, and the router leaves chains of 0.1 mm segments).
When a symbol is copied from another instance, check its flags: `in_bom` / `in_pos_files` / `dnp`
come along (a socket cloned from the DNP debug header J14 ended up out of the BOM).

## 5. PCB edits and routing

- pcbnew scripts: load with `pcbnew.LoadBoard`, save with `board.Save(path)`/`pcbnew.SaveBoard`.
  Collect objects into a list before modifying (iterating `GetFootprints()` while adding/removing
  breaks), and avoid `GetFPIDAsString()` / `GetLibItemName()` before other calls in the same
  script, and do not use the board object again after `Save()`: in KiCad 10's Python these can
  corrupt swig types (later calls return a bare SwigPyObject).
  Plain-text edits of the .kicad_pcb are often simpler (footprint graphics are stored in footprint
  coordinates; pads keep `(at x y angle)` with the absolute angle).
- Refill zones after any copper change: `kicad.sh kicad-cli pcb drc --refill-zones --save-board ...`.
- Autoroute: `scripts/kicad/route/route.sh P.kicad_pcb /tmp/route ayab-sr-esp32/tools/route.conf`
  (power-first Freerouting pass, maze.py pad links and GND fan-outs, locked, then signals, stitching,
  dangling cleanup, DRC-driven fixes). Result in /tmp/route/r.kicad_pcb: inspect, check, copy back.
  Freerouting leaves a few nets: finish with `route/maze.py BOARD pads|rip|fixdrc` (board outline and
  keep-outs are read from the board by pcb/boardgeom.py). Freerouting pitfalls: give fine-pitch
  classes the SMD-SMD clearance exception (prep_dsn.py), keep it off the edge (edge_keepout.py),
  wide power classes must be narrowed for the second pass, and it rips up anything not locked.
- Growing the board: `pcb/stretch.py IN OUT DY STATIC --keep REFS [--move-point X,Y]` (host) moves
  everything outside STATIC (rectangles) by DY and stretches the tracks crossing its horizontal sides
  with vertical extensions; tracks crossing its vertical sides are deleted and listed: reroute them
  (`route/maze.py BOARD fixdrc DRC_REPORT`), then `pcb/prune.py`, refill, check.
- Board cut-outs and holes are Edge.Cuts graphics: remove stitching vias left outside the outline
  (they show up as unconnected/dangling) and those within 0.5 mm of a new edge (copper_edge_clearance).
- Silkscreen: `pcb/placeref.py BOARD REFS` moves labels clear, `pcb/silktext.py` enforces 1.0/0.15 mm,
  `pcb/clipsilk.py` clips outlines off pads (then put the clipped footprint in ayab-library so the
  board still matches its library), `pcb/upright.py` after `pcb/rotate_board.py`.

## 6. Before every push

    scripts/kicad/check.sh ayab-sr-esp32 [GIT_REF]

ERC/DRC by type against `ayab-sr-esp32/check-baseline.txt` (today: ERC 0, DRC 0), 0 unconnected,
pad-net check of the board vs the schematic (66 footprints, 0 mismatches), and with a ref the
netlist comparison (83 nets; pin sets must stay identical unless the change is meant to alter
connectivity, in which case "CHECKS FAILED" is expected: read the listed nets and make sure they
are exactly the intended ones; renames are listed). For a layout-only change, compare with
the last commit. Then regenerate outputs (7) and look at a PNG of what changed.

## 7. Production files and renders

Run from the design checkout (T=../tooling):

    $T/scripts/kicad/production.sh ayab-sr-esp32     # gerbers/, drill, zip, pos, cpl-jlc, bom, schematic PDF
    $T/scripts/kicad/render_board.sh ayab-sr-esp32 ayab-sr-esp32/renders
    $T/ayab-sr-esp32/tools/viewer.sh                  # viewer/board.glb, tray/lid STL, PARTS table
    $T/ayab-sr-esp32/enclosure/tools/regen.sh /tmp/enc [--full] [--install]   # STLs + fit check (+ renders)

regen.sh takes the board, the .scad and the enclosure tools of the current checkout. Its component list
is the placement file plus the BOM (not DNP): U5 (OLED module, plugged into J15 by hand) is in the BOM
only. Its fit check should report "no collision"; U5 within 0.2 mm of the tray is the support block
(0.1 mm gap by design). production.sh rewrites the schematic PDF (dates only when the schematic did
not change: `git checkout` it then).

`.gitignore` ignores *.csv and *.zip: `git add -f` the BOM, pos/CPL and the Gerber zip. Gerber diffs
should only show dates when copper did not change. README galleries use renders/ and enclosure/renders/.

## 8. JLCPCB conventions

- Cheapest tier: 2 layers, <= 100 x 100 mm, 1.6 mm, HASL, Economic assembly (top side, 2-50 boards).
  Design rules: `P.kicad_dru` (2-layer JLCPCB limits, from the silverreed shield) + documented
  exceptions; vias 0.3/0.6 mm (0.2/0.25 mm holes under 0.45 mm diameter cost extra).
- Each unique extended part costs ~$3 per order: prefer basic parts. Check stock and prices live with
  `scripts/kicad/jlc/jlc_parts.py KEYWORD|LCSC` and `jlc/bom_cost.py production/P-bom.csv 5 20 50`.
- Rotation/position corrections: symbol fields `FT Rotation Offset` / `FT Position Offset` (Fabrication
  Toolkit convention), applied by `jlc/jlc_cpl.py` into `production/P-cpl-jlc.csv`; verify every part in
  JLCPCB's placement preview and record new offsets as fields.

## 9. Gotchas

- kicad-cli rewrites the .kicad_pro it opens and leaves ~*.lck files: kicad.sh restores/removes them;
  if you run docker by hand, `git checkout *.kicad_pro` and delete the locks.
- Files written in the container are root-owned; saving into /tmp needs `-u 0` (kicad.sh does it).
- DRC exclusions in .kicad_pro could not be authored headlessly (marker positions unknown): use rule
  exceptions with `(severity ignore)` in the .kicad_dru, scoped by `A.memberOfFootprint('REF')` or
  `A.Reference`.
- `kicad-cli pcb render` / STL export need the -full image; --subst-models for missing STEP models.
- OpenSCAD 2021: no --animate on the command line and `-D $t` is ignored: pass a variable (tt).
- Fit check, enclosure .scad and tools use KiCad x, Y = -y, Z = 0 at PCB bottom; the case model is
  drawn in the board's original frame and turned by `board_frame()` (board was rotated 90 deg; its
  pivot is fixed at the old board centre). Current board (x, y) = old (y + 75.9, 215 - x): moving a
  part down by d on the board is old x - d in the .scad. sections.py works in the current frame.
