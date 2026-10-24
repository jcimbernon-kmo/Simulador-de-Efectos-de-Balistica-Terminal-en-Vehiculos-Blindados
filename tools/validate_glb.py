"""Valida el .glb del vehiculo antes de usarlo en el simulador.

Comprueba, por objeto: propiedades presentes y coherentes, malla cerrada,
normales hacia fuera, convexidad, y espesor geometrico frente a Thickness_mm.
Comprueba, en conjunto: nombres duplicados, simetria en X y materiales
declarados en data/materials.csv.

Uso:  python validate_glb.py modelo.glb [carpeta_de_datos]
Devuelve codigo de salida 1 si hay algun ERROR.
"""
import csv
import json
import math
import os
import struct
import sys

TOL_THICKNESS_MM = 0.5     # margen entre geometria y propiedad
TOL_PLANE_M = 1e-5         # margen de convexidad
TOL_WELD_M = 5e-4          # a partir de aqui dos vertices son el mismo

# --- algebra ---------------------------------------------------------------
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1],
                         a[2] * b[0] - a[0] * b[2],
                         a[0] * b[1] - a[1] * b[0])
def norm(a):
    n = math.sqrt(dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-12 else (0.0, 0.0, 0.0)

# --- lectura ---------------------------------------------------------------
_COMP = {5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2),
         5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
_NUM = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}

def load(path):
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
        return [struct.unpack_from('<' + f * n, bin_, b + i * st)
                for i in range(a['count'])]

    def mat(node):
        if 'matrix' in node:
            m = node['matrix']
            return [[m[0], m[4], m[8], m[12]], [m[1], m[5], m[9], m[13]],
                    [m[2], m[6], m[10], m[14]]]
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
            pos = [(lambda v: (v[0], -v[2], v[1]))(
                       tuple(sum(m[i][j] * q[j] for j in range(3)) + m[i][3]
                             for i in range(3)))
                   for q in read(p['attributes']['POSITION'])]
            idx = ([i[0] for i in read(p['indices'])] if 'indices' in p
                   else list(range(len(pos))))
            tris += [(pos[idx[i]], pos[idx[i + 1]], pos[idx[i + 2]])
                     for i in range(0, len(idx), 3)]
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
    """(cerrada, normales_fuera, convexa, volumen_m3)"""
    used = {}
    for f in faces:
        for i in range(3):
            e = (f[i], f[(i + 1) % 3])
            used[e] = used.get(e, 0) + 1
    closed = all(c == 1 and used.get((b, a), 0) == 1 for (a, b), c in used.items())

    vol = sum(dot(verts[f[0]], cross(verts[f[1]], verts[f[2]])) / 6.0
              for f in faces)

    convex = True
    for f in faces:
        n = norm(cross(sub(verts[f[1]], verts[f[0]]), sub(verts[f[2]], verts[f[0]])))
        p0 = verts[f[0]]
        if max(dot(n, sub(v, p0)) for v in verts) > TOL_PLANE_M:
            convex = False
            break
    return closed, vol > 0, convex, abs(vol)

def geom_thickness(verts, faces):
    """Separacion entre el par de caras paralelas mas proximo, en mm."""
    groups = {}
    for f in faces:
        n = norm(cross(sub(verts[f[1]], verts[f[0]]), sub(verts[f[2]], verts[f[0]])))
        for key in groups:
            if dot(key, n) > 0.9999:
                groups[key].append(f[0])
                break
        else:
            groups[n] = [f[0]]
    best = None
    for n in groups:
        for m in groups:
            if dot(n, m) < -0.9999:
                d = abs(dot(sub(verts[groups[m][0]], verts[groups[n][0]]), n))
                if d > 1e-6 and (best is None or d < best):
                    best = d
    return best * 1000.0 if best else None

def ray_tri(o, d, t):
    e1, e2 = sub(t[1], t[0]), sub(t[2], t[0])
    h = cross(d, e2)
    a = dot(e1, h)
    if abs(a) < 1e-12:
        return None
    f = 1.0 / a
    s_ = sub(o, t[0])
    u = f * dot(s_, h)
    if u < -1e-9 or u > 1 + 1e-9:
        return None
    q = cross(s_, e1)
    v = f * dot(d, q)
    if v < -1e-9 or u + v > 1 + 1e-9:
        return None
    return f * dot(e2, q)


def check_overlaps(objs, n=14):
    """Busca objetos que se solapen: con el calculo por geometria, el camino
    en la zona solapada se contaria dos veces."""
    pts = [p for _, tris, _ in objs for t in tris for p in t]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    worst = {}
    for axis in range(3):
        d = tuple(1.0 if i == axis else 0.0 for i in range(3))
        a, b = [i for i in range(3) if i != axis]
        for ia in range(n):
            for ib in range(n):
                o = [0.0, 0.0, 0.0]
                o[axis] = lo[axis] - 1.0
                o[a] = lo[a] + (hi[a] - lo[a]) * (ia + 0.5) / n
                o[b] = lo[b] + (hi[b] - lo[b]) * (ib + 0.5) / n
                spans = []
                for name, tris, _ in objs:
                    ts = [t for t in (ray_tri(tuple(o), d, tr) for tr in tris)
                          if t is not None]
                    if len(ts) >= 2:
                        spans.append((name, min(ts), max(ts)))
                for i in range(len(spans)):
                    for j in range(i + 1, len(spans)):
                        n1, s1, e1_ = spans[i]
                        n2, s2, e2_ = spans[j]
                        ov = min(e1_, e2_) - max(s1, s2)
                        if ov > 1e-4:          # 0,1 mm
                            k = tuple(sorted((n1, n2)))
                            worst[k] = max(worst.get(k, 0.0), ov)
    return worst


# --- principal --------------------------------------------------------------
def main(glb, data_dir):
    errors, warns = [], []
    materials = set()
    mpath = os.path.join(data_dir, 'materials.csv')
    if os.path.exists(mpath):
        with open(mpath, newline='', encoding='utf-8') as f:
            materials = {r['id'].strip() for r in csv.DictReader(f)}
    else:
        warns.append(f"no encuentro {mpath}; no compruebo materiales")

    objs = load(glb)
    print(f"{len(objs)} objetos en {os.path.basename(glb)}\n")
    names, rows = {}, []

    for name, tris, ex in objs:
        names[name] = names.get(name, 0) + 1
        if name.endswith(('.001', '.002', '.003')):
            warns.append(f"{name}: nombre de duplicado de Blender")

        is_arm = 'Thickness_mm' in ex
        is_mod = 'Health' in ex or 'Module_Type' in ex
        if not is_arm and not is_mod:
            errors.append(f"{name}: sin propiedades; no deberia exportarse")
            continue
        if is_arm and is_mod:
            errors.append(f"{name}: tiene propiedades de placa y de modulo")

        mat = ex.get('Armour_Material')
        if not mat:
            errors.append(f"{name}: sin Armour_Material")
        elif materials and mat not in materials:
            errors.append(f"{name}: material '{mat}' no esta en materials.csv")

        if is_mod:
            if 'Module_Type' not in ex:
                errors.append(f"{name}: modulo sin Module_Type")
            if 'Health' not in ex:
                errors.append(f"{name}: modulo sin Health")
            elif not isinstance(ex['Health'], (int, float)):
                errors.append(f"{name}: Health no es numerico")
            if 'Thickness_mm' in ex:
                warns.append(f"{name}: modulo con Thickness_mm; lo da la geometria")

        verts, faces = weld(tris)
        closed, outward, convex, vol = check_mesh(verts, faces)
        if not closed:
            errors.append(f"{name}: malla abierta (aristas sin pareja)")
        if not outward:
            errors.append(f"{name}: normales hacia dentro")
        if not convex:
            warns.append(f"{name}: no convexo; entrada/salida del rayo no valen")

        gt = geom_thickness(verts, faces)
        if is_arm:
            pt = float(ex['Thickness_mm'])
            if gt is None:
                warns.append(f"{name}: sin caras paralelas; no puedo medir el espesor")
            elif abs(gt - pt) > TOL_THICKNESS_MM:
                errors.append(f"{name}: espesor {gt:.2f} mm vs Thickness_mm {pt}")
            rows.append((name, f"{pt:g}", f"{gt:.2f}" if gt else "-", mat or "-",
                         f"{vol * 1e6:.0f}"))
        else:
            rows.append((name, "-", f"{gt:.2f}" if gt else "-",
                         f"{ex.get('Module_Type', '?')}/{ex.get('Health', '?')}",
                         f"{vol * 1e6:.0f}"))

        xs = [v[0] for v in verts]
        if min(xs) < -1e-6 < 1e-6 < max(xs) and abs(min(xs) + max(xs)) > 1e-4:
            warns.append(f"{name}: cruza X=0 pero esta descentrado "
                         f"(centro {(min(xs)+max(xs))/2:+.4f})")

    for n, c in names.items():
        if c > 1:
            errors.append(f"nombre repetido {c} veces: {n}")

    for (a, b), ov in sorted(check_overlaps(objs).items(),
                             key=lambda kv: -kv[1]):
        errors.append(f"se solapan {a} y {b}: hasta {ov * 1000:.1f} mm "
                      f"de camino contado dos veces")

    w = max(len(r[0]) for r in rows) if rows else 10
    print(f"{'objeto'.ljust(w)}  {'prop':>6}  {'geom':>7}  material/tipo      cm3")
    for r in rows:
        print(f"{r[0].ljust(w)}  {r[1]:>6}  {r[2]:>7}  {r[3]:<17} {r[4]:>6}")

    print()
    for e in errors:
        print(f"ERROR  {e}")
    for x in warns:
        print(f"aviso  {x}")
    print(f"\n{len(errors)} errores, {len(warns)} avisos")
    return 1 if errors else 0


def _find_glb():
    """Si no dan ruta, busca un unico .glb en models/ o en el directorio actual."""
    import glob
    for pattern in ('models/*.glb', '*.glb', '../models/*.glb'):
        found = sorted(glob.glob(pattern))
        if len(found) == 1:
            return found[0]
    return None


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        guess = _find_glb()
        if guess is None:
            print(__doc__)
            print("Falta la ruta del .glb. Ejecutalo desde la raiz del repo:")
            print('  python tools/validate_glb.py "models/Pz IV H.glb" data')
            sys.exit(2)
        args = [guess]
        print(f"(sin argumentos: uso {guess})\n")
    glb = args[0]
    if not os.path.exists(glb):
        print(f"No existe: {glb}")
        sys.exit(2)
    data = args[1] if len(args) > 1 else ('data' if os.path.isdir('data') else
                                          '../data' if os.path.isdir('../data') else 'data')
    sys.exit(main(glb, data))
