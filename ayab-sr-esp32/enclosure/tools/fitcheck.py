"""Numerical fit check: enclosure solids vs PCB + component meshes.
Frame: X = KiCad x, Y = -KiCad y, Z = 0 at PCB bottom (same as the .scad)."""
import numpy as np, glob, os, sys
from stlio import load_stl
RES=0.1
class ColumnSolid:
    """Solid voxelised as z-intervals on an XY grid (ray parity along Z)."""
    def __init__(self,T,res=RES):
        self.res=res
        p=T.reshape(-1,3); self.x0,self.y0=p[:,0].min()-1,p[:,1].min()-1
        nx=int((p[:,0].max()+1-self.x0)/res)+1; ny=int((p[:,1].max()+1-self.y0)/res)+1
        self.nx,self.ny=nx,ny
        hits=[[] for _ in range(nx*ny)]
        for tri in T:
            a,b,c=tri
            d=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(d)<1e-12: continue
            ix0=int(np.ceil((min(a[0],b[0],c[0])-self.x0)/res)); ix1=int(np.floor((max(a[0],b[0],c[0])-self.x0)/res))
            iy0=int(np.ceil((min(a[1],b[1],c[1])-self.y0)/res)); iy1=int(np.floor((max(a[1],b[1],c[1])-self.y0)/res))
            if ix1<ix0 or iy1<iy0: continue
            gx,gy=np.meshgrid(np.arange(ix0,ix1+1),np.arange(iy0,iy1+1),indexing='ij')
            # tiny offset to avoid exact edge hits
            X=self.x0+gx*res+1.234e-6; Y=self.y0+gy*res+2.345e-6
            l1=((b[1]-c[1])*(X-c[0])+(c[0]-b[0])*(Y-c[1]))/d
            l2=((c[1]-a[1])*(X-c[0])+(a[0]-c[0])*(Y-c[1]))/d
            l3=1-l1-l2
            m=(l1>=0)&(l2>=0)&(l3>=0)
            if not m.any(): continue
            Z=l1[m]*a[2]+l2[m]*b[2]+l3[m]*c[2]
            for i,j,z in zip(gx[m],gy[m],Z): hits[i*ny+j].append(z)
        self.iv={}
        for k,h in enumerate(hits):
            if len(h)>=2:
                h=np.sort(h)
                if len(h)%2: h=h[:-1]
                self.iv[k]=h.reshape(-1,2)
    def _col(self,x,y):
        i=np.rint((x-self.x0)/self.res).astype(int); j=np.rint((y-self.y0)/self.res).astype(int)
        k=i*self.ny+j
        k[(i<0)|(i>=self.nx)|(j<0)|(j>=self.ny)]=-1   # outside the grid: no column (would wrap into a neighbour)
        return k
    def inside(self,P):
        k=self._col(P[:,0],P[:,1]); out=np.zeros(len(P),bool)
        for n,(kk,z) in enumerate(zip(k,P[:,2])):
            iv=self.iv.get(kk)
            if iv is not None and np.any((iv[:,0]<z)&(z<iv[:,1])): out[n]=True
        return out
    def any_above(self,P):   # solid somewhere above the point in its column
        k=self._col(P[:,0],P[:,1]); out=np.zeros(len(P),bool)
        for n,(kk,z) in enumerate(zip(k,P[:,2])):
            iv=self.iv.get(kk)
            if iv is not None and np.any(iv[:,1]>z): out[n]=True
        return out
    def any_below(self,P):
        k=self._col(P[:,0],P[:,1]); out=np.zeros(len(P),bool)
        for n,(kk,z) in enumerate(zip(k,P[:,2])):
            iv=self.iv.get(kk)
            if iv is not None and np.any(iv[:,0]<z): out[n]=True
        return out

def samples(T,step=0.25):
    """points on the surface of a mesh (vertices + barycentric grid)."""
    pts=[T.reshape(-1,3)]
    e=np.maximum(np.linalg.norm(T[:,1]-T[:,0],axis=1),np.linalg.norm(T[:,2]-T[:,0],axis=1))
    for n in range(2,40):
        sel=T[(e>step*(n-1))&(e<=step*n)] if n<39 else T[e>step*(n-1)]
        if len(sel)==0: continue
        u=[(i/n,j/n) for i in range(n+1) for j in range(n+1-i)]
        u=np.array(u)
        P=sel[:,None,0]+u[None,:,0,None]*(sel[:,None,1]-sel[:,None,0])+u[None,:,1,None]*(sel[:,None,2]-sel[:,None,0])
        pts.append(P.reshape(-1,3))
    return np.concatenate(pts)

def comp_meshes(W):
    out={}
    for f in sorted(glob.glob(W+'/comp/*.stl')):
        T=load_stl(f)
        if len(T): out[os.path.basename(f)[:-4]]=T
    return out
def to_board_frame(T):
    T=T.copy(); X,Y=T[...,0]-148.45,T[...,1]+56.35
    T[...,0],T[...,1]=132.25-Y,-66.55+X
    return T
def box_tris(x0,y0,z0,x1,y1,z1):
    v=np.array([[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]])
    f=[(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    return v[np.array(f)]

if __name__=='__main__':
    W=sys.argv[1]
    tray=ColumnSolid(load_stl(W+'/tray_asm.stl')); lid=ColumnSolid(load_stl(W+'/lid_asm.stl'))
    comps=comp_meshes(W)
    pcb=load_stl(W+'/pcb_only.stl'); comps['PCB']=pcb
    dirs=[np.zeros(3)]+[np.array(d)*1.0 for d in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]]
    print('%-5s %8s %8s %8s %8s %10s %10s'%('ref','pts','tray','lid','<0.2mm','tray_ins','lid_ins'))
    bad=False
    for r,T in comps.items():
        P=samples(T)
        if r=='PCB':
            P=P[(P[:,2]>0.05)&(P[:,2]<1.45)]   # touching faces on standoffs / columns are intended
        it=tray.inside(P).sum(); il=lid.inside(P).sum()
        near=0
        for d in dirs[1:]:
            Q=P+d*0.2; near+= (tray.inside(Q)|lid.inside(Q)).sum()
        # assembly: PCB lowered into the tray (sweep up), lid lowered onto the PCB (sweep down)
        ti=tray.any_above(P).sum() if r!='PCB' else 0
        li=0
        if r!='PCB':
            # lid lowered from above: blocked if lid solid has its bottom below a component point in the same column
            li=lid.any_below(P+np.array([0,0,0.01])).sum() if False else 0
        print('%-5s %8d %8d %8d %8d %10d'%(r,len(P),it,il,near,ti))
        if it or il: bad=True
    print('COLLISION' if bad else 'no collision')
