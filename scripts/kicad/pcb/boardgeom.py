"""Board outline and keep-out geometry read from the board itself (no hard-coded coordinates).

    geom = BoardGeom(board)
    geom.ok(x_mm, y_mm, margin_mm)   # inside the outline by `margin` and `margin` away from track keep-outs
    geom.bbox                        # (x0, y0, x1, y1) of the outline, mm
"""
import pcbnew

MM = pcbnew.FromMM


class BoardGeom:
    def __init__(self, board):
        self.outline = pcbnew.SHAPE_POLY_SET()
        board.GetBoardPolygonOutlines(self.outline, False)
        bb = board.GetBoardEdgesBoundingBox()
        self.bbox = (bb.GetLeft() / 1e6, bb.GetTop() / 1e6, bb.GetRight() / 1e6, bb.GetBottom() / 1e6)
        zones = list(board.Zones())
        for fp in board.GetFootprints():
            zones += list(fp.Zones())          # e.g. the ESP32 module's antenna keep-out
        self.keepouts = []
        for z in zones:
            if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
                self.keepouts.append(pcbnew.SHAPE_POLY_SET(z.Outline()))
        self._cache = {}

    def _polys(self, m):
        key = round(m, 3)
        if key not in self._cache:
            inner = pcbnew.SHAPE_POLY_SET(self.outline)
            inner.Deflate(MM(m), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
            grown = []
            for k in self.keepouts:
                g = pcbnew.SHAPE_POLY_SET(k)
                g.Inflate(MM(m), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
                grown.append(g)
            self._cache[key] = (inner, grown)
        return self._cache[key]

    def ok(self, x, y, m=0.0):
        inner, grown = self._polys(m)
        p = pcbnew.VECTOR2I(MM(x), MM(y))
        return inner.Contains(p) and not any(g.Contains(p) for g in grown)
