"""Genera la torreta completa del Pz IV H: 9 placas de blindaje mas el techo.

POR QUE ASI
-----------
Construir cada placa uniendo vertices a ojo no funciona: cuatro puntos en el
espacio no son coplanarios salvo que se les obligue, asi que las caras grandes
salen alabeadas. Blender las parte entonces en dos triangulos con normales
distintas, y de ahi venian los tres sintomas que daba el validador a la vez:
"sin caras paralelas", espesores absurdos (101 mm en una placa de 30) y avisos
de no convexo.

Aqui cada placa se define como INTERSECCION DE SEMIESPACIOS:

    plano exterior  +  plano interior (desplazado su espesor)
    suelo Z >= ZB   +  techo Z <= ZT
    los planos de sus dos placas vecinas

La interseccion de semiespacios es convexa por definicion, todas sus caras son
planas por definicion, y el espesor perpendicular es exacto por definicion
(es la separacion entre los dos planos paralelos). Ademas dos placas vecinas
comparten cara exacta, porque el limite de una ES el plano de la otra: no hay
huecos que cerrar ni vertices que casar con el iman.

Los vertices salen resolviendo cada terna de planos y quedandose con los puntos
que cumplen todas las desigualdades. bmesh.ops.convex_hull los cierra.

GEOMETRIA
---------
Del plano: base 1,95 m, techo 1,40 m, altura del Turmgehause 650 mm.
De ahi sale la inclinacion de mejilla y costado, 22,615°, que es la que hace
que el techo mida 1400 mm clavados. La frontal va a 10° y la trasera a 15°,
medidas sobre el modelo anterior.

Pestana Scripting -> New -> pegar -> Run.
"""
import bmesh
import bpy
import itertools
import math

# ------------------------------------------------------------- parametros
ZB = 2.25703          # cara superior del techo del casco: la torreta apoya aqui
ALTURA = 0.650        # altura del Turmgehause, del plano
ANCHO_BASE = 1.950    # del plano
ANCHO_TECHO = 1.400   # del plano (lo consigue la inclinacion de Top y Mid)

INCL = {"Front": 10.000, "Top": 22.615, "Mid": 22.615, "Back": 15.000}
ESP = {"Front": 0.050, "Corner": 0.030, "Top": 0.030, "Mid": 0.030, "Back": 0.030}
ESP_TECHO = 0.016

H_APICE = 0.293       # altura del vertice donde se juntan frontal y mejilla

# --- techo en dos piezas ---------------------------------------------------
# La franja delantera va angulada; la trasera, plana, y lleva el hueco de la
# cupula. El quiebro cae en el vertice que une Top con Mid.
TECHO_INCL = 6.0        # grados sobre la horizontal (84° del vertical)
CUPULA_D = 0.700        # diametro del hueco de la cupula
CUPULA_Y = None         # None = centrado en la placa trasera; o pon la Y
CUPULA_LADOS = 12       # el abanico tendra este numero de cunas

# El plano anota "16/84" la franja de proa y "25/90" la llana, confirmado.
ESP_TECHO_POPA = 0.025

# --- hueco del canon en la placa frontal -----------------------------------
# Una placa con un agujero no es convexa, asi que la frontal sale en 4 piezas:
# faja de arriba, faja de abajo y las dos jambas. Todas convexas, porque el
# hueco es cuadrado y se corta con planos.
CANON_LADO = 0.250      # lado del hueco
# Centro del hueco sobre la base de la placa. 0,28254 lo deja en el centro
# geometrico de ARM_Turret_Front, que va de Z 2,25703 a 2,82211.
CANON_Z = 0.28254

# --- mantelete (Topfblende) ------------------------------------------------
# Lamina curva de eje VERTICAL, montada por delante del hueco. Corrida hacia
# la derecha (X negativa) porque la ametralladora coaxial va a ese lado.
MANTELETE_ANCHO = 0.720
MANTELETE_ESP = 0.050
MANTELETE_X = -0.100       # +X es babor, asi que -0,10 lo corre a estribor

# Tres facetas con angulo PROPIO, no un arco de circunferencia: un arco da
# facetas simetricas (con 3 caras saldria -59°/0°/+59°) y aqui hacen falta 14
# abajo y 30 arriba. Angulos desde la vertical; la del medio es plana.
# La faceta media mide justo lo que la abertura, para que el hueco la parta en
# dos jambas limpias en vez de dejar un agujero en medio de una placa.
MANTELETE_SUP_ANG = 30.0
MANTELETE_INF_ANG = 14.0
MANTELETE_INF_ALTO = 0.090   # cuanto baja la faceta inferior
# El borde de arriba queda a ras de la cara exterior de la frontal, asi que el
# VUELO no se elige: lo fija el angulo superior y lo que cabe hasta el techo.

MATERIAL = "RHA"
COLECCION = "Armor"
PREFIJO = "ARM_Turret_"

# Contorno inferior de la cara EXTERIOR, mitad izquierda, de proa a popa.
# Viene del modelo que hiciste, estrechado en X para que la base mida 1,95 m.
_KX = ANCHO_BASE / 2.072
BASE = [
    (0.00000,       0.80878),   # P0  proa, en el eje
    (0.60293 * _KX, 0.80878),   # P1  fin de la placa frontal
    (0.97444 * _KX, 1.27022),   # P2  union Corner / Top
    (1.03597 * _KX, 1.78980),   # P3  union Top / Mid
    (0.81539 * _KX, 2.52411),   # P4  union Mid / Back
    (0.00000,       2.80638),   # P5  popa, en el eje
]
NOMBRES = ["Front", "Corner", "Top", "Mid", "Back"]
ZT = ZB + ALTURA
# --------------------------------------------------------------------------

CX = sum(p[0] for p in BASE) / len(BASE)
CY = sum(p[1] for p in BASE) / len(BASE)


def _fuera(n, p):
    """Orienta una normal horizontal hacia el exterior del contorno."""
    return n if n[0] * (p[0] - CX) + n[1] * (p[1] - CY) >= 0 else (-n[0], -n[1])


def plano_pared(a, b, grados):
    """Plano que contiene la arista inferior a->b, inclinado 'grados' hacia dentro."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    n2 = _fuera((dy / L, -dx / L), ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
    t = math.radians(grados)
    n = (n2[0] * math.cos(t), n2[1] * math.cos(t), math.sin(t))
    return n, n[0] * a[0] + n[1] * a[1] + n[2] * ZB


def plano_por_3(a, b, c):
    u = tuple(b[i] - a[i] for i in range(3))
    v = tuple(c[i] - a[i] for i in range(3))
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
         u[0] * v[1] - u[1] * v[0])
    L = math.sqrt(sum(k * k for k in n))
    n = tuple(k / L for k in n)
    if n[0] * (a[0] - CX) + n[1] * (a[1] - CY) < 0:
        n = tuple(-k for k in n)
    return n, sum(n[i] * a[i] for i in range(3))


def corte3(pa, pb, z):
    """Punto donde dos planos cortan al plano horizontal z."""
    (a1, b1, c1), d1 = pa
    (a2, b2, c2), d2 = pb
    det = a1 * b2 - a2 * b1
    if abs(det) < 1e-12:
        return None
    e1, e2 = d1 - c1 * z, d2 - c2 * z
    return ((e1 * b2 - e2 * b1) / det, (a1 * e2 - a2 * e1) / det, z)


def espejo(pl):
    (a, b, c), d = pl
    return ((-a, b, c), d)


def vertices(hs):
    """Vertices de la interseccion de semiespacios n.p <= d."""
    out = []
    for ia, ib, ic in itertools.combinations(range(len(hs)), 3):
        M = [hs[ia][0], hs[ib][0], hs[ic][0]]
        r = [hs[ia][1], hs[ib][1], hs[ic][1]]
        det = (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
               - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
               + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))
        if abs(det) < 1e-9:
            continue

        def comp(j):
            N = [list(row) for row in M]
            for k in range(3):
                N[k][j] = r[k]
            return (N[0][0] * (N[1][1] * N[2][2] - N[1][2] * N[2][1])
                    - N[0][1] * (N[1][0] * N[2][2] - N[1][2] * N[2][0])
                    + N[0][2] * (N[1][0] * N[2][1] - N[1][1] * N[2][0])) / det

        p = (comp(0), comp(1), comp(2))
        if all(h[0][0] * p[0] + h[0][1] * p[1] + h[0][2] * p[2] <= h[1] + 1e-7
               for h in hs):
            out.append(tuple(round(k, 6) for k in p))
    return sorted(set(out))


def solido(nombre, verts, col, props):
    me = bpy.data.meshes.new(nombre)
    bm = bmesh.new()
    for v in verts:
        bm.verts.new(v)
    bm.verts.ensure_lookup_table()
    bmesh.ops.convex_hull(bm, input=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.validate()
    ob = bpy.data.objects.new(nombre, me)
    col.objects.link(ob)
    for k, v in props.items():
        ob[k] = v
    return ob


# ------------------------------------------------------------------ planos
P = {}
for i, nom in enumerate(NOMBRES):
    if nom != "Corner":
        P[nom] = plano_pared(BASE[i], BASE[i + 1], INCL[nom])

APICE = corte3(P["Front"], P["Top"], ZB + H_APICE)
P["Corner"] = plano_por_3((BASE[1][0], BASE[1][1], ZB),
                          (BASE[2][0], BASE[2][1], ZB), APICE)

SUELO = ((0.0, 0.0, -1.0), -ZB)
TECHO = ((0.0, 0.0, 1.0), ZT)          # cara inferior del techo trasero, plana
EJE_D = ((-1.0, 0.0, 0.0), 0.0)        # x >= 0

# El quiebro del techo cae en el vertice Top/Mid, a la altura ZT.
Y_QUIEBRO = corte3(P["Top"], P["Mid"], ZT)[1]

# Cara inferior del techo delantero: contiene la linea del quiebro y baja hacia
# proa. Normal hacia arriba, inclinada TECHO_INCL.
_t = math.radians(TECHO_INCL)
TECHO_PROA = ((0.0, -math.sin(_t), math.cos(_t)),
              -math.sin(_t) * Y_QUIEBRO + math.cos(_t) * ZT)

# Plano vertical del quiebro: separa las dos piezas del techo.
QUIEBRO_PROA = ((0.0, 1.0, 0.0), Y_QUIEBRO)     # y <= Y_QUIEBRO
QUIEBRO_POPA = ((0.0, -1.0, 0.0), -Y_QUIEBRO)   # y >= Y_QUIEBRO

# Cada pared termina contra el techo que le toca: las de proa contra el plano
# inclinado, las de popa contra el plano horizontal. Si se dejara ZT plano para
# todas, las de proa asomarian por encima del techo.
TOPE = {"Front": TECHO_PROA, "Corner": TECHO_PROA, "Top": TECHO_PROA,
        "Mid": TECHO, "Back": TECHO}


def inglete(propio, vecino):
    """Semiespacio que deja a 'propio' su mitad del rincon.

    OJO: NO vale usar el plano exterior de la vecina como limite. La vecina
    ocupa la franja que hay POR DENTRO de su propio plano exterior, asi que
    estar dentro de el no te excluye de ella, y las dos placas se comen el
    mismo rincon. Hay que cortar por el inglete, que es el lugar geometrico
    de los puntos a igual profundidad bajo los dos planos:

        d_a - n_a.p  =  d_b - n_b.p     ->    (n_b - n_a).p = d_b - d_a

    y cada placa se queda con el lado en que es ella la menos profunda.
    """
    (na, da), (nb, db) = propio, vecino
    return (tuple(nb[i] - na[i] for i in range(3)), db - da)


VECINAS = {
    "Front":  ["Corner", "Top"],       # y sus espejos, ver abajo
    "Corner": ["Front", "Top"],
    "Top":    ["Corner", "Front", "Mid"],
    "Mid":    ["Top", "Back"],
    "Back":   ["Mid"],
}


def semiespacios(nom):
    n, d = P[nom]
    t = ESP[nom]
    out = [(n, d), (tuple(-k for k in n), -(d - t)), SUELO, TOPE[nom]]
    out += [inglete(P[nom], P[v]) for v in VECINAS[nom]]
    if nom == "Front":                 # cruza el eje: tambien contra el otro lado
        out += [inglete(P[nom], espejo(P[v])) for v in VECINAS[nom]]
    if nom == "Back":                  # las dos traseras se encuentran en el eje
        out += [EJE_D]
    return out


# --------------------------------------------------------- comprobaciones
print()
print(f"apice frontal/mejilla: ({APICE[0]:+.5f}, {APICE[1]:.5f}, {APICE[2]:.5f})"
      f"   {(APICE[2] - ZB) * 1000:.0f} mm sobre el techo del casco")
print(f"inclinacion que le toca al Corner: "
      f"{math.degrees(math.asin(abs(P['Corner'][0][2]))):.2f}°")

esperados = {"Front": 12, "Corner": 6, "Top": 10, "Mid": 8, "Back": 8}
calc = {}
print()
for nom in NOMBRES:
    v = vertices(semiespacios(nom))
    calc[nom] = v
    ok = "OK" if len(v) == esperados[nom] else f"<- esperaba {esperados[nom]}"
    print(f"{nom:<8} {len(v):2d} vertices  {ok}")
    if len(v) < 4:
        raise SystemExit(f"\nABORTADO: {nom} degenerado. Revisa las inclinaciones.")

# El ancho se mide sobre los vertices generados, no cortando planos: el del
# Corner no llega al techo, asi que su interseccion ahi es un punto espurio.
_todos = [p for v in calc.values() for p in v]
anchoB = max(abs(p[0]) for p in _todos if abs(p[2] - ZB) < 1e-6) * 2
anchoT = max(abs(p[0]) for p in _todos if abs(p[2] - ZT) < 1e-6) * 2
print(f"\nbase   {anchoB * 1000:7.1f} mm   (plano: {ANCHO_BASE * 1000:.0f})")
print(f"techo  {anchoT * 1000:7.1f} mm   (plano: {ANCHO_TECHO * 1000:.0f})")
print(f"altura {ALTURA * 1000:7.1f} mm   Z {ZB:.5f} .. {ZT:.5f}")
for etiq, real, obj in (("base", anchoB, ANCHO_BASE), ("techo", anchoT, ANCHO_TECHO)):
    if abs(real - obj) > 0.005:
        print(f"AVISO: el {etiq} se desvia {abs(real - obj) * 1000:.1f} mm del "
              f"plano. Ajusta INCL['Top'] e INCL['Mid'].")

# Espesor perpendicular: es la separacion entre los dos planos paralelos, asi
# que tiene que salir exacto. Si no sale, el semiespacio interior esta mal.
for nom in NOMBRES:
    n, _ = P[nom]
    pr = [n[0] * p[0] + n[1] * p[1] + n[2] * p[2] for p in calc[nom]]
    e = (max(pr) - min(pr)) * 1000
    if abs(e - ESP[nom] * 1000) > 0.01:
        raise SystemExit(f"\nABORTADO: {nom} mide {e:.2f} mm, declarado "
                         f"{ESP[nom] * 1000:.0f}.")

# Solape entre placas: ningun punto interior de una puede caer dentro de otra.
# Esta comprobacion es la que caza el error de usar el plano exterior de la
# vecina como limite en vez del inglete.
def _dentro(p, hs):
    return all(h[0][0] * p[0] + h[0][1] * p[1] + h[0][2] * p[2] <= h[1] - 1e-6
               for h in hs)


solapes = 0
for a, b in itertools.combinations(NOMBRES, 2):
    for u, w in ((a, b), (b, a)):
        v = calc[u]
        c = tuple(sum(p[i] for p in v) / len(v) for i in range(3))
        for p in v:
            q = tuple(p[i] * 0.7 + c[i] * 0.3 for i in range(3))
            if _dentro(q, semiespacios(w)):
                solapes += 1
                break
if solapes:
    raise SystemExit(f"\nABORTADO: {solapes} pares de placas se solapan.")
print("espesores exactos y sin solapes entre placas")

# ------------------------------------------------------------------ generar
if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

col = bpy.data.collections.get(COLECCION)
if col is None:
    col = bpy.data.collections.new(COLECCION)
    bpy.context.scene.collection.children.link(col)

# Los laterales (ARM_Turret_Addon_*) los genera crear_lateral_torreta.py y NO
# son de este script: antes se borraban junto con todo lo que empezara por
# ARM_Turret_, y relanzar la torreta se llevaba el blindaje lateral por delante.
for ob in list(bpy.data.objects):
    if ob.name.startswith(PREFIJO) and not ob.name.startswith(PREFIJO + "Addon_"):
        bpy.data.objects.remove(ob, do_unlink=True)

creados = []

# La frontal cruza el eje y lleva el hueco del canon, asi que sale en 4 piezas.
_zc = ZB + CANON_Z
_h = CANON_LADO / 2.0
_ARRIBA = ((0.0, 0.0, -1.0), -(_zc + _h))      # z >= zc + h
_ABAJO = ((0.0, 0.0, 1.0), _zc - _h)           # z <= zc - h
_BANDA = [((0.0, 0.0, 1.0), _zc + _h), ((0.0, 0.0, -1.0), -(_zc - _h))]

props_f = {"Thickness_mm": ESP["Front"] * 1000, "Armour_Material": MATERIAL}
_hsF = semiespacios("Front")
for sufijo, extra in (
        ("Front_Upper", [_ARRIBA]),
        ("Front_Lower", [_ABAJO]),
        ("Front_Jamb_L", _BANDA + [((-1.0, 0.0, 0.0), -_h)]),   # x >= +h
        ("Front_Jamb_R", _BANDA + [((1.0, 0.0, 0.0), -_h)])):   # x <= -h
    v = vertices(_hsF + extra)
    if len(v) < 4:
        raise SystemExit(f"\nABORTADO: {sufijo} degenerada. Revisa CANON_Z "
                         f"y CANON_LADO.")
    creados.append(solido(PREFIJO + sufijo, v, col, props_f))

print(f"\nhueco del canon: {CANON_LADO*1000:.0f} mm de lado, centro a Z "
      f"{_zc:.5f} ({CANON_Z*1000:.0f} mm sobre la base de la placa)")
print(f"   ocupa Z {_zc-_h:.5f} .. {_zc+_h:.5f}, X {-_h:+.3f} .. {_h:+.3f}")
print(f"   margen hasta la base de la placa: {(_zc-_h-ZB)*1000:.1f} mm")
# las demas, por pares espejo
for nom in ("Corner", "Top", "Mid", "Back"):
    props = {"Thickness_mm": ESP[nom] * 1000, "Armour_Material": MATERIAL}
    creados.append(solido(f"{PREFIJO}{nom}_L", calc[nom], col, props))
    creados.append(solido(f"{PREFIJO}{nom}_R",
                          [(-x, y, z) for x, y, z in calc[nom]], col, props))

# ---------------------------------------------------------------- el techo
# Dos piezas: la franja de proa, angulada, y la de popa, plana, que lleva el
# hueco de la cupula. Un techo con un agujero redondo NO es convexo, asi que
# la de popa va partida en abanico radial, igual que el anillo del casco.
PARED = [P[n] for n in ("Front", "Top", "Mid", "Back")]
PARED += [espejo(p) for p in PARED]

nT, dT = TECHO_PROA
hs_proa = (PARED + [QUIEBRO_PROA,
                    (tuple(-k for k in nT), -dT),
                    (nT, dT + ESP_TECHO)])
creados.append(solido(PREFIJO + "Roof_Front", vertices(hs_proa), col,
                      {"Thickness_mm": ESP_TECHO * 1000,
                       "Armour_Material": MATERIAL}))

hs_popa = PARED + [QUIEBRO_POPA,
                   ((0.0, 0.0, -1.0), -ZT),
                   ((0.0, 0.0, 1.0), ZT + ESP_TECHO_POPA)]

Y_POPA = (P["Back"][1] - P["Back"][0][2] * ZT) / P["Back"][0][1]
CY_CUP = CUPULA_Y if CUPULA_Y is not None else (Y_QUIEBRO + Y_POPA) / 2.0
R_CUP = CUPULA_D / 2.0

th = [2 * math.pi * k / CUPULA_LADOS for k in range(CUPULA_LADOS)]
VC = [(R_CUP * math.cos(t), CY_CUP + R_CUP * math.sin(t)) for t in th]

print(f"\ncupula: hueco de {CUPULA_D * 1000:.0f} mm, {CUPULA_LADOS} lados, "
      f"centro (0, {CY_CUP:.5f})")
print(f"   placa trasera del techo: Y {Y_QUIEBRO:.5f} .. {Y_POPA:.5f}"
      f"   ({(Y_POPA - Y_QUIEBRO) * 1000:.1f} mm)")
print(f"   margen al quiebro {(CY_CUP - R_CUP - Y_QUIEBRO) * 1000:.1f} mm, "
      f"al borde de popa {(Y_POPA - CY_CUP - R_CUP) * 1000:.1f} mm")
if CY_CUP - R_CUP < Y_QUIEBRO or CY_CUP + R_CUP > Y_POPA:
    raise SystemExit("\nABORTADO: el hueco de la cupula se sale de la placa "
                     "trasera. Baja CUPULA_D o mueve CUPULA_Y.")

for k in range(CUPULA_LADOS):
    a, b = VC[k], VC[(k + 1) % CUPULA_LADOS]
    ex, ey = b[0] - a[0], b[1] - a[1]
    L = math.hypot(ex, ey)
    ne = (ey / L, -ex / L)
    if ne[0] * (a[0] - 0.0) + ne[1] * (a[1] - CY_CUP) < 0:
        ne = (-ne[0], -ne[1])              # hacia fuera del poligono
    fuera = ((-ne[0], -ne[1], 0.0), -(ne[0] * a[0] + ne[1] * a[1]))

    n1 = (-math.sin(th[k]), math.cos(th[k]))
    n2 = (-math.sin(th[(k + 1) % CUPULA_LADOS]),
          math.cos(th[(k + 1) % CUPULA_LADOS]))
    rad1 = ((-n1[0], -n1[1], 0.0), -(n1[1] * CY_CUP))
    rad2 = ((n2[0], n2[1], 0.0), n2[1] * CY_CUP)

    v = vertices(hs_popa + [fuera, rad1, rad2])
    if len(v) < 4:
        raise SystemExit(f"\nABORTADO: cuna {k} del techo degenerada.")
    creados.append(solido(f"{PREFIJO}Roof_Ring_{k:02d}", v, col,
                          {"Thickness_mm": ESP_TECHO_POPA * 1000,
                           "Armour_Material": MATERIAL}))


# ------------------------------------------------------------- el mantelete
# Tres facetas planas con angulo propio, formando una curva quebrada: la
# inferior a MANTELETE_INF_ANG, la media vertical y la superior a
# MANTELETE_SUP_ANG, todos medidos desde la vertical.
#
# No es un arco de circunferencia. Un arco reparte el angulo por igual, asi que
# con 3 caras daria -59°/0°/+59°, simetrico, y aqui hacen falta 14 abajo y 30
# arriba. Con angulos explicitos cada faceta es un plano y ya esta.
#
# La faceta media mide exactamente lo que la abertura del canon, de forma que
# el hueco la parte en dos jambas. Si midiera mas, quedaria un agujero en medio
# de una placa, que no es convexo y habria que partirlo en cuatro.
_ZC = ZB + CANON_Z
_w = MANTELETE_ANCHO / 2.0
_zab, _zat = _ZC - CANON_LADO / 2.0, _ZC + CANON_LADO / 2.0

_nF, _dF = P["Front"]
_yface = (_dF - _nF[2] * _ZC) / _nF[1]


# La faceta superior llega hasta donde acaba la placa frontal.
_ZTOP = max(p[2] for v in (calc["Front"],) for p in v)
_hsup = _ZTOP - _zat
_VUELO = _hsup * math.tan(math.radians(MANTELETE_SUP_ANG))
_YMID = _yface - _VUELO
_zbot = _zab - MANTELETE_INF_ALTO
_ybot = _YMID + MANTELETE_INF_ALTO * math.tan(math.radians(MANTELETE_INF_ANG))


def _plano_yz(p1, p2):
    """Plano vertical en X que pasa por dos puntos (y, z), mirando hacia proa."""
    dy, dz = p2[0] - p1[0], p2[1] - p1[1]
    n = (0.0, -dz, dy)
    L = math.hypot(n[1], n[2])
    n = (0.0, n[1] / L, n[2] / L)
    if n[1] > 0:
        n = (0.0, -n[1], -n[2])
    return n, n[1] * p1[0] + n[2] * p1[1]


_PL_SUP = _plano_yz((_YMID, _zat), (_yface, _ZTOP))
_PL_MED = ((0.0, -1.0, 0.0), -_YMID)
_PL_INF = _plano_yz((_YMID, _zab), (_ybot, _zbot))

_LADOS_M = [((1.0, 0.0, 0.0), MANTELETE_X + _w),
            ((-1.0, 0.0, 0.0), -(MANTELETE_X - _w))]

print(f"\nmantelete: {MANTELETE_ANCHO * 1000:.0f} de ancho, 3 facetas con "
      f"angulo propio (no es un arco)")
print(f"   superior {MANTELETE_SUP_ANG:.0f}°  Z {_zat:.5f}..{_ZTOP:.5f}  "
      f"({_hsup * 1000:.1f} mm)")
print(f"   media     plana     Z {_zab:.5f}..{_zat:.5f}  "
      f"({CANON_LADO * 1000:.0f} mm, lo mismo que la abertura)")
print(f"   inferior {MANTELETE_INF_ANG:.0f}°  Z {_zbot:.5f}..{_zab:.5f}  "
      f"({MANTELETE_INF_ALTO * 1000:.1f} mm)")
print(f"   vuelo resultante {_VUELO * 1000:.1f} mm   "
      f"(lo fija el angulo superior, no se elige)")
print(f"   X {MANTELETE_X - _w:+.4f} .. {MANTELETE_X + _w:+.4f}   "
      f"alto total {(_ZTOP - _zbot) * 1000:.1f} mm")
print(f"   el borde inferior sobresale {(_yface - _ybot) * 1000:.1f} mm "
      f"de la cara de la frontal")
if _zbot < ZB:
    raise SystemExit("\nABORTADO: el mantelete baja por debajo de la torreta.")

_MANT = [("Mantlet_Lower", _PL_INF, [((0.0, 0.0, 1.0), _zab),
                                     ((0.0, 0.0, -1.0), -_zbot)], []),
         ("Mantlet_Jamb_L", _PL_MED, [((0.0, 0.0, 1.0), _zat),
                                      ((0.0, 0.0, -1.0), -_zab)],
          [((-1.0, 0.0, 0.0), -CANON_LADO / 2.0)]),
         ("Mantlet_Jamb_R", _PL_MED, [((0.0, 0.0, 1.0), _zat),
                                      ((0.0, 0.0, -1.0), -_zab)],
          [((1.0, 0.0, 0.0), -CANON_LADO / 2.0)]),
         ("Mantlet_Upper", _PL_SUP, [((0.0, 0.0, 1.0), _ZTOP),
                                     ((0.0, 0.0, -1.0), -_zat)], [])]

for nombre, (n, d), zb_, extra in _MANT:
    hs = ([(n, d), (tuple(-q for q in n), -(d - MANTELETE_ESP))]
          + zb_ + _LADOS_M + extra)
    v = vertices(hs)
    if len(v) < 4:
        raise SystemExit(f"\nABORTADO: {nombre} degenerada.")
    creados.append(solido(f"{PREFIJO}{nombre}", v, col,
                          {"Thickness_mm": MANTELETE_ESP * 1000,
                           "Armour_Material": MATERIAL}))

print(f"\n{len(creados)} objetos creados:")
for ob in creados:
    b = [ob.matrix_world @ v.co for v in ob.data.vertices]
    print(f"  {ob.name:<24} {len(ob.data.vertices):2d} vert  "
          f"X {min(p.x for p in b):+.3f}..{max(p.x for p in b):+.3f}  "
          f"Y {min(p.y for p in b):+.3f}..{max(p.y for p in b):+.3f}  "
          f"Z {min(p.z for p in b):+.3f}..{max(p.z for p in b):+.3f}")

print(f"\nla base apoya en Z {ZB:.5f}, cara superior de ARM_Top_Plate_*")
print(f"la torreta va de Y {min(p[1] for p in BASE):.3f} a "
      f"{max(p[1] for p in BASE):.3f}; el anillo, de 0,878 a 2,478: cubierto")
print("\npasa tools/validate_glb.py despues\n")
