"""rotate_board.py BOARD ANGLE_DEG [X0 Y0]  -- rotate the whole board (footprints, tracks, vias, zones,
outline, drawings) by ANGLE (KiCad convention: positive = counter-clockwise on screen) around the centre
of the outline, then move it so the outline's top-left corner is at (X0, Y0) mm (default: unchanged).
Afterwards: upright.py, refill (kicad-cli pcb drc --refill-zones --save-board), check labels with DRC.
Runs inside the KiCad container."""
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1]); ang = float(sys.argv[2])
bb = b.GetBoardEdgesBoundingBox(); c = bb.GetCenter()
items = list(b.GetFootprints()) + list(b.GetTracks()) + list(b.Zones()) + list(b.GetDrawings())
for it in items:
    it.Rotate(c, pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))
if len(sys.argv) > 4:
    nb = b.GetBoardEdgesBoundingBox()
    off = pcbnew.VECTOR2I(pcbnew.FromMM(float(sys.argv[3])) - nb.GetLeft(), pcbnew.FromMM(float(sys.argv[4])) - nb.GetTop())
    for it in items:
        it.Move(off)
b.Save(sys.argv[1])
nb = b.GetBoardEdgesBoundingBox()
print('%d items; outline x %.3f..%.3f, y %.3f..%.3f' % (len(items), nb.GetLeft() / 1e6, nb.GetRight() / 1e6, nb.GetTop() / 1e6, nb.GetBottom() / 1e6))
