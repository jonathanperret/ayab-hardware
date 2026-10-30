#!/usr/bin/env python3
"""bom_cost.py BOM.csv [QTY ...]  -- price a JLCPCB BOM (columns Designator, LCSC; as written by
production.sh) with live JLCPCB part prices, for each batch size (default 5 20 50). Prints per-line
library type / stock, the parts total and per-board cost, and the number of unique extended parts
(each costs a ~$3 loading fee per order). Lines without an LCSC number are listed and skipped.
Runs on the host; needs network access to jlcpcb.com."""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jlc_parts import query, library, unit_price

rows = list(csv.DictReader(open(sys.argv[1], encoding='utf-8')))
qtys = [int(q) for q in sys.argv[2:]] or [5, 20, 50]
lines = []
for r in rows:
    refs, code = r['Designator'], (r.get('LCSC') or '').strip()
    if r.get('DNP'):
        continue
    if not code:
        print('no LCSC number (not priced):', refs); continue
    c = next((c for c in query(code, 3) if c['componentCode'] == code), None)
    if c is None:
        print('NOT FOUND at JLCPCB:', code, refs); continue
    lines.append((refs, code, c))
    print('%-34s %-10s %-26s %-8s stock %8d' % (refs[:34], code, c['componentModelEn'][:26], library(c), c['stockCount']))
ext = [code for _, code, c in lines if library(c) == 'extended']
print('unique extended parts (loading fee each):', len(set(ext)))
for n in qtys:
    tot = 0.0
    for refs, code, c in lines:
        k = len(refs.split(',')) * n
        k = max(k, c.get('minPurchaseNum') or 1)
        tot += k * unit_price(c, k)
    print('%3d boards: parts $%.2f, $%.2f per board' % (n, tot, tot / n))
