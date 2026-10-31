import numpy as np,sys
from stlio import load_stl
def components(T):
    V=np.round(T.reshape(-1,3),4); u,inv=np.unique(V,axis=0,return_inverse=True); inv=inv.reshape(-1,3)
    par=np.arange(len(u))
    def f(a):
        while par[a]!=a: par[a]=par[par[a]]; a=par[a]
        return a
    for a,b,c in inv:
        ra,rb,rc=f(a),f(b),f(c); par[rb]=ra; par[f(rc)]=ra
    roots=np.array([f(i) for i in range(len(u))])
    tri_root=roots[inv[:,0]]
    out=[]
    for r in np.unique(tri_root):
        m=tri_root==r; p=T[m].reshape(-1,3); out.append((m.sum(),p.min(0),p.max(0)))
    return out
if __name__=='__main__':
    for f in sys.argv[1:]:
        T=load_stl(f); print(f.split('/')[-1],len(T))
        for c in components(T): print('  ',c)
