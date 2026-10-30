"""edge_keepout.py BOARD add|remove [WIDTH_MM]

Add (or remove) a ring-shaped keep-out rule area (no tracks, no vias) along the inside of the board
outline, so Freerouting stays WIDTH mm (default 0.55) away from the edge. Runs inside the KiCad container.
"""
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM
NAME = 'autoroute_edge_keepout'
for z in list(b.Zones()):
    if z.GetIsRuleArea() and z.GetZoneName() == NAME:
        b.Remove(z)
if sys.argv[2] == 'add':
    w = float(sys.argv[3]) if len(sys.argv) > 3 else 0.55
    outline = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(outline, False)
    inner = pcbnew.SHAPE_POLY_SET(outline)
    inner.Deflate(MM(w), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
    ring = pcbnew.SHAPE_POLY_SET(outline)
    ring.BooleanSubtract(inner)
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu)
    z = pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetZoneName(NAME); z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowZoneFills(False)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    z.SetOutline(ring)
    b.Add(z)
pcbnew.SaveBoard(sys.argv[1], b)
