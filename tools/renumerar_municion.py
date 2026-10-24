"""Renumera los cartuchos de municion para que la numeracion sea continua.

Util despues de borrar o anadir cartuchos, cuando quedan huecos o saltos en los
nombres. Renombra en dos pasadas con un prefijo temporal, asi que no hay
colisiones aunque los numeros nuevos pisen los viejos.

MODO = "numero"    conserva el orden actual y solo cierra los huecos.
                   Es el cambio minimo: el que ya estaba bien casi no se mueve.
MODO = "posicion"  renumera de delante a atras, de abajo a arriba y de
                   izquierda a derecha. Mas util a largo plazo, porque el
                   numero te dice donde esta el cartucho, pero renombra todo.

Pestana Scripting -> New -> pegar -> Run.
"""
import bpy
import re

PREFIJO = "MOD_Ammo_Shell_"
MODO = "numero"          # "numero" o "posicion"
DIGITOS = 2              # 2 -> _01 ; 3 -> _001
ESPERADOS = 87           # carga historica del Pz IV H; 0 para no comprobar
TEMP = "__renum_tmp_"


def centro(ob):
    b = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return (sum(p.x for p in b) / len(b),
            sum(p.y for p in b) / len(b),
            sum(p.z for p in b) / len(b))


if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

pat = re.compile(re.escape(PREFIJO) + r"(\d+)$")
cart = []
for ob in bpy.data.objects:
    m = pat.match(ob.name)
    if m and ob.type == 'MESH':
        cart.append((ob, int(m.group(1))))

if not cart:
    raise SystemExit(f"no hay ningun objeto {PREFIJO}NN")

print()
viejos = sorted(n for _, n in cart)
huecos = [i for i in range(min(viejos), max(viejos) + 1) if i not in viejos]
dup = sorted({n for n in viejos if viejos.count(n) > 1})
print(f"{len(cart)} cartuchos, numeracion actual {min(viejos)}..{max(viejos)}")
print(f"  huecos:      {huecos or 'ninguno'}")
print(f"  duplicados:  {dup or 'ninguno'}")

if ESPERADOS and len(cart) != ESPERADOS:
    print(f"\n  !! hay {len(cart)} cartuchos y se esperaban {ESPERADOS} "
          f"({len(cart) - ESPERADOS:+d})")
    print("     renumerar no arregla eso: sobra o falta municion.")

if MODO == "posicion":
    # delante->atras, abajo->arriba, izquierda->derecha
    cart.sort(key=lambda t: tuple(round(c, 4) for c in
                                  (centro(t[0])[1], centro(t[0])[2],
                                   centro(t[0])[0])))
else:
    cart.sort(key=lambda t: t[1])

# pasada 1: a nombres temporales, para que no choquen con los definitivos
for i, (ob, _) in enumerate(cart):
    ob.name = f"{TEMP}{i}"
    ob.data.name = f"{TEMP}{i}"

# pasada 2: a los nombres finales
cambios = 0
for i, (ob, viejo) in enumerate(cart, start=1):
    nuevo = f"{PREFIJO}{i:0{DIGITOS}d}"
    if viejo != i:
        cambios += 1
    ob.name = nuevo
    ob.data.name = nuevo

print(f"\nmodo '{MODO}': renumerados 1..{len(cart)}, "
      f"{cambios} objetos cambian de numero")

# comprobacion final
ahora = sorted(int(pat.match(o.name).group(1))
               for o in bpy.data.objects if pat.match(o.name))
assert ahora == list(range(1, len(cart) + 1)), f"la renumeracion fallo: {ahora}"
print(f"comprobado: {PREFIJO}{1:0{DIGITOS}d} .. "
      f"{PREFIJO}{len(cart):0{DIGITOS}d}, sin huecos\n")
