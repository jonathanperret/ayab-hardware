"""Redraw the BL-DT thumb-wheel symbol body (pins untouched)."""
import math, re

def _poly(pts, ind, fill='none', w=0):
    xy = ' '.join('(xy %g %g)' % (round(x, 3), round(y, 3)) for x, y in pts)
    return (f'{ind}(polyline\n{ind}\t(pts\n{ind}\t\t{xy}\n{ind}\t)\n{ind}\t(stroke\n{ind}\t\t(width {w})\n'
            f'{ind}\t\t(type default)\n{ind}\t)\n{ind}\t(fill\n{ind}\t\t(type {fill})\n{ind}\t)\n{ind})\n')

def _head(tip, d, ind):
    # filled arrowhead at tip, pointing along unit vector d
    L, W = 0.9, 0.45
    bx, by = tip[0] - L * d[0], tip[1] - L * d[1]
    px, py = -d[1], d[0]
    return _poly([tip, (bx + W * px, by + W * py), (bx - W * px, by - W * py), tip], ind, 'outline')

def _text(s, x, y, ind, size=1.27):
    return (f'{ind}(text "{s}"\n{ind}\t(at {x:g} {y:g} 0)\n{ind}\t(effects\n{ind}\t\t(font\n'
            f'{ind}\t\t\t(size {size:g} {size:g})\n{ind}\t\t)\n{ind}\t)\n{ind})\n')

def _arc(c, R, a0, a1, ind, fill='none', w=0):
    p = lambda deg: (c[0] + R * math.cos(math.radians(deg)), c[1] + R * math.sin(math.radians(deg)))
    s, m, e = p(a0), p((a0 + a1) / 2), p(a1)
    return (f'{ind}(arc\n{ind}\t(start {s[0]:.3f} {s[1]:.3f})\n{ind}\t(mid {m[0]:.3f} {m[1]:.3f})\n{ind}\t(end {e[0]:.3f} {e[1]:.3f})\n'
            f'{ind}\t(stroke\n{ind}\t\t(width {w})\n{ind}\t\t(type default)\n{ind}\t)\n{ind}\t(fill\n{ind}\t\t(type {fill})\n{ind}\t)\n{ind})\n')

def body(ind):
    # housing with the half-disc wheel sticking out of its right side
    cx, cy, r, R = 8.89, 3.175, 4.445, 5.715
    o = (f'{ind}(rectangle\n{ind}\t(start -3.81 8.89)\n{ind}\t(end {cx:g} -2.54)\n{ind}\t(stroke\n{ind}\t\t(width 0.254)\n'
         f'{ind}\t\t(type default)\n{ind}\t)\n{ind}\t(fill\n{ind}\t\t(type background)\n{ind}\t)\n{ind})\n')
    o += _arc((cx, cy), r, 90, -90, ind, 'background', 0.254)
    for a in range(-75, 76, 15):
        c, s_ = math.cos(math.radians(a)), math.sin(math.radians(a))
        o += _poly([(cx + (r - 0.6) * c, cy + (r - 0.6) * s_), (cx + r * c, cy + r * s_)], ind)
    # roll (datasheet: rolling toward a terminal's side closes it): on the board the
    # B pad faces the USB side (down here), D the DIN side (up)
    p = lambda deg: (cx + R * math.cos(math.radians(deg)), cy + R * math.sin(math.radians(deg)))
    t = lambda deg, sgn: (sgn * -math.sin(math.radians(deg)), sgn * math.cos(math.radians(deg)))
    o += _arc((cx, cy), R, 20, 70, ind) + _head(p(70), t(70, 1), ind)
    o += _arc((cx, cy), R, -20, -70, ind) + _head(p(-70), t(-70, -1), ind)
    b, d = p(70), p(-70)
    o += _text('D', b[0] + 2.032, b[1] + 0.762, ind) + _text('B', d[0] + 2.032, d[1] - 0.762, ind)
    # push: into the housing
    o += _poly([(cx + R + 2.54, cy), (cx + r + 0.4, cy)], ind) + _head((cx + r + 0.25, cy), (-1, 0), ind)
    o += _text('C', cx + R + 3.81, cy, ind)
    return o

def redraw(sym):
    m = re.search(r'(\t+)\(rectangle\n\t+\(start -3.81 5.08\)\n\t+\(end 6.35 -2.54\)\n.*?\n\1\)\n', sym, re.S)
    assert m, 'BL-DT body not found'
    sym = sym[:m.start()] + body(m.group(1)) + sym[m.end():]
    sym = re.sub(r'(\(property "Reference" "S"\n\t+)\(at [^)]*\)', r'\1(at 2.54 12.7 0)', sym, count=1)
    sym = re.sub(r'(\(property "Value" "BL-DT"\n\t+)\(at [^)]*\)', r'\1(at 2.54 10.16 0)', sym, count=1)
    sym = sym.replace('"3-way switch (2 directions + push), common A"',
                      '"Thumb-wheel switch, common A: roll 24 deg toward the B terminal side closes A-B, toward the D side A-D; push closes A-C"')
    return sym

def block(t, start):
    i = t.index(start); d = 0; j = i
    while True:
        d += {'(': 1, ')': -1}.get(t[j], 0)
        if d == 0 and t[j] == ')': return i, j + 1
        j += 1
