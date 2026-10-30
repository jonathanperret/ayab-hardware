"""rm_dangling.py BOARD DRC_REPORT [--tracks]  -- remove vias (and with --tracks, track segments) and track segments reported as dangling in a KiCad DRC report."""
import pcbnew, sys, re
b = pcbnew.LoadBoard(sys.argv[1]); rpt = open(sys.argv[2]).read()
vias = [(float(x), float(y)) for x, y in re.findall(r'\[via_dangling\][^\[]*?@\(([\d.]+) mm, ([\d.]+) mm\): Via', rpt)]
trk = [(float(x), float(y)) for x, y in re.findall(r'\[track_dangling\][^\[]*?@\(([\d.]+) mm, ([\d.]+) mm\): Track', rpt)]
n = 0
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_VIA':
        x, y = pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)
        if any(abs(x - px) < 0.002 and abs(y - py) < 0.002 for px, py in vias):
            b.Remove(t); n += 1
    elif '--tracks' in sys.argv:
        ends = [(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)) for p in (t.GetStart(), t.GetEnd())]
        if any(abs(x - px) < 0.002 and abs(y - py) < 0.002 for px, py in trk for x, y in ends):
            b.Remove(t); n += 1
print('removed dangling', n)
pcbnew.SaveBoard(sys.argv[1], b)
