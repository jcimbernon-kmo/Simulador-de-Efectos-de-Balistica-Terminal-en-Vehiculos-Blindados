#!/usr/bin/env bash
# Crea el backlog inicial del TFG como incidencias de GitHub.
# Requiere gh (https://cli.github.com) autenticado, y ejecutarse dentro del repo.
#
#   bash tools/crear_issues.sh
#
# Es idempotente en las etiquetas, pero NO en las incidencias: si lo lanzas dos
# veces las crea duplicadas. Lanzalo una sola vez.
set -euo pipefail

for l in datos:0E8A16 modelo-3d:1D76DB nucleo:D93F0B validacion:5319E7 \
         proyecto:FBCA04 bloqueante:B60205; do
  gh label create "${l%%:*}" --color "${l##*:}" --force >/dev/null
done

n() { gh issue create --title "$1" --label "$2" --body "$3" >/dev/null && echo "  + $1"; }

echo "Bloqueantes"
n 'Unificar el ID del proyectil HEAT' 'datos,bloqueante' \
'`projectiles.csv` usa `Gr38HlC_75` y `penetration.csv` usa `Gr38HlC_75_L48`. Las filas de penetracion del HEAT no enlazan con ningun proyectil.

Hecho cuando `python tools/ballistic_data.py data/` no muestre el aviso de ID desconocido.'

n 'Rellenar thickness_basis = nominal' 'datos,bloqueante' \
'Confirmado que las tablas dan espesor nominal de placa, pero la columna sigue vacia y el cargador lo esta suponiendo. Condiciona la conversion a linea de vision de docs/modelo_balistico.md 3.4.

Hecho cuando el cargador no avise de thickness_basis sin definir.'

n 'Determinar el criterio de penetracion de cada fuente' 'datos,bloqueante' \
'Una fuente con limite del 50 % da valores mas optimistas que una de perforacion completa. Mezclarlas sesga la calibracion entera del modelo.

Hecho cuando `criterion` este relleno en todas las filas, o se declare desconocido de forma explicita en la memoria.'

n 'Decidir la unidad de Health' 'nucleo,bloqueante' \
'En julios equivalentes, `k_dano` vale 1 y no hay constante que justificar. En puntos arbitrarios hay un parametro libre por tipo de modulo que defender.

Hecho cuando este escrito en docs/modelo_balistico.md 3.7 y reflejado en los modulos de Blender.'

n 'Elegir la distribucion de tamanos de fragmento' 'nucleo,bloqueante' \
'Con la misma energia total, cuatro trozos gordos y cien esquirlas hacen cosas muy distintas dentro del vehiculo. El numero de rayos es resolucion numerica; el tamano es fisica.

Hecho cuando la distribucion este en docs/modelo_balistico.md 6 declarada como supuesto, con su fuente o la palabra supuesto.'

echo "Datos"
n 'Anadir core_mass_kg al APCR' 'datos' \
'Los 4,1 kg del PzGr. 40 son el proyectil entero, pero lo que penetra es el nucleo de tungsteno. Sin esa masa, la razon de masas del spall da una fraccion demasiado baja.

Hecho cuando la columna exista y el cargador no avise.'

n 'Completar explosivo y espoleta del PzGr. 39' 'datos' \
'Es APCBC-HE, o sea que se comporta como APHE. Falta `fuze_delay_ms`, que fija a que distancia dentro del vehiculo detona.

Hecho cuando `explosive_mass_g` y `fuze_delay_ms` esten rellenos con su fuente.'

n 'Completar explosive_mass_g del HEAT' 'datos' \
'Gr. 38 Hl/C no tiene masa explosiva. Hace falta para la onda expansiva posterior a la penetracion del chorro.

Hecho cuando este relleno con su fuente.'

n 'Anadir el material Propellant y revisar mayusculas' 'datos' \
'Falta `Propellant` para el modulo de municion. Ademas, los ids de materials.csv tienen que coincidir exactamente, mayusculas incluidas, con lo que se escriba en `Armour_Material` en Blender.

Hecho cuando el validador de .glb no encuentre materiales desconocidos.'

n 'Rellenar la columna spall de materials.csv' 'datos' \
'`spall` es la fragilidad del material, 0-1, y entra en la razon de masas de `spall_fraction()`. Orden esperado: RHA ductil bajo, blindaje fundido o de cara endurecida claramente mas alto, carne casi cero.

Hecho cuando todos los materiales tengan valor y justificacion o la palabra supuesto.'

n 'Conseguir la columna de 60 grados o declararla extrapolada' 'datos' \
'Es la columna mas importante para un simulador de blindaje inclinado, porque la mayoria de impactos reales son oblicuos. Sin ella, todo lo que pase de 30 grados es extrapolacion y el cargador lo marca como tal.

Hecho cuando este rellena, o cuando la limitacion este escrita en la memoria.'

n 'Anadir source_id por fila' 'datos' \
'Las fuentes se unifican en la memoria, pero sin trazabilidad por fila no se puede reconstruir de donde salio cada numero. Un codigo corto por fila apuntando a la lista basta.

Hecho cuando todas las filas de penetration.csv y materials.csv tengan source_id.'

echo "Modelo 3D"
n 'Cerrar la junta Lower_Front a Middle_Front' 'modelo-3d' \
'Es la unica junta abierta del perfil. Exterior (-0.64882, +1.61881), interior (-0.56871, +1.62669). El punto 3 del contorno de los laterales depende de ella.

Hecho cuando las dos placas compartan sus dos vertices.'

n 'Sacar Template de la coleccion exportada' 'modelo-3d' \
'Viaja en el .glb con `Thickness_mm` y `Armour_Material`, asi que el simulador lo leeria como una placa de dos metros en el origen.

Hecho cuando no aparezca en el .glb exportado.'

n 'Renombrar con prefijos ARM_ y MOD_' 'modelo-3d' \
'glTF no transporta las colecciones de Blender, asi que los prefijos son la red de seguridad legible. El codigo distingue por propiedades, pero el outliner y los avisos del validador se leen mucho mejor.

Hecho cuando todas las placas y modulos tengan prefijo.'

n 'Terminar el exterior del casco' 'modelo-3d' \
'Sin torreta. Cerrar el volumen completo con laterales, popa y todo lo que falte.

Hecho cuando un barrido de rayos desde los seis ejes no encuentre huecos.'

n 'Modelar los modulos internos como cajas' 'modelo-3d' \
'Motor, transmision, municion y tripulantes. Unas diez cajas, no un modelo detallado: ni asientos ni palancas.

Hecho cuando cada uno tenga `Module_Type`, `Health` y `Armour_Material`, y esten dentro del casco.'

n 'Escribir el validador de .glb' 'modelo-3d,validacion' \
'Con el calculo por geometria la malla es la fuente de verdad, asi que una malla defectuosa da un espesor silenciosamente falso.

Comprueba: propiedades presentes y con tipo correcto, materiales existentes en materials.csv, normales hacia fuera, espesor geometrico coincidente con `Thickness_mm` dentro de 0,5 mm, ausencia de huecos y solapes entre placas, y convexidad de cada objeto.

Hecho cuando pase sobre el modelo actual y falle a proposito sobre un modelo roto de prueba.'

echo "Nucleo"
n 'Agrupar tramos por contacto' 'nucleo' \
'Hueco menor de 1 mm entre la salida de un objeto y la entrada del siguiente: son una capa compuesta y la perforacion se evalua sobre el camino equivalente sumado. Hueco mayor: blindaje espaciado. Esto resuelve ademas el doble conteo en las esquinas.

Hecho cuando una prueba con dos placas en contacto de un solo grupo y con 5 mm de separacion de dos.'

n 'Implementar el rebote' 'nucleo' \
'Umbral de angulo por tipo de proyectil y relacion calibre/espesor, nunca global. Componente normal casi anulada, perdida en la tangencial, maximo 2 rebotes, variacion aleatoria con semilla fija.

Hecho cuando un disparo muy oblicuo rebote y el mismo disparo repetido de identico resultado.'

n 'Implementar la comprobacion de perforacion' 'nucleo' \
'Comparar el camino equivalente en RHA medido en la malla contra la capacidad en linea de vision interpolada de la tabla. Si no perfora, el disparo termina sin fragmentos.

Hecho cuando contra placa plana reproduzca exactamente la tabla.'

n 'Implementar la velocidad residual' 'nucleo' \
'Limite balistico derivado de la tabla y Recht-Ipson. Es el punto de calibracion del modelo entero, asi que conviene que los parametros esten declarados y no empotrados.

Hecho cuando la velocidad residual tienda a cero al acercarse al limite y crezca de forma monotona por encima.'

n 'Generar nucleo y fragmentos' 'nucleo' \
'El nucleo sigue con la mayor parte de la energia; los fragmentos son el astillado de la placa mas lo que pierde el proyectil. Reparto por `spall_fraction()`, cono alrededor de la direccion de salida, semilla fija.

Hecho cuando la suma de energias de nucleo y fragmentos sea igual a la residual, comprobado con un assert.'

n 'Aplicar dano a los modulos' 'nucleo' \
'Una sola rutina para placas y modulos: energia perdida = camino x resistance x k_absorcion. Si el objeto tiene `Health`, el dano sale de esa energia por `k_dano[Module_Type]`.

Ojo al acoplamiento: la carne frena poco a proposito, asi que `k_dano[crew]` tiene que ser alto o la tripulacion sale invulnerable.

Hecho cuando un fragmento atraviese a un tripulante, le haga dano y siga hasta el motor.'

n 'Salida como linea temporal JSON' 'nucleo' \
'Eventos con instante y posicion: impact, ricochet, stopped, perforation, fragment_spawn, module_hit, detonation, exit. Es lo que reproduce el render y lo que comparan las pruebas.

Hecho cuando un disparo complejo produzca un JSON legible y estable entre ejecuciones.'

n 'Implementar APHE' 'nucleo' \
'Perfora como un cinetico; despues, armado de espoleta por umbral de espesor, recorrido interior igual a velocidad residual por retardo, detonacion y fragmentos de carcasa en 360 grados. Primera version uniforme.

Hecho cuando un APHE que perfora detone dentro y uno que no perfora se detenga sin fragmentos.'

n 'Implementar HEAT' 'nucleo' \
'Detona al contacto. El chorro es un rayo estrecho con capacidad en mm de RHA que se consume con camino x resistance. Sin efecto de inclinacion mas alla de la linea de vision. Al salir del blindaje, la capacidad restante se convierte a energia con una constante declarada.

Pendiente aparte: la curva de penetracion frente a standoff, unico punto donde el blindaje espaciado necesita codigo propio.

Hecho cuando la penetracion no varie con la distancia de tiro y si con el angulo por pura linea de vision.'

echo "Validacion"
n 'Casos de prueba como ficheros JSON' 'validacion' \
'Cada caso es un JSON con el rayo de entrada y el resultado esperado. Cuando se elija motor y se porte el nucleo, los mismos ficheros validan la version nueva, lo que convierte la eleccion de motor en algo casi secundario.

Primer caso ya verificado: origen (0.50, -2.00, 1.90), direccion (0,1,0), impacto en Upper_Front_Plate, camino 81,00 mm, angulo 9,00 grados.

Hecho cuando exista una carpeta de casos y un comando que los pase todos.'

n 'Prueba de regresion contra las tablas' 'validacion' \
'Disparar contra una placa plana a cada angulo y distancia tabulados y comprobar que el resultado reproduce la tabla. Es lo que da peso de ingenieria a la memoria.

Hecho cuando pase para los tres proyectiles en todas las combinaciones con dato.'

n 'Analisis de sensibilidad de los parametros libres' 'validacion' \
'Los parametros de docs/modelo_balistico.md 6 no estan calibrados contra datos de efectos tras el blindaje, que es el punto mas debil del trabajo. Barrer cada uno en un rango razonable y medir cuanto cambia el resultado.

Si un parametro no mueve la aguja, se declara irrelevante y deja de ser un problema. Si la mueve mucho, se sabe donde hay que justificar bien. Convierte la debilidad en aportacion.

Hecho cuando haya una tabla de sensibilidad por parametro en la memoria.'

echo "Proyecto"
n 'Escribir la solicitud de TFG' 'proyecto' \
'El tutor no se asigna hasta mediados de noviembre. Tener el documento listo convierte la primera reunion en un si o un no, en vez de empezar entonces a explicarse.

Hecho cuando exista el documento con objetivos, alcance, metodologia, planificacion y bibliografia.'

n 'Revisar la normativa de propuesta propia' 'proyecto' \
'No necesita tutor: lo responde el reglamento del grado o la coordinacion. Es el riesgo que invalida todo lo demas.

Hecho cuando se sepa si se admite propuesta propia y en que plazo.'

n 'Definir las reglas de fuera de combate' 'proyecto,nucleo' \
'Por ahora solo se muestra dano acumulado por modulo. Hacen falta reglas: municion alcanzada, muerte de un tripulante critico, motor destruido.

Hecho cuando esten escritas en docs/modelo_balistico.md 7.'

n 'Decidir si la torreta tendra rotacion independiente' 'proyecto,modelo-3d' \
'Si la tiene, debe ser un objeto hijo con su propia transformacion, y eso condiciona como se organiza el archivo de Blender. Rehacerlo con el interior ya modelado cuesta mucho mas.

Hecho cuando este decidido y anotado en tfg.md.'

echo
echo "Listo. Revisa las etiquetas y agrupa en hitos si quieres."
