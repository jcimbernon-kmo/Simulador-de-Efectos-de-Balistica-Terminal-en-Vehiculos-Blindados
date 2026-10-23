"""Crea modulos internos en forma de caja, a partir de una tabla.

Pensado para anaqueles de municion y depositos: piezas convexas por definicion,
donde lo que importa es la posicion y el tamano, no la forma.

Rellena MODULOS y ejecuta. Si un objeto con ese nombre ya existe, lo sustituye.
Pestana Scripting -> New -> pegar -> Run.
"""
import bmesh
import bpy

COLECCION = "Modules"

# nombre, Module_Type, Health (J), Armour_Material, centro (x,y,z), tamano (x,y,z)
MODULOS = [
    ("MOD_Ammo_Sponson_L", "Ammo", 150.0, "Ammo", (0.70, 1.60, 1.45), (0.30, 0.90, 0.40)),
    ("MOD_Ammo_Sponson_R", "Ammo", 150.0, "Ammo", (-0.70, 1.60, 1.45), (0.30, 0.90, 0.40)),
    # anade aqui el resto de anaqueles
]


def caja(nombre, tipo, vida, material, centro, tamano, col):
    viejo = bpy.data.objects.get(nombre)
    if viejo:
        bpy.data.objects.remove(viejo, do_unlink=True)
    hx, hy, hz = (t / 2.0 for t in tamano)
    cx, cy, cz = centro
    verts = [(cx + sx * hx, cy + sy * hy, cz + sz * hz)
             for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]
    # indices: 0..3 abajo (z-), 4..7 arriba (z+), dentro de cada nivel por y luego x
    faces = [(0, 1, 3, 2), (4, 6, 7, 5),          # abajo, arriba
             (0, 2, 6, 4), (1, 5, 7, 3),          # y-, y+
             (0, 4, 5, 1), (2, 3, 7, 6)]          # x-, x+
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
    ob["Module_Type"] = tipo
    ob["Health"] = vida
    ob["Armour_Material"] = material
    return ob


if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

col = bpy.data.collections.get(COLECCION)
if col is None:
    col = bpy.data.collections.new(COLECCION)
    bpy.context.scene.collection.children.link(col)

print()
total = 0.0
for nombre, tipo, vida, material, centro, tamano in MODULOS:
    ob = caja(nombre, tipo, vida, material, centro, tamano, col)
    v = tamano[0] * tamano[1] * tamano[2] * 1e6
    total += v
    b = [ob.matrix_world @ q.co for q in ob.data.vertices]
    print(f"{nombre:<24} {tamano[0]:.2f} x {tamano[1]:.2f} x {tamano[2]:.2f} m  "
          f"{v:7.0f} cm3   X {min(p.x for p in b):+.3f}..{max(p.x for p in b):+.3f}  "
          f"Y {min(p.y for p in b):+.3f}..{max(p.y for p in b):+.3f}  "
          f"Z {min(p.z for p in b):+.3f}..{max(p.z for p in b):+.3f}")
print(f"\n{len(MODULOS)} modulos, {total:.0f} cm3 en total")
print("pasa tools/validate_glb.py despues, sobre todo por los solapes\n")
