# fpmap.json: reference -> footprint, decided from the measured pad positions (geom.json), before the schematic is written
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import footprints
g = json.load(open(sys.argv[1])); out = {}
for pt in g['parts']:
    out[pt['ref']] = '%s:%s' % footprints.choose(pt['ref'], [g['pads'][i] for i in pt['pins']])
for r in ('J1', 'J2', 'JP1', 'JP2'): out[r] = '%s:%s' % footprints.choose(r, [])
json.dump(out, open(os.path.join(sys.argv[2], 'fpmap.json'), 'w'), indent=1)
