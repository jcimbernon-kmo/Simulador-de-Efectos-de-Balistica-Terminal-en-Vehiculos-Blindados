"""Blindaje lateral de la torreta (Turmschuerzen): genera los DOS lados, 8 mm exactos.

POR QUE NO BASTA CON ESPEJAR LO QUE HAY
---------------------------------------
Las cuatro piezas modeladas a mano en el lado R se extruyeron 8 mm a lo largo
del eje X, no a lo largo de la normal de cada plancha. Una plancha que no es
perpendicular a X sale mas fina de lo que declara:

    espesor real = 8 mm * |componente X de su normal|

    Addon_Middle_R      normal (-0,971 ; -0,240)   7,77 mm
    Addon_Back_R_00     normal (+0,964 ; -0,267)   7,71 mm
    Addon_Back_R_01     normal (-0,757 ; +0,654)   6,05 mm   <- 24 % menos
    Front_R             extruida 8 mm en X en un borde y 8 mm en Y en el otro:
                        cuna de 3,2 a 7,4 mm, con caras alabeadas (7 grupos
                        coplanares en una pieza de 5 caras)

El calculo mide el camino dentro de la malla (§3.1), no Thickness_mm, asi que
el trazador usaria 6,05 mm donde el fichero dice 8. Un espejo copiaria el
defecto al otro lado. Por eso este script reconstruye los dos lados desde el
CONTORNO EXTERIOR que tu modelaste, con el espesor medido sobre la normal.

QUE CONSERVA Y QUE CAMBIA
-------------------------
Conserva exactamente tu contorno exterior en planta y todas las alturas: las
caras exteriores no se mueven ni 0,001 mm. Cambia el lado interior de cada
plancha (ahora a 8 mm perpendiculares) y los extremos, que ahora son inglete
exacto con la vecina en vez de un corte contra el eje Y.

  - Borra SOLO los objetos que este mismo script crea (8 nombres) y los cuatro
    que habia a mano. No toca nada mas de ARM_Turret_*.
  - Front_R pasa a llamarse ARM_Turret_Addon_Front_R: el prefijo
    ARM_Turret_Front_ es de la chapa frontal que genera crear_torreta.py.

CADA PLANCHA ES CONVEXA POR CONSTRUCCION
----------------------------------------
Huella en planta (cuadrilatero: linea exterior, linea interior a T, y dos
cortes en inglete) extruida entre dos planos inclinados, uno de suelo y otro de
techo. Las caras laterales son verticales y por tanto planas; el techo y el
suelo son planos por definicion. Vecinas en inglete comparten cara exacta.

Pestana Scripting -> New -> pegar -> Run.
"""
import math

# ------------------------------------------------------------------ parametros
T = 0.008                    # espesor, medido sobre la normal
MATERIAL = "RHA"
COLECCION = "Armor"
PREFIJO = "ARM_Turret_Addon_"

# Contorno EXTERIOR del lado R (x < 0), de proa a popa. Medido en tu modelo del
# 27/10: (x, y, z_suelo, z_techo). El lado L es el espejo en X.
#   F  = punta delantera de la chapa de proa (triangulo, suelo = techo)
#   P0..P3 = esquinas en planta
PUNTOS = [
    (-0.563349, 0.673726, 1.644953, 1.644953),   # F
    (-0.965994, 0.850000, 1.632140, 2.030376),   # P0
    (-1.220573, 1.881439, 1.632140, 2.128831),   # P1
    (-0.947181, 2.869660, 1.632140, 2.128831),   # P2
    (-0.536403, 3.345258, 1.632140, 2.128831),   # P3
]
# nombre de cada tramo entre puntos consecutivos; {s} se sustituye por R o L
TRAMOS = ["Front_{s}", "Middle_{s}", "Back_{s}_00", "Back_{s}_01"]
VIEJOS = ["ARM_Turret_Front_R", "ARM_Turret_Addon_Middle_R",
          "ARM_Turret_Addon_Back_R_00", "ARM_Turret_Addon_Back_R_01"]
CENTRO = (0.0, 1.70)         # para decidir que normal es la exterior
TOL_SOLAPE = 5e-5            # 0,05 mm
# --------------------------------------------------------------------------


def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def unit(a):
    L = math.sqrt(dot(a, a))
    return tuple(x / L for x in a)


def interseccion(p, d, q, e):
    """Punto donde se cortan las rectas p + s d  y  q + t e (2D)."""
    den = d[0] * e[1] - d[1] * e[0]
    s = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return (p[0] + s * d[0], p[1] + s * d[1])


def tramos(puntos):
    """Para cada tramo: extremos, direccion, normal exterior y largo."""
    out = []
    for a, b in zip(puntos, puntos[1:]):
        d = unit((b[0] - a[0], b[1] - a[1]))
        n = (d[1], -d[0])
        m = ((a[0] + b[0]) / 2 - CENTRO[0], (a[1] + b[1]) / 2 - CENTRO[1])
        if n[0] * m[0] + n[1] * m[1] < 0:
            n = (-n[0], -n[1])
        out.append(dict(a=a, b=b, d=d, n=n,
                        L=math.hypot(b[0] - a[0], b[1] - a[1])))
    return out


def huellas(puntos):
    """Cuadrilatero en planta de cada tramo, con ingletes exactos en las juntas."""
    ts = tramos(puntos)
    # linea interior de cada tramo: pasa por a - T n con direccion d
    inter = [((t["a"][0] - T * t["n"][0], t["a"][1] - T * t["n"][1]), t["d"])
             for t in ts]
    res = []
    for k, t in enumerate(ts):
        # extremo inicial
        if k == 0:
            ia = (t["a"][0] - T * t["n"][0], t["a"][1] - T * t["n"][1])
        else:
            ia = interseccion(*inter[k - 1], *inter[k])
        # extremo final
        if k == len(ts) - 1:
            ib = (t["b"][0] - T * t["n"][0], t["b"][1] - T * t["n"][1])
        else:
            ib = interseccion(*inter[k], *inter[k + 1])
        res.append((t, [t["a"][:2], t["b"][:2], ib, ia]))
    return res


def vertices_tramo(t, huella, a, b):
    """Los 8 vertices (con duplicados) de un tramo: huella x {suelo, techo}."""
    pts = []
    for p in huella:
        s = (p[0] - t["a"][0]) * t["d"][0] + (p[1] - t["a"][1]) * t["d"][1]
        u = s / t["L"]
        zs = a[2] + (b[2] - a[2]) * u
        zt = a[3] + (b[3] - a[3]) * u
        pts.append((p[0], p[1], zs))
        pts.append((p[0], p[1], zt))
    out = []
    for p in pts:
        if not any(math.dist(p, q) < 1e-9 for q in out):
            out.append(p)
    return out


def generar(puntos):
    """Lista de (nombre, vertices) para un lado."""
    sol = []
    for (t, hu), nom, (a, b) in zip(huellas(puntos), TRAMOS,
                                    zip(puntos, puntos[1:])):
        sol.append((nom, vertices_tramo(t, hu, a, b), t))
    return sol


# ----------------------------------------------------- comprobaciones (puras)
def planos_casco(pts, eps=1e-9):
    """Planos de las caras de la envolvente convexa, por fuerza bruta."""
    n = len(pts)
    vistos = {}
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                c = cross(sub(pts[j], pts[i]), sub(pts[k], pts[i]))
                if dot(c, c) < 1e-18:
                    continue
                nn = unit(c)
                d = dot(nn, pts[i])
                lado = [dot(nn, p) - d for p in pts]
                if max(lado) <= eps:
                    pass
                elif min(lado) >= -eps:
                    nn, d = tuple(-x for x in nn), -d
                else:
                    continue
                clave = tuple(round(x, 6) for x in nn) + (round(d, 6),)
                vistos.setdefault(clave, (nn, d))
    return list(vistos.values())


def aristas_casco(pts, planos, eps=1e-7):
    en = [{i for i, p in enumerate(pts) if abs(dot(nn, p) - d) < eps}
          for nn, d in planos]
    out = []
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            if sum(1 for s in en if i in s and j in s) >= 2:
                out.append((i, j))
    return out


def penetracion(A, B):
    """Profundidad de solape entre dos convexos (<= 0 : no se solapan)."""
    pa, pb = planos_casco(A), planos_casco(B)
    ejes = [nn for nn, _ in pa] + [nn for nn, _ in pb]
    ea, eb = aristas_casco(A, pa), aristas_casco(B, pb)
    for i, j in ea:
        for k, l in eb:
            c = cross(sub(A[j], A[i]), sub(B[l], B[k]))
            if dot(c, c) > 1e-12:
                ejes.append(unit(c))
    mejor = 1e9
    for e in ejes:
        a = [dot(e, p) for p in A]
        b = [dot(e, p) for p in B]
        mejor = min(mejor, min(max(a), max(b)) - max(min(a), min(b)))
        if mejor <= 0:
            return mejor
    return mejor


def espejo(pts):
    return [(-x, y, z) for x, y, z in pts]


# ================================================================== BLENDER
try:
    import bmesh
    import bpy
except ImportError:          # fuera de Blender solo estan las funciones puras
    bpy = None

if bpy is not None:

    def solido(nombre, verts, col):
        me = bpy.data.meshes.new(nombre)
        bm = bmesh.new()
        for v in verts:
            bm.verts.new(v)
        bm.verts.ensure_lookup_table()
        bmesh.ops.convex_hull(bm, input=bm.verts)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        me.validate()
        ob = bpy.data.objects.new(nombre, me)
        col.objects.link(ob)
        ob["Thickness_mm"] = round(T * 1000, 2)
        ob["Armour_Material"] = MATERIAL
        return ob

    # ---- geometria y comprobaciones antes de tocar la escena
    lado_R = generar(PUNTOS)
    lado_L = generar([(-x, y, zs, zt) for x, y, zs, zt in PUNTOS])
    lados = [("R", lado_R), ("L", lado_L)]

    print()
    for suf, piezas in lados:
        for nom, v, t in piezas:
            nom = nom.format(s=suf)
            ext = [dot((t["n"][0], t["n"][1], 0.0), p) for p in v]
            esp = max(ext) - min(ext)
            if abs(esp - T) > 1e-9:
                raise SystemExit(
                    f"\nABORTADO: {nom} sale con {esp * 1000:.4f} mm, no "
                    f"{T * 1000:.1f}.\n")
        print(f"lado {suf}: {len(piezas)} piezas, espesor {T * 1000:.1f} mm "
              "verificado sobre la normal en todas")

    for suf, piezas in lados:
        for (na, va, _), (nb, vb, _) in zip(piezas, piezas[1:]):
            d = penetracion(va, vb)
            if d > TOL_SOLAPE:
                raise SystemExit(
                    f"\nABORTADO: {na.format(s=suf)} y {nb.format(s=suf)} se solapan "
                    f"{d * 1000:.3f} mm en la junta.\n")

    # ---- cuanto cambia respecto a lo que habia
    for viejo in VIEJOS:
        ob = bpy.data.objects.get(viejo)
        if ob is not None:
            print(f"  sustituye a {viejo}")

    # ---- nada del resto del modelo debe tocar los laterales nuevos
    propios = {PREFIJO + n.format(s=s) for s, ps in lados for n, _, _ in ps}
    mios = [(n.format(s=s), v) for s, ps in lados for n, v, _ in ps]
    choques = []
    for ob in bpy.data.objects:
        if (ob.type != 'MESH' or ob.name in VIEJOS or ob.name in propios
                or ob.name.startswith(PREFIJO)):
            continue
        M = ob.matrix_world
        P = [tuple(M @ v.co) for v in ob.data.vertices]
        if len(P) < 4:
            continue
        for nom, v in mios:
            lo = [min(p[i] for p in v) - 0.01 for i in range(3)]
            hi = [max(p[i] for p in v) + 0.01 for i in range(3)]
            if all(min(q[i] for q in P) <= hi[i] and max(q[i] for q in P) >= lo[i]
                   for i in range(3)):
                d = penetracion(v, P)
                if d > TOL_SOLAPE:
                    choques.append((nom, ob.name, d))
    if choques:
        for nom, otro, d in choques:
            print(f"  SOLAPE {nom} con {otro}: {d * 1000:.3f} mm")
        raise SystemExit("\nABORTADO: habria solapes con el resto del modelo.\n")

    # ---- generar
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    col = bpy.data.collections.get(COLECCION)
    if col is None:
        col = bpy.data.collections.new(COLECCION)
        bpy.context.scene.collection.children.link(col)

    for ob in list(bpy.data.objects):
        if ob.name in VIEJOS or ob.name in propios:
            bpy.data.objects.remove(ob, do_unlink=True)

    n = 0
    for suf, piezas in lados:
        for nom, v, _ in piezas:
            solido(PREFIJO + nom.format(s=suf), v, col)
            n += 1
    print(f"\n{n} piezas generadas ({len(TRAMOS)} por lado)")
    print("pasa tools/revisar_vertices.py y tools/validate_glb.py despues\n")
