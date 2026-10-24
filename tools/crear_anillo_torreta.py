"""Abre el hueco redondo del anillo de torreta en ARM_Top_Plate.

EL PROBLEMA
-----------
ARM_Top_Plate es una plancha maciza de 11 mm que cubre toda la parte superior
del casco. Al no tener el hueco del anillo, cada disparo que baje por el techo
de torreta hacia el interior cuenta 11 mm de blindaje que no existe. El
validador no lo detecta porque la torreta se apoya encima y no hay solape.

POR QUE NO VALE UN BOOLEAN
--------------------------
Restar un cilindro con un modificador Boolean funciona y es rapido, pero deja
una plancha con un agujero, que NO ES CONVEXA. El trazador toma la primera
interseccion como entrada y la ultima como salida (modelo_balistico.md §3.1),
asi que en esa pieza mediria el camino cruzando el hueco. Tampoco vale un hueco
cuadrado: si la base de la torreta es redonda, las esquinas del cuadrado
sobresalen y dejan cuatro zonas con CERO blindaje, que es peor que el error
original.

LA SOLUCION
-----------
Hueco poligonal de N lados (indistinguible de un circulo para el trazador) y la
plancha partida en un abanico radial de N cuñas, cada una convexa por
construccion: cada cuña es la interseccion de un rectangulo, un cono y un
semiplano, y la interseccion de convexos es convexa.

                      . - .
                   .    |    .          cada cuña: un lado del poligono
                  /  \  |  /  \         por dentro, dos radios, y el borde
                 |----- + -----|        de la plancha por fuera
                  \  /  |  \  /
                   .    |    .
                      ` - '
              +-----------------------+
              |    pieza trasera      |   (el mamparo esta en Y 2,510)
              +-----------------------+

IMPORTANTE: LA BASE DE LA TORRETA TIENE QUE USAR LOS MISMOS N, RADIO Y CENTRO.
Si no coinciden quedan huecos sin blindaje o solapes. Apunta los tres valores
antes de modelar la torreta.

Pestana Scripting -> New -> pegar -> Run.
"""
import bmesh
import bpy
import math

# ------------------------------------------------------- el anillo (ajustable)
CENTRO_X = 0.00000       # el vehiculo es simetrico; dejalo en 0
CENTRO_Y = 1.67778       # centro del anillo. VERIFICAR CONTRA PLANO
RADIO = 0.80000          # 1,600 m de diametro, el anillo real del Pz IV
LADOS = 12               # 12 da 27 mm de desvio del circulo; 16 da 14 mm

# --------------------------------------- geometria medida de ARM_Top_Plate
X_EXT = 1.17200          # semiancho de la plancha
Z_BAJO = 2.24602         # cara inferior
Z_ALTO = 2.25702         # cara superior  (11,00 mm)
Y_DELANTE = 0.84556      # borde delantero (cara inferior; ver nota del inglete)
Y_CORTE = 2.51000        # separacion abanico / pieza trasera, en el mamparo
Y_TRAS_BAJO = 4.10706    # borde trasero, cara inferior
Y_TRAS_ALTO = 4.12543    # borde trasero, cara superior (inglete de 18 mm)

MATERIAL = "RHA"
COLECCION = "Armor"
BASE = "ARM_Top_Plate"
# --------------------------------------------------------------------------


def prisma(nombre, planta, z0, z1, col):
    """Extruye un poligono (x, y) de z0 a z1."""
    n = len(planta)
    verts = [(x, y, z0) for x, y in planta] + [(x, y, z1) for x, y in planta]
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
    ob["Thickness_mm"] = round((z1 - z0) * 1000, 2)
    ob["Armour_Material"] = MATERIAL
    return ob


def perfil_yz(nombre, perfil, x0, x1, col):
    """Extruye un perfil (y, z) de x0 a x1. Para la pieza trasera con inglete."""
    n = len(perfil)
    verts = [(x0, y, z) for y, z in perfil] + [(x1, y, z) for y, z in perfil]
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
    ob["Thickness_mm"] = round((Z_ALTO - Z_BAJO) * 1000, 2)
    ob["Armour_Material"] = MATERIAL
    return ob


def abanico():
    """Devuelve (vertices del poligono, lista de plantas de las cuñas)."""
    th = [2 * math.pi * k / LADOS for k in range(LADOS)]
    P = [(CENTRO_X + RADIO * math.cos(t), CENTRO_Y + RADIO * math.sin(t))
         for t in th]

    def al_borde(t):
        """Donde el radio corta el rectangulo de la zona del anillo."""
        dx, dy = math.cos(t), math.sin(t)
        s = math.inf
        for lim, d, c in ((X_EXT, dx, CENTRO_X), (-X_EXT, dx, CENTRO_X),
                          (Y_CORTE, dy, CENTRO_Y), (Y_DELANTE, dy, CENTRO_Y)):
            if abs(d) > 1e-12:
                ss = (lim - c) / d
                if ss > 1e-9:
                    s = min(s, ss)
        return (CENTRO_X + s * dx, CENTRO_Y + s * dy)

    Q = [al_borde(t) for t in th]
    esquinas = [(X_EXT, Y_CORTE), (-X_EXT, Y_CORTE),
                (-X_EXT, Y_DELANTE), (X_EXT, Y_DELANTE)]

    def ang(p):
        return math.atan2(p[1] - CENTRO_Y, p[0] - CENTRO_X) % (2 * math.pi)

    cuñas = []
    for i in range(LADOS):
        a, b = th[i], th[(i + 1) % LADOS]
        if b <= a:
            b += 2 * math.pi
        dentro = sorted(
            (e for e in esquinas
             if a < ang(e) < b or a < ang(e) + 2 * math.pi < b),
            key=lambda e: (ang(e) - a) % (2 * math.pi))
        cuñas.append([P[i], P[(i + 1) % LADOS], Q[(i + 1) % LADOS]]
                     + dentro + [Q[i]])
    return P, cuñas


def convexa(poly):
    n = len(poly)
    sg = []
    for i in range(n):
        a, b, c = poly[i], poly[(i + 1) % n], poly[(i + 2) % n]
        cr = ((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]))
        if abs(cr) > 1e-12:
            sg.append(cr > 0)
    return all(sg) or not any(sg)


def area(poly):
    s = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


# ------------------------------------------------------------------ comprobar
P, cuñas = abanico()
ys = [p[1] for p in P]
xs = [p[0] for p in P]
margen_del = (min(ys) - Y_DELANTE) * 1000
margen_tras = (Y_CORTE - max(ys)) * 1000
margen_lado = (X_EXT - max(xs)) * 1000
desvio = RADIO * (1 - math.cos(math.pi / LADOS)) * 1000

print()
print(f"hueco de {LADOS} lados, {RADIO * 2:.3f} m de diametro, "
      f"centro ({CENTRO_X:+.3f}, {CENTRO_Y:+.5f})")
print(f"  desvio respecto al circulo: {desvio:.1f} mm")
print(f"  margen delantero {margen_del:.1f} mm, trasero {margen_tras:.1f} mm, "
      f"lateral {margen_lado:.0f} mm")

if min(margen_del, margen_tras, margen_lado) < 20:
    raise SystemExit(
        f"\nABORTADO: solo {min(margen_del, margen_tras, margen_lado):.1f} mm "
        "de margen, saldrian cuñas degeneradas.\n"
        "Reduce RADIO o revisa CENTRO_Y contra el plano.")

malas = [i for i, c in enumerate(cuñas) if not convexa(c)]
if malas:
    raise SystemExit(f"\nABORTADO: cuñas no convexas: {malas}")

suma = sum(area(c) for c in cuñas)
rect = 2 * X_EXT * (Y_CORTE - Y_DELANTE)
print(f"  {len(cuñas)} cuñas, todas convexas, suma {suma:.4f} m2 "
      f"(rectangulo {rect:.4f} - hueco {area(P):.4f} = {rect - area(P):.4f})")
print(f"  cuña mas pequena: {min(area(c) for c in cuñas) * 1e4:.0f} cm2\n")

# ------------------------------------------------------------------- generar
if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

col = bpy.data.collections.get(COLECCION)
if col is None:
    col = bpy.data.collections.new(COLECCION)
    bpy.context.scene.collection.children.link(col)

for ob in list(bpy.data.objects):
    if ob.name == BASE or ob.name.startswith(BASE + "_"):
        bpy.data.objects.remove(ob, do_unlink=True)

for i, c in enumerate(cuñas):
    prisma(f"{BASE}_Ring_{i:02d}", c, Z_BAJO, Z_ALTO, col)

perfil_yz(f"{BASE}_Rear",
          [(Y_CORTE, Z_BAJO), (Y_TRAS_BAJO, Z_BAJO),
           (Y_TRAS_ALTO, Z_ALTO), (Y_CORTE, Z_ALTO)],
          -X_EXT, X_EXT, col)

print(f"{len(cuñas)} cuñas + 1 pieza trasera = {len(cuñas) + 1} objetos, "
      f"espesor {(Z_ALTO - Z_BAJO) * 1000:.2f} mm")
print(f"\nPARA LA TORRETA, usa estos mismos valores:")
print(f"  centro ({CENTRO_X:+.5f}, {CENTRO_Y:+.5f})   radio {RADIO:.5f}   "
      f"lados {LADOS}")
print("\nNota: el borde delantero se corta vertical en Y "
      f"{Y_DELANTE:.5f}, asi que queda")
print("0,49 mm de hueco con ARM_Front_Top_Plate en la cara superior. Por debajo")
print("de 1 mm, luego §3.2 lo agrupa como contacto y no es blindaje espaciado.")
print("\npasa tools/validate_glb.py despues\n")
