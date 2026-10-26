"""Crea la cupula del comandante: anillo de 12 lados hueco, blindaje extra y tapa.

POR QUE NO ES UN CILINDRO HUECO
-------------------------------
Un tubo hueco NO ES CONVEXO. Un rayo que lo roce corta la pared, sale al aire
del interior, y vuelve a entrar en la pared de enfrente: cuatro intersecciones.
Como §3.1 toma la primera como entrada y la ultima como salida, mediria el
diametro entero como acero macizo, unos 860 mm en vez de los 50 de pared. Es el
mismo problema que tenia el hueco de ARM_Top_Plate.

La solucion es la misma que en crear_anillo_torreta.py: el anillo se parte en 12
cunas, una por cara del poligono. Cada cuna es un trapecio extruido, o sea la
interseccion de seis semiespacios (cara exterior, cara interior, dos cortes
radiales, suelo y techo), y la interseccion de convexos es convexa.

    vista en planta, una cuna

         V_k ._________. V_k+1        cara exterior, plana
             |         |
         W_k ._________. W_k+1        cara interior, plana y PARALELA
                                      -> espesor exacto por construccion

Las dos caras salen paralelas porque el poligono interior y el exterior tienen
los mismos 12 lados y la MISMA FASE. Si cambiaras el numero de lados de uno de
los dos, el espesor dejaria de ser constante.

DE DONDE SALEN LAS MEDIDAS
--------------------------
Nada esta copiado a mano: todo se deriva de HUECO_D, el hueco que
crear_torreta.py ya abrio en el techo. La cara interior de la cupula se hace
coincidir exactamente con la pared del hueco, asi que el poligono interior de
la cupula ES el poligono del hueco: ni escalon ni voladizo. Si algun dia
cambias el hueco, cambia HUECO_D aqui y vuelve a ejecutar.

LAS DOS PIEZAS DE BLINDAJE
--------------------------
El cuerpo son 50 mm y el blindaje extra otros 30, en contacto, hacia fuera.
Van como dos anillos separados, no como uno de 80, porque §3.2 distingue
planchas: asi puedes separarlas luego con SEPARACION y que cuenten como
blindaje espaciado sin rehacer la geometria. Si tu plano dice que es una sola
pared de 80 mm, pon EXTRA = 0 y PARED = 0.080.

LA TAPA
-------
No la has pedido, pero un anillo hueco deja abierto el hueco del techo, y
entonces el comandante sigue siendo carne con umbral de 80 J visto desde
arriba, que era justo lo que queriamos tapar. Va de 25 mm. Si la vas a modelar
aparte con la escotilla partida, pon TAPA_ESP = 0 y no se genera.

Pestana Scripting -> New -> pegar -> Run.
"""
import bmesh
import bpy
import math

# ------------------------------------------------------------------ parametros
HUECO_D = 0.700          # diametro del hueco del techo (circunscrito)
LADOS = 12               # tiene que ser el mismo que el del hueco
FASE = 0.0               # grados; el hueco tiene vertice a 0, 30, 60, 90...
CENTRO_X = 0.00000
CENTRO_Y = 2.19400       # centro del hueco
ZB = 2.93203             # cara superior del techo trasero: ahi se apoya
ALTURA = 0.200           # alto del anillo

PARED = 0.050            # cuerpo de la cupula
EXTRA = 0.030            # blindaje extra, por fuera
SEPARACION = 0.000       # >0 lo convierte en blindaje espaciado (§3.2)
TAPA_ESP = 0.025         # 0 = no generar tapa

MATERIAL = "RHA"
COLECCION = "Armor"
NOMBRE = "ARM_Cupola"
# --------------------------------------------------------------------------

COS = math.cos(math.pi / LADOS)
fase = math.radians(FASE)


def poligono(apotema):
    """Vertices del poligono de LADOS caras cuya apotema es la dada."""
    rc = apotema / COS
    return [(CENTRO_X + rc * math.cos(fase + 2 * math.pi * k / LADOS),
             CENTRO_Y + rc * math.sin(fase + 2 * math.pi * k / LADOS))
            for k in range(LADOS)]


def prisma(nombre, planta, z0, z1, esp, col):
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
    ob["Thickness_mm"] = round(esp * 1000, 2)
    ob["Armour_Material"] = MATERIAL
    return ob


def anillo(a_in, a_out):
    """Plantas de las LADOS cunas del anillo entre las dos apotemas."""
    V, W = poligono(a_out), poligono(a_in)
    return [[V[k], V[(k + 1) % LADOS], W[(k + 1) % LADOS], W[k]]
            for k in range(LADOS)]


def convexa(poly):
    sg = []
    for i in range(len(poly)):
        a, b, c = poly[i], poly[(i + 1) % len(poly)], poly[(i + 2) % len(poly)]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cr) > 1e-12:
            sg.append(cr > 0)
    return all(sg) or not any(sg)


def dentro(p, poly, margen=0.0):
    """True si (x, y) cae dentro del poligono convexo dado."""
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) < margen:
            return False
    return True


def apotema_de(p):
    """Distancia del punto al centro, medida sobre la direccion de cada cara."""
    return max((p[0] - CENTRO_X) * math.cos(fase + 2 * math.pi * k / LADOS)
               + (p[1] - CENTRO_Y) * math.sin(fase + 2 * math.pi * k / LADOS)
               for k in range(LADOS))


# -------------------------------------------------------------- geometria
A_HUECO = (HUECO_D / 2) * COS            # apotema del hueco del techo
A1_IN = A_HUECO                          # cara interior del cuerpo: a ras
A1_OUT = A1_IN + PARED
A2_IN = A1_OUT + SEPARACION
A2_OUT = A2_IN + EXTRA
Z0, Z1 = ZB, ZB + ALTURA

print()
print(f"hueco {HUECO_D * 1000:.0f} mm, {LADOS} lados, apotema {A_HUECO:.5f}")
print(f"  cuerpo   apotema {A1_IN:.5f} .. {A1_OUT:.5f}   "
      f"pared {PARED * 1000:.0f} mm")
print(f"  extra    apotema {A2_IN:.5f} .. {A2_OUT:.5f}   "
      f"pared {EXTRA * 1000:.0f} mm")
print(f"  exterior {A2_OUT / COS * 2000:.0f} mm de punta a punta, "
      f"{A2_OUT * 2000:.0f} mm entre caras")
print(f"  Z {Z0:.5f} .. {Z1:.5f}"
      + (f" + tapa hasta {Z1 + TAPA_ESP:.5f}" if TAPA_ESP else "  (sin tapa)"))

cuerpo = anillo(A1_IN, A1_OUT)
extra = anillo(A2_IN, A2_OUT) if EXTRA else []

malas = [i for i, c in enumerate(cuerpo + extra) if not convexa(c)]
if malas:
    raise SystemExit(f"\nABORTADO: cunas no convexas: {malas}\n")

# espesor real, medido entre las dos caras paralelas de cada cuna
for nom, cunas, esp in (("cuerpo", cuerpo, PARED), ("extra", extra, EXTRA)):
    if not cunas:
        continue
    peor = 0.0
    for (ax, ay), (bx, by), (cx_, cy_), _ in cunas:
        L = math.hypot(bx - ax, by - ay)
        nx, ny = (by - ay) / L, -(bx - ax) / L
        peor = max(peor, abs(abs((cx_ - ax) * nx + (cy_ - ay) * ny) - esp))
    if peor > 1e-6:
        raise SystemExit(
            f"\nABORTADO: el espesor del {nom} se desvia {peor * 1000:.3f} mm.\n"
            "LADOS y FASE tienen que ser los mismos en los dos poligonos.\n")
    print(f"  espesor {nom} verificado: {esp * 1000:.1f} mm en las "
          f"{LADOS} cunas")

# --- nada del modelo debe quedar dentro de la pared, y holgura interior
choques = []
holgura = None
for ob in bpy.data.objects:
    if ob.type != 'MESH' or ob.name.startswith(NOMBRE):
        continue
    M = ob.matrix_world
    for v in ob.data.vertices:
        p = M @ v.co
        # banda estricta: el techo toca la cupula justo en Z0 y el apoyo no
        # es un solape, asi que los vertices que caen en los planos de
        # contacto no cuentan
        if Z0 + 1e-5 < p.z < Z1 - 1e-5:
            if any(dentro((p.x, p.y), c, 1e-6) for c in cuerpo + extra):
                choques.append((ob.name, p.x, p.y, p.z))
            else:
                d = A1_IN - apotema_de((p.x, p.y))
                if d > 0 and (holgura is None or d < holgura[0]):
                    holgura = (d, ob.name)

if holgura:
    print(f"  holgura interior minima: {holgura[0] * 1000:.1f} mm "
          f"({holgura[1]})")

if choques:
    print(f"\n  {len(choques)} vertices de otros objetos caen dentro de la "
          "pared:")
    vistos = set()
    for n_, x, y, z in choques:
        if n_ not in vistos:
            vistos.add(n_)
            print(f"    {n_}  ({x:+.4f}, {y:+.4f}, {z:+.4f})")
    raise SystemExit("\nABORTADO: habria solape. Mueve esos objetos, reduce "
                     "ALTURA o revisa el centro.\n")

# ------------------------------------------------------------------- generar
if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

col = bpy.data.collections.get(COLECCION)
if col is None:
    col = bpy.data.collections.new(COLECCION)
    bpy.context.scene.collection.children.link(col)

for ob in list(bpy.data.objects):
    if ob.name == NOMBRE or ob.name.startswith(NOMBRE + "_"):
        bpy.data.objects.remove(ob, do_unlink=True)

n = 0
for i, c in enumerate(cuerpo):
    prisma(f"{NOMBRE}_Ring_{i:02d}", c, Z0, Z1, PARED, col)
    n += 1
for i, c in enumerate(extra):
    prisma(f"{NOMBRE}_Armour_{i:02d}", c, Z0, Z1, EXTRA, col)
    n += 1
if TAPA_ESP:
    prisma(f"{NOMBRE}_Hatch", poligono(A1_OUT), Z1, Z1 + TAPA_ESP,
           TAPA_ESP, col)
    n += 1

print(f"\n{n} objetos generados")
print("\npasa tools/revisar_vertices.py y tools/validate_glb.py despues\n")
