"""Reconstruye ARM_Side_Front_L / _R como placas planas de 30 mm.

Pega esto en la pestana Scripting de Blender y dale a Run.
Borra las versiones anteriores si existen.

Las caras quedan: exterior enrasada con ARM_Upper_Front_Plate por delante y
con ARM_Side_Middle por detras; espesor 30,000 mm medido perpendicular.
"""
import bpy

NAME = "ARM_Side_Front"
THICKNESS_MM = 30.0
MATERIAL = "RHA"

# orden: frontal-bajo, frontal-alto, trasero-alto, trasero-bajo
OUTER = [(0.92700, -0.06735, 1.83045),
         (0.92700, -0.01166, 2.18207),
         (1.17200,  0.91017, 2.24602),
         (1.17200,  0.84556, 1.83805)]
INNER = [(0.92700,  0.04829, 1.83012),
         (0.92700,  0.10504, 2.18839),
         (1.14305,  0.91795, 2.24479),
         (1.14305,  0.85334, 1.83682)]

n = len(OUTER)
FACES = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
FACES += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]

for suffix, s in (("_L", 1), ("_R", -1)):
    name = NAME + suffix
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)

    verts = [(s * x, y, z) for x, y, z in OUTER] + \
            [(s * x, y, z) for x, y, z in INNER]
    faces = FACES if s > 0 else [t[::-1] for t in FACES]

    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob["Thickness_mm"] = THICKNESS_MM
    ob["Armour_Material"] = MATERIAL
    print(f"{name}: {len(verts)} vertices, {len(faces)} caras")
