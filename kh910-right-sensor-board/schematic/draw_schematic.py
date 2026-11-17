import schemdraw, schemdraw.elements as elm, sys
import matplotlib; matplotlib.use('Agg')
OUT=sys.argv[1]
schemdraw.config(fontsize=11, lw=1.3, bgcolor='white')
class Sheet(schemdraw.Drawing):
    def __init__(self,file,dpi=130,show=False):
        super().__init__(show=False); self._f=file  # only the .svg is written
    def __exit__(self,*a):
        super().__exit__(*a); self.save(self._f[:-4]+'.svg',transparent=False)

GREY='#8a8a8a'; RED='#d02020'; BLUE='#1f5fbf'; GREEN='#1a8a3a'
def lab(d,pt,text,loc='right',color='black',dx=0.15):
    d.add(elm.Label().at((pt[0]+(dx if loc=='right' else -dx),pt[1])).label(text,loc=loc,color=color,halign='left' if loc=='right' else 'right'))
def flag(d,pt,name,side='right',color='black'):
    t=elm.Tag(width=0.35+0.13*len(name)).label(name,fontsize=9).color(color)
    t=t.left() if side=='left' else t.right()
    return d.add(t.at(pt))
def unk(d,pt,loc='left',text='?'):
    l=d.add(elm.Line().at(pt).length(0.6).left() if loc=='left' else elm.Line().at(pt).length(0.6).right()); lab(d,l.end,text,loc,GREY); return l
def title(d,xy,t,sub=''):
    d.add(elm.Label().at(xy).label(t,fontsize=14,halign='left')); 
    if sub: d.add(elm.Label().at((xy[0],xy[1]-0.55)).label(sub,fontsize=10,color=GREY,halign='left'))
def gnd(d,pt): d.add(elm.Ground().at(pt))
def vcc(d,pt): d.add(elm.Vdd().at(pt).label('+5V'))

# ---------------- 1. HALL ----------------
def comp(d,at,name,pp,pn,po,minus_top=False):
    e=elm.Opamp(leads=True).right()
    if not minus_top: e=e.flip()
    c=d.add(e.anchor('center').at(at))
    d.add(elm.Label().at((c.center[0]-0.25,c.center[1])).label(name,fontsize=9))
    up=0.28; dn=-0.3
    lab(d,(c.in2[0]-0.05,c.in2[1]+(dn if minus_top else up)),pp); lab(d,(c.in1[0]-0.05,c.in1[1]+(up if minus_top else dn)),pn); lab(d,(c.out[0]-0.05,c.out[1]+0.3),po)
    c.minus_top=minus_top
    return c
def threshold_cmp(d,c,rtop,rbot,rser,rhys,outlabel):
    """+ input: divider rtop (from +5V) / rbot (to GND) through rser; hysteresis rhys from the output."""
    p=(c.in2[0]-0.6,c.in2[1]); d.add(elm.Line().at(c.in2).left().length(0.6)); d.add(elm.Dot().at(p))
    rs=d.add(elm.Resistor().at(p).left().length(2.2).label(rser,loc='top' if not c.minus_top else 'bottom')); t=rs.end; d.add(elm.Dot().at(t))
    r=d.add(elm.Resistor().at(t).up().length(1.6).label(rtop,loc='top')); vcc(d,r.end)
    r=d.add(elm.Resistor().at(t).down().length(1.6).label(rbot,loc='top')); gnd(d,r.end)
    o=(c.out[0]+0.9,c.out[1]); d.add(elm.Line().at(c.out).right().tox(o[0])); d.add(elm.Dot().at(o))
    d.add(elm.Line().at(o).right().length(0.6)); d.add(elm.Dot(open=True)); lab(d,(o[0]+0.6,o[1]),outlabel,color=BLUE)
    sgn=-1 if c.minus_top else 1
    d.add(elm.Line().at(o).up(1.5*sgn) if sgn>0 else elm.Line().at(o).down(1.5)); d.add(elm.Resistor().left().tox(p[0]).label(rhys+'  hysteresis',loc='top' if sgn>0 else 'bottom')); d.add(elm.Line().toy(p[1]))
with Sheet(f'{OUT}/1_hall.png') as d:
    title(d,(-6,7.4),'Hall sensor channel','hall board on bottom harness M (+5V), O (GND), N, P (outputs)  ·  IC303B difference amp  ·  IC302C/D: two thresholds on the hall signal')
    op=d.add(elm.Opamp(leads=True).right().at((0,0)).anchor('center'))
    d.add(elm.Label().at((op.center[0]-0.3,op.center[1])).label('IC303B\nµPC358',fontsize=9))
    lab(d,(op.in1[0]-0.05,op.in1[1]+0.3),'6'); lab(d,(op.in2[0]-0.05,op.in2[1]-0.3),'5'); lab(d,(op.out[0]-0.05,op.out[1]+0.3),'7')
    r334=d.add(elm.Resistor().at(op.in1).left().label('R334',loc='top')); d.add(elm.Dot(open=True).at(r334.end)); lab(d,r334.end,'P  hall out',loc='left',color=BLUE)
    r335=d.add(elm.Resistor().at(op.in2).left().label('R335',loc='bottom')); d.add(elm.Dot(open=True).at(r335.end)); lab(d,r335.end,'N  hall out',loc='left',color=BLUE)
    j=(op.in1[0]-0.5,op.in1[1]); d.add(elm.Dot().at(j)); d.add(elm.Line().at(j).up().length(1.3))
    d.add(elm.Resistor().right().tox(op.out[0]+0.7).label('R332',loc='top')); d.add(elm.Line().down().toy(op.out[1]))
    k=(op.in2[0]-0.5,op.in2[1]); d.add(elm.Dot().at(k)); d.add(elm.Line().at(k).down().length(1.8))
    r333=d.add(elm.Resistor().right().length(3).label('R333',loc='bottom')); w=r333.end
    pot=d.add(elm.Potentiometer().up().at((op.out[0]+1.6,w[1]-1.5)).label('VR301',loc='bottom'))
    d.add(elm.Line().at(w).right().tox(pot.tap[0])); gnd(d,pot.start); vcc(d,pot.end)
    n=(op.out[0]+0.7,op.out[1]); d.add(elm.Line().at(op.out).right().length(0.7)); d.add(elm.Dot().at(n))
    d.add(elm.Line().at(n).up().length(0.9)); d.add(elm.Dot(open=True)); lab(d,(n[0]+0.15,n[1]+0.9),'CH301 test point',color=GREEN)
    # hall signal bus to the − inputs of IC302C and IC302D
    XC=12.5
    cC=comp(d,(XC,3.6),'IC302C\nµPC339','9','8','14')
    cD=comp(d,(XC,-3.6),'IC302D\nµPC339','11','10','13',minus_top=True)
    bx=cC.in1[0]-0.35
    d.add(elm.Line().at(n).right().tox(bx)); d.add(elm.Dot().at((bx,n[1])))
    d.add(elm.Line().at((bx,n[1])).up().toy(cC.in1[1])); d.add(elm.Line().right().tox(cC.in1[0]))
    d.add(elm.Line().at((bx,n[1])).down().toy(cD.in1[1])); d.add(elm.Line().right().tox(cD.in1[0]))
    threshold_cmp(d,cC,'R318','R317','R316','R315','C  → S-5.8?  (AYAB "EOL_R")')
    threshold_cmp(d,cD,'R320','R319','R321','R322','D  → S-5.7?  (AYAB "910_L")')
# ---------------- 2. OPTICAL ----------------
with Sheet(f'{OUT}/2_optical.png') as d:
    title(d,(-6,5.6),'Mylar reader (optical) channel','optical board on bottom harness J (signal), K (GND), L (+5V)  ·  IC302A/B: two thresholds on the optical signal')
    c1=comp(d,(4,2.5),'IC302A\nµPC339','5','4','2')
    c2=comp(d,(4,-3.5),'IC302B\nµPC339','7','6','1',minus_top=True)
    J=(-2,0); d.add(elm.Dot(open=True).at(J)); lab(d,J,'J  optical signal',loc='left',color=BLUE)
    bx=c1.in1[0]-0.35
    d.add(elm.Line().at(J).right().tox(bx)); d.add(elm.Dot().at((bx,0))); lab(d,(J[0]+0.6,0.3),'via148',color=GREY)
    d.add(elm.Line().at((bx,0)).up().toy(c1.in1[1])); d.add(elm.Line().right().tox(c1.in1[0]))
    d.add(elm.Line().at((bx,0)).down().toy(c2.in1[1])); d.add(elm.Line().right().tox(c2.in1[0]))
    # A: threshold VREF1 from the encoder sheet's ladder
    q=(c1.in2[0]-0.6,c1.in2[1]); d.add(elm.Line().at(c1.in2).left().length(0.6)); d.add(elm.Dot().at(q))
    d.add(elm.Line().at(q).up().length(0.8)); d.add(elm.Line().left().length(0.3)); flag(d,(q[0]-0.3,q[1]+0.8),'VREF1',side='left')
    lab(d,(q[0]-0.4,q[1]+0.35),'via098',loc='left',color=GREY)
    o=d.add(elm.Line().at(c1.out).right().length(0.8)); d.add(elm.Dot(open=True)); lab(d,o.end,'B  → S-5.9?  (unused by AYAB)',color=BLUE)
    # B: R311/R312 divider through R313, R314 hysteresis
    q2=(c2.in2[0]-0.6,c2.in2[1]); d.add(elm.Line().at(c2.in2).left().length(0.6)); d.add(elm.Dot().at(q2))
    r313=d.add(elm.Resistor().at(q2).left().length(2.2).label('R313',loc='bottom')); nd=r313.end; d.add(elm.Dot().at(nd))
    r=d.add(elm.Resistor().at(nd).up().length(1.6).label('R311',loc='top')); vcc(d,r.end)
    r=d.add(elm.Resistor().at(nd).down().length(1.6).label('R312',loc='top')); gnd(d,r.end)
    oa=(c2.out[0]+1.0,c2.out[1]); d.add(elm.Line().at(c2.out).right().length(1.0)); d.add(elm.Dot().at(oa))
    d.add(elm.Line().at(oa).right().length(0.6)); d.add(elm.Dot(open=True)); lab(d,(oa[0]+0.6,oa[1]),'A  → S-5.10?  (unused by AYAB)',color=BLUE)
    d.add(elm.Line().at(oa).down().length(1.5)); d.add(elm.Resistor().left().tox(q2[0]).label('R314  hysteresis',loc='bottom')); d.add(elm.Line().up().toy(q2[1]))
# ---------------- 3. ENCODERS ----------------
def openjp(d,start,length=0.8,name='JP'):
    d.add(elm.Line().at(start).right(0.25)); a=(start[0]+0.25,start[1]); d.add(elm.Dot(open=True).at(a))
    b=(a[0]+length-0.5,a[1]); d.add(elm.Dot(open=True).at(b)); d.add(elm.Line().at(b).right(0.25))
    lab(d,((a[0]+b[0])/2-0.25,a[1]+0.35),name+' open',color=GREY); return (b[0]+0.25,b[1])
def dbox(d,x0,y0,x1,y1,name):
    for a,b in (((x0,y0),(x1,y0)),((x1,y0),(x1,y1)),((x1,y1),(x0,y1)),((x0,y1),(x0,y0))):
        d.add(elm.Line().at(a).to(b).linestyle('--').color(GREY))
    d.add(elm.Label().at((x0+0.1,y1-0.35)).label(name,halign='left',fontsize=11))
def bpin(d,xy,n,role,side):
    lab(d,(xy[0]+(0.12 if side=='left' else -0.12),xy[1]-0.28),role,color=BLUE,loc='right' if side=='left' else 'left',dx=0)
    lab(d,(xy[0]+(-0.12 if side=='left' else 0.12),xy[1]+0.25),str(n),loc='left' if side=='left' else 'right',dx=0)
def chan(d,xl,yA,yK,yC,yE):
    d.add(elm.LED().at((xl,yA)).down().toy(yK))
    q=d.add(elm.NpnPhoto().right().anchor('base').at((xl+1.6,(yA+yK)/2)))
    d.add(elm.Line().at(q.collector).up().toy(yC)); d.add(elm.Line().at(q.emitter).down().toy(yE)); return q
def cmp(d,at,name,pp,pn,po):
    c=d.add(elm.Opamp(leads=True).right().flip().anchor('center').at(at))
    d.add(elm.Label().at((c.center[0]-0.25,c.center[1])).label(name,fontsize=9))
    lab(d,(c.in2[0]-0.05,c.in2[1]+0.28),pp); lab(d,(c.in1[0]-0.05,c.in1[1]-0.3),pn); lab(d,(c.out[0]-0.05,c.out[1]+0.3),po); return c
with Sheet(f'{OUT}/3_encoders.png') as d:
    LAD={}
    title(d,(-7,12.6),'Encoder channels','PI2 pinout from silkscreen (K, E); PI1 pinout inferred from matching resistor sets  ·  IC301 µPC324 sections B–D as comparators  ·  grey/dashed = not yet confirmed')
    # ---- PI1 ----
    X0,X1=0,5.2; yA1,yK1,yA2,yK2=8.0,6.2,3.8,2.0; yC,yE1,yE2=8.7,5.6,1.6
    dbox(d,X0,0.3,X1,9.6,'PI1  dual')
    q1=chan(d,1.2,yA1,yK1,yC,yE1); q2=chan(d,1.2,yA2,yK2,4.6,yE2)
    cx=q1.collector[0]
    for y in (yA1,yK1,yA2,yK2): d.add(elm.Line().at((1.2,y)).left().tox(X0))
    bpin(d,(X0,yA1),4,'A2','left'); bpin(d,(X0,yK1),6,'K2','left'); bpin(d,(X0,yA2),3,'A1','left'); bpin(d,(X0,yK2),5,'K1','left')
    d.add(elm.Line().at((cx,yC)).right().tox(X1));
    d.add(elm.Line().at((cx,yC)).down().toy(q1.collector[1]))
    xb=cx+0.9
    d.add(elm.Line().at((cx,4.6)).right().tox(xb)); d.add(elm.Line().at((xb,4.6)).up().toy(yC)); d.add(elm.Dot().at((xb,yC)))
    d.add(elm.Line().at((cx,yE1)).right().tox(X1)); d.add(elm.Line().at((cx,yE2)).right().tox(X1))
    bpin(d,(X1,yC),8,'C','right'); bpin(d,(X1,yE1),2,'E2','right'); bpin(d,(X1,yE2),1,'E1','right'); bpin(d,(X1,0.8),7,'NC','right')
    # LED cathodes → current resistors (same value as R329 on PI2)
    for yK,rk in ((yK1,'R331'),(yK2,'R330')):
        d.add(elm.Line().at((X0,yK)).left().length(1.2)); r=d.add(elm.Resistor().down().length(1.2).label(rk,loc='bottom')); gnd(d,r.end)
    # anodes 3–4 tied, common LED supply, on to PI2's anode
    xk=X0-2.3
    d.add(elm.Line().at((X0,yA1)).left().tox(xk)); d.add(elm.Line().at((xk,yA1)).down().toy(yA2))
    d.add(elm.Line().at((X0,yA2)).left().tox(xk)); d.add(elm.Dot().at((xk,yA2)))
    d.add(elm.Dot().at((xk,yA1))); d.add(elm.Line().at((xk,yA1)).up().toy(10.1)); d.add(elm.Line().right().tox(X1+0.2)); d.add(elm.Line().down().toy(yC)); d.add(elm.Dot().at((X1+0.2,yC)))
    # ---- PI2 ----
    yA,yK,yCC,yEE=-2.4,-4.2,-1.7,-4.9
    dbox(d,X0,-5.5,X1,-0.9,'PI2  single')
    q=chan(d,1.2,yA,yK,yCC,yEE)
    d.add(elm.Line().at((1.2,yA)).left().tox(X0)); d.add(elm.Line().at((1.2,yK)).left().tox(X0))
    bpin(d,(X0,yA),4,'A','left'); bpin(d,(X0,yK),3,'K','left')
    d.add(elm.Line().at((q.collector[0],yCC)).right().tox(X1)); d.add(elm.Line().at((q.emitter[0],yEE)).right().tox(X1))
    bpin(d,(X1,yCC),1,'C','right'); bpin(d,(X1,yEE),2,'E','right')
    d.add(elm.Line().at((xk,yA2)).down().toy(yA)); d.add(elm.Line().at((xk,yA)).right().tox(X0))
    d.add(elm.Line().at((X0,yK)).left().length(1.2)); r=d.add(elm.Resistor().down().length(1.2).label('R329',loc='bottom')); gnd(d,r.end)
    d.add(elm.Line().at((X1,yCC)).right().length(0.8)); vcc(d,(X1+0.8,yCC))
    # collector supply, emitter loads (right)
    d.add(elm.Line().at((X1,yC)).right().length(0.2)); c=d.add(elm.Diode().right().reverse().length(1.4).label('D301',loc='top'))
    l=d.add(elm.Line().right().length(0.3)); vcc(d,l.end); lab(d,(l.end[0]-0.9,l.end[1]-0.4),'via089',color=GREY)
    EN={}
    for y,rl,lbl,jp,jr,rs in ((yE1,'R324','E2','JP2','R323','R303'),(yE2,'R326','E1','JP1','R325','R304'),(yEE,'R328','PI2 E',None,None,'R302')):
        d.add(elm.Line().at((X1,y)).right().length(1.0)); n=(X1+1.0,y); d.add(elm.Dot().at(n))
        if jp:
            m=(n[0],n[1]-0.5); d.add(elm.Line().at(n).down().length(0.5)); d.add(elm.Dot().at(m))
            d.add(elm.Line().at(m).right().length(0.3)); d.add(elm.Dot(open=True)); d.add(elm.Dot(open=True).at((m[0]+1.0,m[1])))
            lab(d,(m[0]+0.35,m[1]-0.35),jp,color=GREY)
            r=d.add(elm.Resistor().at((m[0]+1.0,m[1])).right().length(1.4).label(jr,loc='bottom')); d.add(elm.Line().down().length(0.2)); gnd(d,(r.end[0],r.end[1]-0.2))
            r=d.add(elm.Resistor().at(m).down().length(1.2).label(rl,loc='bottom')); gnd(d,r.end)
            EN[lbl]=n
        else:
            r=d.add(elm.Resistor().at(n).down().length(1.2).label(rl,loc='bottom')); gnd(d,r.end); EN[lbl]=n
    # ---- IC301 comparators ----
    XC=17
    cB=cmp(d,(XC,9.0),'IC301B\nµPC324','5','6','7')
    pB=(cB.in2[0]-0.6,cB.in2[1]); d.add(elm.Line().at(cB.in2).left().length(0.6)); d.add(elm.Dot().at(pB))
    oB=(cB.out[0]+0.9,cB.out[1]); d.add(elm.Line().at(cB.out).right().tox(oB[0])); d.add(elm.Dot().at(oB))
    d.add(elm.Line().at(oB).right().length(0.6)); d.add(elm.Dot(open=True)); lab(d,(oB[0]+0.6,oB[1]),'F → S-5.5?  ENC_B',color=BLUE)
    d.add(elm.Line().at(oB).up().length(1.3)); r=d.add(elm.Resistor().left().tox(pB[0]).label('R300  hysteresis',loc='top')); d.add(elm.Line().down().toy(pB[1]))
    cC=cmp(d,(XC,3.8),'IC301C\nµPC324','10','9','8')
    pC=(cC.in2[0]-0.6,cC.in2[1]); d.add(elm.Line().at(cC.in2).left().length(0.6)); d.add(elm.Dot().at(pC))
    oC=(cC.out[0]+0.9,cC.out[1]); d.add(elm.Line().at(cC.out).right().tox(oC[0])); d.add(elm.Dot().at(oC))
    d.add(elm.Line().at(oC).right().length(0.6)); d.add(elm.Dot(open=True)); lab(d,(oC[0]+0.6,oC[1]),'G → S-5.4?  ENC_A',color=BLUE)
    d.add(elm.Line().at(oC).up().length(1.3)); d.add(elm.Resistor().left().tox(pC[0]).label('R308  hysteresis',loc='top')); d.add(elm.Line().down().toy(pC[1]))
    mC=(cC.in1[0]-1.2,cC.in1[1]); d.add(elm.Line().at(cC.in1).left().tox(mC[0]))
    col=mC[0]-2.4; REF=(col,mC[1]); LAD['col']=col
    d.add(elm.Line().at(mC).left().tox(col)); d.add(elm.Dot().at(REF))
    r310=d.add(elm.Resistor().at(REF).down().length(1.4).label('R310',loc='bottom')); gnd(d,r310.end)
    r309=d.add(elm.Resistor().at(REF).up().length(1.4).label('R309',loc='bottom')); v1=r309.end; d.add(elm.Dot().at(v1))
    d.add(elm.Line().at(v1).left().length(0.5)); flag(d,(col-0.5,v1[1]),'VREF1',side='left')
    r307=d.add(elm.Resistor().at(v1).up().length(1.4).label('R307',loc='bottom')); v0=r307.end; d.add(elm.Dot().at(v0))
    r305=d.add(elm.Resistor().at(v0).right().length(1.6).label('R305',loc='top')); d.add(elm.Line().right().length(0.3)); gnd(d,(r305.end[0]+0.3,r305.end[1]))
    r306=d.add(elm.Resistor().at(v0).up().length(1.4).label('R306',loc='top')); vcc(d,r306.end)
    cD=cmp(d,(XC,-2.6),'IC301D\nµPC324','12','13','14')
    pD=(cD.in2[0]-0.6,cD.in2[1]); d.add(elm.Line().at(cD.in2).left().length(0.6)); d.add(elm.Dot().at(pD))
    oD=(cD.out[0]+0.9,cD.out[1]); d.add(elm.Line().at(cD.out).right().tox(oD[0])); d.add(elm.Dot().at(oD))
    d.add(elm.Line().at(oD).right().length(0.6)); d.add(elm.Dot(open=True)); lab(d,(oD[0]+0.6,oD[1]),'E → S-5.6?  ENC_C',color=BLUE)
    d.add(elm.Line().at(oD).up().length(1.3)); d.add(elm.Resistor().left().tox(pD[0]).label('R301  hysteresis',loc='top')); d.add(elm.Line().down().toy(pD[1]))
    r=d.add(elm.Resistor().at(pD).left().length(1.8).label('R302',loc='top'))
    xr=r.end[0]; d.add(elm.Line().at(r.end).down().toy(EN['PI2 E'][1])); d.add(elm.Line().left().tox(EN['PI2 E'][0]))
    lab(d,(xr-2.5,EN['PI2 E'][1]+0.3),'via135',color=GREY)
    # PI1 emitters → IC301B / IC301C (+) : series resistors and assignment not traced yet
    DS=dict(linestyle='--'); 
    rB=d.add(elm.Resistor().at(pB).left().length(1.4).label('R303',loc='bottom')); n=EN['E2']; d.add(elm.Line().at(n).right().tox(9.7)); d.add(elm.Line().up().toy(pB[1])); d.add(elm.Line().right().tox(rB.end[0])); lab(d,(9.9,pB[1]+0.3),'via166',color=GREY)
    rC=d.add(elm.Resistor().at(pC).left().length(1.4).label('R304',loc='bottom')); n=EN['E1']; xv=rC.end[0]-0.2
    d.add(elm.Line().at(n).right().tox(9.9)); d.add(elm.Line().down().toy(0.4))
    d.add(elm.Line().right().tox(xv)); d.add(elm.Line().up().toy(pC[1])); d.add(elm.Line().right().tox(rC.end[0]))
    # shared IN− bus for pins 6, 9, 13
    bx=cC.in1[0]-0.3
    d.add(elm.Line().at(cB.in1).left().tox(bx)); d.add(elm.Line().down().toy(cC.in1[1]))
    d.add(elm.Line().at(cD.in1).left().tox(bx)); d.add(elm.Line().up().toy(cC.in1[1])); d.add(elm.Dot().at((bx,cC.in1[1])))
    d.add(elm.Label().at((XC-1.5,-6.0)).label('IC301A (pins 1–3) unused',color=GREY,halign='left'))
# ---------------- 4. POWER / CONNECTORS ----------------
with Sheet(f'{OUT}/4_power.png',dpi=130,show=False) as d:
    title(d,(0,4.6),'Connectors, power, jumpers')
    rows=[('I','S-5.1','+5V'),('H','S-5.2','GND'),('—','S-5.3','(empty slot)'),('G','S-5.4?','ENC_A ← IC301.8'),('F','S-5.5?','ENC_B ← IC301.7'),('E','S-5.6?','ENC_C ← IC301.14'),
          ('D','S-5.7?','"910_L" ← IC302.13 (hall, threshold 2)'),('C','S-5.8?','"EOL_R" ← IC302.14 (hall, threshold 1)'),('B','S-5.9?','IC302.2 (optical, unused by AYAB)'),('A','S-5.10?','IC302.1 (optical, unused by AYAB)')]
    y=3.6
    d.add(elm.Label().at((0,y)).label('Top harness → S-5 → AYAB shield',halign='left',fontsize=12)); y-=0.6
    for p,s5,f in rows:
        d.add(elm.Dot(open=True).at((0.4,y))); d.add(elm.Label().at((0,y)).label(p,halign='right'))
        d.add(elm.Label().at((0.8,y)).label(f'{s5:8s} {f}',halign='left',color=GREY if p=='—' else 'black')); y-=0.5
    y-=0.4; d.add(elm.Label().at((0,y)).label('Bottom harness',halign='left',fontsize=12)); y-=0.6
    for p,f in [('J','optical signal'),('K','optical GND'),('L','optical +5V'),('M','hall +5V'),('N','hall out → R335'),('O','hall GND'),('P','hall out → R334')]:
        d.add(elm.Dot(open=True).at((0.4,y))); d.add(elm.Label().at((0,y)).label(p,halign='right')); d.add(elm.Label().at((0.8,y)).label(f,halign='left')); y-=0.5
    x=9; y=3.6
    d.add(elm.Label().at((x,y)).label('Supplies',halign='left',fontsize=12)); y-=0.6
    for t in ['IC301 µPC324C: VCC pin 4, GND pin 11','IC302 µPC339C: VCC pin 3, GND pin 12','IC303 µPC358C: VCC pin 8, GND pin 4','PI2.1 on +5V; VR301 across +5V/GND']:
        d.add(elm.Label().at((x,y)).label(t,halign='left')); y-=0.5
    y-=0.4; d.add(elm.Label().at((x,y)).label('Open solder jumpers (solder side)',halign='left',fontsize=12)); y-=0.6
    for t in ['JP1: R325.1 ↔ R326.1 (PI1.1 net); R325.2 GND','JP2: R323.1 ↔ R324.1 (PI1.2 net)']:
        d.add(elm.Label().at((x,y)).label(t,halign='left')); y-=0.5
    y-=0.4; d.add(elm.Label().at((x,y)).label('Still to confirm (photos only)',halign='left',fontsize=12)); y-=0.6
    for t in ['Links drawn under parts: beep list in README','D301 orientation (band)','Resistor values (colour bands unverified)']:
        d.add(elm.Label().at((x,y)).label(t,halign='left',color=GREY)); y-=0.5
print('ok')

# ---------------- combined SVG (sheets stacked as nested SVGs) ----------------
import re
parts=[]; y=0; W=0
for f in ['1_hall.svg','2_optical.svg','3_encoders.svg','4_power.svg']:
    t=open(f'{OUT}/{f}').read()
    m=re.search(r'<svg[^>]*\bwidth="([\d.]+)pt"[^>]*\bheight="([\d.]+)pt"[^>]*viewBox="([^"]+)"',t,re.S)
    w,h,vb=float(m.group(1)),float(m.group(2)),m.group(3)
    body=t[t.index('>',m.end())+1:t.rindex('</svg>')]; pre=f.split('_')[0]+'_'
    body=re.sub(r'id="([^"]+)"',lambda k:f'id="{pre}{k.group(1)}"',body)
    body=re.sub(r'(xlink:href|href)="#([^"]+)"',lambda k:f'{k.group(1)}="#{pre}{k.group(2)}"',body)
    body=re.sub(r'url\(#([^)]+)\)',lambda k:f'url(#{pre}{k.group(1)})',body)
    parts.append(f'<svg x="0" y="{y}" width="{w}" height="{h}" viewBox="{vb}">{body}</svg>'); y+=h+20; W=max(W,w)
open(f'{OUT}/schematic_so_far.svg','w').write(f'<?xml version="1.0" encoding="utf-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}pt" height="{y}pt" viewBox="0 0 {W} {y}">\n<rect width="100%" height="100%" fill="#ffffff"/>\n'+'\n'.join(parts)+'\n</svg>\n')
