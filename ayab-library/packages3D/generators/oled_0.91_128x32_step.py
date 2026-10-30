"""Write a coloured STEP (AP214) assembly of axis-aligned boxes: a 0.91in 128x32 I2C OLED module.

Coordinates in mm, footprint frame of Display:ER_OLEDM0.91_1x-I2C with model y = -footprint y
Dimensions from the Hansheng HS91L02W2C01 drawing (LCSC C5248081), same outline as the ER-OLEDM0.91
(pin 1 at the origin, module body x -2.19..9.81, footprint y -1.5..36.5)."""
import sys

class Step:
    def __init__(self):
        self.lines, self.n = [], 0
    def add(self, s):
        self.n += 1
        self.lines.append(f'#{self.n}={s};')
        return f'#{self.n}'

def write(boxes, path, name):
    st = Step(); a = st.add
    ctx_len = a("(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.))")
    ctx_ang = a("(NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.))")
    ctx_sol = a("(NAMED_UNIT(*) SI_UNIT($,.STERADIAN.) SOLID_ANGLE_UNIT())")
    unc = a(f"UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),{ctx_len},'distance_accuracy_value','confusion accuracy')")
    ctx = a(f"(GEOMETRIC_REPRESENTATION_CONTEXT(3) GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT(({unc})) "
            f"GLOBAL_UNIT_ASSIGNED_CONTEXT(({ctx_len},{ctx_ang},{ctx_sol})) REPRESENTATION_CONTEXT('Context #1','3D Context with UNIT and UNCERTAINTY'))")
    appctx = a("APPLICATION_CONTEXT('core data for automotive mechanical design processes')")
    a(f"APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,{appctx})")
    pctx = a(f"PRODUCT_CONTEXT('',{appctx},'mechanical')")
    prod = a(f"PRODUCT('{name}','{name}','',({pctx}))")
    a(f"PRODUCT_RELATED_PRODUCT_CATEGORY('part',$,({prod}))")
    pdf = a(f"PRODUCT_DEFINITION_FORMATION('','',{prod})")
    pdctx = a(f"PRODUCT_DEFINITION_CONTEXT('part definition',{appctx},'design')")
    pd = a(f"PRODUCT_DEFINITION('design','',{pdf},{pdctx})")
    pds = a(f"PRODUCT_DEFINITION_SHAPE('','',{pd})")
    origin = a("CARTESIAN_POINT('',(0.,0.,0.))")
    dz = a("DIRECTION('',(0.,0.,1.))"); dx = a("DIRECTION('',(1.,0.,0.))")
    world = a(f"AXIS2_PLACEMENT_3D('',{origin},{dz},{dx})")
    solids, styled = [], []
    def P(x, y, z): return a(f"CARTESIAN_POINT('',({x:.4f},{y:.4f},{z:.4f}))")
    def D(x, y, z): return a(f"DIRECTION('',({x:.1f},{y:.1f},{z:.1f}))")
    for (x0, x1, y0, y1, z0, z1, rgb, label) in boxes:
        X, Y, Z = (x0, x1), (y0, y1), (z0, z1)
        vp = {}
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    vp[i, j, k] = a(f"VERTEX_POINT('',{P(X[i], Y[j], Z[k])})")
        edges = {}
        def edge(u, v):
            if (u, v) in edges: return edges[u, v], True
            if (v, u) in edges: return edges[v, u], False
            p0 = (X[u[0]], Y[u[1]], Z[u[2]]); p1 = (X[v[0]], Y[v[1]], Z[v[2]])
            d = [p1[t] - p0[t] for t in range(3)]; L = max(abs(c) for c in d)
            vec = a(f"VECTOR('',{D(*(c / L for c in d))},1.)")
            line = a(f"LINE('',{P(*p0)},{vec})")
            e = a(f"EDGE_CURVE('',{vp[u]},{vp[v]},{line},.T.)")
            edges[u, v] = e
            return e, True
        faces = []
        # each face: fixed axis/value, outward normal, 4 corners counter-clockwise seen from outside
        for ax in range(3):
            for side in range(2):
                o1, o2 = [t for t in range(3) if t != ax]
                quad = [(0, 0), (1, 0), (1, 1), (0, 1)]
                corners = []
                for q in quad:
                    c = [0, 0, 0]; c[ax] = side; c[o1], c[o2] = q; corners.append(tuple(c))
                n = [0, 0, 0]; n[ax] = 1 if side else -1
                # (o1,o2,ax) is right-handed for ax=0 (y,z,x), ax=1 (x,z,y) is left-handed, ax=2 (x,y,z) right-handed
                righthanded = ax != 1
                if righthanded != bool(side):
                    corners = corners[::-1]
                oes = []
                for t in range(4):
                    e, fwd = edge(corners[t], corners[(t + 1) % 4])
                    oes.append(a(f"ORIENTED_EDGE('',*,*,{e},{'.T.' if fwd else '.F.'})"))
                loop = a(f"EDGE_LOOP('',({','.join(oes)}))")
                bound = a(f"FACE_OUTER_BOUND('',{loop},.T.)")
                c0 = corners[0]
                ref = [0, 0, 0]; ref[o1] = 1
                ax3 = a(f"AXIS2_PLACEMENT_3D('',{P(X[c0[0]], Y[c0[1]], Z[c0[2]])},{D(*n)},{D(*ref)})")
                plane = a(f"PLANE('',{ax3})")
                faces.append(a(f"ADVANCED_FACE('',({bound}),{plane},.T.)"))
        shell = a(f"CLOSED_SHELL('',({','.join(faces)}))")
        solid = a(f"MANIFOLD_SOLID_BREP('{label}',{shell})")
        solids.append(solid)
        col = a(f"COLOUR_RGB('',{rgb[0]:.3f},{rgb[1]:.3f},{rgb[2]:.3f})")
        fill = a(f"FILL_AREA_STYLE_COLOUR('',{col})")
        fas = a(f"FILL_AREA_STYLE('',({fill}))")
        sfa = a(f"SURFACE_STYLE_FILL_AREA({fas})")
        sss = a(f"SURFACE_SIDE_STYLE('',({sfa}))")
        ss = a(f"SURFACE_STYLE_USAGE(.BOTH.,{sss})")
        psa = a(f"PRESENTATION_STYLE_ASSIGNMENT(({ss}))")
        styled.append(a(f"STYLED_ITEM('color',({psa}),{solid})"))
    rep = a(f"ADVANCED_BREP_SHAPE_REPRESENTATION('{name}',({world},{','.join(solids)}),{ctx})")
    a(f"SHAPE_DEFINITION_REPRESENTATION({pds},{rep})")
    a(f"MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION('',({','.join(styled)}),{ctx})")
    hdr = ("ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('" + name + "'),'2;1');\n"
           "FILE_NAME('" + name + ".step','2026-10-29T00:00:00',(''),(''),'','','');\n"
           "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\nENDSEC;\nDATA;\n")
    open(path, 'w').write(hdr + '\n'.join(st.lines) + '\nENDSEC;\nEND-ISO-10303-21;\n')

def oled():
    H, T, G = 2.5, 1.2, 1.4           # header spacer, module PCB, glass
    blue, black, glass, active, gold, fpc = (0.05, 0.25, 0.6), (0.06, 0.06, 0.06), (0.04, 0.04, 0.05), (0.1, 0.3, 0.55), (0.85, 0.7, 0.3), (0.75, 0.45, 0.1)
    fy = lambda y0, y1: (-y1, -y0)    # footprint y (down) -> model y (up)
    b = []
    b.append((-1.27, 8.89, *fy(-1.27, 1.27), 0, H, black, 'header_spacer'))
    for i in range(4):
        x = i * 2.54
        b.append((x - 0.32, x + 0.32, *fy(-0.32, 0.32), -3.0, H + T + 0.5, gold, f'pin{i + 1}'))
    b.append((-2.19, 9.81, *fy(-1.5, 36.5), H, H + T, blue, 'module_pcb'))
    b.append((-1.94, 9.56, *fy(4.0, 34.0), H + T, H + T + G, glass, 'glass'))           # 30.0 x 11.5 panel
    b.append((2.126, 7.71, *fy(6.12, 28.5), H + T + G, H + T + G + 0.05, active, 'active_area'))  # HS91L02W2C01: AA 7.62 mm from the board end
    b.append((0.5, 7.1, *fy(34.0, 35.6), H + T - 0.3, H + T + G, fpc, 'fpc'))          # ribbon folded under the panel
    return b

write(oled(), sys.argv[1], 'OLED_0.91_128x32_I2C')
