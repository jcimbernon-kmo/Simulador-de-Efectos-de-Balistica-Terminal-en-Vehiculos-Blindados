"""Prueba de extremo a extremo: carga un .glb, lanza un rayo y lista lo que atraviesa.

Sin motor y sin dependencias: solo la biblioteca estandar.
Uso:  python raycast_test.py modelo.glb
      python raycast_test.py --selftest
"""
import json
import math
import os
import struct
import sys

# --- el disparo -------------------------------------------------------------
ORIGIN = (0.50, -2.00, 1.90)   # coordenadas de Blender (Z arriba, morro a -Y)
DIRECTION = (0.0, 1.0, 0.0)

# --- algebra minima ---------------------------------------------------------
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1],
                         a[2] * b[0] - a[0] * b[2],
                         a[0] * b[1] - a[1] * b[0])
def norm(a):
    n = math.sqrt(dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n) if n else a
def along(o, d, t): return (o[0] + d[0] * t, o[1] + d[1] * t, o[2] + d[2] * t)

EPS = 1e-9

def ray_triangle(orig, dirn, tri):
    """Moller-Trumbore. Devuelve la distancia t, o None si no hay impacto."""
    e1, e2 = sub(tri[1], tri[0]), sub(tri[2], tri[0])
    h = cross(dirn, e2)
    a = dot(e1, h)
    if abs(a) < EPS:                      # rayo paralelo al triangulo
        return None
    f = 1.0 / a
    s = sub(orig, tri[0])
    u = f * dot(s, h)
    if u < -EPS or u > 1 + EPS:
        return None
    q = cross(s, e1)
    v = f * dot(dirn, q)
    if v < -EPS or u + v > 1 + EPS:
        return None
    t = f * dot(e2, q)
    return t if t > EPS else None

# --- lectura del .glb -------------------------------------------------------
_COMP = {5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2),
         5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
_NUM = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}

def load_glb(path):
    """Devuelve [(nombre, [triangulos], extras)] en coordenadas de Blender."""
    data = open(path, 'rb').read()
    if data[:4] != b'glTF':
        raise ValueError('no es un .glb binario')
    off, js, bin_ = 12, None, b''
    while off < len(data):
        length, kind = struct.unpack_from('<II', data, off)
        off += 8
        chunk = data[off:off + length]
        off += length
        if kind == 0x4E4F534A:
            js = json.loads(chunk)
        elif kind == 0x004E4942:
            bin_ = chunk

    def read(idx):
        acc = js['accessors'][idx]
        view = js['bufferViews'][acc['bufferView']]
        fmt, size = _COMP[acc['componentType']]
        n = _NUM[acc['type']]
        base = view.get('byteOffset', 0) + acc.get('byteOffset', 0)
        stride = view.get('byteStride') or size * n
        return [struct.unpack_from('<' + fmt * n, bin_, base + i * stride)
                for i in range(acc['count'])]

    def matrix(node):
        if 'matrix' in node:                       # columna a columna
            m = node['matrix']
            return [[m[0], m[4], m[8], m[12]],
                    [m[1], m[5], m[9], m[13]],
                    [m[2], m[6], m[10], m[14]]]
        x, y, z, w = node.get('rotation', [0, 0, 0, 1])
        s = node.get('scale', [1, 1, 1])
        t = node.get('translation', [0, 0, 0])
        r = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
             [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
             [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
        return [[r[i][j] * s[j] for j in range(3)] + [t[i]] for i in range(3)]

    def apply(m, v):
        return tuple(sum(m[i][j] * v[j] for j in range(3)) + m[i][3]
                     for i in range(3))

    # glTF usa Y arriba; Blender usa Z arriba
    def to_blender(p): return (p[0], -p[2], p[1])

    out = []
    for node in js.get('nodes', []):
        if 'mesh' not in node:
            continue
        m = matrix(node)
        tris = []
        for prim in js['meshes'][node['mesh']]['primitives']:
            pos = [to_blender(apply(m, v)) for v in read(prim['attributes']['POSITION'])]
            idx = ([i[0] for i in read(prim['indices'])] if 'indices' in prim
                   else list(range(len(pos))))
            tris += [(pos[idx[i]], pos[idx[i + 1]], pos[idx[i + 2]])
                     for i in range(0, len(idx), 3)]
        out.append((node.get('name', '?'), tris, node.get('extras') or {}))
    return out

# --- el disparo propiamente dicho ------------------------------------------
def shoot(objects, orig, dirn):
    """Para cada objeto atravesado: entrada, salida, camino recorrido y angulo."""
    dirn = norm(dirn)
    hits = []
    for name, tris, extras in objects:
        ts = []
        for tri in tris:
            t = ray_triangle(orig, dirn, tri)
            if t is not None:
                ts.append((t, tri))
        if len(ts) < 2:                 # un solo impacto = roza un borde
            continue
        ts.sort(key=lambda it: it[0])
        t_in, tri_in = ts[0]
        t_out = ts[-1][0]
        n = norm(cross(sub(tri_in[1], tri_in[0]), sub(tri_in[2], tri_in[0])))
        cos = abs(dot(n, dirn))
        hits.append({
            'name': name,
            'entry': along(orig, dirn, t_in),
            'exit': along(orig, dirn, t_out),
            'path_mm': (t_out - t_in) * 1000.0,
            'angle_deg': math.degrees(math.acos(max(-1.0, min(1.0, cos)))),
            'extras': extras,
        })
    hits.sort(key=lambda h: h['entry'][1] * dirn[1] + h['entry'][0] * dirn[0]
                            + h['entry'][2] * dirn[2])
    return hits

def report(hits):
    if not hits:
        print('El rayo no toca nada.')
        return
    for i, h in enumerate(hits, 1):
        e, x = h['entry'], h['exit']
        print(f"{i}. {h['name']}")
        print(f"   entrada  ({e[0]:+.5f}, {e[1]:+.5f}, {e[2]:+.5f})")
        print(f"   salida   ({x[0]:+.5f}, {x[1]:+.5f}, {x[2]:+.5f})")
        print(f"   camino   {h['path_mm']:.2f} mm")
        print(f"   angulo   {h['angle_deg']:.2f}deg respecto a la normal")
        if h['extras']:
            print(f"   props    {h['extras']}")

# --- comprobacion -----------------------------------------------------------
def selftest():
    tri = ((-1.0, 1.0, -1.0), (1.0, 1.0, -1.0), (0.0, 1.0, 1.0))
    assert abs(ray_triangle((0, 0, 0), (0, 1, 0), tri) - 1.0) < 1e-9
    assert ray_triangle((0, 0, 0), (0, -1, 0), tri) is None      # hacia atras
    assert ray_triangle((0, 0, 5), (0, 1, 0), tri) is None       # fuera
    assert ray_triangle((0, 0, 0), (1, 0, 0), tri) is None       # paralelo
    print('selftest OK')

if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
        sys.exit()
    args = sys.argv[1:]
    if not args:
        import glob
        for pattern in ('models/*.glb', '*.glb', '../models/*.glb'):
            found = sorted(glob.glob(pattern))
            if len(found) == 1:
                args = [found[0]]
                print(f"(sin argumentos: uso {found[0]})\n")
                break
        else:
            print(__doc__)
            print("Falta la ruta del .glb. Ejecutalo desde la raiz del repo:")
            print('  python tools/raycast_test.py "models/Pz IV H.glb"')
            sys.exit(2)
    report(shoot(load_glb(args[0]), ORIGIN, DIRECTION))
