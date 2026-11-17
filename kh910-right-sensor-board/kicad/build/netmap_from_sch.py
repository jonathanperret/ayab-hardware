# write netmap.json ("REF.PIN" -> net) and values into symmap.json from the schematic's exported netlist
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicad_netlist
netfile, projdir = sys.argv[1], sys.argv[2]
nets = kicad_netlist.parse(netfile)
json.dump({f'{r}.{p}': n for n, nodes in nets.items() for r, p in nodes}, open(os.path.join(projdir, 'netmap.json'), 'w'), indent=1)
t = open(netfile).read()
vals = dict(re.findall(r'\(comp\s*\(ref "([^"]+)"\)\s*\(value "([^"]*)"\)', t))
sm = json.load(open(os.path.join(projdir, 'symmap.json'))); sm['values'] = vals
json.dump(sm, open(os.path.join(projdir, 'symmap.json'), 'w'), indent=1)
print('nets', len(nets), 'parts', len(vals))
