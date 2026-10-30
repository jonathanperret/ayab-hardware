"""silktext.py BOARD  -- raise every visible silkscreen text to at least 1.0 mm height / 0.15 mm stroke
(JLCPCB minimum). Runs inside the KiCad container."""
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
SL = (pcbnew.F_SilkS, pcbnew.B_SilkS)
H, T = pcbnew.FromMM(1.0), pcbnew.FromMM(0.15)
n = 0
items = list(b.GetDrawings())
for fp in b.GetFootprints(): items += list(fp.GraphicalItems()) + list(fp.GetFields())
for it in items:
    if it.GetLayer() in SL and it.GetClass() in ('PCB_TEXT', 'PCB_FIELD') and it.IsVisible():
        if it.GetTextHeight() < H or it.GetTextThickness() < T:
            print(it.GetParentFootprint().GetReference() if it.GetParentFootprint() else 'board', it.GetText(), pcbnew.ToMM(it.GetTextHeight()), pcbnew.ToMM(it.GetTextThickness()))
            it.SetTextSize(pcbnew.VECTOR2I(max(H, it.GetTextWidth()), max(H, it.GetTextHeight())))
            it.SetTextThickness(max(T, it.GetTextThickness()))
            n += 1
b.Save(sys.argv[1])
print('changed', n)
