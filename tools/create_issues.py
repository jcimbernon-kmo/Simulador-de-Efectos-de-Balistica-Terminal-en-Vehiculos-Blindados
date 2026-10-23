"""Crea en GitHub los issues del plan de trabajo.

Requiere la CLI de GitHub autenticada:  gh auth login
Uso:   python tools/create_issues.py --dry-run     ver que haria
       python tools/create_issues.py               crearlos

No duplica: antes de crear comprueba los titulos que ya existen.
"""
import json
import subprocess
import sys

DOC = 'docs/modelo_balistico.md'

LABELS = [
    ('bloqueante', 'b60205', 'Impide avanzar con el nucleo'),
    ('datos',      '0e8a16', 'Tablas de data/'),
    ('modelo',     '1d76db', 'Modelado 3D en Blender'),
    ('nucleo',     '5319e7', 'Motor de calculo balistico'),
    ('validacion', 'fbca04', 'Pruebas y calibracion'),
    ('proyecto',   'c5def5', 'Gestion del TFG'),
]

ISSUES = [
    # --- bloqueante -------------------------------------------------------
    ("Unificar el ID del proyectil HEAT",
     "`projectiles.csv` usa `Gr38HlC_75` y `penetration.csv` usa `Gr38HlC_75_L48`. "
     "No enlazan, asi que el HEAT se queda sin datos de proyectil. "
     "`tools/ballistic_data.py` ya lo detecta y avisa.",
     ['bloqueante', 'datos']),

    ("Rellenar thickness_basis = nominal en penetration.csv",
     "Confirmado que los milimetros de las tablas son espesor nominal, pero la columna "
     f"sigue vacia y el cargador lo esta suponiendo. Ver {DOC} seccion 3.4.",
     ['bloqueante', 'datos']),

    ("Determinar el criterio de perforacion de cada fuente",
     "Una fuente con limite del 50 % da numeros mas optimistas que una de perforacion "
     "completa. Mezclarlas sesga la calibracion entera. Rellenar la columna `criterion` "
     "por fila y normalizar a un unico criterio.",
     ['bloqueante', 'datos']),

    ("Decidir la unidad de Health",
     "En julios equivalentes, `k_dano` vale 1 y no hay constante que justificar. "
     "En puntos arbitrarios, hay un parametro libre por tipo de modulo que defender. "
     f"Ver {DOC} seccion 3.7.",
     ['bloqueante', 'nucleo']),

    ("Elegir la distribucion de tamanos de fragmento",
     "Con la misma energia total, cuatro trozos gordos y cien esquirlas hacen cosas muy "
     "distintas dentro del tanque. Hace falta una distribucion de masas (tipo Mott, "
     "normalizada a la masa arrancada) y declararla como supuesto. "
     "El numero de rayos es resolucion numerica, no fisica.",
     ['bloqueante', 'nucleo']),

    # --- datos ------------------------------------------------------------
    ("Anadir core_mass_kg del APCR",
     "Los 4,1 kg del PzGr. 40 son el proyectil entero; lo que penetra es solo el nucleo "
     "de tungsteno. Sin esa masa, la razon de masas del spall da una fraccion demasiado "
     "baja. `mass_kg` se mantiene como dato historico.",
     ['datos']),

    ("Completar explosivo y espoleta del PzGr. 39",
     "Es APCBC-HE, o sea que se comporta como APHE. Faltan `fuze_delay_ms` y confirmar "
     "`explosive_mass_g` (16,4 g equivalentes de TNT).",
     ['datos']),

    ("Completar explosive_mass_g del Gr. 38 Hl/C",
     "Vacio en `projectiles.csv`.",
     ['datos']),

    ("Anadir el material Propellant y unificar mayusculas",
     "Falta `Propellant` para el modulo de municion. Ademas, los ids de `materials.csv` "
     "(`Flesh`, `Cast_Iron`) tienen que coincidir exactamente con lo que se escriba en "
     "`Armour_Material` en Blender: la comparacion distingue mayusculas.",
     ['datos', 'modelo']),

    ("Rellenar la columna spall de materials.csv",
     "`spall` es la fragilidad del material (0-1). El reparto de energia sale de la razon "
     "de masas implementada en `spall_fraction()`. Orden esperable: RHA ductil bajo, "
     "blindaje fundido o de cara endurecida mas alto, carne practicamente cero. "
     f"Ver {DOC} seccion 6.",
     ['datos']),

    ("Conseguir la penetracion a 60 grados",
     "La columna esta vacia y es la mas importante para un simulador de blindaje "
     "inclinado: la mayoria de impactos reales son oblicuos. Sin ella, todo lo que pase "
     "de 30 grados es extrapolacion, y el cargador lo marca como tal.",
     ['datos']),

    ("Anadir source_id por fila en penetration.csv",
     "Las fuentes van unificadas en el documento, pero hace falta trazabilidad por fila. "
     "Un codigo corto que apunte a la lista del documento basta y no repite citas largas.",
     ['datos']),

    ("Marcar como derivados los valores angulados del HEAT",
     "Los 45 mm a 60 grados son exactamente 90 x cos 60. La derivacion es correcta porque "
     "un chorro no tiene efecto de inclinacion, solo linea de vision, pero no es un dato "
     "de fuente y no debe presentarse como tal. Alternativa: dejar solo las filas de "
     "0 grados y que el angulo lo resuelva la geometria.",
     ['datos']),

    # --- modelo -----------------------------------------------------------
    ("Cerrar la junta Lower_Front_Plate -> Middle_Front_Plate",
     "Es la unica junta abierta del perfil. Exterior (-0.64882, +1.61881), "
     "interior (-0.56871, +1.62669). El punto 3 del contorno de los laterales depende "
     "de ella.",
     ['modelo']),

    ("Excluir Template de la coleccion que se exporta",
     "Viaja en el .glb con `Thickness_mm` y `Armour_Material`, y el simulador lo leeria "
     "como una placa de dos metros en el origen.",
     ['modelo']),

    ("Renombrar las placas y modulos con prefijos ARM_ y MOD_",
     "glTF no transporta las colecciones de Blender, asi que el codigo distingue por "
     "propiedades. Los prefijos son una red de seguridad y hacen legible el outliner.",
     ['modelo']),

    ("Terminar el exterior del casco y cerrarlo",
     "Sin torreta. Despues, decidir si la torreta tendra rotacion independiente.",
     ['modelo']),

    ("Modelar los modulos internos como cajas",
     "Unas diez: motor, transmision, municion y tripulantes. No un modelo detallado. "
     "Propiedades: `Module_Type`, `Health` (float) y `Armour_Material`. Sin espesor: "
     "lo da la geometria.",
     ['modelo']),

    ("Escribir el validador de .glb",
     "Comprobar: propiedades presentes y bien escritas, normales hacia fuera, espesor "
     "geometrico coherente con `Thickness_mm` (tolerancia 0,5 mm), sin huecos ni solapes "
     "entre placas, materiales existentes en `materials.csv`, y convexidad de cada objeto. "
     "Con el calculo por geometria, una malla defectuosa da un espesor silenciosamente "
     "falso.",
     ['modelo', 'validacion']),

    # --- nucleo -----------------------------------------------------------
    ("Lista de tramos con agrupacion por contacto",
     "Recorrer el rayo y agrupar tramos consecutivos separados por menos de 1 mm como una "
     "capa compuesta: se suman los caminos equivalentes y la perforacion se evalua sobre "
     "el total. Esto resuelve tambien las esquinas convexas. "
     f"Ver {DOC} seccion 3.2. Base: `tools/raycast_test.py`.",
     ['nucleo']),

    ("Rebote por angulo",
     "Umbral por tipo de proyectil y relacion calibre/espesor, nunca global. Maximo 2 "
     "rebotes. Variacion aleatoria pequena con semilla fija. "
     f"Ver {DOC} seccion 3.3.",
     ['nucleo']),

    ("Perforacion contra la tabla",
     "Comparar el camino equivalente en RHA medido en la malla con la capacidad en linea "
     "de vision interpolada de la tabla. Si no perfora, el disparo termina y no genera "
     f"fragmentos. Ver {DOC} seccion 3.4.",
     ['nucleo']),

    ("Velocidad residual",
     "Limite balistico derivado de la tabla y velocidad residual por Recht-Ipson. "
     f"Es el punto de calibracion del modelo entero. Ver {DOC} seccion 3.5.",
     ['nucleo']),

    ("Nucleo y fragmentos",
     "El nucleo sigue con la mayor parte de la energia; los fragmentos son el astillado "
     "de la placa mas lo que pierde el proyectil. Reparto por `spall_fraction()`. "
     f"Presupuesto de energia cerrado. Ver {DOC} seccion 3.6.",
     ['nucleo']),

    ("Dano a modulos",
     "Una sola rutina para placas y modulos: energia perdida = camino x resistance x "
     "k_absorcion. Si el objeto tiene `Health`, el dano sale de esa energia por "
     "`k_dano[Module_Type]`. Ojo al acoplamiento: la carne frena poco (resistance bajo) "
     "pero incapacita mucho (k_dano alto). Son dos fenomenos distintos.",
     ['nucleo']),

    ("Salida como linea temporal JSON",
     "El disparo se calcula entero y devuelve eventos con instante y posicion: `impact`, "
     "`ricochet`, `stopped`, `perforation`, `fragment_spawn`, `module_hit`, `detonation`, "
     f"`exit`. El render solo los reproduce. Ver {DOC} seccion 7.",
     ['nucleo']),

    ("APHE: armado, retardo y detonacion",
     "Armado de espoleta por espesor minimo, recorrido interior = v_residual x retardo, "
     "detonacion con fragmentos de carcasa y onda expansiva. Primera version a 360 grados "
     f"uniforme. Definir que pasa si el punto de detonacion cae fuera. Ver {DOC} seccion 4.",
     ['nucleo']),

    ("HEAT: chorro y standoff",
     "Detona al contacto. Capacidad en mm de RHA que se consume con el camino. El "
     "blindaje espaciado es la unica excepcion al calculo por geometria: actua por "
     "distancia de detonacion y necesita su propia curva. "
     f"Ver {DOC} seccion 5.",
     ['nucleo']),

    # --- validacion -------------------------------------------------------
    ("Casos de prueba como ficheros JSON",
     "Cada caso: rayo de entrada y resultado esperado. Cuando se elija motor y se porte "
     "el nucleo, los mismos ficheros validan la version nueva. Primer caso ya verificado: "
     "origen (0.50, -2.00, 1.90) direccion (0,1,0) da 81,00 mm y 9,00 grados contra "
     "`Upper_Front_Plate`.",
     ['validacion']),

    ("Regresion contra las tablas de penetracion",
     "Disparar contra una placa plana a los angulos y distancias tabulados y comprobar "
     "que el resultado reproduce la tabla. Es lo que da peso de ingenieria a la memoria.",
     ['validacion']),

    ("Analisis de sensibilidad de los parametros libres",
     "Lanzar la misma bateria de disparos variando `spall`, `resistance` de la carne, "
     "`k_absorcion` y `k_dano`. Si el resultado no cambia, el parametro deja de ser un "
     "problema y se dice en la memoria. Si cambia mucho, hay que justificarlo bien. "
     "Convierte el punto mas debil del trabajo en una aportacion.",
     ['validacion']),

    # --- proyecto ---------------------------------------------------------
    ("Escribir la solicitud de propuesta propia",
     "Lista para entregar el dia que asignen tutor, a mediados de noviembre. Objetivo: "
     "salir de esa reunion con un si o un no, no empezar entonces a explicarse.",
     ['proyecto']),

    ("Revisar la normativa de propuesta propia y su plazo",
     "No necesita tutor: lo responde la coordinacion del grado o el propio reglamento.",
     ['proyecto']),

    ("Definir las reglas de fuera de combate",
     "Por ahora solo se muestra dano acumulado. Hace falta decidir cuando un vehiculo se "
     "da por destruido: municion alcanzada, muerte de un tripulante critico, motor "
     f"destruido. Ver {DOC} seccion 7.",
     ['proyecto', 'nucleo']),

    ("Decidir si la torreta tendra rotacion independiente",
     "Si la tiene, debe ser un objeto hijo con su propia transformacion. Condiciona como "
     "se organiza el archivo de Blender y rehacerlo despues cuesta.",
     ['proyecto', 'modelo']),
]


def run(args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check)


def main():
    dry = '--dry-run' in sys.argv

    try:
        run(['gh', 'auth', 'status'])
    except FileNotFoundError:
        sys.exit("No se encuentra 'gh'. Instala la CLI de GitHub.")
    except subprocess.CalledProcessError:
        sys.exit("'gh' no esta autenticado. Ejecuta: gh auth login")

    existing = set()
    out = run(['gh', 'issue', 'list', '--state', 'all', '--limit', '500',
               '--json', 'title']).stdout
    for it in json.loads(out or '[]'):
        existing.add(it['title'])

    for name, color, desc in LABELS:
        if dry:
            print(f"[dry] label {name}")
            continue
        run(['gh', 'label', 'create', name, '--color', color,
             '--description', desc, '--force'], check=False)

    created = skipped = 0
    for title, body, labels in ISSUES:
        if title in existing:
            print(f"ya existe: {title}")
            skipped += 1
            continue
        if dry:
            print(f"[dry] {title}  [{', '.join(labels)}]")
            created += 1
            continue
        r = run(['gh', 'issue', 'create', '--title', title, '--body', body,
                 '--label', ','.join(labels)], check=False)
        if r.returncode:
            print(f"ERROR en '{title}': {r.stderr.strip()}")
        else:
            print(f"creado: {title}")
            created += 1

    print(f"\n{created} {'se crearian' if dry else 'creados'}, {skipped} ya existian")


if __name__ == '__main__':
    main()
