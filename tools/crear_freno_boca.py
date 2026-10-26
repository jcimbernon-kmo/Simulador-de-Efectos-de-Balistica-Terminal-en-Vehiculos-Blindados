"""Anade el freno de boca de dos camaras al final de MOD_Barrel.

Mide MOD_Barrel en la escena (radio, centro, numero de lados y fase angular) y
coloca el freno pegado a la boca con la misma fase, para que la silueta no
quede girada respecto al tubo. Si mueves o rehaces el tubo, vuelve a ejecutar
esto y el freno se recoloca solo: no hay coordenadas copiadas a mano.

POR QUE TRES PIEZAS Y NO UNA
----------------------------
El freno es un escalon HACIA FUERA respecto al tubo. La envolvente convexa de
tubo + freno incluye un cono de transicion que no existe, asi que el freno no
puede ir en la malla de MOD_Barrel sin romper el §3.1 (entrada = primera
interseccion, salida = ultima). Y la cintura entre las dos camaras es un
escalon HACIA DENTRO, asi que las dos camaras tampoco pueden ser una sola
pieza. Tres prismas, cada uno convexo por construccion.

POR QUE NO LLEVA Module_Type NI Health
--------------------------------------
Perder el freno de boca no impide disparar: sube el retroceso y ensucia la
punteria, pero el canon sigue funcionando. Si llevara Module_Type "Gun", la
regla OR de §3.7.3 lo contaria como averia del canon, que es falso. Lleva por
tanto el juego de propiedades de las piezas que son solo acero, el mismo que
los 69 objetos ARM_ del modelo: Armour_Material y Thickness_mm. El prefijo
ARM_ va por coherencia con ese juego de propiedades, no porque sea blindaje;
segun §2.4 el codigo distingue por propiedades, no por el nombre.

ponytail: camaras macizas. En realidad son de pared delgada, y un proyectil que
cruce el freno fuera del eje atraviesa unos 70 mm de acero, no 180. Esto
sobreestima el blindaje en una franja de 180 mm justo delante de la abertura
del canon, que es exactamente donde apunta el tirador. Si decides que pesa,
parte cada camara en un anillo de cunas convexas como en
crear_anillo_torreta.py y anotalo; mientras no lo hagas, va al §9.

Pestana Scripting -> New -> pegar -> Run.
"""
import bmesh
import bpy
import math

# ------------------------------------------------------------------ parametros
TUBO = "MOD_Barrel"
NOMBRE = "ARM_Muzzle_Brake"
COLECCION = "Armor"
MATERIAL = "Steel"
PARED_MM = 35.0          # informativo (§3.1 mide el camino en la malla)

# (sufijo, largo m, radio m) desde la boca del tubo hacia delante
PERFIL = [("Rear",  0.135, 0.0900),
          ("Neck",  0.040, 0.0625),
          ("Front", 0.125, 0.0900)]
# --------------------------------------------------------------------------


def prisma(nombre, y0, y1, r, lados, fase, cx, cz, col):
    """Prisma de N lados con el eje en Y. Convexo por construccion."""
    pts = [(cx + r * math.cos(fase + 2 * math.pi * k / lados),
            cz + r * math.sin(fase + 2 * math.pi * k / lados))
           for k in range(lados)]
    n = lados
    verts = [(x, y0, z) for x, z in pts] + [(x, y1, z) for x, z in pts]
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
    ob["Armour_Material"] = MATERIAL
    ob["Thickness_mm"] = PARED_MM
    return ob


# ------------------------------------------------------- medir el tubo
ob = bpy.data.objects.get(TUBO)
if ob is None or ob.type != 'MESH':
    raise SystemExit(f"\nNo encuentro la malla {TUBO!r}. Revisa el nombre.\n")

M = ob.matrix_world
P = [M @ v.co for v in ob.data.vertices]
y_boca = min(p.y for p in P)
cx = (min(p.x for p in P) + max(p.x for p in P)) / 2
cz = (min(p.z for p in P) + max(p.z for p in P)) / 2
r_tubo = max(math.hypot(p.x - cx, p.z - cz) for p in P)

boca = [p for p in P if abs(p.y - y_boca) < 1e-6]
lados = len(boca)
angs = sorted(math.atan2(p.z - cz, p.x - cx) % (2 * math.pi) for p in boca)
fase = angs[0]

print()
print(f"{TUBO}: boca en Y {y_boca:+.5f}, eje ({cx:+.5f}, {cz:+.5f}), "
      f"radio {r_tubo * 1000:.1f} mm, {lados} lados, fase {math.degrees(fase):.1f}º")

if lados < 3:
    raise SystemExit(
        f"\nABORTADO: solo {lados} vertices en la boca. El tubo no es un "
        "prisma cerrado, o su eje no es Y.\n")

paso = 2 * math.pi / lados
if max(abs((angs[k] - angs[0]) - k * paso) for k in range(lados)) > 1e-4:
    raise SystemExit(
        "\nABORTADO: los vertices de la boca no estan repartidos a intervalos "
        "iguales.\nNo es un prisma regular y el freno no encajaria.\n")

finos = [(s, r) for s, _, r in PERFIL if r <= r_tubo]
if finos:
    raise SystemExit(
        f"\nABORTADO: estas piezas son mas estrechas que el tubo "
        f"({r_tubo * 1000:.1f} mm) y quedarian dentro de el: {finos}\n")

# ------------------------------------------------------------------- generar
if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

col = bpy.data.collections.get(COLECCION)
if col is None:
    col = bpy.data.collections.new(COLECCION)
    bpy.context.scene.collection.children.link(col)

for o in list(bpy.data.objects):
    if o.name == NOMBRE or o.name.startswith(NOMBRE + "_"):
        bpy.data.objects.remove(o, do_unlink=True)

y = y_boca
for sufijo, largo, r in PERFIL:
    prisma(f"{NOMBRE}_{sufijo}", y, y - largo, r, lados, fase, cx, cz, col)
    print(f"  {NOMBRE}_{sufijo:5s}  Y {y:+.5f} .. {y - largo:+.5f}   "
          f"diametro {r * 2000:.0f} mm")
    y -= largo

print(f"\n{len(PERFIL)} piezas, largo total {y_boca - y:.3f} m, "
      f"punta en Y {y:+.5f}")
print(f"  vuelo del canon desde el mantelete: {abs(y):.3f} m")
print("\npasa tools/validate_glb.py despues\n")
