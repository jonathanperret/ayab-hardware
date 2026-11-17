import re
L='/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/'
def block(t,name,start=0):
    i=t.index(f'(symbol "{name}"',start); d=0; instr=False
    for j in range(i,len(t)):
        c=t[j]
        if c=='"' and t[j-1]!='\\': instr=not instr
        if instr: continue
        if c=='(': d+=1
        elif c==')':
            d-=1
            if d==0: return t[i:j+1]
def get(lib,name):
    """flattened symbol text named 'lib:name' plus pin table {unit:[(num,name,x,y,angle,len)]}"""
    t=open(L+lib+'.kicad_sym').read(); b=block(t,name)
    m=re.search(r'\(extends "([^"]+)"\)',b)
    if m:
        parent=get(lib,m.group(1))[0]
        par=parent.split('\n',1)[1]   # drop header line
        # child properties override parent's
        props=dict(re.findall(r'(\(property "([^"]+)".*?\n\s*\))',b,re.S)[i][::-1] for i in range(0))
        body=par.replace(f'"{m.group(1)}_','"'+name+'_')
        for pm in re.finditer(r'\(property "([^"]+)" "([^"]*)"',b):
            body=re.sub(r'\(property "%s" "[^"]*"'%re.escape(pm.group(1)),lambda _:f'(property "{pm.group(1)}" "{pm.group(2)}"',body,count=1)
        b=f'(symbol "{name}"\n'+body
    b=b.replace(f'(symbol "{name}"',f'(symbol "{lib}:{name}"',1)
    pins={}
    for sm in re.finditer(r'\(symbol "%s_(\d+)_(\d+)"'%re.escape(name),b):
        sub=block(b,f'{name}_{sm.group(1)}_{sm.group(2)}')
        for p in re.finditer(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)\s*\(length ([\d.]+)\).*?\(name "([^"]*)".*?\(number "([^"]*)"',sub,re.S):
            pins.setdefault(int(sm.group(1)),[]).append((p.group(6),p.group(5),float(p.group(1)),float(p.group(2)),float(p.group(3)),float(p.group(4))))
    return b,pins
if __name__=='__main__':
    for lib,n in [('Comparator','LM339'),('Amplifier_Operational','LM324'),('Amplifier_Operational','LM358'),('Sensor_Proximity','ITR9608-F'),('Device','R_Potentiometer'),('Connector_Generic','Conn_01x09'),('power','+5V'),('power','GND')]:
        b,p=get(lib,n); print(f'{lib}:{n}',{u:[(q[0],q[1]) for q in v] for u,v in p.items()})
