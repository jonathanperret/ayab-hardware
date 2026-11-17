import sys,re,pcbnew
pcb,drc=sys.argv[1],sys.argv[2]
b=pcbnew.LoadBoard(pcb); t=open(drc).read(); n=0
for name,ref,pad in re.findall(r'Pad missing net given by schematic \(([^)]*\))\)\n\s*[^\n]*\n?\s*@\([^)]*\): PTH pad (\d+) \[<no net>\] of (\w+)',t) and [] or re.findall(r'Pad missing net given by schematic \((.*?)\)\n.*?PTH pad (\S+) \[<no net>\] of (\w+)',t):
    pass
for m in re.finditer(r'Pad missing net given by schematic \((.*)\)\n(?:.*\n)*?.*?PTH pad (\S+) \[<no net>\] of (\w+)',t):
    name,pad,ref=m.group(1),m.group(2),m.group(3)
    fp=b.FindFootprintByReference(ref); ni=pcbnew.NETINFO_ITEM(b,name); b.Add(ni)
    for p in fp.Pads():
        if p.GetNumber()==pad: p.SetNet(ni); n+=1
b.Save(pcb); print('named',n)
