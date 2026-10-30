"""update_pcb.py BOARD NETLIST.net  -- apply a schematic netlist to the board, like "Update PCB from
Schematic" with default options: adds missing footprints (parked right of the board), updates values,
fields, sheet paths, pad nets and pin functions. Footprint swaps are reported, not done.
Export the netlist first: kicad-cli sch export netlist -o NETLIST.net PROJECT.kicad_sch
Runs inside the KiCad container."""
import os, re, sys, pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sexp
from sexp import kid, kids

board_path, net_path = sys.argv[1], sys.argv[2]
t = sexp.parse(open(net_path, encoding='utf-8').read())
S = lambda n, k, d='': str(kid(n, k)[1]) if kid(n, k) is not None and len(kid(n, k)) > 1 else d
comps, pins = {}, {}
for c in kids(kid(t, 'components'), 'comp'):
    fields = {}
    f = kid(c, 'fields')
    for fl in (kids(f, 'field') if f is not None else []):
        fields[str(kid(fl, 'name')[1])] = str(fl[2]) if len(fl) > 2 else ''
    comps[S(c, 'ref')] = dict(value=S(c, 'value'), footprint=S(c, 'footprint'), fields=fields,
                              path=S(kid(c, 'sheetpath'), 'tstamps') + S(c, 'tstamps'),
                              sheetname=S(kid(c, 'sheetpath'), 'names'))
for n in kids(kid(t, 'nets'), 'net'):
    for nd in kids(n, 'node'):
        pins.setdefault(S(nd, 'ref'), {})[S(nd, 'pin')] = [S(n, 'name'), S(nd, 'pinfunction'), S(nd, 'pintype')]
d = dict(comps=comps, pins=pins)
sch_file = os.path.splitext(os.path.basename(board_path))[0] + '.kicad_sch'

# footprint libraries from the project's fp-lib-table (${KIPRJMOD} = board directory), else KiCad's own
LIBS = {}
tbl = os.path.join(os.path.dirname(os.path.abspath(board_path)), 'fp-lib-table')
if os.path.exists(tbl):
    for name, uri in re.findall(r'\(lib \(name "([^"]+)"\).*?\(uri "([^"]+)"\)', open(tbl).read()):
        LIBS[name] = uri.replace('${KIPRJMOD}', os.path.dirname(os.path.abspath(board_path)))
b = pcbnew.LoadBoard(board_path)
fps = {f.GetReference(): f for f in b.GetFootprints()}
mm = pcbnew.FromMM
bb = b.GetBoardEdgesBoundingBox()
drop_x, drop_y = bb.GetRight() + mm(8), bb.GetTop() + mm(5)
# continue the column of footprints already waiting right of the board
for f in fps.values():
    if f.GetPosition().x > bb.GetRight():
        drop_y = max(drop_y, f.GetPosition().y + mm(5))

for ref in sorted(set(fps) - set(d['comps'])):
    print(f'not in schematic (kept): {ref}')

for ref, c in sorted(d['comps'].items()):
    lib, name = c['footprint'].split(':', 1)
    fp = fps.get(ref)
    if fp is None:
        fp = pcbnew.FootprintLoad(LIBS.get(lib, f'/usr/share/kicad/footprints/{lib}.pretty'), name)
        fp.SetFPIDAsString(c['footprint'])
        fp.SetReference(ref)
        fp.SetPosition(pcbnew.VECTOR2I(drop_x, drop_y))
        drop_y += mm(5)
        b.Add(fp)
        print(f'added {ref} {c["footprint"]}')
    elif fp.GetFPIDAsString() != c['footprint']:
        print(f'WARNING footprint differs for {ref}: {fp.GetFPIDAsString()} -> {c["footprint"]} (not swapped)')
    if fp.GetValue() != c['value']:
        print(f'{ref} value {fp.GetValue()} -> {c["value"]}')
        fp.SetValue(c['value'])
    fp.SetPath(pcbnew.KIID_PATH(c['path']))
    fp.SetSheetname(c['sheetname'])
    fp.SetSheetfile(sch_file)
    for k, v in c['fields'].items():
        if k in ('Footprint', 'Datasheet', 'Description', 'Value', 'Reference'):
            continue
        if fp.GetFieldText(k) != v if fp.HasField(k) else v:
            fp.SetField(k, v)
            if not fp.HasField(k): continue
            fp.GetField(k).SetVisible(False)
    for f in (fp.GetField('Description'),):
        if f is not None: f.SetText(c['fields'].get('Description', f.GetText()))
    pins = d['pins'].get(ref, {})
    for pad in fp.Pads():
        num = pad.GetNumber()
        if not num:
            continue
        netname, func, ptype = pins.get(num, ['', '', ''])
        net = b.FindNet(netname) if netname else None
        if netname and net is None:
            net = pcbnew.NETINFO_ITEM(b, netname)
            b.Add(net)
        old = pad.GetNetname()
        if old != netname:
            print(f'  {ref}.{num}: {old or "<none>"} -> {netname or "<none>"}')
        if net is not None:
            pad.SetNet(net)
        else:
            pad.SetNetCode(0)
        pad.SetPinFunction(func)
        pad.SetPinType(ptype)

b.BuildConnectivity()
pcbnew.SaveBoard(board_path, b)
