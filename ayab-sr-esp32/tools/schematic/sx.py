import re
def items(txt):
    """Return (start,end) spans of top-level items (depth-1 children of kicad_sch)."""
    out=[];d=0;i=0;st=None;n=len(txt);instr=False
    while i<n:
        c=txt[i]
        if instr:
            if c=='\\': i+=2; continue
            if c=='"': instr=False
        elif c=='"': instr=True
        elif c=='(':
            d+=1
            if d==2: st=i
        elif c==')':
            if d==2: out.append((st,i+1))
            d-=1
        i+=1
    return out
def head(s): return re.match(r'\((\S+)',s).group(1)
