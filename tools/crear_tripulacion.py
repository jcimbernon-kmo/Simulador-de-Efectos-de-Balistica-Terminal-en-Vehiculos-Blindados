"""Crea la tripulacion sentada como modulos convexos, en Blender.

Cada tripulante son dos objetos: torso+cabeza y piernas. Ambos se generan como
ENVOLVENTE CONVEXA de puntos anatomicos, asi que la convexidad esta garantizada
por construccion y el trazador de rayos puede usar primera entrada / ultima
salida sin medir de mas.

Pestana Scripting -> New -> pegar -> Run.
"""
import bmesh
import bpy
import math

# ---------------------------------------------------------------- parametros
HEALTH_TORSO = 80.0        # julios; umbral de incapacitacion por fragmento
HEALTH_LEGS = 80.0
MATERIAL = "Flesh"         # tiene que existir en data/materials.csv
COLECCION = "Modules"

# nombre, cadera (x, y, z), reclinacion en grados
# +X es el lado izquierdo del vehiculo, -Y el morro.
TRIPULACION = [
    ("driver", (0.45, 0.75, 1.30), 20),
    ("radio",  (-0.45, 0.75, 1.30), 20),
]

# Torso: (semiancho, semiprofundidad, altura sobre la cadera)
TORSO = [
    (0.190, 0.140, 0.00),   # cadera
    (0.225, 0.135, 0.55),   # hombros
    (0.105, 0.110, 0.68),   # cuello
    (0.095, 0.105, 0.90),   # coronilla
]

# Piernas: (semiancho, y respecto a la cadera, z minima, z maxima)
PIERNAS = [
    (0.190,  0.00, -0.10, 0.09),    # cadera
    (0.175, -0.45, -0.13, 0.03),    # rodilla
    (0.150, -0.82, -0.155, -0.03),  # pie
]
# ---------------------------------------------------------------------------


def reclinar(p, grados):
    """Gira alrededor de X: al subir, el punto se va hacia atras (+Y)."""
    t = math.radians(grados)
    x, y, z = p
    return (x, y * math.cos(t) + z * math.sin(t), -y * math.sin(t) + z * math.cos(t))


def puntos_torso(cadera, grados):
    out = []
    for w, d, h in TORSO:
        for sx in (-1, 1):
            for sy in (-1, 1):
                p = reclinar((sx * w, sy * d, h), grados)
                out.append((cadera[0] + p[0], cadera[1] + p[1], cadera[2] + p[2]))
    return out


def puntos_piernas(cadera):
    out = []
    for w, y, z0, z1 in PIERNAS:
        for sx in (-1, 1):
            for z in (z0, z1):
                out.append((cadera[0] + sx * w, cadera[1] + y, cadera[2] + z))
    return out


def envolvente(nombre, puntos, props, coleccion):
    bm = bmesh.new()
    for p in puntos:
        bm.verts.new(p)
    bm.verts.ensure_lookup_table()
    r = bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
    basura = list(set(r.get("geom_unused", []) + r.get("geom_interior", [])))
    if basura:
        bmesh.ops.delete(bm, geom=basura, context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nombre, me)
    coleccion.objects.link(ob)
    for k, v in props.items():
        ob[k] = v
    return ob


col = bpy.data.collections.get(COLECCION)
if col is None:
    col = bpy.data.collections.new(COLECCION)
    bpy.context.scene.collection.children.link(col)

print("\n--- tripulacion creada ---")
for nombre, cadera, grados in TRIPULACION:
    for sufijo, pts, vida in (
        ("torso", puntos_torso(cadera, grados), HEALTH_TORSO),
        ("legs", puntos_piernas(cadera), HEALTH_LEGS),
    ):
        ob = envolvente(
            f"MOD_{nombre}_{sufijo}", pts,
            {"Module_Type": "crew", "Health": vida, "Armour_Material": MATERIAL},
            col)
        d = ob.dimensions
        b = [ob.matrix_world @ v.co for v in ob.data.vertices]
        print(f"{ob.name:<22} {len(ob.data.vertices):>3} vert  "
              f"{d.x:.3f} x {d.y:.3f} x {d.z:.3f} m   "
              f"Z {min(p.z for p in b):.3f}..{max(p.z for p in b):.3f}  "
              f"Y {min(p.y for p in b):.3f}..{max(p.y for p in b):.3f}")
print("--- pasa ahora tools/validate_glb.py para comprobar solapes ---\n")
