# Modelo balístico

Documento de diseño del núcleo de cálculo. Define qué se simula, con qué datos y con qué fórmulas, antes de programarlo.

Convención: **[D]** decidido · **[S]** supuesto, pendiente de fuente o de verificación · **[A]** abierto, hay que decidirlo.

Última revisión: 2026-10-26 (4ª).

---

## 1. Principios

**[D] El espesor atravesado se mide en la geometría, no en las propiedades.** Para cada objeto que el rayo cruza se calcula la longitud de camino entre la intersección de entrada y la de salida. Con eso salen gratis la oblicuidad, las esquinas convexas (que son realmente más gruesas), las orugas usadas como blindaje extra y el blindaje espaciado.

`Thickness_mm` se conserva en cada placa para validar que la geometría coincide, para la relación espesor/calibre en la fragmentación, y como respaldo. **No se usa para calcular la penetración.**

**[D] La malla es la fuente de verdad.** Un hueco hace atravesar menos acero del real; un solape, de más. De ahí que el validador de `.glb` sea parte del núcleo y no un extra.

**[D] Presupuesto de energía cerrado.** Tras perforar, el núcleo y todos los fragmentos se reparten la energía residual. La suma nunca puede superarla.

**[D] Una sola rutina de recorrido.** Placas y módulos hacen lo mismo: algo entra con energía, recorre un camino dentro de un material y pierde energía. La única diferencia es que un módulo además anota el daño en su `Health`. Un fragmento puede atravesar a un tripulante y clavarse en el motor sin lógica adicional.

**[D] Reproducibilidad.** Toda la aleatoriedad (dispersión de fragmentos, umbrales de rebote) usa una semilla fija derivada del disparo. El mismo disparo da siempre el mismo resultado.

**[D] Cálculo y reproducción separados.** El disparo se calcula entero de golpe y devuelve una línea temporal de eventos. El render la reproduce a la velocidad que sea.

**[D] Todo dato vive fuera del código.** Ni una constante física, ni un umbral, ni un coeficiente escritos dentro de un `.py`. Todo sale de los ficheros de `data/` y del `.glb`. Tres razones, y la tercera es la que importa:

1. Cambiar un vehículo, un proyectil o un criterio no toca el código.
2. El análisis de sensibilidad (§6) consiste en variar esos ficheros, así que tienen que ser el único sitio donde están los números.
3. **Varios de esos valores están sin validar y se van a tener que cambiar.** El umbral de incapacitación de §3.7.2 es el caso claro: está pendiente de consulta con el tutor, y si hay que cambiarlo tiene que ser editando una celda, no buscando por dónde andaba.

Corolario para el núcleo: una capa de carga de datos que devuelve estructuras, y un cálculo que no sabe de dónde vienen. Las pruebas de §8 inyectan datos sintéticos por esa misma capa.

---

## 2. Datos de entrada

### 2.1 Proyectil — `data/shells.csv`

| Campo | Unidad | Notas |
|---|---|---|
| `shell_id` | — | p. ej. `PzGr39_75_L48` |
| `name` | — | nombre histórico |
| `type` | — | `AP`, `APCBC`, `APCR`, `APHE`, `HEAT` |
| `caliber_mm` | mm | |
| `mass_kg` | kg | proyectil completo |
| `core_mass_kg` | kg | solo APCR: masa que de verdad penetra |
| `muzzle_velocity_ms` | m/s | |
| `explosive_mass_g` | g | equivalente en TNT; 0 si no lleva |
| `fuze_delay_ms` | ms | solo con explosivo (ver §4) |
| `cd` | — | coeficiente de arrastre; **solo respaldo** si no hay fila en `velocity.csv` (§2.2.1) |
| `source_id` | — | clave en `data/sources.md` |

**[D] Todas las masas en kg.** El fichero llegó a tener una columna `core_mass_hg` en hectogramos, unidad que no aparece en ningún otro sitio del proyecto y que existía sólo porque hacía parecer correcto un valor equivocado. Una sola unidad por magnitud en todo el proyecto: kg, m, m/s, J, y mm únicamente para espesores y calibres, por ser la convención de las fuentes.

### 2.2 Tabla de penetración — `data/penetration.csv`

| Campo | Unidad | Notas |
|---|---|---|
| `shell_id` | — | enlaza con la tabla anterior |
| `distance_m` | m | |
| `angle_deg` | ° | **[D] medido desde la normal**: 0° es impacto perpendicular |
| `penetration_mm` | mm | espesor perforado |
| `armour_type` | — | contra qué blindaje se midió |
| `angle_from` | — | desde dónde mide el ángulo la fuente de esa fila |
| `thickness_basis` | — | `nominal` o `los`; decide si §3.4 divide por el coseno |
| `criterion` | — | criterio de penetración de la fuente (`complete`, …). **Imprescindible**: alemanes, británicos y estadounidenses no usaban el mismo, y comparar cifras de criterios distintos es el error clásico de este tema. Es además la clave de §8 |
| `source_id` | — | clave en `data/sources.md` |

La velocidad de impacto ya no vive aquí: tiene fichero propio (§2.2.1).

**[D] Comprobación obligatoria en el cargador: la penetración tiene que decrecer al aumentar el ángulo.** Para un mismo `shell_id` y una misma `distance_m`, si una fila de ángulo mayor da más penetración que una de ángulo menor, o los datos están mal o la convención de `angle_from` es la contraria. Son tres líneas y protege del error de convención, que no se ve a ojo.

Interpolación lineal entre filas en distancia y en ángulo. Fuera del rango tabulado, extrapolación marcada como tal en la salida, para no presentar como dato lo que es una extrapolación.

#### 2.2.1 Velocidad de impacto

Hace falta para evaluar la perforación de **cualquier capa que no sea la primera**: el mamparo interno, el blindaje espaciado o las orugas reciben el proyectil con velocidad residual, y esa velocidad no corresponde a ninguna distancia de la tabla.

**[D] La fuente de verdad es una tabla medida, no un modelo ajustado.** Vive en
`data/velocity.csv` (`shell_id, distance_m, velocity_ms`) y se interpola por distancia con la
misma rutina que ya interpola `penetration.csv`. Una interpolación pasa exacta por cada punto
medido, cosa que ningún exponencial ajustado hace.

El modelo de arrastre `v(x) = v₀·e^{-Kx}`, con `K = ρ·Cd·A/(2m)`, queda como **respaldo** para
proyectiles sin tabla, y como el método con el que se obtuvieron los puntos que faltaban del
PzGr. 39. No como camino principal.

**[D] PzGr. 39, resuelto** (23/10/2026). El `Cd` despejado de cada punto por separado sale
0,4118 / 0,4143 / 0,4198, o sea **la misma constante dentro del 1,9 %**. Con `Cd = 0,415` el
ajuste queda por debajo de 2 m/s en los tres puntos medidos, así que los dos interpolados son
fiables.

| Distancia | m/s | Origen |
|---|---|---|
| 100 m | 738 | del modelo |
| 500 m | 691 | medido |
| 1000 m | 636 | medido |
| 1500 m | 585 | del modelo |
| 2000 m | 537 | medido |

**[D] PzGr. 40, resuelto** (24/10/2026), y es el caso que justifica haber pasado a tabla. Los
cinco puntos son medidos: 905 / 790 / 660 / 540 / 430 m/s a 100, 500, 1000, 1500 y 2000 m,
coherentes con los 930 m/s de boca al extrapolar el primer tramo hacia atrás.

Aquí **un solo exponencial no vale**. El `Cd` despejado tramo a tramo no es constante:

| Tramo | `Cd` implicado |
|---|---|
| 0–100 m | 0,413 |
| 100–500 m | 0,515 |
| 500–1000 m | 0,545 |
| 1000–1500 m | 0,608 |
| 1500–2000 m | 0,690 |

La subida es física, no error de los datos: el proyectil baja de Mach 2,7 a Mach 1,26 y el `Cd`
crece al acercarse a la transónica. Con un `Cd` único ajustado a todo el rango (0,584) el error
llega al **−4,2 % en velocidad y −8,2 % en energía a 1000 m**, que es la distancia más usada.
Por eso el `cd` de `shells.csv` es respaldo y no fuente.

Dato para la memoria: el primer tramo del PzGr. 40 da `Cd` 0,413, prácticamente el 0,415 del
PzGr. 39. **Las dos formas arrastran igual**; la caída mucho más rápida del APCR viene de su
masa, 4,1 kg frente a 6,8 para el mismo calibre, y eso ya lo recoge la masa en `K`. Explica de
paso por qué el APCR perdía prestaciones a distancia.

**[S] Gr. 38 Hl/C: la tabla está rellena con 450 m/s constantes, y eso es un marcador, no un
dato.** El proyectil decelera como cualquier otro. Se acepta porque la penetración de una carga
hueca no depende de la velocidad de impacto (§5), así que el valor sólo entra en la energía del
cuerpo del proyectil, que no es el penetrador. Declarado en §9.

**Comprobación cruzada con la caída.** Los datos de caída de la misma fuente (−2,4 m a 500 m,
−10,0 a 1000, −44,8 a 2000) son independientes de la velocidad. Derivando el tiempo de vuelo
del modelo y aplicando solo gravedad, la caída sale con un −1 % de error a 500 m, +3 % a 1000
y +9 % a 2000. La desviación a larga distancia es esperable, porque ese cálculo supone
trayectoria plana. Confirma que velocidades y tiempos de vuelo son coherentes entre sí.

**[D] El exponente de De Marre, medido en vez de supuesto.** Cruzando las velocidades reales
con la tabla de penetración se obtiene el exponente de `P ∝ vⁿ`:

| Distancia | n medido |
|---|---|
| 500 m | 1,4082 |
| 1000 m | 1,4383 |
| 1500 m | 1,4288 |
| 2000 m | 1,4361 |

Media 1,428, frente al valor teórico de De Marre de **1,4283**. Dos conjuntos de datos
históricos independientes —una tabla de penetración y una de velocidades— coinciden con una
relación teórica que no interviene en la elaboración de ninguno de los dos. Es el resultado de
validación más fuerte del trabajo hasta la fecha, y justifica usar `n = 1,428` en §3.4.1.

**[D] Precedencia, para que no haya dos fuentes de verdad.** El cargador resuelve la velocidad
a una distancia así, y en este orden:

1. Interpolación de `velocity.csv` si el `shell_id` tiene filas. **Es el caso normal.**
2. Si no las tiene, `v₀·e^{-Kx}` con el `cd` de `shells.csv`, marcando el valor como estimado
   en la salida.
3. Si tampoco hay `cd`, error en la carga. Nunca un valor por defecto silencioso.

Para un proyectil nuevo sin datos basta **un solo punto publicado** de velocidad restante para
despejar su `Cd`; a falta de eso, estimarlo por forma, declararlo supuesto y meterlo en el
análisis de sensibilidad. Si se consiguen tres puntos o más, pasa a `velocity.csv` y el `cd`
deja de usarse, como ha ocurrido con el PzGr. 40.

### 2.3 Materiales — `data/materials.csv`

Una sola tabla para blindaje y para módulos. El blindaje de referencia es RHA con coeficiente 1,0.

| Campo | Notas |
|---|---|
| `id` | `RHA`, `Steel`, `Track`, `Flesh`, `Cast_Iron`, `Ammo`, `Engine`, `Gasoline`, `Diesel`. Mayúscula inicial, igual que en el `.glb` |
| `resistance` | **[S]** resistencia relativa a RHA; multiplica la longitud de camino para obtener el equivalente en RHA |
| `spall` | **[S]** tendencia a astillar, 0–1. Vacío a 26/10/2026 |
| `source_id` | clave en `data/sources.md`, o la palabra «supuesto» |

**[D] El `spall` no es un dato histórico y no se va a encontrar en ninguna tabla.** Es un
parámetro libre del modelo (§6). Lo investigable no son los nueve números sino la literatura de
*behind-armour debris*, para poder justificar el rango en el que se fijan.

**[S]** `Track` debe quedar bastante por debajo de 1: una oruga son eslabones con huecos, no un bloque macizo.

### 2.4 Objetos del modelo

**Placas** (`ARM_*`): `Thickness_mm` (float), `Armour_Material` (texto, id de materiales).

**Módulos** (`MOD_*`): `Module_Type` (texto, con mayuscula inicial: `Crew`, `Engine`, `Transmission`, `Ammo`, `Fuel`, `Gun`), `Health` (**[D] float**), `Armour_Material` (texto, misma tabla).

**[D] Los módulos no llevan propiedad de espesor**: la longitud de camino por dentro de su caja ya la da la malla. Un fragmento que entra de refilón por una esquina del motor atraviesa menos que uno que lo cruza entero.

**[D]** El código distingue por propiedades, no por colección ni por prefijo: glTF no transporta las colecciones de Blender. Los prefijos del nombre son una red de seguridad.

---

## 3. Flujo de un disparo cinético (AP, APCBC, APCR)

### 3.1 Tramos

Se lanza el rayo y se obtiene la lista ordenada de tramos: objeto, punto de entrada, punto de salida, longitud, normal de entrada.

**[S] Suposición de convexidad.** La entrada es la primera intersección y la salida la última. Vale para cualquier objeto convexo. Una pieza en L o una lámina curva rompería la suposición en silencio, así que el validador lo comprueba desde el 23/10/2026.

**El caso que más duele es la lámina curva**, y conviene entenderlo antes de modelar manteletes, cúpulas o una torreta fundida. Una lámina curva no es convexa, y con un rayo rasante a la curvatura puede dar cuatro intersecciones: entra por la cara exterior, sale por la interior, vuelve a entrar por la interior y sale por la exterior. Primera y última abarcan entonces también el hueco de aire intermedio, y el camino sale casi el doble del real. Con rayos aproximadamente radiales no ocurre.

**[D] Solución general: facetar.** Todo lo curvo se parte en tramos casi planos, suficientes para que ningún rayo pueda cruzar dos superficies interiores dentro de la misma pieza. Es lo que se hizo con los cilindros de la transmisión, con el anillo de torreta del techo del casco y con el mantelete.

**[D] Corolario de construcción: las piezas se generan como intersección de semiespacios**, no uniendo vértices. Cuatro puntos en el espacio no son coplanarios salvo que se les obligue, así que una placa construida a mano sale con las caras grandes alabeadas, y entonces el espesor medido no es el declarado y la pieza deja de ser convexa. Definida como intersección de planos (exterior, interior, suelo, techo y los planos de las piezas vecinas), la convexidad y la planitud salen por definición, y dos piezas contiguas comparten cara exacta porque el límite de una *es* el plano de la otra.

**[S] No convexas pendientes a 26/10/2026**: `ARM_Front_Top_Plate`, `ARM_Lower_Side_L_Plate`, `ARM_Lower_Side_R_Plate` y `MOD_Engine` (este último, convexo a propósito para imitar el V12, se deja como está).

### 3.2 Agrupación por contacto

Entre tramos consecutivos se mide el hueco: `entrada_siguiente − salida_actual`.

**[D] El hueco se mide perpendicular a las placas, no a lo largo del rayo.** Si un rayo oblicuo cruza un hueco de 0,78 mm a 70°, la distancia que recorre por el aire es de 2,27 mm. Usar esa distancia haría que dos placas fueran «en contacto» para un disparo perpendicular y «espaciadas» para uno oblicuo, lo cual es absurdo: que dos placas estén unidas o separadas es una propiedad de la geometría, no del disparo. La conversión es inmediata:

```
hueco_perpendicular = hueco_a_lo_largo_del_rayo × cos(ángulo con la normal de entrada de la capa siguiente)
```

- **[S] Hueco perpendicular < 1 mm:** placas en contacto. Forman una capa compuesta: se suman los caminos equivalentes y la perforación se evalúa sobre el total.
- **Hueco perpendicular ≥ 1 mm:** blindaje espaciado. Se perfora la primera, se generan fragmentos en el hueco, y lo que llegue a la segunda lo resuelve el propio trazado sin código especial.

Esto resuelve además las esquinas: las bandas estrechas donde un rayo frontal cruza dos placas de una misma esquina se agrupan y se cuentan una sola vez como capa compuesta.

### 3.3 Rebote

Antes de evaluar la perforación, con el ángulo entre el rayo y la normal de entrada:

- Por encima del umbral, rebota: la componente normal de la velocidad se anula casi entera y la tangencial pierde energía. El proyectil desviado sigue como un rayo nuevo. **[D] Máximo 2 rebotes.**
- **[S] El umbral depende del tipo de proyectil y de la relación calibre/espesor.** Un APCBC con casquete balístico aguanta ángulos más cerrados que un APCR. **Nunca un umbral global.**
- **[S]** Pequeña variación aleatoria alrededor del umbral, con semilla fija, para que no sea todo o nada.

### 3.4 Perforación

Camino equivalente en RHA de la capa: `Σ (longitud_tramo × resistance_material)`.

Capacidad del proyectil, desde la tabla interpolada a la distancia y al ángulo de impacto:

- Si la tabla da **espesor nominal**: `capacidad_LOS = tabla(θ, d) / cos θ`
- Si la tabla da **línea de visión**: `capacidad_LOS = tabla(θ, d)`

Perfora si `camino_equivalente ≤ capacidad_LOS`. En una placa plana esto reproduce exactamente la tabla; en esquinas y capas, generaliza.

**[D] Si no perfora, el disparo termina ahí y no genera fragmentos.** Simplificación aceptada.

### 3.4.1 Capas posteriores a la primera

**[D] La cadena de perforación se lleva en capacidad, no en velocidad.** Lo que necesita una
segunda capa no es los m/s del proyectil sino cuántos milímetros de RHA le queda por perforar.
Recht-Ipson, transplantado a esas unidades con `P ∝ vⁿ`:

```
P_residual = (P_impacto^(2/n) − t_equivalente^(2/n))^(n/2)
```

con `n = 1,428` medido arriba. El proyectil llega con la capacidad que da la tabla, la capa le
consume su espesor equivalente, y el resto va contra la siguiente. Sin velocidades de por medio.

La velocidad sigue haciendo falta para dos cosas, y solo dos: la **energía** de núcleo y
fragmentos (`½mv²`, §3.7) y el **recorrido de la espoleta** del APHE (§4). Las dos toleran más
error que la perforación.

### 3.5 Energía residual

**[S]** Límite balístico de la capa derivado de la tabla (tipo De Marre, exponente ≈0,7 — verificar), y velocidad residual por Recht-Ipson. **Es el punto de calibración del modelo entero.**

`E_residual = ½ · m · v_residual²`

### 3.6 Núcleo y fragmentos

**[D] El núcleo sigue.** Un AP macizo que perfora no se convierte entero en metralla: el núcleo continúa como un rayo más, con la mayor parte de la energía, y puede atravesar el motor y salir por el otro lado.

Reparto de la energía residual:

- `E_astillado = E_residual × spall_fraction`
- `E_núcleo = E_residual − E_astillado`

Los fragmentos son el astillado de la placa más los trozos que pierde el proyectil. Se generan `N` rayos dentro de un cono alrededor de la dirección de salida, repartiéndose `E_astillado`.

### 3.7 Pérdida de energía y daño

**[D] La energía perdida depende del área frontal del penetrador, no solo del camino.** Una constante global por unidad de longitud no vale: un núcleo de 75 mm y una esquirla de 3 mm no depositan lo mismo por milímetro recorrido, porque la resistencia del material actúa sobre la sección que empuja.

Para cada rayo (núcleo o fragmento), tramo a tramo:

```
E_perdida = camino × resistance_material × σ_RHA × (π/4)·d²
E -= E_perdida
si el objeto tiene Health:  Health -= E_perdida
si E <= 0: el rayo se detiene dentro del objeto
```

con `camino` en metros, `d` el diámetro del penetrador en metros y `σ_RHA` una resistencia dinámica en Pa.

**[D] `σ_RHA` se deriva de las tablas, no se inventa.** En el límite balístico el proyectil deposita toda su energía en el espesor que justo perfora:

```
σ_RHA = E_impacto / (espesor_perforado × área_frontal)
```

Con el PzGr. 39 (6,8 kg, 750 m/s, 1,913 MJ) perforando 135 mm a 100 m y 0°, sobre sus 44,18 cm² de sección: **σ_RHA ≈ 3,21 GPa**.

Dos limitaciones de ese anclaje, que van a la memoria: en el límite no *toda* la energía va a la placa, algo queda como velocidad residual, así que σ sale ligeramente sobrestimada; y se ha usado la velocidad de boca para la penetración a 100 m. Recalcular cuando esté `striking_velocity_ms` (§2.2).

**[D] `Health` se expresa en julios**, así que no hay constante de conversión entre energía depositada y daño: el daño *es* la energía depositada. Eso elimina el `k_daño` por tipo de módulo que figuraba antes.

### 3.7.1 La regla de daño depende del tipo de módulo

**[D] La energía depositada vale para máquinas, no para personas.** Un motor se avería absorbiendo energía: cuanto más lo atraviesa el proyectil, más destroza, y acumular tiene sentido. A una persona no la incapacita la cantidad de tejido recorrido sino **alcanzar algo vital**.

El problema se ve con números. En el modelo, las piernas de un tripulante sentado se extienden 0,82 m hacia delante y el torso tiene 0,27 m de fondo, así que un fragmento frontal recorre el triple de carne en las piernas:

| Fragmento | Torso (0,27 m) | Piernas (0,82 m) |
|---|---|---|
| 3 mm | 61 J | 186 J |
| 5 mm | 170 J | 517 J |
| 10 mm | 681 J | 2067 J |

Con el mismo `Health` en ambos, el modelo diría que un disparo frontal destroza las piernas tres veces más que el torso: lo contrario de la realidad. Y subir el `Health` de las piernas solo taparía el síntoma.

Por tanto, **una rutina de recorrido y dos reglas de daño**:

| `Module_Type` | Regla |
|---|---|
| `Engine`, `Transmission`, `Gun` | Daño = energía depositada, acumulativa |
| `Crew` | Incapacitado si un fragmento **entra** con energía por encima del umbral; la energía que deposite después no cuenta |
| `Ammo`, `Fuel` | Umbral de detonación / ignición (§4, §7) |

El rayo sigue frenándose igual en todos los casos: lo único que cambia es cómo se traduce eso en daño.

Órdenes de magnitud que produce el modelo, útiles para fijar los valores:

| Caso | Energía depositada |
|---|---|
| Esquirla de 3 mm cruzando 30 cm de torso | 68 J |
| Esquirla de 5 mm, mismo torso | 189 J |
| Esquirla de 10 mm, mismo torso | 756 J |
| Núcleo de 75 mm, 10 cm dentro del motor | 425 kJ |

**[S] Valores de partida de `Health`:**

| `Module_Type` | Health | Criterio |
|---|---|---|
| `Crew` torso y cabeza | 80 J | Umbral de energía de **entrada** del fragmento. **Convención declarada, no criterio validado** — ver §3.7.2. |
| `Crew` piernas | 3-5× el del torso | **[S]** La dependencia de la región del cuerpo está reconocida en los modelos de vulnerabilidad militares, así que el efecto es citable; el factor concreto es supuesto y va al análisis de sensibilidad (§6). |
| `Transmission` | ~150 kJ | Menor que el motor; un impacto de lleno la inutiliza. |
| `Engine` | ~300 kJ | Un núcleo que llega con esa energía se detiene en 7 cm de motor y la deposita entera. |
| `Gun` tubo | ~40 kJ | **[S]** Acero macizo de pared gruesa, y sale por delante del mantelete. El más robusto de los dos. |
| `Gun` recámara | ~15 kJ | **[S]** Mecanismo de precisión: se agarrota mucho antes de destruirse. Los dos valores son parámetros libres (§6) y no tienen fuente; lo que sí está razonado es el **orden**, tubo por encima de recámara. |
| `Ammo` | — | No aplica: es un **umbral de detonación**, no una reserva. |
| `Fuel` | — | No aplica: **umbral de ignición**. El incendio no es destrucción instantánea (§7). |

### 3.7.2 El umbral de 80 J es una convención sin validar

Hay que escribirlo con precisión, porque la bibliografía dice algo distinto de lo que suele citarse.

**Qué se creía.** Que 80 J (58 ft·lb) es el umbral de incapacitación por fragmento. Nota de unidades: **58 ft·lb *son* 80 J**, no son dos criterios distintos ni los extremos de un rango.

**Qué dice la fuente.** El artículo localizado el 24/10/2026 (PMID 28505551, en `data/sources.md`) rastrea el origen del criterio hasta Rohne y concluye tres cosas:

1. Ni Rohne ni los balísticos de la década siguiente explicaron **de dónde salía** el valor de 8 mkg ni **qué entendían por inmovilización**.
2. El poder de penetración de la bala M/88 a 80 J se reprodujo en laboratorio sobre jabón balístico, y la profundidad alcanzada es llamativamente alta, lo que respalda la afirmación de Rohne.
3. Pero **no fue posible validar el criterio**, y el artículo **recomienda explícitamente no usar un límite de energía para definir ningún tipo de incapacitación**.

**Dos saltos, no uno.** Aunque el criterio fuese válido, se refiere a **una bala M/88 penetrando tejido**. Aquí se aplica a **fragmentos de blindaje**: irregulares, volteando, con otra relación entre energía y daño. Trasladarlo es una segunda suposición sin validar, que el artículo ni aborda.

**[D] Qué se hace, y por qué.** Se mantienen los 80 J como valor de partida, porque dentro del alcance de este trabajo no hay sustituto mejor: cualquier criterio más fino es balística de heridas, no penetración de blindaje. Pero cambia de categoría: deja de presentarse como dato con fuente y pasa a **convención con origen documentado y sin validación**, citada en §9 y ajustable desde fichero (§1, §6).

Declararlo así es mejor defensa que citarlo con aplomo. **[A] Pendiente de consulta con el tutor**, y la pregunta es de alcance, no de balística: *¿se acepta un criterio de daño a la tripulación que es una convención sin validar y declarada como tal, o el proyecto necesita otro criterio?*

### 3.7.3 Un `Module_Type` puede abarcar varios objetos

**[D] Algunos tipos se evalúan en conjunto, no pieza a pieza.** La munición ya funcionaba así: hay 87 cartuchos como objetos independientes, y la detonación de cualquiera inutiliza el vehículo. El cañón es el mismo patrón: tubo y recámara son objetos separados en el modelo 3D, con `Health` distinto, pero **si cualquiera de los dos queda fuera de servicio el vehículo no puede devolver el fuego**.

En vez de un caso especial por tipo, una sola regla:

| `Module_Type` | Agregación entre objetos del mismo tipo |
|---|---|
| `Ammo`, `Gun` | **OR**: basta con que uno caiga |
| `Crew` | OR dentro de cada tripulante, pero cada tripulante cuenta por separado (§7) |
| `Engine`, `Transmission`, `Fuel` | Cada objeto, por su cuenta |

Esto evita tener que inventar un tipo nuevo por cada cosa que se modele en varias piezas, y es lo que hace que la decisión de «tubo y recámara separados en el 3D pero un solo módulo lógico» no necesite código especial.

---

## 4. APHE

Perfora igual que un cinético (§3.3 a §3.5). La diferencia viene después.

1. **Armado de la espoleta. [S]** Si el camino equivalente de la capa queda por debajo de un umbral, la espoleta no se arma y el proyectil sigue sin detonar.
2. **Recorrido con retardo.** `distancia = v_residual × fuze_delay`, medida desde el punto de salida de la capa. **[S]** Se supone velocidad constante durante el retardo, que es muy corto.
3. **Punto de detonación.** Si cae dentro del vehículo, detona ahí. **[A]** Si cae fuera porque lo ha atravesado entero, hay que definir la regla: lo razonable es que detone fuera y no cause daño interior.
4. **Explosión.** Energía del explosivo repartida entre:
   - **Fragmentos de la carcasa**, en 360°. **[S]** Velocidad por Gurney, distribución de tamaños por Mott.
   - **Onda expansiva**, esfera de rayos con oclusión por los módulos. **[S]** Distancia escalada de Hopkinson-Cranz, más un factor de confinamiento por estar en un espacio cerrado.

**[D] Primera versión: 360° uniforme.** Se mejora si sobra tiempo.

---

## 5. HEAT

La carga hueca cambia la moneda del cálculo.

- **[D] Detona al contacto** con la primera superficie, sin perforación previa.
- **[S] La penetración no depende de la velocidad de impacto ni de la distancia de tiro.** Depende del calibre, del ángulo y de la distancia de detonación (standoff).
- El chorro es un **rayo estrecho** desde el punto de detonación, a lo largo de la dirección de impacto.
- El chorro tiene una **capacidad en mm de RHA equivalente** que se va consumiendo con `camino × resistance` de cada tramo. Cuando se agota, se detiene.
- El ángulo lo resuelve la geometría: para un chorro no hay efecto de inclinación más allá de la línea de visión.

**Blindaje espaciado contra HEAT. [S]** No actúa por material sino por distancia de detonación: el chorro detona antes y llega disperso. **Esto no lo captura la longitud de camino** y hay que tratarlo aparte: una curva de penetración frente a standoff. Es la única parte del modelo donde el blindaje espaciado necesita código propio.

**Conversión a energía.** Para que la rutina de daño de §3.7 sea única, al salir del blindaje la capacidad restante del chorro se convierte a energía con una constante declarada **[S]**. A partir de ahí, chorro y fragmentos se tratan igual.

---

## 6. Parámetros libres

Es la parte más difícil de defender, porque **no hay datos para calibrarla**: las tablas solo cubren la perforación, no los efectos tras el blindaje. Cada parámetro es un número que hay que justificar o declarar como supuesto.

Van todos en `data/fragmentation.csv`, una fila por tipo de proyectil, nunca escondidos en el
código (§1). **El fichero no existe aún a 26/10/2026**; se crea con el núcleo en noviembre. Los
parámetros que no dependen del proyectil van en un `data/parametros.csv` de pares clave-valor,
y los `Health` de los módulos salen del `.glb`.

| Parámetro | Depende de | Qué controla |
|---|---|---|
| `n_fragments` | tipo, espesor/calibre, energía residual | cuántos rayos se lanzan |
| `cone_half_angle` | tipo | cuánto se abre la metralla |
| `spall_fraction` | material y espesor/calibre | reparto entre metralla y núcleo |
| `ricochet_angle` | tipo, calibre/espesor | umbral de rebote |
| `k_absorcion` | — | pérdida de energía por recorrido |
| `umbral_crew_torso` | — | energía de entrada que incapacita (§3.7.2). **Sin validar**, y el que más probabilidades tiene de cambiar |
| `umbral_crew_piernas` | — | múltiplo del umbral del torso (§3.7.1) |
| `fuze_arm_threshold` | solo APHE | espesor mínimo para armar |
| `standoff_curve` | solo HEAT | penetración frente a distancia de detonación |

**Esta tabla es la sección de limitaciones de la memoria.** Cuantos menos parámetros, más defendible el modelo.

Fuentes a consultar, verificando rangos de validez: Rosenberg y Dekel, *Terminal Ballistics*; Zukas, *Impact Dynamics*; Bird y Livingston, *WWII Ballistics: Armor and Gunnery*.

---

## 7. Salida: línea temporal

El cálculo devuelve una lista de eventos con instante y posición, que el render reproduce a cámara lenta. Formato JSON, que es también lo que comparan las pruebas.

Tipos de evento: `impact`, `ricochet`, `stopped`, `perforation`, `fragment_spawn`, `module_hit`, `detonation`, `exit`.

**Estado final del vehículo. [D]** Por ahora solo se muestra el daño acumulado por módulo. **[A]** Más adelante, reglas de «fuera de combate»: munición alcanzada, o muerte de un tripulante crítico. Hay que definirlas antes de la entrega.

---

## 8. Validación

**Pruebas como datos.** Cada caso es un JSON con el rayo de entrada y el resultado esperado. Cuando se elija motor y se porte el núcleo, los mismos ficheros validan la versión nueva. Eso convierte la elección de motor en algo casi secundario: el motor solo dibuja la línea temporal.

**Prueba de regresión ya verificada** (22/10/2026), con `tools/raycast_test.py` sobre `models/Pz IV H.glb`:

| | |
|---|---|
| Origen / dirección | (0,50, −2,00, 1,90) / (0, 1, 0) |
| Primer impacto | `Upper_Front_Plate` |
| Entrada / salida (Y) | −0,05634 / +0,02466 |
| Longitud de camino | **81,00 mm** |
| Ángulo respecto a la normal | **9,00°** |
| Propiedades | `Thickness_mm` 80, `Armour_Material` RHA |

Los 81,00 mm son los 80 nominales divididos por el coseno de 9°. Si el cálculo devuelve 80,0 es que está midiendo con la propiedad y no con la geometría.

**Validación contra las tablas.** Pruebas automáticas que disparen contra una placa plana a los ángulos y distancias tabulados y comprueben que el resultado reproduce la tabla.

**[A] Pero esto por sí solo es circular, y hay que decirlo.** `penetration.csv` es la *entrada* del modelo, así que reproducir la tabla demuestra que la interpolación y la geometría funcionan, no que el modelo acierte. Es una prueba de regresión necesaria, no una validación.

Para que haya validación hacen falta datos **independientes de los que alimentan el modelo**. La vía más practicable aprovecha la columna `criterion` de §2.2: alemanes, británicos y estadounidenses midieron el mismo cañón con criterios de penetración distintos. Si el modelo, alimentado con la tabla alemana, reproduce las mediciones aliadas del KwK 40 dentro de un margen declarado, eso ya no es circular. Localizar esas mediciones es tarea abierta y es la pregunta que va a hacer el tribunal.

El resultado de §2.2.1 sobre el exponente de De Marre **sí** es validación real, y conviene presentarlo como tal: dos conjuntos de datos históricos independientes coinciden con una relación teórica que no interviene en la elaboración de ninguno de los dos.

---

## 9. Limitaciones declaradas

- Un APHE que no perfora puede romperse o detonar en superficie; no se modela.
- Una placa gruesa golpeada cerca de su límite puede astillar por dentro sin ser perforada; no se modela.
- Sin deformación real del blindaje ni del proyectil: solo una marca del agujero.
- Las caras de canto dan un ángulo y un espesor no representativos. Hay que tratar aparte las caras cuya normal es casi perpendicular a la normal exterior de su placa.
- La suposición de convexidad (§3.1).
- Los parámetros de §6 no están calibrados contra datos de efectos tras el blindaje.
- **El criterio de incapacitación de la tripulación es una convención sin validar** (§3.7.2). La fuente que documenta su origen recomienda explícitamente no usar umbrales de energía para esto. Se usa por falta de alternativa dentro del alcance, no por estar respaldado.
- La velocidad del Gr. 38 Hl/C está puesta como constante y no lo es (§2.2.1). Irrelevante para su penetración, que no depende de la velocidad.
- La validación contra tablas es circular mientras no haya datos independientes (§8).
- **`Gun` es una sola caja para recámara y tubo**, y no se comportan igual: el tubo es acero macizo y sale por delante del mantelete, la recámara es un mecanismo de precisión y va dentro. Con un único `Health` un impacto en el tubo cuenta lo mismo que uno en el cierre. Si hace falta, se parte en `Gun_Barrel` y `Gun_Breech` con valores distintos.

---

## 10. Pendientes

- [x] ~~`striking_velocity_ms` del PzGr. 39~~ (§2.2.1, 23/10/2026).
- [x] ~~Velocidad del PzGr. 40~~ (§2.2.1, 24/10/2026, cinco puntos medidos).
- [x] ~~Citar el umbral de incapacitación~~ (§3.7.2, 24/10/2026: la fuente localizada recomienda *no* usar umbrales de energía; el valor queda como convención declarada).
- [x] ~~Comprobación de convexidad en el validador~~ (23/10/2026).

**Datos**

- [ ] **Corregir la masa del núcleo del PzGr. 40 en `shells.csv`.** El valor `0,9` en hectogramos son 90 g; el núcleo de tungsteno ronda los 0,85 kg, un 21 % de los 4,1 kg totales. Pasar la columna a `core_mass_kg` (§2.1).
- [ ] Decidir si se borra la columna `cd` de `shells.csv` o se deja como respaldo documentado (§2.2.1).
- [ ] Velocidad real del Gr. 38 Hl/C, o dejarla declarada en §9 como está.
- [ ] Dar claves a `data/sources.md` y rellenar `source_id` en las tres tablas. Hoy es una lista plana de URL, así que ninguna cifra es trazable a su fuente.
- [ ] Columna de 60° para los dos proyectiles cinéticos. Vendrá de ensayos aliados, que son además los datos independientes que pide §8.
- [ ] `fuze_delay_ms` del PzGr. 39 (ver §4: la espoleta Bd.Z. 5103 no lleva retardo de diseño).
- [ ] Literatura de *behind-armour debris* para justificar el rango del `spall` (§2.3).

**Modelo y alcance**

- [ ] **Consultar con el tutor el criterio de incapacitación** (§3.7.2), planteado como cuestión de alcance.
- [ ] Datos de penetración independientes para romper la circularidad de §8.
- [ ] Regla de detonación de APHE fuera del vehículo (§4).
- [ ] Reglas de «fuera de combate» (§7), incluida la agregación de §3.7.3.
- [ ] Resolver las cuatro piezas no convexas pendientes (§3.1).
- [ ] Abrir el hueco del anillo de torreta en el techo del casco si vuelve a hacer falta: `ARM_Top_Plate` fue sustituida por 12 cuñas más la pieza trasera el 24/10/2026.

**Segundo vehículo [A]**

- [ ] Decidir si el T-44 entra, y si entra, si es **sólo blanco** (no requiere ni un dato nuevo de munición) o también **tirador** (duplica la tabla de proyectiles con el ZiS-S-53 de 85 mm). Casco sencillo y muy inclinado, torreta fundida redondeada: ejercita justo la parte del modelo que justifica medir la geometría, y por eso vale más como demostración que un segundo vehículo de planchas planas.
