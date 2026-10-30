#!/usr/bin/env python3
"""netcmp.py A.net B.net  -- compare two KiCad netlists (kicad-cli sch export netlist).

Reports: whether every net connects the same pins (pin sets compared regardless of net names),
renamed nets, nets whose pins changed, and components whose value/footprint/fields changed.
Exit status 1 if connectivity differs. Runs on the host (plain Python)."""
import re, sys

def load(path):
    t = open(path, encoding='utf-8').read()
    nets = {n: frozenset(re.findall(r'\(ref "([^"]+)"\)\s+\(pin "([^"]+)"', body))
            for n, body in re.findall(r'\(net\s+\(code "\d+"\)\s+\(name "([^"]*)"\)(.*?)\n\t\t\)', t, re.S)}
    comps = {r: re.sub(r'\s+', ' ', body) for r, body in re.findall(r'\(comp\s+\(ref "([^"]+)"\)(.*?)\(sheetpath', t, re.S)}
    return nets, comps

(na, ca), (nb, cb) = load(sys.argv[1]), load(sys.argv[2])
same = set(na.values()) == set(nb.values())
print('nets %d -> %d, components %d -> %d, connectivity (pin sets) %s' % (len(na), len(nb), len(ca), len(cb), 'IDENTICAL' if same else 'DIFFERENT'))
by_pins = {v: k for k, v in na.items()}
for name, pins in sorted(nb.items()):
    old = by_pins.get(pins)
    if old is None:
        print('  changed net', name, sorted(pins))
    elif old != name:
        print('  renamed', old, '->', name)
for r in sorted(set(ca) | set(cb)):
    if ca.get(r) != cb.get(r):
        print('  component', r, 'added' if r not in ca else 'removed' if r not in cb else 'fields/value/footprint changed')
sys.exit(0 if same else 1)
