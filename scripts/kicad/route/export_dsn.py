"""export_dsn.py BOARD OUT.dsn  -- export a Specctra DSN for Freerouting."""
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
print('tracks', len(b.GetTracks()))
print('export', pcbnew.ExportSpecctraDSN(b, sys.argv[2]))
