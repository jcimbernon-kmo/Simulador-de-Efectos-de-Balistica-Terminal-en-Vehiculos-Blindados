"""Crea ARM_Turret_Front_L y _R unidas a ras con ARM_Turret_Front.

EL PROBLEMA QUE RESUELVE
------------------------
ARM_Turret_Front se inclina 10,00 grados desde la vertical, asi que su arista
izquierda NO es vertical: al subir se va hacia atras y hacia dentro. Un costado
vertical no puede contener esa arista, asi que solo la toca a una altura y se
separa al bajar (a la altura del techo la separacion pasaba de 30 cm).

La opcion A consiste en inclinar el costado hasta que su plano contenga la
arista entera de la frontal. Entonces la union es a ras de arriba abajo.
El plano no se elige: lo fija la arista de la frontal mas la arista trasera
que pongas aqui.

COMO SE USA
-----------
Toca solo TRASERO_BAJO y TRASERO_ALTO. El script:

  1. define el plano con la arista de la frontal y el centro de la trasera,
  2. proyecta tus dos puntos traseros sobre ese plano y te dice cuanto se han
     movido (si se mueven mucho, la arista que has puesto no es compatible),
  3. comprueba que la cara es plana y convexa, y ABORTA si no,
  4. extruye 30 mm hacia dentro y crea _L y _R.

La arista delantera NO se toca: son las dos esquinas de ARM_Turret_Front y por
ahi tienen que casar.

OJO: la frontal tiene un vertice mal en el lado -X, 25,4 mm fuera de su propio
plano. Este script construye desde el lado +X, que es el correcto, y espeja.
Arregla el otro aparte:
    (-0.81500, 0.88934, 2.57861)  ->  (-0.81500, 0.86472, 2.58295)

Pestana Scripting -> New -> pegar -> Run.
"""
import bmesh
import bpy
import math

# --------------------------------------- arista delantera: NO TOCAR
# Son las esquinas izquierdas de la cara exterior de ARM_Turret_Front.
P_MEDIO = (0.81500, 0.86472, 2.58295)    # esquina media (el punto mas ancho)
P_ALTO = (0.71051, 0.90540, 2.81364)     # esquina superior

# --------------------------------------- arista trasera: AJUSTA ESTO
# Donde quieres que acabe el costado por detras. El script los proyecta al
# plano, asi que no hace falta que sean exactos, pero cuanto mas cerca del
# plano los pongas, menos se moveran.
TRASERO_BAJO = (1.06860, 1.65808, 2.31480)
TRASERO_ALTO = (1.05856, 1.63654, 2.84472)

THICKNESS = 0.030
MATERIAL = "RHA"
COLECCION = "Armor"
Z_TECHO = 2.25702        # cara superior del techo, solo para informar
TOL_PLANO_MM = 0.01
# --------------------------------------------------------------------------


def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def add(a, b): return tuple(x + y for x, y in zip(a, b))
def mul(a, s): return tuple(x * s for x in a)
def dot(a, b): return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def norm(a):
    L = math.sqrt(dot(a, a))
    if L < 1e-12:
        raise SystemExit("ABORTADO: puntos degenerados, revisa la arista trasera")
    return tuple(x / L for x in a)


def largo(a): return math.sqrt(dot(a, a))


# ----------------------------------------------- plano y proyeccion
medio_tras = mul(add(TRASERO_BAJO, TRASERO_ALTO), 0.5)
n = norm(cross(sub(P_ALTO, P_MEDIO), sub(medio_tras, P_MEDIO)))
if n[0] < 0:                                  # que mire hacia fuera (+X)
    n = mul(n, -1)

inclinacion = math.degrees(math.asin(abs(n[2])))
print()
print(f"normal exterior  {tuple(round(c, 5) for c in n)}")
print(f"inclinacion desde la vertical  {inclinacion:.2f} grados")

proy = lambda p: sub(p, mul(n, dot(sub(p, P_MEDIO), n)))
tb, ta = proy(TRASERO_BAJO), proy(TRASERO_ALTO)

print("\nvertices traseros proyectados al plano:")
for nom, o, q in (("bajo", TRASERO_BAJO, tb), ("alto", TRASERO_ALTO, ta)):
    print(f"  {nom:<5} {tuple(round(c, 5) for c in o)} -> "
          f"{tuple(round(c, 5) for c in q)}   "
          f"se mueve {largo(sub(q, o)) * 1000:.1f} mm")

CARA = [P_MEDIO, P_ALTO, ta, tb]

# ----------------------------------------------- comprobaciones
d = max(abs(dot(sub(p, CARA[0]), n)) for p in CARA) * 1000
if d > TOL_PLANO_MM:
    raise SystemExit(f"\nABORTADO: la cara se desvia {d:.4f} mm del plano")

u = norm(sub(CARA[1], CARA[0]))
v = cross(n, u)
pl = [(dot(sub(p, CARA[0]), u), dot(sub(p, CARA[0]), v)) for p in CARA]
sg = []
for i in range(4):
    a, b, c = pl[i], pl[(i + 1) % 4], pl[(i + 2) % 4]
    cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
    if abs(cr) > 1e-12:
        sg.append(cr > 0)
if not (all(sg) or not any(sg)):
    raise SystemExit("\nABORTADO: la cara no es convexa; mueve la arista trasera")

area = abs(sum(pl[i][0] * pl[(i + 1) % 4][1] - pl[(i + 1) % 4][0] * pl[i][1]
               for i in range(4))) / 2.0

zmin = min(p[2] for p in CARA)
xmax = max(p[0] for p in CARA)
print(f"\ncara plana ({d:.5f} mm) y convexa, area {area:.4f} m2")
print(f"  X maximo {xmax:+.5f}  ->  anchura de torreta {xmax * 2:.3f} m")
print(f"  Z minimo {zmin:.5f}   ->  {(zmin - Z_TECHO) * 1000:.0f} mm "
      f"por encima del techo")
if xmax > 0.90:
    print(f"  AVISO: {xmax * 2:.2f} m es mucho para una torreta de Panzer IV, "
          "cuya frontal mide 1,63 m")
if zmin - Z_TECHO > 0.005:
    print(f"  AVISO: queda hueco hasta el techo; hara falta otra pieza debajo")

# ----------------------------------------------- generar
def construir(nombre, cara, col):
    dentro = [sub(p, mul(n, THICKNESS)) for p in cara]
    verts = list(cara) + dentro
    faces = [(3, 2, 1, 0), (4, 5, 6, 7)]
    faces += [(i, (i + 1) % 4, 4 + (i + 1) % 4, 4 + i) for i in range(4)]

    me = bpy.data.meshes.new(nombre)
    me.from_pydata(verts, [], faces)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.validate()

    ob = bpy.data.objects.new(nombre, me)
    col.objects.link(ob)
    ob["Thickness_mm"] = THICKNESS * 1000
    ob["Armour_Material"] = MATERIAL
    return ob


if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

col = bpy.data.collections.get(COLECCION)
if col is None:
    col = bpy.data.collections.new(COLECCION)
    bpy.context.scene.collection.children.link(col)

for nombre in ("ARM_Turret_Front_L", "ARM_Turret_Front_R"):
    viejo = bpy.data.objects.get(nombre)
    if viejo:
        bpy.data.objects.remove(viejo, do_unlink=True)

construir("ARM_Turret_Front_L", CARA, col)
n = (-n[0], n[1], n[2])        # al espejar en X, la normal se espeja tambien
construir("ARM_Turret_Front_R", [(-p[0], p[1], p[2]) for p in CARA], col)

print(f"\nARM_Turret_Front_L y _R creados: 8 vertices, 6 caras planas, "
      f"{THICKNESS * 1000:.2f} mm")
print("pasa tools/validate_glb.py despues\n")
