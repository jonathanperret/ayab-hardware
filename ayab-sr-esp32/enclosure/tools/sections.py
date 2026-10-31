"""2D cross-sections (CAD-like) of the enclosure with the board and components."""
import numpy as np, sys
from PIL import Image, ImageDraw, ImageFont, ImageChops
from stlio import load_stl
from fitcheck import comp_meshes
from glb import load_glb
W=sys.argv[1] if len(sys.argv) > 1 else '..'   # work dir of regen.sh (tray_asm.stl, comp/, renders/)
def slice_mesh(T, axis, val):
    """returns segments (N,2,3) of the intersection of triangles with plane coord[axis]=val"""
    d=T[...,axis]-val
    segs=[]
    s=np.sign(d); s[s==0]=1e-9
    m=~((s>0).all(1)|(s<0).all(1))
    for tri,dd in zip(T[m],d[m]):
        pts=[]
        for i in range(3):
            a,b=tri[i],tri[(i+1)%3]; da,db=dd[i],dd[(i+1)%3]
            if (da<0)!=(db<0):
                t=da/(da-db); pts.append(a+t*(b-a))
        if len(pts)==2: segs.append(pts)
    return np.array(segs)
def loops(segs, tol=1e-3):
    key=lambda p: (round(p[0]/tol),round(p[1]/tol))
    adj={}
    for i,(a,b) in enumerate(segs):
        adj.setdefault(key(a),[]).append((i,0)); adj.setdefault(key(b),[]).append((i,1))
    used=np.zeros(len(segs),bool); out=[]
    for i in range(len(segs)):
        if used[i]: continue
        used[i]=True; loop=[segs[i][0],segs[i][1]]; cur=segs[i][1]
        while True:
            nxt=None
            for j,e in adj.get(key(cur),[]):
                if not used[j]: nxt=(j,e);break
            if nxt is None: break
            j,e=nxt; used[j]=True; cur=segs[j][1-e]; loop.append(cur)
        out.append(np.array(loop))
    return out
FONT=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
FONTB=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',22)
def draw_section(name, axis, val, h_axis, view_rng, z_rng, title, notes=(), scale=14, flip_h=False):
    tray=load_stl(W+'/tray_asm.stl'); lid=load_stl(W+'/lid_asm.stl')
    comps=comp_meshes(W); comps['PCB']=load_stl(W+'/pcb_only.stl')
    # S1 & U5 from comp; colours
    x0,x1=view_rng; z0,z1=z_rng
    Wd=max(int((x1-x0)*scale)+40,1150); Hd=int((z1-z0)*scale)+120
    img=Image.new('RGB',(Wd,Hd),'white'); d=ImageDraw.Draw(img)
    def P(p):
        h=p[h_axis]; h=-h if flip_h else h
        return (20+(h-x0)*scale, 60+(z1-p[2])*scale)
    # grid
    for z in range(int(np.ceil(z0)),int(z1)+1,2):
        y=60+(z1-z)*scale; d.line([(20,y),(Wd-20,y)],fill=(238,238,238))
    def fill(T,col,outline):
        segs=slice_mesh(T,axis,val)
        if len(segs)==0: return
        A=np.array([P(a) for a,b in segs]); B=np.array([P(b) for a,b in segs])
        px=img.load()
        for row in range(Hd):
            yc=row+0.5
            m=((A[:,1]<=yc)&(B[:,1]>yc))|((B[:,1]<=yc)&(A[:,1]>yc))
            if not m.any(): continue
            a=A[m]; b=B[m]; t=(yc-a[:,1])/(b[:,1]-a[:,1]); xs=np.sort(a[:,0]+t*(b[:,0]-a[:,0]))
            for k in range(0,len(xs)-1,2):
                d.line([(xs[k],row),(xs[k+1],row)],fill=col)
        for a,b in segs: d.line([P(a),P(b)],fill=outline,width=1)
    fill(tray,(110,118,130),(40,45,55)); fill(lid,(205,203,195),(120,118,110))
    fill(comps['PCB'],(60,140,90),(20,80,40))
    for r,T in comps.items():
        if r=='PCB': continue
        segs=slice_mesh(T,axis,val)
        for a,b in segs: d.line([P(a),P(b)],fill=(200,60,30),width=1)
    d.text((20,10),title,fill='black',font=FONTB)
    yy=Hd-26
    d.text((20,yy-24),'   '.join(notes),fill=(60,60,60),font=FONT)
    d.text((20,yy),'grille 2 mm ; rouge = contours des composants, vert = PCB, gris foncé = fond, gris clair = couvercle',fill=(110,110,110),font=FONT)
    img.save(W+'/renders/'+name)
if __name__=='__main__':
    # Board frame (KiCad x, Y = -KiCad y), DIN socket facing up, USB-C on the right edge
    draw_section('11_section_wheel_oled.png',0,142.55,1,(-66,-18),(-7,25.5),
        'Coupe x=142.55 (molette S1 + OLED U5)',
        ('OLED sur support J15 de 5 mm : verre z=11.74, plafond z=12.8, fenêtre chanfreinée','molette : dépasse du bord haut'))
    draw_section('12_section_din.png',0,111.36,1,(-66,-18),(-7,25.5),
        'Coupe x=111.36 (axe de la DIN J3)',('DIN : haut z=21.25, plafond de la bosse z=22.3','le boîtier s\'arrête au ras de la face de la prise'))
    draw_section('13_section_usb.png',1,-104.42,0,(138,168),(-7,25.5),
        'Coupe y=104.42 (USB-C J1)',('face USB x=164.2, mur intérieur x=165.0','poche extérieure 1.2 mm'),scale=16)
    draw_section('14_section_columns.png',0,133.3,1,(-116,-20),(-7,25.5),
        'Coupe x=133.3 (colonne H2, vis M3 + insert)',(),scale=11)
    draw_section('15_section_oled_post.png',1,-32.3,0,(118,170),(-7,25.5),
        'Coupe y=32.3 (poteau sous le bout de l\'OLED)',('poteau Ø3 du fond, à travers le trou Ø3.6 du PCB','sommet z=9.0, dessous du module z=9.1'),scale=14)
