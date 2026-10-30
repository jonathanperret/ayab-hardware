import re,sys
from sx import *; from regions import *
t=open(sys.argv[1]).read()
skip=('lib_symbols','sheet_instances','embedded_fonts','title_block','paper','version','generator','generator_version','uuid')
res=[]
for a,b in items(t):
    s=t[a:b];h=head(s)
    if h in skip: continue
    pts=[tuple(map(float,p)) for p in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)',s)] if h in('wire','polyline') else [tuple(map(float,re.search(r'\((?:at|start) ([-\d.]+) ([-\d.]+)',s).groups()))]
    ss={sect(*p) for p in pts}
    tag=re.search(r'\(property "Reference" "([^"]+)"',s) if h=='symbol' else re.match(r'\(\S+ "([^"]{0,20})',s)
    tag=tag.group(1).replace('\n','|') if tag else ''
    res.append((a,b,h,tag,pts,ss))
if __name__=='__main__':
    for a,b,h,tag,pts,ss in res:
        if len(ss)!=1 or None in ss: print('PROBLEM',h,tag,pts,ss)
    from collections import Counter
    print(Counter(next(iter(r[5])) for r in res if len(r[5])==1))
    for sct in sorted({s for _, *_x, ss in res for s in ss if s}):
        print(sct, sorted(r[3] for r in res if r[2]=='symbol' and r[5]=={sct} and not r[3].startswith('#')))
