"""x3d_to_step.py IN.x3d OUT.step [NAME]  -- convert a triangle-mesh X3D model (KiCad units: 1 = 0.1 in)
into a coloured STEP (AP214) for KiCad: one open shell of planar triangular faces per material colour,
coordinates in mm. kicad-cli's STEP/GLB exports (OpenCASCADE) ignore X3D/VRML models; this makes the part
show up there. Used for SW-SMD_BL-DT (the S1 thumb wheel, from Blender)."""
import sys, xml.etree.ElementTree as ET
import numpy as np

def rotm(ax, ang):
    ax = np.array(ax, float); n = np.linalg.norm(ax)
    if n == 0 or ang == 0: return np.eye(3)
    x, y, z = ax / n; c, s = np.cos(ang), np.sin(ang); C = 1 - c
    return np.array([[c + x*x*C, x*y*C - z*s, x*z*C + y*s], [y*x*C + z*s, c + y*y*C, y*z*C - x*s], [z*x*C - y*s, z*y*C + x*s, c + z*z*C]])

def load(path):
    groups = {}
    def walk(el, M, t):
        if el.tag == 'Transform':
            tr = np.array([float(v) for v in el.get('translation', '0 0 0').split()])
            sc = np.array([float(v) for v in el.get('scale', '1 1 1').split()])
            r = [float(v) for v in el.get('rotation', '0 0 1 0').split()]
            M, t = M @ rotm(r[:3], r[3]) @ np.diag(sc), M @ tr + t
        if el.tag == 'Shape':
            mat = el.find('.//Material'); c = (0.6, 0.6, 0.6)
            if mat is not None and mat.get('diffuseColor'): c = tuple(round(float(v), 3) for v in mat.get('diffuseColor').split())
            ifs = el.find('.//IndexedFaceSet')
            if ifs is None: return
            pts = np.array([float(v) for v in ifs.find('.//Coordinate').get('point').replace(',', ' ').split()]).reshape(-1, 3)
            P = (M @ pts.T).T + t
            face = []
            for i in (int(v) for v in ifs.get('coordIndex').replace(',', ' ').split()):
                if i < 0:
                    for k in range(1, len(face) - 1): groups.setdefault(c, []).append((P[face[0]], P[face[k]], P[face[k + 1]]))
                    face = []
                else: face.append(i)
            return
        for ch in el: walk(ch, M, t)
    walk(ET.parse(path).getroot(), np.eye(3), np.zeros(3))
    return groups

def write(groups, path, name, scale=2.54):
    L = []
    def a(s):
        L.append(s); return '#%d' % len(L)
    def num(v): return '%.5f' % v
    def pt(k): return a("CARTESIAN_POINT('',(%s))" % ','.join(map(num, k)))
    def dr(k): return a("DIRECTION('',(%s))" % ','.join(map(num, k)))
    u_len = a("(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.))")
    u_ang = a("(NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.))")
    u_sol = a("(NAMED_UNIT(*) SI_UNIT($,.STERADIAN.) SOLID_ANGLE_UNIT())")
    unc = a("UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),%s,'distance_accuracy_value','confusion accuracy')" % u_len)
    ctx = a("(GEOMETRIC_REPRESENTATION_CONTEXT(3) GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((%s)) "
            "GLOBAL_UNIT_ASSIGNED_CONTEXT((%s,%s,%s)) REPRESENTATION_CONTEXT('Context #1','3D Context with UNIT and UNCERTAINTY'))"
            % (unc, u_len, u_ang, u_sol))
    app = a("APPLICATION_CONTEXT('core data for automotive mechanical design processes')")
    a("APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,%s)" % app)
    pctx = a("PRODUCT_CONTEXT('',%s,'mechanical')" % app)
    prod = a("PRODUCT('%s','%s','',(%s))" % (name, name, pctx))
    a("PRODUCT_RELATED_PRODUCT_CATEGORY('part',$,(%s))" % prod)
    pdf = a("PRODUCT_DEFINITION_FORMATION('','',%s)" % prod)
    pdctx = a("PRODUCT_DEFINITION_CONTEXT('part definition',%s,'design')" % app)
    pd = a("PRODUCT_DEFINITION('design','',%s,%s)" % (pdf, pdctx))
    pds = a("PRODUCT_DEFINITION_SHAPE('','',%s)" % pd)
    world = a("AXIS2_PLACEMENT_3D('',%s,%s,%s)" % (pt((0, 0, 0)), dr((0, 0, 1)), dr((1, 0, 0))))
    models, styled = [], []
    for col, tris in groups.items():
        verts, edges, faces = {}, {}, []
        def V(p):
            k = tuple(round(float(c) * scale, 5) for c in p)
            if k not in verts: verts[k] = a("VERTEX_POINT('',%s)" % pt(k))
            return k
        def E(k0, k1):
            if (k0, k1) in edges: return edges[k0, k1], '.T.'
            if (k1, k0) in edges: return edges[k1, k0], '.F.'
            d = np.subtract(k1, k0); d = d / np.linalg.norm(d)
            line = a("LINE('',%s,%s)" % (pt(k0), a("VECTOR('',%s,1.)" % dr(d))))
            edges[k0, k1] = a("EDGE_CURVE('',%s,%s,%s,.T.)" % (verts[k0], verts[k1], line))
            return edges[k0, k1], '.T.'
        for tri in tris:
            ks = [V(p) for p in tri]
            if len(set(ks)) < 3: continue
            p0, p1, p2 = (np.array(k) for k in ks)
            n = np.cross(p1 - p0, p2 - p0); nl = np.linalg.norm(n)
            if nl < 1e-9: continue
            n = n / nl; xd = (p1 - p0) / np.linalg.norm(p1 - p0)
            oes = []
            for i in range(3):
                e, sense = E(ks[i], ks[(i + 1) % 3])
                oes.append(a("ORIENTED_EDGE('',*,*,%s,%s)" % (e, sense)))
            loop = a("EDGE_LOOP('',(%s))" % ','.join(oes))
            bound = a("FACE_OUTER_BOUND('',%s,.T.)" % loop)
            plane = a("PLANE('',%s)" % a("AXIS2_PLACEMENT_3D('',%s,%s,%s)" % (pt(ks[0]), dr(n), dr(xd))))
            faces.append(a("ADVANCED_FACE('',(%s),%s,.T.)" % (bound, plane)))
        shell = a("OPEN_SHELL('',(%s))" % ','.join(faces))
        sbsm = a("SHELL_BASED_SURFACE_MODEL('',(%s))" % shell)
        models.append(sbsm)
        rgb = a("COLOUR_RGB('',%.3f,%.3f,%.3f)" % col)
        fas = a("FILL_AREA_STYLE('',(%s))" % a("FILL_AREA_STYLE_COLOUR('',%s)" % rgb))
        sss = a("SURFACE_SIDE_STYLE('',(%s))" % a("SURFACE_STYLE_FILL_AREA(%s)" % fas))
        psa = a("PRESENTATION_STYLE_ASSIGNMENT((%s))" % a("SURFACE_STYLE_USAGE(.BOTH.,%s)" % sss))
        styled.append(a("STYLED_ITEM('color',(%s),%s)" % (psa, sbsm)))
    rep = a("MANIFOLD_SURFACE_SHAPE_REPRESENTATION('%s',(%s),%s)" % (name, ','.join([world] + models), ctx))
    a("SHAPE_DEFINITION_REPRESENTATION(%s,%s)" % (pds, rep))
    a("MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION('',(%s),%s)" % (','.join(styled), ctx))
    hdr = ("ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('" + name + "'),'2;1');\n"
           "FILE_NAME('" + name + ".step','2026-10-30T00:00:00',(''),(''),'','','');\n"
           "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\nENDSEC;\nDATA;\n")
    open(path, 'w').write(hdr + '\n'.join('#%d=%s;' % (i + 1, s) for i, s in enumerate(L)) + '\nENDSEC;\nEND-ISO-10303-21;\n')

if __name__ == '__main__':
    g = load(sys.argv[1])
    write(g, sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else sys.argv[2].rsplit('/', 1)[-1].rsplit('.', 1)[0])
    print(sys.argv[2], {k: len(v) for k, v in g.items()})
