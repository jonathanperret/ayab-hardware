"""prep_dsn.py FILE.dsn  -- in place: give every net class the same SMD-to-SMD clearance exception as the default rule (fine-pitch pads)."""
import re, sys
s = open(sys.argv[1]).read()
s, n = re.subn(r'(\(class (?!kicad_default)[^\n]*\n(?:.*\n)*?\s*\(rule\n\s*\(width \d+\)\n\s*\(clearance \d+\))\n', r'\1\n        (clearance 50 (type smd_smd))\n', s)
print('patched classes:', n)
open(sys.argv[1], 'w').write(s)
