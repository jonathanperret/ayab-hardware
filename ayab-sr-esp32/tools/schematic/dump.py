import re,sys
from sx import *
t=open(sys.argv[1]).read()
for a,b in items(t):
    s=t[a:b];h=head(s)
    if h in('lib_symbols','sheet_instances','embedded_fonts','title_block','paper','version','generator','generator_version','uuid'):continue
    if h=='symbol':
        ref=re.search(r'\(property "Reference" "([^"]+)"',s).group(1)
        at=re.search(r'\(at ([-\d.]+) ([-\d.]+)',s).groups()
        print('sym',ref,*at)
    elif h=='wire':
        p=re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)',s);print('wire',*[c for q in p for c in q])
    else:
        m=re.search(r'\((?:at|start|xy) ([-\d.]+) ([-\d.]+)',s)
        name=re.match(r'\(\S+ "([^"]{0,30})',s)
        print(h,name.group(1).replace('\n','|') if name else '',*(m.groups() if m else ()))
