"""Crea las dos orugas del Pz IV como MODULO (Module_Type "Track"), en piezas convexas.

LA ORUGA ES UN MODULO, NO UNA PLACA
-----------------------------------
Si se daña, el vehiculo queda inmovilizado: es un componente de movilidad, como
el motor o la transmision. Cada pieza lleva Module_Type, Health y
Armour_Material (Track, resistencia 0,7: sigue frenando el rayo), y NO lleva
Thickness_mm: validate_glb.py rechaza un objeto con propiedades de placa y de
modulo a la vez, y el espesor lo da la malla (20 mm).

Las 42 piezas son un artefacto de la convexidad, no 42 componentes. Por eso la
regla de dano no debe acumular energia pieza a pieza (el total dependeria de
como se ha cortado la cinta): ver docs/modelo_balistico.md, §3.7.1 y §3.7.3.

La cinta de 20 mm, partida en piezas convexas:

POR QUE UNA CINTA EN FACETAS
----------------------------
Una oruga es un lazo cerrado: hueca por dentro y por tanto NO CONVEXA. Un rayo
lateral que cruce el lazo corta la cinta, atraviesa el aire del interior y
vuelve a cortarla, y como §3.1 toma la primera interseccion como entrada y la
ultima como salida, mediria todo el hueco como acero. Es el mismo problema que
la cupula y el hueco del anillo, y la misma solucion: la cinta se parte en
tramos, cada uno una plancha recta de 20 mm entre dos planos paralelos, y los
arcos de las ruedas se aproximan por facetas.

    tramo recto superior        una pieza
    arco de la rueda tensora    ~8 facetas de 20 grados
    tramo inferior              pieza de bajada + tramo de suelo + pieza de subida
    arco de la rueda motriz     ~10 facetas de 20 grados

Cada pieza es la huella en planta (Y, Z) de un cuadrilatero convexo, con el
lado exterior en el contorno y el interior desplazado 20 mm hacia dentro,
extruida a lo ancho de la cinta (eje X). Las piezas vecinas se unen en
inglete exacto y comparten cara.

DE DONDE SALE LA FORMA
----------------------
Se midio sobre tu vista lateral (500 px de ancho). Los numeros en pixeles de
mas abajo son del dibujo; el script los convierte a metros con dos referencias
tuyas:

    suelo (Z = 0)         fila 205,5 del dibujo
    tramo superior        fila 122,0  ->  Z = Z_TOP

El eje Y se coloca con la punta de la proa y la cola del casco del dibujo
(columnas 47,2 y 494,0) sobre la placa frontal y la trasera de TU casco, asi
que el largo lo manda tu casco y no el dibujo.

LA ALTURA: Z_TOP ES EL UNICO MANDO
----------------------------------
Todo lo demas (radios de las ruedas, altura de los centros, codo del tramo
superior) esta en pixeles del dibujo y se escala con Z_TOP, asi que cambiarlo
sube o baja la oruga entera sin deformarla: las ruedas siguen siendo
circulos.

    0,90629  escala uniforme con tu casco  <- valor actual
    1,00000  intermedio
    1,09586  pegada a la cara inferior del faldon de antes de subir el casco
    1,16750  pegada al faldon de ahora

El valor puesto, 0,90629, es el unico que lee el dibujo a UNA sola escala:
tu casco mide 4,85 m contra los 5,89 m del Pz IV real (82,3 %), asi que la
oruga se queda tambien al 82,3 % de su altura. Es la unica altura con la que
las ruedas motriz y tensora te van a salir proporcionadas cuando las modeles:
con 1,1 m el radio de envoltura de la motriz salia de 430 mm, contra los
~320 mm que toca.

A cambio deja 261 mm de aire entre el tramo superior y el faldon. Ahi es
donde van los rodillos de retorno, pero son 261 mm, no los ~80 mm del
vehiculo real. Si prefieres cerrar ese hueco, sube Z_TOP y pierdes la
proporcion de las ruedas: una cosa o la otra, no las dos.

ESTE SCRIPT NO COMPROBA SOLAPES CONTRA EL RESTO DEL MODELO: con 42 piezas y
205 objetos el calculo tarda minutos y deja Blender congelado, que es lo que
parece un cuelgue. Para eso pasa tools/validate_glb.py despues de exportar.

Pestana Scripting -> New -> pegar -> Run.
"""
import math

# ------------------------------------------------------------ medido en el dibujo (px)
RUEDA_MOTRIZ = (88.3, 154.8, 32.8)      # centro x, y y radio EXTERIOR de la cinta al darle la vuelta
RUEDA_TENSORA = (449.8, 163.7, 29.5)
SUELO_1 = (130.0, 205.5)                # primer punto de apoyo en el suelo (rueda de rodadura 1)
SUELO_2 = (392.5, 205.5)                # ultimo punto de apoyo (rueda de rodadura 8)
CODO_SUP = (345.0, 124.0)               # donde el tramo superior empieza a bajar hacia la tensora
Y_SUELO_PX = 205.5
Y_TECHO_PX = 122.0
X_NARIZ_PX = 47.2                       # punta de la proa del casco en el dibujo
X_COLA_PX = 494.0                       # cola del casco

# --------------------------------------------------------------- tu modelo (m)
Z_TOP = 0.90629                         # altura del tramo superior: el mando, ver arriba
Y_CASCO_FRENTE = -0.64882               # ARM_Lower_Front_Plate
Y_CASCO_POPA = 4.20065                  # ARM_Lower_Back_Plate
X_INT = 0.92700                         # cara exterior de ARM_Hull_Side_*
Z_FALDON = 1.16750                      # cara inferior de ARM_Side_Skirt_*, solo para avisar del hueco

# ------------------------------------------------------------------- la cinta
ESPESOR = 0.020
ANCHO = 0.560                           # lo que me diste; ver nota en el informe
ARCO_PASO = 20.0                        # grados por faceta
MATERIAL = "Track"
COLECCION = "Modules"
PREFIJO = "MOD_Track_"
PREFIJO_VIEJO = "ARM_Track_"            # la version anterior (placas): se borra al regenerar
MODULO = "Track"
VIDA = 5000.0                           # J. SUPUESTO sin fuente: ver el informe; parametro libre (§6)
BORRADOR = ["ARM_Addon_R", "ARM_Addon_R.001"]
BORRAR_BORRADOR = False
# --------------------------------------------------------------------------

ESCALA_Z = Z_TOP / (Y_SUELO_PX - Y_TECHO_PX)
ESCALA_Y = (Y_CASCO_POPA - Y_CASCO_FRENTE) / (X_COLA_PX - X_NARIZ_PX)
# ESCALA_Y = ESCALA_Z      # <- descomenta si alargas el casco al largo real


def a_modelo(x, y):
    return (Y_CASCO_FRENTE + (x - X_NARIZ_PX) * ESCALA_Y, (Y_SUELO_PX - y) * ESCALA_Z)


def tangente(P, C, R, hacia):
    """Punto de tangencia desde el punto P a la circunferencia (C, R), con la
    circunferencia a la derecha del recorrido (el lazo se recorre en sentido
    horario). hacia=True: se va de P a la circunferencia; False: de ella a P."""
    v = (P[0] - C[0], P[1] - C[1])
    a = math.acos(R / math.hypot(*v))
    base = math.atan2(v[1], v[0])
    for sg in (1, -1):
        ang = base + sg * a
        Q = (C[0] + R * math.cos(ang), C[1] + R * math.sin(ang))
        d = (Q[0] - P[0], Q[1] - P[1]) if hacia else (P[0] - Q[0], P[1] - Q[1])
        if d[0] * (C[1] - Q[1]) - d[1] * (C[0] - Q[0]) < 0:
            return Q, ang
    raise ValueError("sin tangente")


def arco(C, R, a0, a1):
    """Facetas sobre la circunferencia de a0 a a1 en sentido horario."""
    d = (a0 - a1) % (2 * math.pi)
    n = max(1, math.ceil(d / math.radians(ARCO_PASO)))
    return [(C[0] + R * math.cos(a0 - d * k / n), C[1] + R * math.sin(a0 - d * k / n))
            for k in range(n + 1)]


def contorno():
    """Puntos del contorno exterior, en sentido horario, en (Y, Z) metros."""
    Sx, Sy, Sr = RUEDA_MOTRIZ
    Ix, Iy, Ir = RUEDA_TENSORA
    S, I = a_modelo(Sx, Sy), a_modelo(Ix, Iy)
    Rs, Ri = Sr * ESCALA_Z, Ir * ESCALA_Z
    G1, G2, T1 = a_modelo(*SUELO_1), a_modelo(*SUELO_2), a_modelo(*CODO_SUP)
    _, as1 = tangente(G1, S, Rs, True)
    _, as2 = tangente(T1, S, Rs, False)
    _, ai1 = tangente(T1, I, Ri, True)
    _, ai2 = tangente(G2, I, Ri, False)
    pts = arco(S, Rs, as1, as2) + [T1] + arco(I, Ri, ai1, ai2) + [G2, G1]
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts))) / 2
    assert area < 0, "el contorno no esta en sentido horario"
    return pts, dict(S=S, I=I, Rs=Rs, Ri=Ri, G1=G1, G2=G2, T1=T1)


def inters(p, d, q, e):
    den = d[0] * e[1] - d[1] * e[0]
    if abs(den) < 1e-12:
        return None
    s = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return (p[0] + s * d[0], p[1] + s * d[1])


def huellas(pts):
    """Cuadrilatero (Y, Z) de cada tramo, con ingletes exactos en todas las juntas."""
    n = len(pts)
    dirs, nin = [], []
    for k in range(n):
        dx = pts[(k + 1) % n][0] - pts[k][0]
        dy = pts[(k + 1) % n][1] - pts[k][1]
        L = math.hypot(dx, dy)
        dirs.append((dx / L, dy / L))
        nin.append((dy / L, -dx / L))                  # normal hacia el interior del lazo
    base = [(pts[k][0] + ESPESOR * nin[k][0], pts[k][1] + ESPESOR * nin[k][1]) for k in range(n)]
    interior = []
    for k in range(n):                                 # vertice interior en la junta k
        q = inters(base[k - 1], dirs[k - 1], base[k], dirs[k])
        interior.append(q if q is not None else base[k])
    return [([pts[k], pts[(k + 1) % n], interior[(k + 1) % n], interior[k]], nin[k])
            for k in range(n)]


def convexa(poly):
    sg = []
    for i in range(len(poly)):
        a, b, c = poly[i], poly[(i + 1) % len(poly)], poly[(i + 2) % len(poly)]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cr) > 1e-14:
            sg.append(cr > 0)
    return all(sg) or not any(sg)


def piezas(signo):
    """Vertices 3D de cada pieza para un lado (signo +1 = L, -1 = R)."""
    pts, info = contorno()
    x0, x1 = sorted((signo * X_INT, signo * (X_INT + ANCHO)))
    out = []
    for hu, nin in huellas(pts):
        v = [(x, y, z) for (y, z) in hu for x in (x0, x1)]
        out.append((v, hu, nin))
    return out, info, pts


def comprobar(lados):
    """Convexidad de la huella y espesor exacto sobre la normal. Aborta si fallan."""
    for suf, (ps, _, _) in lados:
        for k, (v, hu, nin) in enumerate(ps):
            if not convexa(hu):
                raise SystemExit(f"\nABORTADO: la huella de {suf}_{k:02d} no es convexa.\n")
            for q in hu[2:]:
                d = abs((q[0] - hu[0][0]) * nin[0] + (q[1] - hu[0][1]) * nin[1])
                if abs(d - ESPESOR) > 1e-9:
                    raise SystemExit(f"\nABORTADO: {suf}_{k:02d} sale con {d * 1000:.4f} mm.\n")


# ================================================================== BLENDER
try:
    import bmesh
    import bpy
except ImportError:          # fuera de Blender solo estan las funciones puras
    bpy = None

if bpy is not None:

    def solido(nombre, verts, col):
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
        ob["Module_Type"] = MODULO
        ob["Health"] = VIDA
        ob["Armour_Material"] = MATERIAL
        return ob

    lados = [("L", piezas(+1)), ("R", piezas(-1))]
    comprobar(lados)
    _, info, pts = lados[0][1]
    ys = [p[0] for p in pts]
    print()
    print(f"cinta de {ESPESOR * 1000:.0f} mm x {ANCHO * 1000:.0f} mm, {len(pts)} piezas por lado, "
          f"espesor y convexidad verificados")
    print(f"  suelo Z = 0, tramo superior Z = {Z_TOP:.5f}")
    print(f"  X {X_INT:.3f} .. {X_INT + ANCHO:.3f}  (ancho total del vehiculo "
          f"{2 * (X_INT + ANCHO):.3f} m)")
    print(f"  lazo Y {min(ys):+.3f} .. {max(ys):+.3f}   casco {Y_CASCO_FRENTE:+.3f} .. "
          f"{Y_CASCO_POPA:+.3f}")
    print(f"  rueda motriz  centro ({info['S'][0]:+.3f}, {info['S'][1]:.3f})  radio {info['Rs']:.3f}")
    print(f"  rueda tensora centro ({info['I'][0]:+.3f}, {info['I'][1]:.3f})  radio {info['Ri']:.3f}")
    print(f"  apoyo en suelo Y {info['G1'][0]:+.3f} .. {info['G2'][0]:+.3f}  "
          f"({abs(info['G2'][0] - info['G1'][0]):.2f} m)")
    print(f"  hueco hasta el faldon {(Z_FALDON - max(p[1] for p in pts)) * 1000:.0f} mm "
          f"(rodillos de retorno)")
    print(f"  flecha maxima de las facetas "
          f"{max(info['Rs'], info['Ri']) * (1 - math.cos(math.radians(ARCO_PASO / 2))) * 1000:.1f} mm")

    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    col = bpy.data.collections.get(COLECCION)
    if col is None:
        col = bpy.data.collections.new(COLECCION)
        bpy.context.scene.collection.children.link(col)
    for ob in list(bpy.data.objects):
        if (ob.name.startswith((PREFIJO, PREFIJO_VIEJO))
                or (BORRAR_BORRADOR and ob.name in BORRADOR)):
            bpy.data.objects.remove(ob, do_unlink=True)
    n = 0
    for suf, (ps, _, _) in lados:
        for k, (v, _h, _n) in enumerate(ps):
            solido(f"{PREFIJO}{suf}_{k:02d}", v, col)
            n += 1
    print(f"\n{n} piezas generadas")

    quedan = [o for o in BORRADOR if bpy.data.objects.get(o) is not None]
    if quedan:
        print(f"\n  OJO: {', '.join(quedan)} ocupan el mismo espacio que la oruga "
              f"(solape de 5 mm medido\n  sobre el .glb). Borralos, o pon BORRAR_BORRADOR = True.")
    print("\npasa tools/revisar_vertices.py y tools/validate_glb.py despues\n")
