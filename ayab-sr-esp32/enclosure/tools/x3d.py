import xml.etree.ElementTree as ET, numpy as np
def rotm(ax,ang):
    ax=np.array(ax,float);n=np.linalg.norm(ax)
    if n==0 or ang==0: return np.eye(3)
    x,y,z=ax/n;c,s=np.cos(ang),np.sin(ang);C=1-c
    return np.array([[c+x*x*C,x*y*C-z*s,x*z*C+y*s],[y*x*C+z*s,c+y*y*C,y*z*C-x*s],[z*x*C-y*s,z*y*C+x*s,c+z*z*C]])
def load_x3d(path):
    root=ET.parse(path).getroot()
    tris=[];cols=[]
    def walk(el,M,t,col):
        if el.tag=='Transform':
            tr=np.array([float(v) for v in el.get('translation','0 0 0').split()])
            sc=np.array([float(v) for v in el.get('scale','1 1 1').split()])
            r=[float(v) for v in el.get('rotation','0 0 1 0').split()]
            R=rotm(r[:3],r[3])
            # p_parent = T + R S p
            newM=M@R@np.diag(sc); newt=M@tr+t
            M,t=newM,newt
        if el.tag=='Shape':
            mat=el.find('.//Material'); c=(0.6,0.6,0.6)
            if mat is not None and mat.get('diffuseColor'): c=tuple(float(v) for v in mat.get('diffuseColor').split())
            ifs=el.find('.//IndexedFaceSet')
            if ifs is not None:
                pts=np.array([float(v) for v in ifs.find('.//Coordinate').get('point').replace(',',' ').split()]).reshape(-1,3)
                idx=[int(v) for v in ifs.get('coordIndex').replace(',',' ').split()]
                face=[]
                P=(M@pts.T).T+t
                for i in idx:
                    if i<0:
                        for k in range(1,len(face)-1): tris.append([P[face[0]],P[face[k]],P[face[k+1]]]);cols.append(c)
                        face=[]
                    else: face.append(i)
            return
        for ch in el: walk(ch,M,t,col)
    walk(root,np.eye(3),np.zeros(3),None)
    return np.array(tris),np.array(cols)
if __name__=='__main__':
    import sys
    T,C=load_x3d(sys.argv[1]); p=T.reshape(-1,3)
    print(len(T),p.min(0),p.max(0)); print(set(map(tuple,C)))
