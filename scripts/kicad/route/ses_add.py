"""ses_add.py BOARD SESSION.ses  -- add the wires and vias of a Specctra session to a board WITHOUT removing existing tracks."""
import pcbnew, sys, re, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pcb'))
import sexp as sx
b = pcbnew.LoadBoard(sys.argv[1])
t = sx.parse(open(sys.argv[2]).read())
def kid(n, h):
    for c in n[1:]:
        if isinstance(c, list) and c and str(c[0]) == h:
            return c
def kids(n, h):
    return [c for c in n[1:] if isinstance(c, list) and c and str(c[0]) == h]
routes = kid(t, 'routes')
res = kid(routes, 'resolution')
scale = {'um': 1000.0, 'mm': 1e6, 'mil': 25400.0}[str(res[1])] / float(res[2])   # nm per unit
U = lambda v: int(round(float(v) * scale))
layers = {'F.Cu': pcbnew.F_Cu, 'B.Cu': pcbnew.B_Cu}
nw = kid(routes, 'network_out')
nt = nv = 0
for net in kids(nw, 'net'):
    name = str(net[1]).strip('"')
    ni = b.FindNet(name)
    if ni is None:
        print('unknown net', name); continue
    for w in kids(net, 'wire'):
        p = kid(w, 'path')
        layer, width = str(p[1]), U(p[2])
        pts = [(U(p[i]), -U(p[i + 1])) for i in range(3, len(p) - 1, 2)]
        for a, c in zip(pts, pts[1:]):
            tr = pcbnew.PCB_TRACK(b); tr.SetStart(pcbnew.VECTOR2I(*a)); tr.SetEnd(pcbnew.VECTOR2I(*c))
            tr.SetWidth(width); tr.SetLayer(layers[layer]); tr.SetNet(ni); b.Add(tr); nt += 1
    for v in kids(net, 'via'):
        m = re.search(r'_(\d+):(\d+)_um', str(v[1]))
        via = pcbnew.PCB_VIA(b); via.SetPosition(pcbnew.VECTOR2I(U(v[2]), -U(v[3])))
        via.SetWidth(int(m.group(1)) * 1000); via.SetDrill(int(m.group(2)) * 1000); via.SetNet(ni); b.Add(via); nv += 1
print('added tracks', nt, 'vias', nv)
pcbnew.SaveBoard(sys.argv[1], b)
