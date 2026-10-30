"""lock.py BOARD lock|unlock  -- lock or unlock every track and via (Freerouting keeps locked tracks fixed)."""
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
for t in b.GetTracks():
    t.SetLocked(sys.argv[2] == 'lock')
pcbnew.SaveBoard(sys.argv[1], b)
