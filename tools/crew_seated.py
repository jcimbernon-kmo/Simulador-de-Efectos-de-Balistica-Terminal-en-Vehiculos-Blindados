"""Tripulacion sentada del Pz IV H: conductor y radiooperador (ametrallador del casco).

Cada tripulante se construye en ocho piezas CONVEXAS: cabeza, torso, y muslo,
pierna y pie de cada lado. Un cuerpo sentado es concavo en el cuello, la cadera,
la rodilla, el tobillo y entre las piernas; si fuera una sola pieza, el calculo
por geometria contaria como carne el aire de esos huecos. Cada pieza se recorta
por un plano de inglete en su articulacion, como las juntas del blindaje: las
piezas se tocan sin solaparse.

Cada pieza es la envolvente convexa de secciones elipticas, asi que la forma es
razonablemente humana y la convexidad esta garantizada por construccion.
Sin brazos: irian como piezas aparte y aportan poco al calculo.

Uso en Blender: Scripting > Open > Run Script.
Se puede ejecutar las veces que haga falta: borra y recrea sus propios objetos.
Medidas antropometricas aproximadas (adulto varon de ~1,72 m, percentil 50).
"""
import math

# --- parametros -------------------------------------------------------------
FLOOR_Z = 1.13959      # cara interior del suelo del casco
SEAT_H = 0.15          # altura del cojin del asiento sobre el suelo
RECLINE = 20.0         # grados de inclinacion del tronco hacia atras
SHIN_TILT = 20.0       # grados que adelantan los pies respecto a las rodillas
SCALE = 1.0            # 1.0 = adulto de ~1,72 m; 0.97 = ~1,67 m
HEALTH_J = 80.0        # julios; ver docs/modelo_balistico.md 3.7
MODULE_TYPE = "Crew"
MATERIAL = "Flesh"
COLLECTION = "Modules"

# nombre, X del eje del cuerpo, Y de la articulacion de la cadera
# (morro hacia -Y: el lado izquierdo del vehiculo es +X)
CREW = [
    ("Driver", +0.45, 0.78),
    ("Radio",  -0.45, 0.78),
]

# --- antropometria (metros, multiplicadas por SCALE) -----------------------
HIP_ABOVE_SEAT = 0.10  # articulacion de la cadera sobre el asiento
L_TH = 0.43            # cadera -> rodilla
L_SH = 0.42            # rodilla -> tobillo
ANKLE_H = 0.07         # tobillo sobre la suela
NECK_S = 0.64          # altura del corte del cuello, sobre el asiento

NSEG = 12             # puntos por seccion eliptica

# tronco: (altura sobre el asiento, semiancho, espalda, pecho)
#   f negativo = hacia atras, f positivo = hacia delante (respecto a la cadera)
TORSO = [(0.00, 0.17, -0.12, 0.12),
         (0.10, 0.18, -0.13, 0.13),   # cadera
         (0.30, 0.15, -0.10, 0.10),   # cintura
         (0.45, 0.17, -0.11, 0.12),   # pecho
         (0.57, 0.225, -0.08, 0.08),  # hombros
         (0.64, 0.06, -0.05, 0.05)]   # base del cuello
HEAD = [(0.64, 0.06, -0.05, 0.05),
        (0.70, 0.07, -0.08, 0.10),    # mandibula
        (0.78, 0.078, -0.10, 0.10),   # ojos
        (0.85, 0.075, -0.10, 0.08),
        (0.89, 0.04, -0.04, 0.03)]    # coronilla
# cada pierna por separado, centrada a +-LEG_X del eje del cuerpo
LEG_X = 0.095
# muslo: (distancia desde la cadera, semiancho, abajo, arriba)
THIGH = [(-0.08, 0.085, -0.10, 0.08),
         (0.00, 0.085, -0.10, 0.08),
         (0.20, 0.08, -0.08, 0.07),
         (L_TH, 0.06, -0.06, 0.06),
         (L_TH + 0.07, 0.06, -0.05, 0.05)]
# pierna: (distancia desde la rodilla, semiancho, detras, delante)
SHIN = [(-0.07, 0.06, -0.06, 0.06),
        (0.00, 0.06, -0.06, 0.06),
        (0.18, 0.055, -0.07, 0.05),   # gemelo
        (L_SH, 0.04, -0.04, 0.04),    # tobillo
        (L_SH + 0.05, 0.04, -0.04, 0.04)]
# pie, en el plano sagital y respecto al tobillo: (adelante, arriba)
FOOT = [(-0.04, 0.05), (0.04, 0.05),
        (-0.06, -ANKLE_H + 0.002), (-0.06, 0.03), (0.04, 0.03),
        (0.13, -ANKLE_H + 0.05), (0.18, -ANKLE_H + 0.025), (0.16, -ANKLE_H + 0.002)]
FOOT_HW = 0.045


# --- geometria pura, sin Blender --------------------------------------------
def _n2(v):
    m = math.hypot(v[0], v[1])
    return (v[0] / m, v[1] / m)


def _clip(points, origin, normal, keep_negative):
    """Recorta por un plano y devuelve los puntos del lado elegido mas los cortes
    de cada par que lo cruza. La envolvente convexa del resultado es exactamente
    la pieza recortada."""
    sgn = 1.0 if keep_negative else -1.0
    d = [sgn * sum((p[i] - origin[i]) * normal[i] for i in range(3)) for p in points]
    out = [p for p, di in zip(points, d) if di <= 1e-12]
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            if d[i] * d[j] < 0:
                t = d[i] / (d[i] - d[j])
                out.append(tuple(points[i][k] + t * (points[j][k] - points[i][k])
                                 for k in range(3)))
    return out


def _miter(joint, ua, ub):
    """Plano bisector en el plano sagital entre dos piezas que salen de 'joint'
    en las direcciones ua y ub. Devuelve (origen, normal) con la pieza A en el
    lado negativo."""
    b = _n2((ua[0] + ub[0], ua[1] + ub[1]))
    n = (-b[1], b[0])
    if n[0] * ua[0] + n[1] * ua[1] > 0:
        n = (-n[0], -n[1])
    return (0.0, joint[0], joint[1]), (0.0, n[0], n[1])


def crew_parts(x_center, y_hip):
    """Devuelve {sufijo: [puntos en coordenadas del mundo]} para un tripulante."""
    s = SCALE
    hip_up = HIP_ABOVE_SEAT * s
    hip_h = SEAT_H + hip_up
    a = math.radians(RECLINE)
    tilt = math.radians(SHIN_TILT)

    # muslos: angulo que hace falta para que los pies apoyen en el suelo
    knee_h = L_SH * s * math.cos(tilt) + ANKLE_H * s
    rise = knee_h - hip_h
    if abs(rise) > L_TH * s:
        raise ValueError("los muslos no alcanzan: sube SEAT_H o baja SHIN_TILT")
    th = math.asin(rise / (L_TH * s))

    u_t = (-math.sin(a), math.cos(a))                  # eje del tronco (f, z)
    u_th = (math.cos(th), math.sin(th))                # eje del muslo
    u_sh = (math.sin(tilt), -math.cos(tilt))           # eje de la pierna
    n_th = (-math.sin(th), math.cos(th))               # "arriba" del muslo
    n_sh = (math.cos(tilt), math.sin(tilt))            # "delante" de la pierna
    knee = (L_TH * s * u_th[0], L_TH * s * u_th[1])
    ankle = (knee[0] + L_SH * s * u_sh[0], knee[1] + L_SH * s * u_sh[1])
    toe = (ankle[0] + 0.18 * s, ankle[1] + (-ANKLE_H + 0.025) * s)
    u_ft = _n2((toe[0] - ankle[0], toe[1] - ankle[1]))

    def rot(f, z):  # inclina hacia atras alrededor de la cadera
        return (f * math.cos(a) - z * math.sin(a), f * math.sin(a) + z * math.cos(a))

    def sections(table, frame, xc=0.0):
        """Secciones elipticas: semiancho lateral y extension en el plano sagital."""
        pts = []
        for pos, hw, lo, hi in table:
            tc, tr = (lo + hi) / 2.0, (hi - lo) / 2.0
            for k in range(NSEG):
                ang = 2.0 * math.pi * k / NSEG
                f, z = frame(pos * s, (tc + tr * math.sin(ang)) * s)
                pts.append(((xc + hw * math.cos(ang)) * s, f, z))
        return pts

    torso = sections(TORSO, lambda h, f: rot(f, h - hip_up))
    head = sections(HEAD, lambda h, f: rot(f, h - hip_up))
    leg = {}
    for side, xc in (("L", LEG_X), ("R", -LEG_X)):
        leg[side] = (
            sections(THIGH, lambda d, t: (d * u_th[0] + t * n_th[0],
                                          d * u_th[1] + t * n_th[1]), xc),
            sections(SHIN, lambda d, t: (knee[0] + d * u_sh[0] + t * n_sh[0],
                                         knee[1] + d * u_sh[1] + t * n_sh[1]), xc),
            [((xc + dx) * s, ankle[0] + f * s, ankle[1] + z * s)
             for f, z in FOOT for dx in (-FOOT_HW, FOOT_HW)])

    seat = ((0.0, 0.0, -hip_up), (0.0, 0.0, -1.0))           # z >= asiento
    floor = ((0.0, 0.0, -hip_h + 0.002), (0.0, 0.0, -1.0))   # z >= suelo
    neck_o = (0.0,) + rot(0.0, NECK_S * s - hip_up)
    neck = (neck_o, (0.0, u_t[0], u_t[1]))
    hip = _miter((0.0, 0.0), u_t, u_th)
    knee_p = _miter(knee, (-u_th[0], -u_th[1]), u_sh)
    ankle_p = _miter(ankle, (-u_sh[0], -u_sh[1]), u_ft)

    def world(pts):
        return [(x_center + x, y_hip - f, FLOOR_Z + hip_h + z) for x, f, z in pts]

    out = {
        "Head": world(_clip(head, *neck, False)),
        "Torso": world(_clip(_clip(_clip(torso, *neck, True), *hip, True), *seat, True)),
    }
    # el lado izquierdo del tripulante es +X (morro hacia -Y)
    for side, (thigh, shin, foot) in leg.items():
        out[f"Thigh_{side}"] = world(_clip(_clip(_clip(thigh, *hip, False),
                                                 *knee_p, True), *seat, True))
        out[f"Shin_{side}"] = world(_clip(_clip(_clip(shin, *knee_p, False),
                                                *ankle_p, True), *floor, True))
        out[f"Foot_{side}"] = world(_clip(_clip(foot, *ankle_p, False), *floor, True))
    return out


# --- Blender ----------------------------------------------------------------
try:
    import bpy
    import bmesh
except ImportError:      # fuera de Blender: solo la geometria, para pruebas
    bpy = None


def _make(name, points, collection):
    old = bpy.data.objects.get(name)
    if old is not None:
        mesh = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)

    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    cz = sum(p[2] for p in points) / len(points)

    bm = bmesh.new()
    for p in points:
        bm.verts.new((p[0] - cx, p[1] - cy, p[2] - cz))
    ret = bmesh.ops.convex_hull(bm, input=bm.verts)
    loose = [g for g in ret["geom_interior"] + ret["geom_unused"]
             if isinstance(g, bmesh.types.BMVert)]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0),
                             verts=bm.verts, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = (cx, cy, cz)
    collection.objects.link(obj)
    obj["Module_Type"] = MODULE_TYPE
    obj["Health"] = float(HEALTH_J)
    obj["Armour_Material"] = MATERIAL
    return obj


def build():
    coll = bpy.data.collections.get(COLLECTION) or bpy.context.scene.collection
    for crew_name, x, y in CREW:
        for part, pts in crew_parts(x, y).items():
            _make(f"MOD_{crew_name}_{part}", pts, coll)


if bpy is not None:
    build()
