"""upright.py BOARD  -- turn upside-down texts (angle in (90, 270]) by 180 deg so they read from the
bottom or the right (after rotating a board). Runs inside the KiCad container."""
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
n = 0
items = list(b.GetDrawings())
for fp in b.GetFootprints(): items += list(fp.GetFields()) + list(fp.GraphicalItems())
for it in items:
    if it.GetClass() not in ('PCB_TEXT', 'PCB_FIELD'): continue
    a = it.GetTextAngleDegrees() % 360
    if 90 < a <= 270:
        it.SetTextAngleDegrees(a - 180); n += 1
b.Save(sys.argv[1])
print('flipped', n)
