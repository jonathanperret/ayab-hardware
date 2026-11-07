"""preroute.py DIR -- short critical links drawn from pad positions (locked), the Kelvin rule area, judge settings."""
import json, re, sys, uuid
D = sys.argv[1]; P = D + '/ayab-sr-esp32.kicad_pcb'; s = open(P).read()
def seg(x0, y0, x1, y1, w, net, tag):
    u = uuid.uuid5(uuid.NAMESPACE_URL, 'ayab-sr-esp32 preroute ' + tag)
    return f'\t(segment\n\t\t(start {x0} {y0})\n\t\t(end {x1} {y1})\n\t\t(width {w})\n\t\t(locked yes)\n\t\t(layer "F.Cu")\n\t\t(net "{net}")\n\t\t(uuid "{u}")\n\t)\n'
add = ''
# Kelvin pair: U7 IN+/IN- straight to the inner side of the shunt's pads (R6), so the sense joins at the shunt
add += seg(111.73, 90.84, 112.6, 90.84, 0.25, '/Vout', 'k1a') + seg(112.6, 90.84, 112.6, 88.9, 0.25, '/Vout', 'k1b')
add += seg(116.03, 90.84, 115.2, 90.84, 0.25, '/Vsol', 'k2a') + seg(115.2, 90.84, 115.2, 88.9, 0.25, '/Vsol', 'k2b')
# J1 VBUS: leave both VBUS pad pairs straight out at 0.5 mm, clear of the CC/D+/D- pins beside them
add += seg(156.485, 109.47, 154.9, 109.47, 0.5, '+15V', 'v1') + seg(156.485, 104.57, 154.9, 104.57, 0.5, '+15V', 'v2')
area = f'''	(zone
		(net "")
		(name "kelvin-u7")
		(layers "F.Cu" "B.Cu")
		(uuid "{uuid.uuid5(uuid.NAMESPACE_URL, 'ayab-sr-esp32 kelvin-u7')}")
		(hatch edge 0.5)
		(connect_pads
			(clearance 0)
		)
		(min_thickness 0.25)
		(keepout
			(tracks allowed)
			(vias allowed)
			(pads allowed)
			(copperpour allowed)
			(footprints allowed)
		)
		(placement
			(enabled no)
			(sheetname "")
		)
		(fill
			(thermal_gap 0.5)
			(thermal_bridge_width 0.5)
		)
		(polygon
			(pts
				(xy 111.4 89.3) (xy 116.4 89.3) (xy 116.4 91.0) (xy 111.4 91.0)
			)
		)
	)
'''
k = s.index('\t(zone\n\t\t(net "GND")'); s = s[:k] + area + add + s[k:]
open(P, 'w').write(s)
dru = D + '/ayab-sr-esp32.kicad_dru'; t = open(dru).read()
if 'kelvin-u7' not in t:
    t += '''# The Kelvin sense tracks from R6's pads to U7 carry no current.
(rule "Kelvin sense into U7"
	(condition "A.NetClass == 'Power' && A.intersectsArea('kelvin-u7')")
	(constraint track_width (min 0.2mm))
)
'''
    open(dru, 'w').write(t)
pro = D + '/ayab-sr-esp32.kicad_pro'; p = json.load(open(pro)); r = p['board']['design_settings']['rules']
r['min_connection'] = 0.127          # the board's minimum track (JLCPCB 2-layer: 0.127 mm), LESSONS
r['min_resolved_spokes'] = 1         # every SMD GND pad also has its own via (pad vias laid before routing)
json.dump(p, open(pro, 'w'), indent=2)
print('ok')
