import json,struct,numpy as np
CT={5126:np.float32,5125:np.uint32,5123:np.uint16,5121:np.uint8}
NC={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def qmat(q):
    x,y,z,w=q
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
# J2 (+U2,R2,R3) moved 3.8 mm left after the export (parent session update)
SHIFT={'J2':-0.0038,'U2':-0.0038,'R2':-0.0038,'R3':-0.0038}
def load_glb(path):
    d=open(path,'rb').read()
    L=struct.unpack('<I',d[12:16])[0]; j=json.loads(d[20:20+L])
    off=20+L; BL=struct.unpack('<I',d[off:off+4])[0]; buf=d[off+8:off+8+BL]
    def acc(i):
        a=j['accessors'][i]; bv=j['bufferViews'][a['bufferView']]
        dt=CT[a['componentType']]; n=NC[a['type']]
        start=bv.get('byteOffset',0)+a.get('byteOffset',0)
        stride=bv.get('byteStride',0); isz=np.dtype(dt).itemsize*n
        if stride and stride!=isz:
            raw=np.frombuffer(buf,dtype=np.uint8,count=stride*(a['count']-1)+isz,offset=start)
            idx=np.arange(a['count'])[:,None]*stride+np.arange(isz)[None,:]
            return raw[idx].copy().view(dt).reshape(a['count'],n)
        return np.frombuffer(buf,dtype=dt,count=a['count']*n,offset=start).reshape(a['count'],n)
    cols=[]
    for m in j['materials']:
        c=m.get('pbrMetallicRoughness',{}).get('baseColorFactor',[0.7,0.7,0.7,1]); cols.append(tuple(c))
    groups={}
    def walk(ni,M):
        n=j['nodes'][ni]
        L=np.eye(4)
        if n.get('name') in SHIFT: M=M.copy(); M[0,3]+=SHIFT[n['name']]
        if 'matrix' in n: L=np.array(n['matrix']).reshape(4,4).T
        else:
            T=np.eye(4)
            if 'scale' in n: T=np.diag(list(n['scale'])+[1])@T
            if 'rotation' in n: R=np.eye(4);R[:3,:3]=qmat(n['rotation']);T=R@T
            if 'translation' in n: Tt=np.eye(4);Tt[:3,3]=n['translation'];T=Tt@T
            L=T
        G=M@L
        if 'mesh' in n:
            for p in j['meshes'][n['mesh']]['primitives']:
                P=acc(p['attributes']['POSITION']).astype(np.float64)
                idx=acc(p['indices']).reshape(-1) if 'indices' in p else np.arange(len(P))
                P=(G[:3,:3]@P.T).T+G[:3,3]
                tris=P[idx.reshape(-1,3)]
                c=cols[p.get('material',0)] if j.get('materials') else (0.7,0.7,0.7,1)
                groups.setdefault(c,[]).append(tris)
        for ch in n.get('children',[]): walk(ch,G)
    for root in j['scenes'][j.get('scene',0)]['nodes']: walk(root,np.eye(4))
    out={}
    for c,l in groups.items():
        T=np.concatenate(l)*1000.0
        # glTF (x, y_up, z=kicad_y) -> world (x, -kicad_y, up)
        out[c]=np.stack([T[...,0],-T[...,2],T[...,1]],-1)
    return out
if __name__=='__main__':
    import sys
    g=load_glb(sys.argv[1])
    for c,T in sorted(g.items(),key=lambda kv:-len(kv[1])):
        p=T.reshape(-1,3); print(np.round(c,3),len(T),np.round(p.min(0),2),np.round(p.max(0),2))
