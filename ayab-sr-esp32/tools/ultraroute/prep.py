"""prep.py DIR -- turn the board in DIR into ultraroute's input (in place): bare copper, mechanical parts
locked, GND pour on B.Cu only (the soft plane while routing), edge strips, width rules, strict DRC severities."""
import json, re, sys, uuid
D = sys.argv[1]; P = D + "/ayab-sr-esp32.kicad_pcb"
s = open(P).read()
# 1. bare board: drop every track, arc and via (zones stay)
s, n = re.subn(r'\n\t\((?:segment|arc|via)\n.*?\n\t\)', '', s, flags=re.S)
print('copper items removed', n)
# 2. lock the parts the mechanics fix, unlock the rest
LOCK = {'J1', 'J2', 'J3', 'J15', 'U5', 'S1', 'H1', 'H2', 'H3', 'U3'}
def fp(m):
    b = m.group(0); ref = re.search(r'\(property "Reference" "([^"]+)"', b).group(1)
    b = re.sub(r'\n\t\t\(locked (?:yes|no)\)', '', b, count=1)
    if ref in LOCK:
        b = re.sub(r'(\n\t\t\(layer "[^"]+"\))', r'\1\n\t\t(locked yes)', b, count=1)
    return b
s = re.sub(r'\n\t\(footprint ".*?\n\t\)(?=\n)', fp, s, flags=re.S)
# 3. GND pour: B.Cu only while routing, saved fill dropped (refilled on the bare board next)
i = s.index('\t(zone\n\t\t(net "GND")'); j = s.index('\n\t)\n', i) + 3
z = s[i:j]
z = z.replace('(layers "F.Cu" "B.Cu")', '(layer "B.Cu")', 1)
z = re.sub(r'\n\t\t\(filled_polygon\n.*?\n\t\t\)', '', z, flags=re.S)
z = re.sub(r'\(clearance [\d.]+\)', '(clearance 0.3)', z, count=1)    # explicit pour clearance (LESSONS)
s = s[:i] + z + s[j:]
# 4. edge strips: no tracks or vias between connector pads and the board edge (pours allowed)
def strip(name, x0, y0, x1, y1):
    return f'''	(zone
		(net "")
		(name "{name}")
		(layers "F.Cu" "B.Cu")
		(uuid "{uuid.uuid5(uuid.NAMESPACE_URL, 'ayab-sr-esp32 ' + name)}")
		(hatch edge 0.5)
		(connect_pads
			(clearance 0)
		)
		(min_thickness 0.25)
		(keepout
			(tracks not_allowed)
			(vias not_allowed)
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
				(xy {x0} {y0}) (xy {x1} {y0}) (xy {x1} {y1}) (xy {x0} {y1})
			)
		)
	)
'''
strips = strip('edge-usbc', 162.45, 86.6, 164.6, 120.1) + strip('edge-din', 99.9, 33.6, 123.9, 35.1) + strip('edge-j14', 99.9, 60.0, 101.75, 82.0)
k = s.index('\t(zone\n\t\t(net "GND")'); s = s[:k] + strips + s[k:]
open(P, 'w').write(s)
# 5. width rules KiCad DRC enforces and ultraroute routes to (LESSONS: a class width is only a target)
dru = D + '/ayab-sr-esp32.kicad_dru'; t = open(dru).read()
if 'Power nets minimum width' not in t:
    t += '''
# --- Routing rules (ultraroute and KiCad DRC both apply them) ---
# Power class (+15V, Vout, Vsol, U6 switch node): about 1 A of solenoid current; 0.4 mm keeps a 1 oz
# outer track under 10 C rise (IPC-2221) and still enters J1's and U6's pads; 0.6 mm where there is room.
(rule "Power nets minimum width"
	(condition "A.NetClass == 'Power'")
	(constraint track_width (min 0.4mm) (opt 0.6mm))
)
# Supply class (+5V, +3.3V, LDO input, J2 VBUS, U9 switch node): up to 0.5 A.
(rule "Supply nets minimum width"
	(condition "A.NetClass == 'Supply'")
	(constraint track_width (min 0.25mm) (opt 0.3mm))
)
'''
    open(dru, 'w').write(t)
# 6. stricter DRC severities and min_connection (LESSONS: KiCad otherwise accepts end-cap grazes)
pro = D + '/ayab-sr-esp32.kicad_pro'; p = json.load(open(pro))
ds = p['board']['design_settings']
ds['rules']['min_connection'] = 0.15
for k in ('track_dangling', 'via_dangling', 'copper_sliver', 'isolated_copper', 'connection_width'):
    ds['rule_severities'][k] = 'error'
json.dump(p, open(pro, 'w'), indent=2)
print('ok')
