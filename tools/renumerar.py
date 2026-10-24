"""Compacta la numeracion de una serie de objetos, sin huecos.

Caso de uso: MOD_Ammo_Shell_01..88 con el 24 vacio. Son 87 objetos, los 87
correctos, pero numerados hasta 88. Esto los renumera a 01..87.

POR QUE EN DOS PASADAS
----------------------
Si se renombra de uno en uno, Blender anade .001 cuando el nombre destino ya
existe, y acabas con MOD_Ammo_Shell_25.001. Renombrar en orden ascendente
funcionaria en este caso concreto, porque cada destino queda libre justo antes,
pero falla en cuanto hay dos huecos o el orden es otro. Dos pasadas con nombres
temporales es inmune a cualquier patron de huecos.

OJO: esto es puramente cosmetico. Segun modelo_balistico.md §2.4 el codigo
distingue los objetos por sus propiedades, no por el nombre; el prefijo es solo
una red de seguridad. El hueco no rompe nada. Lo que evita es la trampa de que
alguien cuente "01 a 88" y espere 88 proyectiles.

Pestana Scripting -> New -> pegar -> Run.
"""
import bpy
import re

# ----------------------------------------------------------------- parametros
PREFIJO = "MOD_Ammo_Shell_"
ANCHO = 2            # 2 -> 01, 3 -> 001
DESDE = 1            # primer numero de la serie nueva
SIMULAR = False      # True = solo informa, no renombra
# --------------------------------------------------------------------------

patron = re.compile(r"^" + re.escape(PREFIJO) + r"(\d+)$")

objs = []
for ob in bpy.data.objects:
    m = patron.match(ob.name)
    if m:
        objs.append((int(m.group(1)), ob))
objs.sort(key=lambda t: t[0])

if not objs:
    raise SystemExit(f"\nNo hay objetos que empiecen por {PREFIJO!r}.\n")

viejos = [n for n, _ in objs]
huecos = [k for k in range(min(viejos), max(viejos) + 1) if k not in viejos]
dup = sorted({k for k in viejos if viejos.count(k) > 1})

print()
print(f"{len(objs)} objetos con prefijo {PREFIJO!r}")
print(f"  numeracion actual: {min(viejos)} .. {max(viejos)}")
print(f"  huecos:            {huecos or 'ninguno'}")
print(f"  duplicados:        {dup or 'ninguno'}")

nuevos = list(range(DESDE, DESDE + len(objs)))
cambios = [(ob, f"{PREFIJO}{n:0{ANCHO}d}")
           for (_, ob), n in zip(objs, nuevos) if ob.name != f"{PREFIJO}{n:0{ANCHO}d}"]

if not cambios:
    print("\nNada que hacer: la numeracion ya es continua.\n")
    raise SystemExit

print(f"  numeracion nueva:  {min(nuevos)} .. {max(nuevos)}")
print(f"\n{len(cambios)} objetos a renombrar:")
for ob, nuevo in cambios[:6]:
    print(f"    {ob.name}  ->  {nuevo}")
if len(cambios) > 6:
    print(f"    ... y {len(cambios) - 6} mas")

if SIMULAR:
    print("\nSIMULAR = True, no se ha cambiado nada.\n")
    raise SystemExit

# Pasada 1: a nombres temporales que no pueden chocar con nada.
for i, (ob, _) in enumerate(cambios):
    ob.name = f"__renum_tmp_{i:04d}__"

# Pasada 2: a los nombres definitivos, ya libres.
for (ob, nuevo) in cambios:
    ob.name = nuevo

# Comprobacion: ni .001 ni huecos.
quedan = sorted(int(patron.match(o.name).group(1))
                for o in bpy.data.objects if patron.match(o.name))
sucios = [o.name for o in bpy.data.objects
          if o.name.startswith(PREFIJO) and not patron.match(o.name)]

print(f"\nhecho: {len(quedan)} objetos, {min(quedan)} .. {max(quedan)}")
print(f"  huecos: {[k for k in range(min(quedan), max(quedan) + 1) if k not in quedan] or 'ninguno'}")
if sucios:
    print(f"  CUIDADO, nombres con sufijo raro: {sucios}")
else:
    print("  sin sufijos .001")
print("\npasa tools/validate_glb.py despues\n")
