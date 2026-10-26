"""Busca vertices sobrantes y agujeros de malla en todo el modelo.

NO MODIFICA NADA. Solo informa, y dice que operador de Blender arregla cada
cosa. Arreglar a mano dos objetos es mas rapido y mas seguro que dejar que un
script toque 169.

POR QUE SE BORRA UNA CARA AL ELIMINAR EL VERTICE
------------------------------------------------
Porque X -> Delete Vertices no borra solo el vertice: borra TODA cara que lo
use. Si tienes dos vertices encima del mismo punto y una de las caras se
construyo sobre el duplicado, al borrar el duplicado desaparece esa cara. El
vertice sobraba, la cara no.

Lo que hay que usar es M -> By Distance (Merge by Distance). Eso no borra: suelda
el duplicado contra el original, las caras que lo usaban pasan a usar el
original, y las caras que quedan con area cero se colapsan solas. Mismo
resultado visual, cero caras perdidas.

    duplicados sobre un punto .......  M -> By Distance   (umbral 0,0001 m)
    agujero en la malla .............  selecciona las aristas rojas y F
                                       o Mesh -> Clean Up -> Fill Holes
    vertices sin ninguna cara .......  Mesh -> Clean Up -> Delete Loose
    cara alabeada ...................  no hay operador: mueve el vertice hundido
                                       al plano, o regenera la pieza

QUE IMPORTA Y QUE NO
--------------------
Un vertice de sobra en medio de una arista recta no cambia la forma, asi que al
trazador le da igual: es suciedad, no un error. Los dos que SI rompen el
modelo son el agujero de malla y la cara alabeada:

  - Agujero: §3.1 toma la primera interseccion como entrada y la ultima como
    salida. Un rayo que entre por el agujero corta la malla una sola vez, no
    hay par entrada/salida, y la pieza no cuenta blindaje.
  - Cara alabeada: cuatro vertices que no son coplanares se trianguladan de
    dos maneras distintas segun el exportador, asi que el camino medido
    depende de quien lea el archivo.

Pestana Scripting -> New -> pegar -> Run. Mira la consola del sistema
(Window -> Toggle System Console) si la salida es larga.
"""
import bmesh
import bpy
import math
from collections import defaultdict

# ------------------------------------------------------------------ parametros
UMBRAL = 1e-4        # 0,1 mm: por debajo de esto son el mismo punto
PLANA = 1e-4         # 0,1 mm de desvio maximo de una cara respecto a su plano
FILTRO = ""          # "" = todo el modelo; p.ej. "ARM_Turret" para una zona
# --------------------------------------------------------------------------

filas = []

for ob in bpy.data.objects:
    if ob.type != 'MESH' or (FILTRO and FILTRO.lower() not in ob.name.lower()):
        continue

    bm = bmesh.new()
    bm.from_mesh(ob.data)

    # --- duplicados: dos vertices sobre el mismo punto
    cubos = defaultdict(list)
    for v in bm.verts:
        cubos[tuple(round(c / UMBRAL) for c in v.co)].append(v)
    dup = sum(len(g) - 1 for g in cubos.values() if len(g) > 1)

    # --- caras de area nula, consecuencia tipica de los duplicados
    degen = sum(1 for f in bm.faces if f.calc_area() < UMBRAL ** 2)

    # --- malla abierta: arista con menos (o mas) de dos caras
    abiertas = [e for e in bm.edges if len(e.link_faces) != 2]

    # --- vertices que no forman parte de ninguna cara
    sueltos = [v for v in bm.verts if not v.link_faces]

    # --- caras alabeadas
    alabeadas = []
    for f in bm.faces:
        if len(f.verts) > 3:
            c = f.calc_center_median()
            d = max(abs((v.co - c).dot(f.normal)) for v in f.verts)
            if d > PLANA:
                alabeadas.append((f.index, d))

    # --- vertices que no son esquina: sobre una arista o dentro de una cara
    noesq = 0
    for v in bm.verts:
        if v.link_faces:
            nn = {tuple(round(x, 4) for x in f.normal) for f in v.link_faces}
            if len(nn) <= 2:
                noesq += 1

    if dup or degen or abiertas or sueltos or alabeadas:
        filas.append((ob.name, len(bm.verts), len(bm.faces), dup, degen,
                      len(abiertas), len(sueltos), alabeadas, noesq))

    bm.free()

# --------------------------------------------------------------------- informe
print()
if not filas:
    print(f"{'todo limpio' if not FILTRO else 'limpio en ' + FILTRO}: "
          "ni duplicados, ni agujeros, ni caras alabeadas.\n")
    raise SystemExit

print(f"{len(filas)} objetos con algo que revisar\n")
print(f"{'objeto':34s} {'vrt':>4s} {'car':>4s} {'dup':>4s} {'ar0':>4s} "
      f"{'abrt':>5s} {'slt':>4s} {'alab':>5s}")
for (n, nv, nf, dup, degen, ab, sl, alab, _) in filas:
    print(f"{n:34s} {nv:4d} {nf:4d} {dup:4d} {degen:4d} {ab:5d} {sl:4d} "
          f"{len(alab):5d}")

print("\n  dup  = vertices duplicados sobre otro      -> M -> By Distance")
print("  ar0  = caras de area nula                  -> las borra el Merge")
print("  abrt = aristas sin dos caras: MALLA ABIERTA -> selecciona y F")
print("  slt  = vertices sin ninguna cara            -> Clean Up -> Delete Loose")
print("  alab = caras no planas                      -> mover vertice o regenerar")

for (n, _, _, dup, _, ab, _, alab, noesq) in filas:
    print(f"\n{n}")
    if dup:
        print(f"   {dup} duplicados. Entra en modo edicion, A para seleccionar")
        print(f"   todo, M -> By Distance con umbral {UMBRAL}. NO uses X -> Delete.")
    if ab:
        print(f"   {ab} aristas de borde: la malla NO esta cerrada. Esto si")
        print("   rompe el calculo, la pieza no cuenta blindaje por ese lado.")
    for i, d in alab[:4]:
        print(f"   cara {i} alabeada {d * 1000:.2f} mm fuera de su plano")
    print(f"   ({noesq} vertices que no son esquina, normalmente inofensivos)")
print()
