import numpy as np, struct
def load_stl(path):
    data=open(path,'rb').read()
    if data[:5]==b'solid' and b'facet' in data[:400]:
        v=[]
        for line in data.decode(errors='ignore').splitlines():
            line=line.strip()
            if line.startswith('vertex'):
                v.append([float(t) for t in line.split()[1:4]])
        return np.array(v,dtype=np.float64).reshape(-1,3,3)
    n=struct.unpack('<I',data[80:84])[0]
    a=np.frombuffer(data,dtype=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]),count=n,offset=84)
    return a['v'].astype(np.float64)
def save_stl(path,tris):
    tris=np.asarray(tris,dtype=np.float32)
    n=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0])
    rec=np.zeros(len(tris),dtype=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]))
    rec['n']=n;rec['v']=tris
    with open(path,'wb') as f:
        f.write(b'\0'*80);f.write(struct.pack('<I',len(tris)));f.write(rec.tobytes())
