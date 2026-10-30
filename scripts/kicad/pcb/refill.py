"""refill.py BOARD  -- refill all copper zones and save (same as kicad-cli pcb drc --refill-zones --save-board)."""
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(sys.argv[1], b)
