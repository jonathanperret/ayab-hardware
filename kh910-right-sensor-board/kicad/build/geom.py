# photo/tracer geometry -> board millimetres (front view), for the KiCad build
import json,sys,os,numpy as np
from scipy.interpolate import RBFInterpolator
ROOT,OUT=sys.argv[1],sys.argv[2]
s=json.load(open(ROOT+'/tracer/state.json')); P={p['id']:p for p in s['pads']}
PX=21.0
# solder photo -> front photo, fitted on every pad the user placed on both sides
ids=[k for k,p in P.items() if p.get('ok',{}).get('f') and p.get('ok',{}).get('b')]
A=np.array([P[k]['b'] for k in ids],float); B=np.array([P[k]['f'] for k in ids],float)
b2f=RBFInterpolator(A,B,kernel='thin_plate_spline',smoothing=5.0)
res=np.linalg.norm(b2f(A)-B,axis=1); print('b->f fit on',len(ids),'pads, residual median %.1fpx max %.1fpx'%(np.median(res),res.max()))
out=np.load(os.path.join(os.path.dirname(__file__),'board_outline.npy')).reshape(-1,2).astype(float)
x0,y0=out[:,0].min(),out[:,1].min()
mm=lambda p:[round((p[0]-x0)/PX,3),round((p[1]-y0)/PX,3)]
pads={k:mm(p['f']) for k,p in P.items()}
links=[]
for i,l in enumerate(s['links']):
    if l['status']=='wrong': continue
    pts=l.get('pts',[])
    if l.get('layer')=='b' and pts: pts=b2f(np.array(pts,float)).tolist()
    if l.get('board_exact'): links.append(dict(a=l['a'],b=l['b'],layer=l.get('layer'),pts=[list(q) for q in l['board_pts']],status=l['status'],board_exact=True,idx=i,board_width=l.get('board_width'))); continue
    links.append(dict(a=l['a'],b=l['b'],layer=l.get('layer'),pts=[mm(q) for q in pts],status=l['status'],idx=i))
json.dump(dict(px_per_mm=PX,outline=[mm(q) for q in out],pads=pads,links=links,
               parts=s['parts'],labels={k:p['label'] for k,p in P.items()},jumpers=s.get('jumpers',[]),nc=s.get('nc',[])),
          open(OUT,'w'),indent=1)
w=(out[:,0].max()-x0)/PX; h=(out[:,1].max()-y0)/PX; print('board %.1f x %.1f mm'%(w,h))
