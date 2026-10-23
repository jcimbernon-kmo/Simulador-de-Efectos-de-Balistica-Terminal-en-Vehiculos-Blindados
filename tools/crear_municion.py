"""Genera los cartuchos de municion como cilindros convexos, por anaqueles.

Cada cartucho es un objeto propio: convexo, con sus propiedades, y con el aire
entre cartuchos realmente vacio. Una caja maciza sobre un anaquel supondria
mas del doble de municion de la que hay.

Pestana Scripting -> New -> pegar -> Run.
"""
import bmesh
import bpy
import math

# ------------------------------------------------------------- parametros
DIAMETRO = 0.1115        # cartucho completo, en metros
LONGITUD = 0.870         # largo del cartucho; ajustalo al tuyo
PASO = 0.1515            # diametro + separacion entre cartuchos
LADOS = 8                # 8 basta: el trazador no ve la curvatura
HEALTH = 150.0           # umbral de detonacion, en julios
MATERIAL = "Ammo"
COLECCION = "Modules"

# nombre, centro del primer cartucho, eje del cartucho,
# direccion de fila, direccion de columna, nº filas, nº columnas
ANAQUELES = [
    ("Sponson_L", (0.70, 1.25, 1.30), (0, 1, 0), (1, 0, 0), (0, 0, 1), 2, 5),
    ("Sponson_R", (-0.70, 1.25, 1.30), (0, 1, 0), (1, 0, 0), (0, 0, 1), 2, 5),
    # anade aqui el resto hasta llegar a tus 87
]
# --------------------------------------------------------------------------


def unit(v):
    L = math.sqrt(sum(c * c for c in v))
    return tuple(c / L for c in v)


def perpendiculares(eje):
    """Dos vectores unitarios perpendiculares al eje y entre si."""
    a = (0.0, 0.0, 1.0) if abs(eje[2]) < 0.9 else (1.0, 0.0, 0.0)
    u = unit((eje[1] * a[2] - eje[2] * a[1],
              eje[2] * a[0] - eje[0] * a[2],
              eje[0] * a[1] - eje[1] * a[0]))
    w = (eje[1] * u[2] - eje[2] * u[1],
         eje[2] * u[0] - eje[0] * u[2],
         eje[0] * u[1] - eje[1] * u[0])
    return u, w


def cartucho(nombre, centro, eje, col):
    eje = unit(eje)
    u, w = perpendiculares(eje)
    r, h = DIAMETRO / 2.0, LONGITUD / 2.0
    verts = []
    for s in (-1, 1):
        base = tuple(centro[i] + eje[i] * h * s for i in range(3))
        for k in range(LADOS):
            a = 2 * math.pi * k / LADOS
            verts.append(tuple(base[i] + r * (math.cos(a) * u[i] + math.sin(a) * w[i])
                               for i in range(3)))
    n = LADOS
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
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
    ob["Module_Type"] = "Ammo"
    ob["Health"] = HEALTH
    ob["Armour_Material"] = MATERIAL
    return ob


if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

col = bpy.data.collections.get(COLECCION)
if col is None:
    col = bpy.data.collections.new(COLECCION)
    bpy.context.scene.collection.children.link(col)

for ob in list(bpy.data.objects):
    if ob.name.startswith("MOD_Ammo_"):
        bpy.data.objects.remove(ob, do_unlink=True)

print()
total = 0
for nombre, p0, eje, dfila, dcol, nf, nc in ANAQUELES:
    dfila, dcol = unit(dfila), unit(dcol)
    for i in range(nf):
        for j in range(nc):
            c = tuple(p0[k] + dfila[k] * PASO * i + dcol[k] * PASO * j for k in range(3))
            cartucho(f"MOD_Ammo_{nombre}_{i}{j}", c, eje, col)
            total += 1
    print(f"  {nombre:<14} {nf} x {nc} = {nf * nc:2d} cartuchos")
vol = total * math.pi / 4 * DIAMETRO ** 2 * LONGITUD * 1e6
print(f"\n{total} cartuchos, {vol:.0f} cm3 de municion real")
print(f"{total * (LADOS * 2 + (LADOS - 2) * 2)} triangulos aproximadamente")
print("pasa tools/validate_glb.py despues\n")
