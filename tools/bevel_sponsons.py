"""Corta a bisel el borde delantero de ARM_Side_Middle_L / _R.

Pega esto en la pestana Scripting de Blender y dale a Run.
Solo mueve cuatro vertices por objeto; no borra ni recrea nada.

Hace falta despues de ejecutar rebuild_cheeks.py: la mejilla queda inclinada
siguiendo la placa del conductor, asi que su union con el sponson es oblicua.
Sin esto, la mejilla se solapa con el sponson hasta 64,6 mm por arriba.
"""
import bpy
from mathutils import Vector

Y_FRONT = 0.84556          # Y actual de todo el borde delantero
TOL = 2e-3

# (X, Z) -> nueva Y, en coordenadas de mundo del lado izquierdo
RULES = [(( 1.17200, 1.83804), 0.84556),
         (( 1.17200, 2.24602), 0.91017),
         (( 1.14200, 1.83804), 0.85382),
         (( 1.14200, 2.24602), 0.91844)]

for name, sx in (("ARM_Side_Middle_L", 1.0), ("ARM_Side_Middle_R", -1.0)):
    ob = bpy.data.objects.get(name)
    if ob is None:
        print(f"{name}: no existe, lo salto")
        continue
    M = ob.matrix_world
    Minv = M.inverted()
    moved, unmatched = 0, []
    for v in ob.data.vertices:
        w = M @ v.co
        if abs(w.y - Y_FRONT) > TOL:
            continue                                  # no es el borde delantero
        for (x, z), new_y in RULES:
            if abs(w.x - sx * x) < TOL and abs(w.z - z) < TOL:
                v.co = Minv @ Vector((w.x, new_y, w.z))
                moved += 1
                break
        else:
            unmatched.append(tuple(round(c, 5) for c in w))
    ob.data.update()
    print(f"{name}: {moved} vertices movidos")
    for u in unmatched:
        print(f"   sin regla: {u}  <- revisa a mano")
