"""Genera el canon y el motor del Pz IV H como piezas convexas.

Sustituye MOD_Barrel, MOD_Gun y MOD_Engine. Los tres salian marcados por
tools/validate_glb.py por dos defectos distintos:

  MOD_Barrel  1,39 mm  La seccion es un octogono regular y es convexa. Lo que
                       estaba mal era la tapa de popa: la mitad X<0 a
                       Y=0,75797 y la mitad X>=0 a Y=0,75657, un escalon de
                       1,40 mm. De paso solapaba 0,87 mm con la recamara.
  MOD_Gun     ok       Caja correcta, con 0,01 mm de desviacion en una cara.
                       Se regenera por exactitud, no porque fallara.
  MOD_Engine  176,6 mm Prisma de seccion hexagonal en U: un bloque arriba y
                       dos patas con una muesca en medio. Concavo de verdad.
                       Rellenar la muesca con el casco convexo duplicaria el
                       volumen (+104%), asi que se parte en tres convexas que
                       conservan el volumen exacto.

Todas las piezas son prismas: un contorno plano en X-Z extruido a lo largo de
Y. Esa construccion garantiza caras planas y, si el contorno 2D es convexo, la
pieza 3D tambien lo es (§3.1). Es el mismo arreglo que funciono con
ARM_Front_Top_Plate.

Uso:
  Dentro de Blender      ejecutar en el editor de scripts: borra y reconstruye.
  Fuera de Blender       python tools/crear_canon_motor.py  -> solo las
                         comprobaciones, sin tocar nada. Util para revisar los
                         numeros sin abrir Blender.

Despues de ejecutarlo hay que reexportar el .glb y pasar validate_glb.py.
"""

import math

try:
    import bmesh
    import bpy
    EN_BLENDER = True
except ImportError:
    EN_BLENDER = False


# --------------------------------------------------------------------------
# Constantes. Medidas tomadas de models/Pz IV H.glb el 29/10/2026.
# --------------------------------------------------------------------------

COLECCION = "Modules"

# --- Canon: tubo ---
NOMBRE_TUBO = "MOD_Barrel"
RADIO_TUBO = 0.05575          # m, al vertice del octogono
LADOS_TUBO = 8
CENTRO_TUBO = (0.0, 1.69492)  # (X, Z) del eje
Y_BOCA = -2.04580             # extremo delantero
Y_CULATA = 0.75657            # tapa de popa, plana. Ver nota de arriba
VIDA_TUBO = 40000.0

# --- Canon: recamara ---
NOMBRE_RECAMARA = "MOD_Gun"
X_RECAMARA = 0.12500          # semiancho
Z_RECAMARA = (1.57449, 1.82449)
Y_RECAMARA = (0.75710, 1.95710)
VIDA_RECAMARA = 25000.0

MATERIAL_CANON = "Steel"

# --- Motor ---
PREFIJO_MOTOR = "MOD_Engine"  # pasa a MOD_Engine_1, _2 y _3
Y_MOTOR = (2.71462, 3.55987)
VIDA_MOTOR = 300000.0         # se reparte entre las tres piezas por volumen
MATERIAL_MOTOR = "Cast_Iron"
Z_MUESCA = 0.83054            # altura del techo de la muesca

# Contorno original, hexagonal y concavo. Solo se usa para comprobar que las
# tres piezas conservan el volumen.
CONTORNO_ORIGINAL = [
    (-0.20519, 1.04186),
    (+0.21743, 1.04186),
    (+0.15404, 0.40792),
    (+0.13291, Z_MUESCA),
    (-0.12067, Z_MUESCA),
    (-0.14180, 0.40792),
]

# Las tres piezas convexas. El bloque queda por encima de Z_MUESCA y las dos
# patas por debajo, asi que no pueden solaparse entre si.
CONTORNOS_MOTOR = [
    [(-0.20519, 1.04186), (+0.21743, 1.04186),
     (+0.19630, Z_MUESCA), (-0.18406, Z_MUESCA)],          # bloque
    [(-0.18406, Z_MUESCA), (-0.12067, Z_MUESCA), (-0.14180, 0.40792)],   # pata izq
    [(+0.13291, Z_MUESCA), (+0.19630, Z_MUESCA), (+0.15404, 0.40792)],   # pata der
]

TOL_AREA = 1e-5   # m2, holgura al comparar volumenes


# --------------------------------------------------------------------------
# Geometria pura. Sin bpy, O(n), sin comprobaciones contra la escena entera:
# un barrido de toda la escena dentro de Blender es lo que lo colgaba.
# --------------------------------------------------------------------------

def cruz(o, a, b):
    """Producto cruzado 2D de (a-o) x (b-o). El signo da el sentido del giro."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def area(contorno):
    """Area del poligono por la formula del cordon de zapato."""
    n = len(contorno)
    s = sum(contorno[i][0] * contorno[(i + 1) % n][1]
            - contorno[(i + 1) % n][0] * contorno[i][1] for i in range(n))
    return abs(s) / 2.0


def convexo(contorno):
    """True si todos los giros van en el mismo sentido."""
    n = len(contorno)
    s = [cruz(contorno[i - 1], contorno[i], contorno[(i + 1) % n])
         for i in range(n)]
    return all(v > 1e-12 for v in s) or all(v < -1e-12 for v in s)


def octogono(centro, radio, lados):
    """Contorno regular en X-Z, con un vertice en +X como en el modelo."""
    cx, cz = centro
    return [(cx + radio * math.cos(2 * math.pi * k / lados),
             cz + radio * math.sin(2 * math.pi * k / lados))
            for k in range(lados)]


def rectangulo(semiancho, z0, z1):
    return [(-semiancho, z0), (+semiancho, z0), (+semiancho, z1), (-semiancho, z1)]


def piezas():
    """Devuelve la lista de (nombre, contorno, y0, y1, tipo, vida, material)."""
    out = [
        (NOMBRE_TUBO, octogono(CENTRO_TUBO, RADIO_TUBO, LADOS_TUBO),
         Y_BOCA, Y_CULATA, "Gun", VIDA_TUBO, MATERIAL_CANON),
        (NOMBRE_RECAMARA, rectangulo(X_RECAMARA, *Z_RECAMARA),
         Y_RECAMARA[0], Y_RECAMARA[1], "Gun", VIDA_RECAMARA, MATERIAL_CANON),
    ]
    total = sum(area(c) for c in CONTORNOS_MOTOR)
    for i, c in enumerate(CONTORNOS_MOTOR, start=1):
        # El Health se reparte por volumen, igual que la transmision va en
        # cinco cajas de 30 kJ. Ver la nota de comprobar() sobre §3.7.3.
        out.append((f"{PREFIJO_MOTOR}_{i}", c, Y_MOTOR[0], Y_MOTOR[1],
                    "Engine", VIDA_MOTOR * area(c) / total, MATERIAL_MOTOR))
    return out


def comprobar():
    """Imprime los numeros y aborta si algun contorno sale concavo."""
    print("Contornos:")
    malos = []
    for nombre, c, y0, y1, tipo, vida, mat in piezas():
        ok = convexo(c)
        vol = area(c) * (y1 - y0)
        print(f"  {nombre:16s} {len(c)} vert  "
              f"{'convexo' if ok else 'CONCAVO':8s}  "
              f"{area(c) * 1e4:8.1f} cm2  {vol * 1e3:7.2f} L  "
              f"{tipo:12s} {vida:9.0f} J")
        if not ok:
            malos.append(nombre)
    assert not malos, f"contornos concavos: {malos}"

    # El volumen del motor tiene que coincidir con el del hexagono original.
    a_orig = area(CONTORNO_ORIGINAL)
    a_nuevo = sum(area(c) for c in CONTORNOS_MOTOR)
    print(f"\nMotor: hexagono original {a_orig * 1e4:.1f} cm2, "
          f"tres piezas {a_nuevo * 1e4:.1f} cm2, "
          f"diferencia {abs(a_orig - a_nuevo) * 1e4:+.3f} cm2")
    assert abs(a_orig - a_nuevo) < TOL_AREA, "las tres piezas no conservan el volumen"
    assert not convexo(CONTORNO_ORIGINAL), "el hexagono original deberia ser concavo"

    # Bloque arriba, patas abajo: no pueden solaparse.
    bloque = CONTORNOS_MOTOR[0]
    assert min(z for _, z in bloque) >= Z_MUESCA - 1e-9
    for pata in CONTORNOS_MOTOR[1:]:
        assert max(z for _, z in pata) <= Z_MUESCA + 1e-9
    print("Bloque por encima de la muesca y patas por debajo: no se solapan.")

    # El tubo no debe entrar en la recamara.
    hueco = Y_RECAMARA[0] - Y_CULATA
    print(f"Tubo y recamara: hueco de {hueco * 1000:+.2f} mm "
          f"({'contiguos' if 0 <= hueco < 0.001 else 'revisar'})")
    assert hueco >= 0, "el tubo solapa la recamara"

    print("\nAVISO: el motor pasa de 1 objeto a 3, con 'Health' acumulativo "
          "(§3.7.1).\n  §3.7.3 tiene que SUMAR el dano de los tres, no "
          "agregarlos con OR:\n  con OR, el motor se averiaria al agotar "
          "cualquiera de las piezas,\n  y una pata sola son 36 kJ de los "
          "300 kJ del conjunto.")


# --------------------------------------------------------------------------
# Construccion en Blender
# --------------------------------------------------------------------------

def coleccion():
    col = bpy.data.collections.get(COLECCION)
    if col is None:
        col = bpy.data.collections.new(COLECCION)
        bpy.context.scene.collection.children.link(col)
    return col


def borrar(nombre):
    ob = bpy.data.objects.get(nombre)
    if ob is None:
        return False
    malla = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if malla is not None and malla.users == 0:
        bpy.data.meshes.remove(malla)
    return True


def prisma(nombre, contorno, y0, y1, col):
    """Extruye el contorno X-Z a lo largo de Y y devuelve el objeto."""
    bm = bmesh.new()
    popa = [bm.verts.new((x, y0, z)) for x, z in contorno]
    proa = [bm.verts.new((x, y1, z)) for x, z in contorno]
    bm.faces.new(popa)
    bm.faces.new(proa)
    n = len(contorno)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((popa[i], popa[j], proa[j], proa[i]))
    # Normales hacia fuera sin depender del sentido de giro del contorno.
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    malla = bpy.data.meshes.new(nombre)
    bm.to_mesh(malla)
    bm.free()
    ob = bpy.data.objects.new(nombre, malla)
    col.objects.link(ob)
    return ob


def construir():
    col = coleccion()

    # El motor pasa de un objeto a tres, asi que hay que quitar el viejo.
    for viejo in (PREFIJO_MOTOR, NOMBRE_TUBO, NOMBRE_RECAMARA):
        if borrar(viejo):
            print(f"  borrado {viejo}")
    for i in range(1, len(CONTORNOS_MOTOR) + 1):
        borrar(f"{PREFIJO_MOTOR}_{i}")

    for nombre, contorno, y0, y1, tipo, vida, material in piezas():
        ob = prisma(nombre, contorno, y0, y1, col)
        ob["Module_Type"] = tipo
        ob["Health"] = float(vida)
        ob["Armour_Material"] = material
        # Los modulos no llevan Thickness_mm (§2.4); validate_glb.py rechaza
        # un objeto que tenga las dos cosas.
        print(f"  creado  {nombre:16s} {len(ob.data.vertices):3d} vert  "
              f"{len(ob.data.polygons):2d} caras")


if __name__ == "__main__":
    comprobar()
    if EN_BLENDER:
        print("\nConstruyendo:")
        construir()
        print("\nHecho. Reexportar el .glb y pasar validate_glb.py.")
    else:
        print("\nFuera de Blender: no se ha tocado nada.")
