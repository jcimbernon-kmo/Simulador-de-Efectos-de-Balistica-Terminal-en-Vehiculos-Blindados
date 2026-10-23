"""Mueve vertices concretos a coordenadas exactas, sin iman ni raton.

Busca el vertice mas cercano a la coordenada 'actual' dentro de un radio y lo
coloca en la 'correcta'. Trabaja en coordenadas de mundo, asi que da igual la
transformacion que tenga el objeto.

Pestana Scripting -> New -> pegar -> Run.
"""
import bpy
from mathutils import Vector

RADIO = 0.003      # 3 mm de busqueda alrededor de la coordenada 'actual'

# objeto, coordenada actual (aproximada), coordenada correcta
CORRECCIONES = [
    # el vertice que se engancho al iman, en las dos piezas centrales
    ("ARM_Side_Middle_L", (1.14321, 0.78807, 1.82913), (1.14200, 0.77974, 1.83045)),
    ("ARM_Side_Middle_R", (-1.14321, 0.78807, 1.82913), (-1.14200, 0.77974, 1.83045)),

    # la placa inferior derecha, puesta como espejo exacto de la izquierda
    ("ARM_Lower_Side_R_Plate", (-0.92700, 0.01502, 1.83805), (-0.92700, 0.01502, 1.83914)),
    ("ARM_Lower_Side_R_Plate", (-0.89700, 0.01502, 1.83805), (-0.89700, 0.01502, 1.83914)),
    ("ARM_Lower_Side_R_Plate", (-0.89700, 2.50656, 1.83805), (-0.89700, 2.50656, 1.83914)),
    ("ARM_Lower_Side_R_Plate", (-1.14200, 2.50656, 1.83915), (-1.14200, 2.50656, 1.83805)),
    ("ARM_Lower_Side_R_Plate", (-0.89700, 0.01502, 1.84604), (-0.89700, 0.01502, 1.84714)),
    ("ARM_Lower_Side_R_Plate", (-0.89700, 2.50656, 1.84604), (-0.89700, 2.50656, 1.84714)),
    ("ARM_Lower_Side_R_Plate", (-0.92700, 0.01502, 1.84605), (-0.92700, 0.01502, 1.84714)),
    ("ARM_Lower_Side_R_Plate", (-1.14321, 0.78807, 1.84714), (-1.14321, 0.78807, 1.84604)),
    ("ARM_Lower_Side_R_Plate", (-1.14200, 2.50656, 1.84714), (-1.14200, 2.50656, 1.84604)),
]

if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

hechos = fallos = 0
for nombre, actual, correcta in CORRECCIONES:
    ob = bpy.data.objects.get(nombre)
    if ob is None or ob.type != 'MESH':
        print(f"  NO ENCONTRADO  {nombre}")
        fallos += 1
        continue
    M = ob.matrix_world
    Minv = M.inverted()
    objetivo = Vector(actual)
    mejor, mejor_d = None, RADIO
    for v in ob.data.vertices:
        d = (M @ v.co - objetivo).length
        if d < mejor_d:
            mejor, mejor_d = v, d
    if mejor is None:
        print(f"  SIN VERTICE a menos de {RADIO*1000:.0f} mm  {nombre} {actual}")
        fallos += 1
        continue
    mejor.co = Minv @ Vector(correcta)
    print(f"  ok  {nombre:<24} movido {mejor_d*1000:5.2f} mm -> "
          f"({correcta[0]:+.5f}, {correcta[1]:+.5f}, {correcta[2]:+.5f})")
    hechos += 1

for nombre in {c[0] for c in CORRECCIONES}:
    ob = bpy.data.objects.get(nombre)
    if ob:
        ob.data.update()

print(f"\n{hechos} vertices corregidos, {fallos} fallos")
print("guarda con Ctrl+S y exporta el .glb\n")
