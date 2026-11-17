import json,collections,re,sys
s=json.load(open(sys.argv[1])); P={p['id']:p for p in s['pads']}
pin={}
for pt in s['parts']:
    for i,pid in enumerate(pt['pins']): pin[pid]=f"{pt['ref']}.{i+1}"+(f"({pt['pinnames'][i]})" if pt.get('pinnames') else '')
def name(pid): return pin.get(pid) or (P[pid]['label'].replace('pad ','J.').replace(' (','(') if P[pid]['label'] else 'via'+pid[1:])
par={k:k for k in P}
def f(a):
    while par[a]!=a: par[a]=par[par[a]]; a=par[a]
    return a
st=collections.Counter(l['status'] for l in s['links']); print('links',len(s['links']),dict(st))
for l in s['links']:
    if l['status']=='wrong' or l['a'] not in P or l['b'] not in P: continue
    par[f(l['a'])]=f(l['b'])
g=collections.defaultdict(list)
for k in P: g[f(k)].append(k)
nets=[m for m in g.values() if len(m)>1]
def key(n):
    m=re.match(r'([A-Za-z]+)(\d*)\.?(\d*)',n); return (m.group(1),int(m.group(2) or 0),int(m.group(3) or 0))
def netof(label):
    k=[x for x in P if name(x).split('(')[0].strip()==label]; return f(k[0]) if k else None
print(len(nets),'nets')
for m in sorted(nets,key=len,reverse=True):
    print(f'{len(m):3d}', ' '.join(sorted((name(x) for x in m),key=key)))
nc=set(s.get('nc',[]))
print('\nNC (marked unused):',' '.join(sorted((name(k) for k in nc),key=key)))
single=[name(k) for k,m in g.items() if len(m)==1 and k in pin and k not in nc]
print('\nUNCONNECTED part pins:',' '.join(sorted(single,key=key)))
print('\nMEASURED CHECKS:')
for a,b,exp in [('J.I','J.H',False),('J.I','IC303.8',True),('J.I','IC302.3',True),('J.I','IC301.4',True),('J.H','IC303.4',True),('J.H','IC302.12',True),('J.H','IC301.11',True),
                ('J.D','IC302.13',True),('J.E','IC301.14',True),('J.F','IC301.7',True),('J.G','IC301.8',True),('J.K','J.H',True),('J.O','J.H',True)]:
    same=netof(a)==netof(b); print(f"  {a:6s}-{b:9s} measured {'joined' if exp else 'open  '}  traces {'joined' if same else 'open  '}  {'OK' if same==exp else '<-- MISMATCH'}")
