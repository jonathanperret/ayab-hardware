"""filter_dsn.py in.dsn out.dsn keep|width  ...
keep NET1,NET2,...   : keep only these nets (plus planes) in the network section
width CLASS=um,...    : override class track widths"""
import re, sys
src, dst, mode, arg = sys.argv[1:5]
s = open(src).read()
def blocks(text, start):
    """yield (start, end) of '(net ' blocks inside the network section."""
    i = text.index('(network', start)
    j = i
    depth = 0
    for k in range(i, len(text)):
        c = text[k]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i, k + 1
if mode == 'keep':
    keep = set(arg.split(','))
    a, b = blocks(s, 0)
    net = s[a:b]
    out, pos = [], 0
    for m in re.finditer(r'\n(\s*)\(net ("[^"]*"|\S+)\n', net):
        pass
    # rebuild network: walk top-level children
    body = net[len('(network'):-1]
    i, depth, cur, kids = 0, 0, '', []
    start = None
    for k, c in enumerate(body):
        if c == '(':
            if depth == 0:
                start = k
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                kids.append(body[start:k + 1])
    newkids = []
    for kid in kids:
        m = re.match(r'\(net ("[^"]*"|[^\s()]+)', kid)
        if m:
            name = m.group(1).strip('"')
            if name in keep:
                newkids.append(kid)
        elif kid.startswith('(class'):
            q = False
            for idx in range(1, len(kid)):
                if kid[idx] == '"':
                    q = not q
                elif kid[idx] == '(' and not q:
                    break
            names = re.findall(r'"[^"]*"|[^\s"]+', kid[len('(class '):idx])
            cname, members = names[0], [n for n in names[1:] if n.strip('"') in keep]
            if members:
                newkids.append('(class ' + cname + ' ' + ' '.join(members) + '\n      ' + kid[idx:])
        else:
            newkids.append(kid)
    s = s[:a] + '(network\n    ' + '\n    '.join(newkids) + '\n  )' + s[b:]
elif mode == 'width':
    for item in arg.split(','):
        cname, w = item.split('=')
        s, n = re.subn(r'(\(class ' + re.escape(cname) + r' [^\n]*\n(?:.*\n)*?\s*\(rule\n\s*\(width )\d+', r'\g<1>' + w, s, count=1)
        print(cname, 'patched', n)
open(dst, 'w').write(s)
