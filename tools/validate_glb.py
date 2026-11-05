"""Valida el .glb del vehiculo antes de usarlo en el simulador.

Por objeto: propiedades presentes, material declarado en data/materials.csv,
malla cerrada, normales hacia fuera, convexidad (§3.1) y espesor geometrico
frente a Thickness_mm. En conjunto: nombres repetidos y solapes entre objetos.
Tambien es el lector de .glb que usa disparo.py (load, ray_tri y el algebra).

Uso:  python tools/validate_glb.py ["models/Pz IV H.glb"] [data]
      python tools/validate_glb.py --selftest
Devuelve codigo de salida 1 si hay algun ERROR.
"""
import csv
import json
import math
import os
import struct
import sys

TOL_THICKNESS_MM = 0.5     # margen entre geometria y propiedad
TOL_PLANE_M = 1e-5         # por debajo: ruido de coma flotante
TOL_WARP_M = 1e-3          # por encima: cara alabeada (aviso)
TOL_CONCAV_M = 1e-3        # por encima: concavidad real que falsea el camino (error)
TOL_WELD_M = 5e-4          # a partir de aqui dos vertices son el mismo
TOL_OVERLAP_M = 1e-4       # por encima: solape que cuenta camino dos veces (error)


# --- algebra ---------------------------------------------------------------
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1],
                         a[2] * b[0] - a[0] * b[2],
                         a[0] * b[1] - a[1] * b[0])
def norm(a):
    n = math.sqrt(dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-12 else (0.0, 0.0, 0.0)


def ray_tri(o, d, t):
    """Moller-Trumbore. Distancia a lo largo de d, o None si no corta."""
    e1, e2 = sub(t[1], t[0]), sub(t[2], t[0])
    h = cross(d, e2)
    a = dot(e1, h)
    if abs(a) < 1e-12:
        return None
    f = 1.0 / a
    s = sub(o, t[0])
    u = f * dot(s, h)
    if u < -1e-9 or u > 1 + 1e-9:
        return None
    q = cross(s, e1)
    v = f * dot(d, q)
    if v < -1e-9 or u + v > 1 + 1e-9:
        return None
    return f * dot(e2, q)


# --- lectura ---------------------------------------------------------------
_COMP = {5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2),
         5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
_NUM = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}


def load(path):
    """[(nombre, triangulos en coordenadas de Blender, propiedades)] por nodo con malla."""
    data = open(path, 'rb').read()
    off, js, bin_ = 12, None, b''
    while off < len(data):
        ln, kind = struct.unpack_from('<II', data, off)
        off += 8
        if kind == 0x4E4F534A:
            js = json.loads(data[off:off + ln])
        elif kind == 0x004E4942:
            bin_ = data[off:off + ln]
        off += ln

    def read(i):
        a = js['accessors'][i]
        v = js['bufferViews'][a['bufferView']]
        f, sz = _COMP[a['componentType']]
        n = _NUM[a['type']]
        b = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        st = v.get('byteStride') or sz * n
        return [struct.unpack_from('<' + f * n, bin_, b + k * st) for k in range(a['count'])]

    def mat(node):
        if 'matrix' in node:
            m = node['matrix']
            return [[m[0], m[4], m[8], m[12]], [m[1], m[5], m[9], m[13]], [m[2], m[6], m[10], m[14]]]
        x, y, z, w = node.get('rotation', [0, 0, 0, 1])
        s = node.get('scale', [1, 1, 1])
        t = node.get('translation', [0, 0, 0])
        r = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
             [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
             [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
        return [[r[i][j] * s[j] for j in range(3)] + [t[i]] for i in range(3)]

    objs = []
    for node in js.get('nodes', []):
        if 'mesh' not in node:
            continue
        m = mat(node)
        tris = []
        for p in js['meshes'][node['mesh']]['primitives']:
            # glTF es Y-arriba; se vuelve a Z-arriba, el sistema de Blender.
            pos = [(lambda v: (v[0], -v[2], v[1]))(
                       tuple(sum(m[i][j] * q[j] for j in range(3)) + m[i][3] for i in range(3)))
                   for q in read(p['attributes']['POSITION'])]
            idx = [i[0] for i in read(p['indices'])] if 'indices' in p else list(range(len(pos)))
            tris += [(pos[idx[i]], pos[idx[i + 1]], pos[idx[i + 2]]) for i in range(0, len(idx), 3)]
        objs.append((node.get('name', '?'), tris, node.get('extras') or {}))
    return objs


# --- comprobaciones por objeto ---------------------------------------------
def weld(tris):
    """Une vertices coincidentes y devuelve (vertices, caras por indice)."""
    verts, faces = [], []
    for tri in tris:
        f = []
        for p in tri:
            for i, q in enumerate(verts):
                if abs(p[0] - q[0]) < TOL_WELD_M and abs(p[1] - q[1]) < TOL_WELD_M \
                        and abs(p[2] - q[2]) < TOL_WELD_M:
                    f.append(i)
                    break
            else:
                verts.append(p)
                f.append(len(verts) - 1)
        if len(set(f)) == 3:
            faces.append(tuple(f))
    return verts, faces


def check_mesh(verts, faces):
    """(cerrada, normales_fuera, concavidad_m, alabeo_m, volumen_m3).

    Un vertice por delante del plano de una cara rompe la convexidad, por dos
    causas que se arreglan distinto. Si es la esquina opuesta de un triangulo
    vecino, la cara de esos dos triangulos esta ALABEADA: la pieza es convexa
    salvo ese pliegue, y se arregla aplanando la cara. Cualquier otro vertice es
    una esquina entrante de verdad (pieza en L o escalonada): CONCAVIDAD, y hay
    que partir la pieza.
    """
    usadas, vecino = {}, {}
    for f in faces:
        for k in range(3):
            a, b = f[k], f[(k + 1) % 3]
            usadas[(a, b)] = usadas.get((a, b), 0) + 1
            vecino.setdefault((min(a, b), max(a, b)), []).append(f)
    cerrada = all(c == 1 and usadas.get((b, a), 0) == 1 for (a, b), c in usadas.items())
    vol = sum(dot(verts[f[0]], cross(verts[f[1]], verts[f[2]])) / 6.0 for f in faces)

    warp = concav = 0.0
    for f in faces:
        n = norm(cross(sub(verts[f[1]], verts[f[0]]), sub(verts[f[2]], verts[f[0]])))
        opuestos = {i for k in range(3)
                    for g in vecino[(min(f[k], f[(k + 1) % 3]), max(f[k], f[(k + 1) % 3]))]
                    if g != f for i in g if i not in (f[k], f[(k + 1) % 3])}
        for i, v in enumerate(verts):
            fuera = dot(n, sub(v, verts[f[0]]))
            if fuera > TOL_PLANE_M:
                if i in opuestos:
                    warp = max(warp, fuera)
                else:
                    concav = max(concav, fuera)
    return cerrada, vol > 0, concav, warp, abs(vol)


def geom_thickness(verts, faces):
    """Separacion entre el par de caras paralelas mas proximo, en mm."""
    grupos = {}
    for f in faces:
        n = norm(cross(sub(verts[f[1]], verts[f[0]]), sub(verts[f[2]], verts[f[0]])))
        for key in grupos:
            if dot(key, n) > 0.9999:
                break
        else:
            grupos[n] = verts[f[0]]
    seps = [abs(dot(sub(grupos[m], grupos[n]), n)) for n in grupos for m in grupos
            if dot(n, m) < -0.9999]
    seps = [s for s in seps if s > 1e-6]
    return min(seps) * 1000.0 if seps else None


def check_overlaps(objs, n=14):
    """Rejilla de rayos en los tres ejes: {(a, b): solape maximo en m}. Con el
    camino medido en la geometria, un solape se contaria dos veces."""
    pts = [p for _, tris, _ in objs for t in tris for p in t]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    peor = {}
    for eje in range(3):
        d = tuple(1.0 if i == eje else 0.0 for i in range(3))
        a, b = [i for i in range(3) if i != eje]
        for ia in range(n):
            for ib in range(n):
                o = [0.0, 0.0, 0.0]
                o[eje] = lo[eje] - 1.0
                o[a] = lo[a] + (hi[a] - lo[a]) * (ia + 0.5) / n
                o[b] = lo[b] + (hi[b] - lo[b]) * (ib + 0.5) / n
                tramos = []
                for nombre, tris, _ in objs:
                    ts = [t for t in (ray_tri(tuple(o), d, tr) for tr in tris) if t is not None]
                    if len(ts) >= 2:
                        tramos.append((nombre, min(ts), max(ts)))
                for i, (n1, s1, e1) in enumerate(tramos):
                    for n2, s2, e2 in tramos[i + 1:]:
                        ov = min(e1, e2) - max(s1, s2)
                        if ov > TOL_OVERLAP_M:
                            k = tuple(sorted((n1, n2)))
                            peor[k] = max(peor.get(k, 0.0), ov)
    return peor


# --- principal --------------------------------------------------------------
def main(glb, data_dir):
    with open(os.path.join(data_dir, 'materials.csv'), newline='', encoding='utf-8') as f:
        materiales = {r['id'].strip() for r in csv.DictReader(f)}
    objs = load(glb)
    print(f"{len(objs)} objetos en {os.path.basename(glb)}\n")
    errores, avisos, filas, vistos = [], [], [], set()

    for nombre, tris, ex in objs:
        if nombre in vistos:
            errores.append(f"nombre repetido: {nombre}")   # disparo.py indexa por nombre
        vistos.add(nombre)
        es_placa, es_mod = 'Thickness_mm' in ex, 'Module_Type' in ex
        if es_placa == es_mod:
            errores.append(f"{nombre}: necesita Thickness_mm (placa) o Module_Type (modulo), "
                           f"uno de los dos")
            continue
        mat = ex.get('Armour_Material')
        if mat not in materiales:
            errores.append(f"{nombre}: material {mat!r} no esta en materials.csv")
        if es_mod and not isinstance(ex.get('Health'), (int, float)):
            errores.append(f"{nombre}: modulo sin Health numerico")

        verts, faces = weld(tris)
        cerrada, fuera, concav, warp, vol = check_mesh(verts, faces)
        if not cerrada:
            errores.append(f"{nombre}: malla abierta (aristas sin pareja)")
        if not fuera:
            errores.append(f"{nombre}: normales hacia dentro")
        if concav > TOL_CONCAV_M:
            errores.append(f"{nombre}: concavo {concav * 1000:.2f} mm; el camino se mide de mas "
                           f"(§3.1). Partir en piezas convexas")
        elif warp > TOL_WARP_M:
            avisos.append(f"{nombre}: cara alabeada hasta {warp * 1000:.2f} mm; solo afecta "
                          f"a los rayos que pasan por ese borde")

        gt = geom_thickness(verts, faces)
        if es_placa:
            pt = float(ex['Thickness_mm'])
            if gt is not None and abs(gt - pt) > TOL_THICKNESS_MM:
                errores.append(f"{nombre}: espesor {gt:.2f} mm vs Thickness_mm {pt}")
            filas.append((nombre, f"{pt:g}", f"{gt:.2f}" if gt else "-", mat, vol))
        else:
            filas.append((nombre, "-", f"{gt:.2f}" if gt else "-",
                          f"{ex['Module_Type']}/{ex.get('Health')}", vol))

    for (a, b), ov in sorted(check_overlaps(objs).items(), key=lambda kv: -kv[1]):
        errores.append(f"se solapan {a} y {b}: hasta {ov * 1000:.1f} mm de camino contado dos veces")

    w = max(len(r[0]) for r in filas) if filas else 10
    print(f"{'objeto'.ljust(w)}  {'prop':>6}  {'geom':>7}  material/tipo      cm3")
    for r in filas:
        print(f"{r[0].ljust(w)}  {r[1]:>6}  {r[2]:>7}  {r[3]:<17} {r[4] * 1e6:>6.0f}")
    print()
    for e in errores:
        print(f"ERROR  {e}")
    for x in avisos:
        print(f"aviso  {x}")
    print(f"\n{len(errores)} errores, {len(avisos)} avisos")
    return 1 if errores else 0


def _autoprueba():
    """Separacion alabeo/concavidad con tres casos de respuesta conocida."""
    def prisma(perfil):
        v = [(x, y, z) for (x, y) in perfil for z in (0.0, 1.0)]
        n, f = len(perfil), []
        for i in range(n):                       # laterales
            a0, a1, b0, b1 = 2 * i, 2 * i + 1, 2 * ((i + 1) % n), 2 * ((i + 1) % n) + 1
            f += [(a0, b0, b1), (a0, b1, a1)]
        for i in range(1, n - 1):                # tapas
            f += [(0, 2 * (i + 1), 2 * i), (1, 2 * i + 1, 2 * (i + 1) + 1)]
        if sum(dot(v[a], cross(v[b], v[c])) for a, b, c in f) < 0:
            f = [(a, c, b) for a, b, c in f]     # normales hacia fuera
        return v, f

    v, f = prisma([(0, 0), (1, 0), (1, 1), (0, 1)])
    cerrada, fuera, c, w, vol = check_mesh(v, f)
    assert cerrada and fuera and c < 1e-9 and w < 1e-9 and abs(vol - 1.0) < 1e-9
    assert abs(geom_thickness(v, f) - 1000.0) < 1e-6
    v2 = list(v)
    v2[7] = (v2[7][0], v2[7][1], v2[7][2] + 0.05)   # una esquina fuera del plano
    _, _, c, w, _ = check_mesh(v2, f)
    assert c < 1e-9 and w > 1e-3, f"caja alabeada: {c}, {w}"
    v, f = prisma([(0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)])
    assert check_mesh(v, f)[2] > 0.1, "prisma en L"
    print("selftest OK")


if __name__ == '__main__':
    args = sys.argv[1:]
    if args[:1] == ['--selftest']:
        _autoprueba()
        sys.exit(0)
    raiz = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    glb = args[0] if args else os.path.join(raiz, 'models', 'Pz IV H.glb')
    data = args[1] if len(args) > 1 else os.path.join(raiz, 'data')
    sys.exit(main(glb, data))
