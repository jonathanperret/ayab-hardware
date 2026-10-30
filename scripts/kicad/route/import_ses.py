"""import_ses.py BOARD SESSION.ses [lock]  -- import a Freerouting session (replaces routed nets), optionally lock tracks."""
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
print('import', pcbnew.ImportSpecctraSES(b, sys.argv[2]))
if len(sys.argv) > 3 and sys.argv[3] == 'lock':
    for t in b.GetTracks():
        t.SetLocked(True)
pcbnew.SaveBoard(sys.argv[1], b)
