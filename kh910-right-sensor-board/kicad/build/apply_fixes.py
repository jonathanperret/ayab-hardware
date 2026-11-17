# write re-routed corners (board mm, from build_pcb.py KH_FIX mode) back into the tracer state
import json, sys, numpy as np
from scipy.interpolate import RBFInterpolator
state, fixed = sys.argv[1], sys.argv[2]
s = json.load(open(state)); FF = json.load(open(fixed)); F = FF['pts'] if 'pts' in FF else FF; W = FF.get('w', {})
PX, X0, Y0 = 21.0, 148.0, 303.0
ids = [p['id'] for p in s['pads'] if p.get('ok', {}).get('f') and p.get('ok', {}).get('b')]
P = {p['id']: p for p in s['pads']}
f2b = RBFInterpolator(np.array([P[k]['f'] for k in ids], float), np.array([P[k]['b'] for k in ids], float), kernel='thin_plate_spline', smoothing=5.0)
for k, pts in F.items():
    l = s['links'][int(k)]
    front = [[round(x * PX + X0, 1), round(y * PX + Y0, 1)] for x, y in pts]
    l['pts'] = front if l['layer'] == 'f' else [[round(a, 1), round(b, 1)] for a, b in f2b(np.array(front, float)).tolist()]
    l['board_pts'] = [[round(x, 3), round(y, 3)] for x, y in pts]; l['board_exact'] = True
    if k in W: l['board_width'] = W[k]
    l['note'] = (l.get('note', '') + ' rerouted for clearance on the KiCad board').strip()
json.dump(s, open(state, 'w'), indent=1); print('updated links', list(F))
