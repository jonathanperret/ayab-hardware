"""Import a Freerouting session, add GND stitching vias next to SMD GND pads, refill zones, save."""
import pcbnew, sys, math
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pcb'))
from boardgeom import BoardGeom
board_path, ses = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(board_path)
if ses != '-':
    print('import', pcbnew.ImportSpecctraSES(b, ses))
mm, MM = pcbnew.ToMM, pcbnew.FromMM
gnd = b.FindNet('GND')
VIA_D, VIA_DRILL, STUB_W, CLR = 0.6, 0.3, 0.4, 0.2
GEOM = BoardGeom(b)
edge = b.GetBoardEdgesBoundingBox()

def edge_ok(x, y):
    return GEOM.ok(x, y, 0.5 + VIA_D / 2)

def collides(x, y, r, layers=('F', 'B')):
    p = pcbnew.VECTOR2I(MM(x), MM(y))
    acc = MM(r + CLR)
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == gnd.GetNetCode() and pad.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                continue
            if pad.HitTest(p, acc):
                return True
            if pad.HasHole() and math.dist((x, y), (mm(pad.GetPosition().x), mm(pad.GetPosition().y))) < r + 0.25 + mm(pad.GetDrillSize().x) / 2:
                return True
    for t in b.GetTracks():
        if t.GetNetCode() == gnd.GetNetCode():
            continue
        if t.HitTest(p, acc):
            return True
    return False

def seg_free(x0, y0, x1, y1, w):
    n = max(2, int(math.dist((x0, y0), (x1, y1)) / 0.1))
    for i in range(n + 1):
        x, y = x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n
        if collides(x, y, w / 2):
            return False
    return True

added = 0
for fp in b.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNetCode() != gnd.GetNetCode() or pad.HasHole():
            continue
        if not pad.IsOnLayer(pcbnew.F_Cu):
            continue
        px, py = mm(pad.GetPosition().x), mm(pad.GetPosition().y)
        bb = pad.GetBoundingBox()
        half = max(mm(bb.GetWidth()), mm(bb.GetHeight())) / 2
        # already has a GND via close by?
        if any(t.GetClass() == 'PCB_VIA' and t.GetNetCode() == gnd.GetNetCode() and math.dist((px, py), (mm(t.GetPosition().x), mm(t.GetPosition().y))) < half + 1.2 for t in b.GetTracks()):
            continue
        stub_w = 0.25 if min(mm(pad.GetSize(pcbnew.F_Cu).x), mm(pad.GetSize(pcbnew.F_Cu).y)) < 0.5 else STUB_W
        cx, cy = mm(fp.GetPosition().x), mm(fp.GetPosition().y)
        away = math.atan2(py - cy, px - cx) if (px, py) != (cx, cy) else 0
        done = False
        for dist in (half + 0.7, half + 1.0, half + 1.4, half + 1.9, half + 2.5):
            for k in range(24):
                ang = away + (k // 2 + 1) // 1 * (math.pi / 12) * (1 if k % 2 else -1) if k else away
                vx, vy = px + dist * math.cos(ang), py + dist * math.sin(ang)
                if not edge_ok(vx, vy) or collides(vx, vy, VIA_D / 2):
                    continue
                # stub leaves the pad from its centre; ignore the first part inside the pad itself
                if not seg_free(px, py, vx, vy, stub_w):
                    continue
                via = pcbnew.PCB_VIA(b); via.SetPosition(pcbnew.VECTOR2I(MM(vx), MM(vy)))
                via.SetWidth(MM(VIA_D)); via.SetDrill(MM(VIA_DRILL)); via.SetNet(gnd); b.Add(via)
                tr = pcbnew.PCB_TRACK(b); tr.SetStart(pad.GetPosition()); tr.SetEnd(via.GetPosition())
                tr.SetWidth(MM(stub_w)); tr.SetLayer(pcbnew.F_Cu); tr.SetNet(gnd); b.Add(tr)
                added += 1; done = True
                break
            if done:
                break
        if not done:
            # fall back: straight F.Cu link to the nearest GND copper (pad or via) within 4 mm
            targets = []
            for f2 in b.GetFootprints():
                for p2 in f2.Pads():
                    if p2.GetNetCode() == gnd.GetNetCode() and p2 is not pad and p2.IsOnLayer(pcbnew.F_Cu) and not (f2.GetReference() == fp.GetReference() and p2.GetNumber() == pad.GetNumber()):
                        targets.append((mm(p2.GetPosition().x), mm(p2.GetPosition().y)))
            for t in b.GetTracks():
                if t.GetClass() == 'PCB_VIA' and t.GetNetCode() == gnd.GetNetCode():
                    targets.append((mm(t.GetPosition().x), mm(t.GetPosition().y)))
            for tx, ty in sorted(targets, key=lambda q: math.dist(q, (px, py))):
                if math.dist((tx, ty), (px, py)) > 4.0:
                    break
                if math.dist((tx, ty), (px, py)) < 0.05:
                    continue
                if seg_free(px, py, tx, ty, stub_w):
                    tr = pcbnew.PCB_TRACK(b); tr.SetStart(pad.GetPosition()); tr.SetEnd(pcbnew.VECTOR2I(MM(tx), MM(ty)))
                    tr.SetWidth(MM(stub_w)); tr.SetLayer(pcbnew.F_Cu); tr.SetNet(gnd); b.Add(tr)
                    added += 1; done = True
                    break
        if not done:
            print('no via for', fp.GetReference(), pad.GetNumber())
print('GND vias added', added)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(board_path, b)
