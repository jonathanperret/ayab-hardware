"""padcheck.py BOARD NETLIST.net  -- check the board against a schematic netlist, without changing it:
every footprint exists with the same value and footprint ID, every pad is on the netlist's net
(unconnected-* nets match by name prefix only). Prints mismatches and a summary line; exit status 1
if anything differs. Runs inside the KiCad container."""
import os, re, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
t = open(sys.argv[2], encoding='utf-8').read()
N = {}
for n, body in re.findall(r'\(net\s+\(code "\d+"\)\s+\(name "([^"]*)"\)(.*?)\n\t\t\)', t, re.S):
    for r, p in re.findall(r'\(ref "([^"]+)"\)\s+\(pin "([^"]+)"', body):
        N[(r, p)] = n
C = {r: (v, f) for r, v, f in re.findall(r'\(comp\s+\(ref "([^"]+)"\)\s+\(value "([^"]*)"\)\s+\(footprint "([^"]*)"\)', t)}
bad = 0
refs = set()
for fp in b.GetFootprints():
    r = fp.GetReference(); refs.add(r)
    if r in C and (fp.GetValue(), fp.GetFPIDAsString()) != C[r]:
        print('VALUE/FOOTPRINT', r, (fp.GetValue(), fp.GetFPIDAsString()), '!= schematic', C[r]); bad += 1
    for pad in fp.Pads():
        if not pad.GetNumber():
            continue
        want, have = N.get((r, pad.GetNumber()), ''), pad.GetNetname()
        if want != have and not (want.startswith('unconnected-') and have.startswith('unconnected-')):
            print('PAD', r, pad.GetNumber(), 'board', repr(have), 'schematic', repr(want)); bad += 1
missing = sorted(set(C) - refs)
if missing:
    print('MISSING on board:', missing); bad += len(missing)
print('footprints %d, schematic components %d, mismatches %d' % (len(refs), len(C), bad))
sys.exit(1 if bad else 0)
