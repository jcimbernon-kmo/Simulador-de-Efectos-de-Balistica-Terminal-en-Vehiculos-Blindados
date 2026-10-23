"""Crea ARM_Back_Upper_Side_Addon_L y _R con caras planas garantizadas.

Extruye una cara plana a lo largo de su propia normal y recalcula las normales
con bmesh. Las seis caras salen planas por construccion y el espesor es exacto.

Pestana Scripting -> New -> pegar -> Run.
"""
import bmesh
import bpy
import math

THICKNESS = 0.030
MATERIAL = "RHA"
COLECCION = "Armor"

# Cara EXTERIOR, en orden alrededor del contorno.
# Opcion B: el borde inferior queda a X = 0,927 constante, a ras del costado.
CARA = [
    (1.17200, 2.50656, 2.24602),   # arriba, delante
    (0.92700, 2.50656, 1.83914),   # abajo, delante
    (0.92700, 4.18034, 1.83915),   # abajo, detras
    (1.17200, 4.10706, 2.24602),   # arriba, detras
]


def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def cross(a, b): return (a[1] * b[2] - a[2] * b[1],
                         a[2] * b[0] - a[0] * b[2],
                         a[0] * b[1] - a[1] * b[0])
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def normal(q):
    n = cross(sub(q[1], q[0]), sub(q[2], q[0]))
    L = math.sqrt(dot(n, n))
    return (n[0] / L, n[1] / L, n[2] / L)


def comprobar(q):
    n = normal(q)
    d = max(abs(dot(sub(p, q[0]), n)) for p in q)
    sg = [dot(cross(sub(q[(i + 1) % 4], q[i]),
                    sub(q[(i + 2) % 4], q[(i + 1) % 4])), n) > 0 for i in range(4)]
    return d, (all(sg) or not any(sg))


def construir(nombre, cara, col):
    n = normal(cara)
    if n[0] * cara[0][0] < 0:                 # que mire hacia fuera del vehiculo
        n = (-n[0], -n[1], -n[2])
    dentro = [(p[0] - n[0] * THICKNESS,
               p[1] - n[1] * THICKNESS,
               p[2] - n[2] * THICKNESS) for p in cara]
    verts = list(cara) + dentro
    faces = [(3, 2, 1, 0), (4, 5, 6, 7)]
    faces += [(i, (i + 1) % 4, 4 + (i + 1) % 4, 4 + i) for i in range(4)]
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(verts, [], faces)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)   # orienta hacia fuera
    bm.to_mesh(me)
    bm.free()
    me.validate()
    ob = bpy.data.objects.new(nombre, me)
    col.objects.link(ob)
    ob["Thickness_mm"] = THICKNESS * 1000
    ob["Armour_Material"] = MATERIAL
    return ob


col = bpy.data.collections.get(COLECCION)
if col is None:
    col = bpy.data.collections.new(COLECCION)
    bpy.context.scene.collection.children.link(col)

d, convexa = comprobar(CARA)
print(f"\ncara base: desviacion del plano {d * 1000:.4f} mm, convexa={convexa}")
if d > 1e-5 or not convexa:
    raise SystemExit("la cara base no sirve; revisa CARA antes de generar")

for nombre in ("ARM_Back_Upper_Side_Addon_L", "ARM_Back_Upper_Side_Addon_R"):
    viejo = bpy.data.objects.get(nombre)
    if viejo:
        bpy.data.objects.remove(viejo, do_unlink=True)

construir("ARM_Back_Upper_Side_Addon_L", CARA, col)
construir("ARM_Back_Upper_Side_Addon_R", [(-p[0], p[1], p[2]) for p in CARA], col)
print("ARM_Back_Upper_Side_Addon_L y _R creados: 8 vertices, 6 caras planas, 30,00 mm\n")
