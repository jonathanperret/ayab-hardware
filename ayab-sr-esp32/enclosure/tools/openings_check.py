import numpy as np
from stlio import load_stl
def P(r): return load_stl('../comp/%s.stl'%r).reshape(-1,3)*[1,-1,1]
usb={'J1':116.58,'J2':128.78}; w,h,zc=9.6,3.9,3.33
for r,xc in usb.items():
    p=P(r); q=p[p[:,1]>86.0]
    print(r,'shell x %.2f..%.2f (opening %.2f..%.2f) z %.2f..%.2f (opening %.2f..%.2f) -> margins x %.2f/%.2f z %.2f/%.2f'%(
        q[:,0].min(),q[:,0].max(),xc-w/2,xc+w/2,q[:,2].min(),q[:,2].max(),zc-h/2,zc+h/2,
        q[:,0].min()-(xc-w/2),(xc+w/2)-q[:,0].max(),q[:,2].min()-(zc-h/2),(zc+h/2)-q[:,2].max()))
p=P('J3'); q=p[p[:,0]>179]; r=np.hypot(q[:,1]-35.46,q[:,2]-11.62)
print('J3 socket ring: max radius %.2f mm (opening radius 8.5), face x=%.2f (inner wall 181.9)'%(r[r<8.4].max(),q[:,0].max()))
p=P('S1'); q=p[p[:,0]>190.3]
print('S1 wheel beyond the wall: y %.2f..%.2f (slot %.2f..%.2f) z %.2f..%.2f (slot 1.0..; lid tab at 4.6), max protrusion x %.2f (outer wall 192.3, thumb pocket bottom 191.3)'%(q[:,1].min(),q[:,1].max(),59.2-0.8,74.1+0.8,q[:,2].min(),q[:,2].max(),q[:,0].max()))
p=P('U5'); print('U5 top %.2f (well bottom 7.74)'%p[:,2].max())
p=P('U3'); print('U3 y max %.2f (inner wall 87.3)'%p[:,1].max())
