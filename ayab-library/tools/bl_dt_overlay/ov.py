"""ov.py STEP OUT.png -- the model's four views drawn on the datasheet page itself, at the drawing's single
scale (30 px/mm on the 300 dpi render), each view anchored on the pegs (y 1.32 -> page row 725) and the body's
centre column; the front elevation on the PCB line (z 0 -> row 1432), the side view on z 0 -> column 1118.5."""
import sys, numpy as np, cadquery as cq
from PIL import Image, ImageDraw
from views import PAGE, PPM, row_of_y
COL = {'housing': (60, 60, 60), 'lever': (110, 110, 110), 'cover': (150, 170, 200), 'metal': (190, 160, 120)}
def kind(bb):
    if bb.zmin < -0.1: return 'housing'
    if bb.zmax <= 0.2: return 'metal'
    if bb.zmin >= Z_COVER: return 'cover'
    if bb.xmax > 6.5: return 'lever'
    return 'metal'
Z_COVER = 2.29
def load(path):
    out = []
    for s in cq.importers.importStep(path).solids().vals():
        v, t = s.tessellate(0.01, 0.12); out.append((np.array([(p.x, p.y, p.z) for p in v]), np.array(t), kind(s.BoundingBox())))
    return out
VIEWS = {
  'top':    (lambda P: np.c_[513 + P[:, 0] * PPM, row_of_y(P[:, 1])],  lambda P: P[:, 2], np.array([0, 0, 1.0])),
  'bottom': (lambda P: np.c_[1620 - P[:, 0] * PPM, row_of_y(P[:, 1])], lambda P: -P[:, 2], np.array([0, 0, -1.0])),
  'front':  (lambda P: np.c_[512.75 + P[:, 0] * PPM, 1432 - P[:, 2] * PPM], lambda P: -P[:, 1], np.array([0, -1.0, 0])),
  'side':   (lambda P: np.c_[1118.5 - P[:, 2] * PPM, row_of_y(P[:, 1])], lambda P: P[:, 0], np.array([1.0, 0, 0])),
}
BOX = (270, 420, 1960, 1500)
if __name__ == '__main__':
    solids = load(sys.argv[1])
    page = Image.open(PAGE).convert('L').crop(BOX)
    blk = np.array(page) < 128
    layer = Image.new('RGB', page.size, (255, 255, 255)); mask = Image.new('L', page.size, 0)
    dl, dm = ImageDraw.Draw(layer), ImageDraw.Draw(mask)
    for name, (proj, depth, viewdir) in VIEWS.items():
        tris = []
        for V, T, k in solids:
            for tri in T:
                p = V[tri]; n = np.cross(p[1] - p[0], p[2] - p[0]); ln = np.linalg.norm(n)
                if ln < 1e-12: continue
                n /= ln
                if n @ viewdir <= 0: continue
                lum = 0.7 + 0.3 * abs(n @ viewdir)
                tris.append((depth(p).mean(), proj(p) - BOX[:2], lum, k))
        tris.sort(key=lambda t: t[0])
        for _, Q, lum, k in tris:
            c = tuple(int(v * lum) for v in COL[k]); pts = [tuple(q) for q in Q]
            dl.polygon(pts, fill=c); dm.polygon(pts, fill=255)
    out = Image.composite(Image.blend(page.convert('RGB'), layer, 0.55), page.convert('RGB'), mask)
    a = np.array(out); a[blk] = (0, 0, 0); a[blk & (np.array(mask) > 0)] = (200, 0, 0)
    Image.fromarray(a).save(sys.argv[2]); print(sys.argv[2], out.size)
