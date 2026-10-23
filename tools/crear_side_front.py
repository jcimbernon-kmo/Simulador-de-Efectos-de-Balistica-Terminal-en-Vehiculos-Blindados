"""Crea ARM_Side_Front_L y _R con caras planas y normales garantizadas.

El prisma se construye extruyendo una cara plana a lo largo de su propia normal,
asi que las seis caras son planas por construccion y el espesor es exacto.
No usa Solidify, que es lo que deformaba la pieza, y recalcula las normales con
bmesh para que no dependan del orden en que yo escriba los vertices.

Pestana Scripting -> New -> pegar -> Run.
"""
import bmesh
import bpy
import math

THICKNESS = 0.030
MATERIAL = "RHA"
COLECCION = "Armor"

# Cara EXTERIOR, en orden alrededor del contorno.
# El primero es punto de inglete del casco y no debe tocarse.
# El segundo esta recortado para apoyar en la cara INFERIOR del techo
# delantero; si se deja en el punto de inglete exterior (-0.01166, 2.18207)
# la mejilla se mete dentro de la plancha del techo.
CARA = [
    (0.92700, -0.06735, 1.83045),   # casco, abajo
    (0.92700, -0.01343, 2.17087),   # casco, arriba (bajo el techo)
    (1.17200,  0.84556, 2.24602),   # exterior, arriba
    (1.17200,  0.77974, 1.83045),   # exterior, abajo (borde angulado)
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
    """La cara tiene que ser plana y convexa, o el prisma no vale."""
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
    bm = bmesh.new()                          # <-- esto es lo que faltaba
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

d, convexa = comprobar(CARA)
print(f"\ncara base: desviacion del plano {d * 1000:.4f} mm, convexa={convexa}")
if d > 1e-5 or not convexa:
    raise SystemExit("la cara base no sirve; revisa CARA antes de generar")

for nombre in ("ARM_Side_Front_L", "ARM_Side_Front_R"):
    viejo = bpy.data.objects.get(nombre)
    if viejo:
        bpy.data.objects.remove(viejo, do_unlink=True)

construir("ARM_Side_Front_L", CARA, col)
construir("ARM_Side_Front_R", [(-p[0], p[1], p[2]) for p in CARA], col)
print("ARM_Side_Front_L y _R creados: 8 vertices, 6 caras planas, 30,00 mm\n")
