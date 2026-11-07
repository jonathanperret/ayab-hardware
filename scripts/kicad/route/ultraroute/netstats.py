import re, sys, math
def stats(path):
    s = open(path).read(); L = {}; V = {}; W = {}
    for m in re.finditer(r'\n\t\((segment|via|arc)\n(.*?)\n\t\)', s, re.S):
        b = m.group(2); n = re.search(r'\(net "([^"]*)"', b).group(1)
        if m.group(1) == 'via': V[n] = V.get(n, 0) + 1; continue
        a = list(map(float, re.search(r'\(start ([\d.]+) ([\d.]+)', b).groups())); e = list(map(float, re.search(r'\(end ([\d.]+) ([\d.]+)', b).groups()))
        L[n] = L.get(n, 0) + math.dist(a, e); w = float(re.search(r'\(width ([\d.]+)', b).group(1)); W[n] = min(W.get(n, 9), w)
    return L, V, W
A = stats(sys.argv[1]); B = stats(sys.argv[2])
print('total length %.0f -> %.0f mm, vias %d -> %d' % (sum(A[0].values()), sum(B[0].values()), sum(A[1].values()), sum(B[1].values())))
for n in sys.argv[3:]:
    print('%-22s len %6.1f -> %6.1f  vias %2d -> %2d  min w %.3f -> %.3f' % (n, A[0].get(n, 0), B[0].get(n, 0), A[1].get(n, 0), B[1].get(n, 0), A[2].get(n, 0), B[2].get(n, 0)))
