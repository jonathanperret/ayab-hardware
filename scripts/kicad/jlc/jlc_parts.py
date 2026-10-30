#!/usr/bin/env python3
"""jlc_parts.py KEYWORD_OR_LCSC [...]  -- search JLCPCB's assembly parts library (live: stock, basic /
extended, price breaks). Needs network access to jlcpcb.com. Runs on the host (plain Python).

    python3 scripts/kicad/jlc/jlc_parts.py C2913198 "SS34 SMA" "13.7kΩ 0603"
"""
import json, sys, urllib.request

API = 'https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList'


def query(keyword, n=6):
    req = urllib.request.Request(API, data=json.dumps({"keyword": keyword, "currentPage": 1, "pageSize": n}).encode(),
                                 headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    return (d.get('data') or {}).get('componentPageInfo', {}).get('list') or []


def library(c):
    """basic: no loading fee; pref-ext: preferred extended (no fee in Economic assembly); extended: fee."""
    if c['componentLibraryType'] == 'base':
        return 'basic'
    return 'pref-ext' if c.get('preferredComponentFlag') else 'extended'


def unit_price(c, qty):
    p = c['componentPrices'][0]['productPrice']
    for t in c['componentPrices']:
        if qty >= t['startNumber']:
            p = t['productPrice']
    return p


if __name__ == '__main__':
    for kw in sys.argv[1:]:
        print('==', kw)
        for c in query(kw):
            tiers = ', '.join('%d+: $%.4f' % (p['startNumber'], p['productPrice']) for p in c['componentPrices'][:4])
            print('  %-11s %-28s %-16s %-8s stock %8d  %s' % (c['componentCode'], c['componentModelEn'][:28],
                  c['componentSpecificationEn'][:16], library(c), c['stockCount'], tiers))
