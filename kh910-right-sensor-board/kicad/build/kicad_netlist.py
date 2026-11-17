"""parse a KiCad s-expression netlist (kicad-cli sch export netlist) into {net name: [(ref, pin)]}"""
import re
def parse(path):
    t = open(path).read(); i = t.index('(nets'); nets = {}
    for blk in re.split(r'\n\s*\(net\b', t[i:])[1:]:
        name = re.search(r'\(name "([^"]*)"\)', blk).group(1)
        nets[name] = re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk)
    return nets
