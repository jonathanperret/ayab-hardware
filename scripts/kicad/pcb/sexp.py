import re

_tok = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')


def parse(text):
    stack = [[]]
    for m in _tok.finditer(text):
        t = m.group(0)
        if t == '(':
            stack.append([])
        elif t == ')':
            node = stack.pop()
            stack[-1].append(node)
        elif t[0] == '"':
            stack[-1].append(Str(t[1:-1].replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')))
        else:
            stack[-1].append(t)
    return stack[0][0]


class Str(str):
    """Quoted string (distinguish from bare symbols)."""


def head(n):
    return n[0] if isinstance(n, list) and n else None


def kids(n, name):
    return [c for c in n[1:] if isinstance(c, list) and c and c[0] == name]


def kid(n, name):
    for c in n[1:]:
        if isinstance(c, list) and c and c[0] == name:
            return c
    return None


def val(n, name, default=None, i=1):
    k = kid(n, name)
    if k is None or len(k) <= i:
        return default
    return k[i]


def nums(n, name):
    k = kid(n, name)
    if k is None:
        return None
    out = []
    for x in k[1:]:
        try:
            out.append(float(x))
        except (TypeError, ValueError):
            pass
    return out
