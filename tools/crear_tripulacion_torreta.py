"""Crea los tres tripulantes de la torreta copiando las mallas del conductor.

POR QUE COPIA Y NO GENERA
-------------------------
MOD_Driver_Torso son 12 vertices en tres anillos de cuatro, con dos conicidades
(hombros y cabeza). MOD_Driver_Legs es una cuna de 11 caras, 9 cuadrados y 2
triangulos. No son primitivas de Blender: las modelaste a mano. Reconstruirlas
con formulas seria inventarse 24 vertices que no cuadrarian con los que ya hay,
asi que el script lee las dos mallas de la escena y coloca copias desplazadas.
Si retocas al conductor y vuelves a ejecutar esto, los tres de la torreta
heredan el cambio, con las mismas propiedades (Flesh, Health 80, Crew).

SENTADO Y DE PIE
----------------
Sentado: las dos mallas tal cual, con el MISMO desplazamiento para las dos, asi
que la postura relativa (muslos adelante, torso atras y arriba) se conserva
exacta.

De pie: el torso es el mismo molde, y las piernas son el molde DEL TORSO
escalado y volteado en Z. El molde de las piernas no sirve de pie porque su eje
largo va en Y y al girarlo la cuna de la rodilla queda mirando hacia arriba. El
torso ya es vertical y conico, y volteado deja la parte estrecha abajo, que es
lo que quieres para unos tobillos.

DE PIE NO CABE EN ESTA TORRETA, Y NO ES CULPA DEL MODELO
--------------------------------------------------------
El suelo del compartimento de combate no es ARM_Floor_Plate: es el techo de
MOD_Fuel_Tank_1, que ocupa X -0,578..+0,822, Y 1,325..2,475 y llega a Z 1,440.
La cara inferior del techo de torreta esta a Z 2,907. Quedan 1,467 m de altura
libre. No cabe nadie de pie, y por eso el comandante del Pz IV va sentado con
la cabeza dentro de la cupula, no de pie. La postura "de_pie" se queda en el
script porque la pediste y sirve para una figura fuera del vehiculo, pero los
tres de la torreta van sentados.

IZQUIERDA Y DERECHA
-------------------
El vehiculo mira a -Y, asi que +X es la izquierda: el conductor esta en +X y el
radio en -X, igual que en el Pz IV real. Artillero a la izquierda del canon
(+X), cargador a la derecha (-X). El script refleja la malla cuando X es
negativo, para que el cargador no sea un conductor del reves.

DE DONDE SALEN LAS COORDENADAS
------------------------------
No de un plano: de buscar, para cada uno, la posicion con menos solape real
contra las 169 piezas que ya hay. |X| = 0,35 es el minimo para que el cuerpo
quede entero fuera del eje del canon, porque MOD_Gun ocupa X +-0,125 y el torso
mide 0,45 de ancho. El artillero no puede ir mas adelante que Y 2,40 porque se
lo impide la municion del piso (X +0,06..+0,77, Y 0,83..1,30) y las 6 piezas
altas de X -0,01..+0,74, Z 1,92..2,16. Esa municion esta justo donde irian sus
espinillas y su pecho. Si la mueves, el artillero puede bajar y adelantarse, y
entonces el hombro le sale de la pared de la torreta.

Pestana Scripting -> New -> pegar -> Run.
"""
import bmesh
import bpy

# ------------------------------------------------------------------ parametros
MOLDE_PIERNAS = "MOD_Driver_Legs"
MOLDE_TORSO = "MOD_Driver_Torso"
COLECCION = "Crew"

#     nombre        X del eje   Y de la espalda   Z del apoyo   postura
PERSONAS = [
    ("Gunner",        +0.350,        2.400,         1.720,      "sentado"),
    ("Loader",        -0.350,        1.950,         1.720,      "sentado"),
    ("Commander",      0.000,        2.400,         1.800,      "sentado"),
]

PIERNA = (0.380, 0.300, 0.920)   # de pie: ancho X, fondo Y, alto Z
SOLAPE = 0.073                   # cuanto se mete el torso en las piernas
PASO = 0.010                     # muestreo del test de solapes, en metros
# --------------------------------------------------------------------------


def molde(nombre):
    ob = bpy.data.objects.get(nombre)
    if ob is None or ob.type != 'MESH':
        raise SystemExit(f"\nNo encuentro la malla {nombre!r}.\n")
    M = ob.matrix_world
    V = [tuple(M @ v.co) for v in ob.data.vertices]
    F = [tuple(p.vertices) for p in ob.data.polygons]
    props = {k: ob[k] for k in ob.keys() if not k.startswith("_")}
    return V, F, props


def caja(V):
    return [(min(p[i] for p in V), max(p[i] for p in V)) for i in range(3)]


def semiespacios(V, F):
    """n.p <= d por cada cara. Solo vale si el solido es convexo, que es la
    condicion que §3.1 ya exige a todas las piezas del modelo."""
    c = [sum(p[i] for p in V) / len(V) for i in range(3)]
    out = []
    for f in F:
        A, B, C = V[f[0]], V[f[1]], V[f[2]]
        u = [B[i] - A[i] for i in range(3)]
        w = [C[i] - A[i] for i in range(3)]
        n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2],
             u[0] * w[1] - u[1] * w[0]]
        L = sum(x * x for x in n) ** 0.5
        if L < 1e-12:
            continue
        n = [x / L for x in n]
        d = sum(n[i] * A[i] for i in range(3))
        if sum(n[i] * c[i] for i in range(3)) > d:
            n, d = [-x for x in n], -d
        if not any(abs(d - d2) < 1e-5 and all(abs(n[i] - n2[i]) < 1e-4
                                              for i in range(3))
                   for n2, d2 in out):
            out.append((n, d))
    return out


def crea(nombre, V, F, props, col):
    me = bpy.data.meshes.new(nombre)
    me.from_pydata([tuple(p) for p in V], [], F)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.validate()
    ob = bpy.data.objects.new(nombre, me)
    col.objects.link(ob)
    for k, v in props.items():
        ob[k] = v
    return ob


VL, FL, PL = molde(MOLDE_PIERNAS)
VT, FT, PT = molde(MOLDE_TORSO)
bL, bT = caja(VL), caja(VT)
anchoT = bT[0][1] - bT[0][0]
fondoT = bT[1][1] - bT[1][0]
altoT = bT[2][1] - bT[2][0]

print()
print(f"moldes: torso {anchoT:.3f} x {fondoT:.3f} x {altoT:.3f} m, "
      f"piernas {bL[0][1] - bL[0][0]:.3f} x {bL[1][1] - bL[1][0]:.3f} x "
      f"{bL[2][1] - bL[2][0]:.3f} m")
print(f"propiedades heredadas: {PT}")

if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

col = bpy.data.collections.get(COLECCION)
if col is None:
    col = bpy.data.collections.new(COLECCION)
    bpy.context.scene.collection.children.link(col)

for nom, *_ in PERSONAS:
    for o in list(bpy.data.objects):
        if o.name in (f"MOD_{nom}_Legs", f"MOD_{nom}_Torso"):
            bpy.data.objects.remove(o, do_unlink=True)

# las piezas que ya habia, antes de anadir las nuevas
previas = [o for o in bpy.data.objects if o.type == 'MESH' and o.data.vertices]

nuevos = []
for nom, X, Yb, Z0, postura in PERSONAS:
    esp = -1.0 if X < 0 else 1.0
    cxT = (bT[0][0] + bT[0][1]) / 2

    if postura == "sentado":
        # mismo desplazamiento para las dos piezas: la postura no se deforma
        T = (X - esp * cxT, Yb - bT[1][1], Z0 - bL[2][0])
        piernas = [(esp * p[0] + T[0], p[1] + T[1], p[2] + T[2]) for p in VL]
        torso = [(esp * p[0] + T[0], p[1] + T[1], p[2] + T[2]) for p in VT]
        caras_p = FL
    elif postura == "de_pie":
        kx, ky, kz = PIERNA[0] / anchoT, PIERNA[1] / fondoT, PIERNA[2] / altoT
        p0 = [(esp * kx * p[0], ky * p[1], -kz * p[2]) for p in VT]
        b = caja(p0)
        yc = Yb - fondoT / 2
        Tp = (X - (b[0][0] + b[0][1]) / 2, yc - (b[1][0] + b[1][1]) / 2,
              Z0 - b[2][0])
        piernas = [(p[0] + Tp[0], p[1] + Tp[1], p[2] + Tp[2]) for p in p0]
        zt = Z0 + PIERNA[2] - SOLAPE
        Tt = (X - esp * cxT, Yb - bT[1][1], zt - bT[2][0])
        torso = [(esp * p[0] + Tt[0], p[1] + Tt[1], p[2] + Tt[2]) for p in VT]
        caras_p = FT
    else:
        raise SystemExit(f"\npostura desconocida: {postura!r}\n")

    nuevos.append((nom, crea(f"MOD_{nom}_Legs", piernas, caras_p, PL, col),
                   crea(f"MOD_{nom}_Torso", torso, FT, PT, col)))

    bp, bt = caja(piernas), caja(torso)
    print(f"\n{nom} ({postura})")
    print(f"   piernas  X {bp[0][0]:+.3f}..{bp[0][1]:+.3f}  "
          f"Y {bp[1][0]:+.3f}..{bp[1][1]:+.3f}  Z {bp[2][0]:+.3f}..{bp[2][1]:+.3f}")
    print(f"   torso    X {bt[0][0]:+.3f}..{bt[0][1]:+.3f}  "
          f"Y {bt[1][0]:+.3f}..{bt[1][1]:+.3f}  Z {bt[2][0]:+.3f}..{bt[2][1]:+.3f}")
    print(f"   cabeza a Z {bt[2][1]:.3f}, alto {bt[2][1] - bp[2][0]:.3f} m")


# -------------------------------------------------------------- test de solapes
# Muestrea el OBSTACULO, no el cuerpo. Al reves, una rejilla sobre un torso de
# 0,84 m se cuela entre las placas de 11 mm del anillo y da cero solape cuando
# si lo hay. El obstaculo es lo fino, asi que muestrearlo a 10 mm los ve todos.
def dentro(p, hs):
    return all(sum(n[i] * p[i] for i in range(3)) <= d + 1e-9 for n, d in hs)


def volumen_comun(cb, hs, b):
    it = [(max(cb[i][0], b[i][0]), min(cb[i][1], b[i][1])) for i in range(3)]
    if any(it[i][1] - it[i][0] <= 1e-9 for i in range(3)):
        return 0.0
    ns = [max(1, int((it[i][1] - it[i][0]) / PASO)) for i in range(3)]
    dv = 1.0
    for i in range(3):
        dv *= (it[i][1] - it[i][0]) / ns[i]
    k = 0
    for a in range(ns[0]):
        x = it[0][0] + (a + 0.5) * (it[0][1] - it[0][0]) / ns[0]
        for b2 in range(ns[1]):
            y = it[1][0] + (b2 + 0.5) * (it[1][1] - it[1][0]) / ns[1]
            for c in range(ns[2]):
                z = it[2][0] + (c + 0.5) * (it[2][1] - it[2][0]) / ns[2]
                if dentro((x, y, z), hs):
                    k += 1
    return k * dv


otros = []
for o in previas:
    V = [tuple(o.matrix_world @ v.co) for v in o.data.vertices]
    otros.append((o.name, caja(V), o.get("Module_Type", "")))

print("\n--- solapes ---")
duros = flesh = 0
for nom, op, ot in nuevos:
    for ob in (op, ot):
        V = [tuple(ob.matrix_world @ v.co) for v in ob.data.vertices]
        cb = caja(V)
        hs = semiespacios(V, [tuple(p.vertices) for p in ob.data.polygons])
        for n2, b2, mt in otros:
            v = volumen_comun(cb, hs, b2)
            if v > 1e-6:
                if mt == "Crew":
                    flesh += 1
                    print(f"  carne  {ob.name} x {n2}: {v * 1000:.2f} l")
                else:
                    duros += 1
                    print(f"  DURO   {ob.name} x {n2}: {v * 1000:.2f} l")

print(f"\n  {duros} contra blindaje o maquinas, {flesh} contra otro tripulante")
print("  Carne dentro de carne es inofensivo: en un Pz IV van hombro con hombro,")
print("  y un rayo que cruce esa zona deposita energia en los dos, que es lo")
print("  correcto. Carne dentro de blindaje sobrevalora un poco el acero en ese")
print("  trozo. Lo que si hay que corregir siempre es blindaje dentro de")
print("  blindaje, que cuenta la proteccion dos veces.")
print(f"\n{len(nuevos) * 2} objetos en la coleccion {COLECCION!r}")
print("pasa tools/revisar_vertices.py y tools/validate_glb.py despues\n")
