# Compare the KiCad schematic's connectivity with the tracer netlist.
# Two-pin passives (R*, JP*) may be drawn either way round: their orientation is solved from the netlists and written to swap.json.
# Usage: python check_sch.py <tracer state.json> <kicad netlist (kicadsexpr)> <swap.json>
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicad_netlist

state, netfile, swapfile = sys.argv[1:4]
s = json.load(open(state)); P = {p['id']: p for p in s['pads']}
PINMAP = {'VR301': {1: '1', 2: '3', 3: '2'}}
pinof = {}
for pt in s['parts']:
    for i, pid in enumerate(pt['pins']): pinof[pid] = (pt['ref'], PINMAP.get(pt['ref'], {}).get(i + 1, str(i + 1)))
for c, i in zip('ABCDEFGHI', range(9)):
    pinof[next(k for k, p in P.items() if p['label'].startswith('pad ' + c))] = ('J1', str(i + 1))
for c, i in zip('JKLMNOP', range(7)):
    pinof[next(k for k, p in P.items() if p['label'].startswith('pad ' + c))] = ('J2', str(i + 1))
nc = {pinof[k] for k in s.get('nc', []) if k in pinof}
par = {k: k for k in P}
def f(a):
    while par[a] != a: par[a] = par[par[a]]; a = par[a]
    return a
for l in s['links']:
    if l['status'] != 'wrong': par[f(l['a'])] = f(l['b'])
T = {}
for k in P:
    if k in pinof and pinof[k] not in nc: T.setdefault(f(k), set()).add(pinof[k])
extra = {}
for j in s.get('jumpers', []):   # JP pin 1 joins tracer pad a, pin 2 pad b
    for pinno, pad in (('1', j['a']), ('2', j['b'])): T[f(pad)].add((j['ref'], pinno))
T = [frozenset(v) for v in T.values()]

Knets = kicad_netlist.parse(netfile)
Kg = {name: set(nodes) for name, nodes in Knets.items() if not name.startswith('unconnected-')}
pin2T = {p: i for i, g in enumerate(T) for p in g}
pin2K = {p: n for n, g in Kg.items() for p in g}
swappable = {r for g in T for r, _ in g if r.startswith(('R', 'JP'))}
swap = {}
def kname(p):
    r, n = p
    if r in swap and swap[r]: n = {'1': '2', '2': '1'}[n]
    return pin2K.get((r, n))
Kmap = {}  # kicad net -> tracer group index
for p, ti in pin2T.items():
    if p[0] not in swappable and pin2K.get(p): Kmap.setdefault(pin2K[p], set()).add(ti)
changed = True
while changed:
    changed = False
    for r in sorted(swappable - set(swap)):
        for opt in (False, True):
            ok = True; decided = False
            for n in ('1', '2'):
                kn = pin2K.get((r, {'1': '2', '2': '1'}[n] if opt else n)); ti = pin2T.get((r, n))
                if kn in Kmap:
                    decided = True
                    if Kmap[kn] != {ti}: ok = False
            if decided and ok:
                swap[r] = opt; changed = True
                for n in ('1', '2'):
                    kn = pin2K.get((r, {'1': '2', '2': '1'}[n] if opt else n)); Kmap.setdefault(kn, set()).add(pin2T[(r, n)])
                break
unresolved = swappable - set(swap)
# final comparison
Tsets = {frozenset(g) for g in T if len(g) > 1}
Ksets = set()
for n, g in Kg.items():
    ks = frozenset((r, {'1': '2', '2': '1'}[p] if swap.get(r) else p) for r, p in g)
    if len(ks) > 1: Ksets.add(ks)
only_T = Tsets - Ksets; only_K = Ksets - Tsets
json.dump(sorted(r for r, v in swap.items() if v), open(swapfile, 'w'))
print(f'tracer nets {len(Tsets)}, schematic nets {len(Ksets)}, flipped parts {sum(swap.values())}, unresolved {sorted(unresolved)}')
fmt = lambda g: ' '.join(sorted(f'{r}.{p}' for r, p in g))
for g in only_T: print('  only in tracer   :', fmt(g))
for g in only_K: print('  only in schematic:', fmt(g))
print('MATCH' if not only_T and not only_K and not unresolved else 'MISMATCH')
