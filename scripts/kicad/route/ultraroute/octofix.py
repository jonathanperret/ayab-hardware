"""octofix.py BOARD_DIR [ROUNDS] [PAD_MIN_MM]  -- make routed copper 0/45/90-degree: every segment off a multiple of 45 degrees
that does not end on a pad becomes two segments through a corner M (a 45-degree leg and an orthogonal leg; first
the diagonal-first variant, then the other), KiCad DRC (all severities, zones refilled) judges the board, and a
change touching any violation is switched to its other variant, then reverted to the original segment.
Segments ending on a pad are treated too when longer than PAD_MIN_MM (default 0.3): only a short pad entry may
keep an angle, which the pad's position then forces. Ends never move, so connectivity is unchanged. BOARD_DIR holds board.kicad_pcb with its .kicad_pro/.kicad_dru
(finish.sh's OUTDIR). Runs on the host; DRC through scripts/kicad/kicad.sh. Collinear pieces are merged first
(octo.py --fix)."""
import json, math, os, re, subprocess, sys, uuid
D = os.path.realpath(sys.argv[1]); ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 3
PAD_MIN = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
H = os.path.dirname(os.path.realpath(__file__)); K = os.path.realpath(os.path.join(H, '..', '..', 'kicad.sh'))
PCB = os.path.join(D, 'board.kicad_pcb')
subprocess.run([sys.executable, os.path.join(H, 'octo.py'), PCB, '--fix'], check=True)
s = open(PCB).read()
# reuse octo.py's parsing (pads, segments) on this file
src = open(os.path.join(H, 'octo.py')).read()
ns = {'__name__': 'octo'}; sys_argv = sys.argv; sys.argv = ['octo.py', PCB]
exec(src.split("L = defaultdict(float)")[0], ns); sys.argv = sys_argv
segs, on_pad, off45 = ns['segs'], ns['on_pad'], ns['off45']
cand = [i for i, sg in enumerate(segs) if math.dist(sg['a'], sg['e']) > 1e-6 and off45(sg)
        and (not (on_pad(sg['a']) or on_pad(sg['e'])) or math.dist(sg['a'], sg['e']) > PAD_MIN)]
def corner(a, e, variant):
    dx, dy = e[0] - a[0], e[1] - a[1]; m = min(abs(dx), abs(dy)); sx, sy = math.copysign(1, dx), math.copysign(1, dy)
    if variant == 0:  # diagonal first
        return (a[0] + sx * m, a[1] + sy * m)
    return (e[0] - sx * m, e[1] - sy * m)  # orthogonal first
state = {i: 0 for i in cand}   # 0, 1 = variant; 2 = original
def f(v): return ('%.6f' % v).rstrip('0').rstrip('.')
def build():
    out, pos, owner = [], 0, {}
    for i, sg in enumerate(segs):
        st, en = sg['span']; out.append(s[pos:st]); pos = en
        if i not in state or state[i] == 2:
            out.append(s[st:en]); continue
        M = corner(sg['a'], sg['e'], state[i])
        for k, (p, q) in enumerate(((sg['a'], M), (M, sg['e']))):
            if math.dist(p, q) < 1e-6: continue
            u = str(uuid.uuid5(uuid.NAMESPACE_URL, 'octofix %d %d %d' % (i, state[i], k)))
            b = re.sub(r'\(start [-\d.]+ [-\d.]+\)', '(start %s %s)' % (f(p[0]), f(p[1])), sg['body'], count=1)
            b = re.sub(r'\(end [-\d.]+ [-\d.]+\)', '(end %s %s)' % (f(q[0]), f(q[1])), b, count=1)
            b = re.sub(r'\(uuid "[^"]+"\)', '(uuid "%s")' % u, b, count=1)
            out.append('\n\t(segment\n' + b + '\n\t)'); owner[u] = i
    out.append(s[pos:]); return ''.join(out), owner
def drc():
    r = subprocess.run([K, 'sh', '-c', 'python3 %s/../../pcb/refill.py board.kicad_pcb >/dev/null && kicad-cli pcb drc --severity-all --format json -o octo.json board.kicad_pcb >/dev/null'
                        % H], cwd=D, env=dict(os.environ, KICAD_KEEP_PRO='1'))
    j = json.load(open(os.path.join(D, 'octo.json')))
    bad = set(); n = 0
    for v in j.get('violations', []) + j.get('unconnected_items', []):
        if v.get('type') in ('lib_footprint_issues', 'lib_footprint_mismatch'): continue
        n += 1
        for it in v.get('items', []): bad.add(it.get('uuid'))
    return n, bad
base_n = None
for rnd in range(ROUNDS + 2):
    txt, owner = build(); open(PCB, 'w').write(txt)
    n, bad = drc()
    hit = {owner[u] for u in bad if u in owner}
    print('round %d: %d candidates, violations %d, touching changes %d, states %s' % (rnd, len(cand), n, len(hit),
          {k: sum(1 for v in state.values() if v == k) for k in (0, 1, 2)}))
    if not hit: break
    for i in hit: state[i] = min(state[i] + 1, 2)
txt, owner = build(); open(PCB, 'w').write(txt)
n, bad = drc(); print('final violations (lib issues excluded):', n)
