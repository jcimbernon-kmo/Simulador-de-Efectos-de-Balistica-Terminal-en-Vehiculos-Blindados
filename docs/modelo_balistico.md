# Modelo balístico

Documento de diseño del núcleo de cálculo. Define qué se simula, con qué datos y con qué fórmulas, antes de programarlo.

Convención: **[D]** decidido · **[S]** supuesto, pendiente de fuente o de verificación · **[A]** abierto, hay que decidirlo.

Última revisión: 2026-10-29 (6ª).

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
| `type` | — | `AP`, `APCBC-HE`, `APCR`, `APHE`, `HEAT` |
| `caliber_mm` | mm | calibre del arma. **No se toca nunca**: ver la nota de abajo |
| `core_diameter_mm` | mm | solo APCR: diámetro del penetrador. Vacío = se usa `caliber_mm` |
| `mass_kg` | kg | proyectil completo |
| `core_mass_kg` | kg | solo APCR: masa que de verdad penetra |
| `muzzle_velocity_ms` | m/s | |
| `explosive_mass_g` | g | equivalente en TNT; 0 si no lleva |
| `fuze_delay_ms` | ms | solo con explosivo (ver §4) |
| `cd` | — | coeficiente de arrastre; **solo respaldo** si no hay fila en `velocity.csv` (§2.2.1) |
| `source_id` | — | clave en `data/sources.md` |

**[D] Todas las masas en kg.** El fichero llegó a tener una columna `core_mass_hg` en hectogramos, unidad que no aparece en ningún otro sitio del proyecto y que existía sólo porque hacía parecer correcto un valor equivocado. Una sola unidad por magnitud en todo el proyecto: kg, m, m/s, J, y mm únicamente para espesores y calibres, por ser la convención de las fuentes.

**[D] El proyectil tiene dos tamaños y los dos hacen falta** (29/10/2026). El APCR es un cuerpo
de 75 mm que lleva dentro un núcleo de carburo de tungsteno, y en el impacto el cuerpo se
descascarilla: lo que perfora es el núcleo. Así que hay dos pares de columnas y el cargador deriva
de cada par el valor que usa la física:

```
penetrating_mass_kg     = core_mass_kg     o mass_kg     si está vacía
penetrating_diameter_mm = core_diameter_mm o caliber_mm  si está vacía
```

**`caliber_mm` se queda en 75 también para el APCR**, y no se sobrescribe con el diámetro del
núcleo, por tres razones. Es la identidad del proyectil y lo que lo liga al arma y a las tablas:
un `shells.csv` que dijera «75 → 28» afirmaría que el PzGr. 40 es un proyectil de 28 mm. El `cd`
de vuelo describe el cuerpo de 75 mm, así que calibre y `cd` son una pareja que hay que mantener
coherente. Y el umbral de rebote de §6 depende de «calibre/espesor», donde lo que rebota es el
cuerpo con su cofia, que es lo que toca la placa primero; el núcleo todavía no ha llegado.

Lo que cuesta confundirlos: contra la placa frontal de 80 mm, usar 75 mm en vez de 28 multiplica
la masa de tapón de §3.5 por (75/28)² = 7,2, y la fracción de astillado del PzGr. 40 pasa de 0,313
a 0,765. El número equivocado sale plausible, que es lo que lo hace peligroso, así que
`ballistic_data.spall()` saca el diámetro del propio proyectil en vez de dejarlo a elección de
quien llama.

**[S] `core_diameter_mm` del PzGr. 40 = 28 mm.** No se ha localizado el dato en ninguna fuente:
la ficha del KwK 40 da masa, velocidad y penetración pero no toca el núcleo. El valor se **deriva**
de `core_mass_kg` = 0,85 kg con carburo de tungsteno a ~15 000 kg/m³, suponiendo un núcleo
cilíndrico: sale 27–31 mm según la esbeltez que se adopte (L/d de 3,5 a 2,5), y 28 mm corresponde
a L/d ≈ 3,3. La suposición que hay que declarar es la esbeltez, no el diámetro. Pendiente de
fuente en §10.

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

Una sola tabla para blindaje y para módulos. El blindaje de referencia es RHA, con coeficiente 1,0.

| Campo | Notas |
|---|---|
| `id` | `RHA`, `Steel`, `Track`, `Wheel`, `Flesh`, `Cast_Iron`, `Ammo`, `Engine`, `Gasoline`, `Diesel`. Mayúscula inicial `.glb` |
| `resistance` | **[S]** resistencia relativa a RHA; multiplica la longitud de camino para obtener el equivalente en RHA |
| `spall` | **[S]** multiplicador de masa de tapón relativo a RHA, que es 1,0. |
| `source_id` | clave en `data/sources.md`, o la palabra «supuesto» |

**[D] El nivel absoluto del astillado lo fija Recht-Ipson** (§3.5 y §3.6).
La columna no es «cuánta energía astilla», que es lo que decía la versión anterior de este
apartado, sino **cuánta masa de tapón arranca este material comparado con el RHA**, con la misma
convención relativa que `resistance`.

Siete de los nueve valores son 0 o 1 por una razón física declarable, no por estimación: los
líquidos y la carne no arrancan tapón ni lanzan fragmentos metálicos, un impacto en munición lo
resuelve la detonación de §4, y no hay base para distinguir `Steel` del RHA en esto, así que
fingir un 0,8 sería ruido. Los dos únicos valores discutibles son:

**[S]** `Cast_Iron` a 1,5: frágil, rompe en fragmentos en vez de sacar un tapón limpio, así que la
masa que sale por detrás es mayor que la del cilindro geométrico.

**[S]** `Track` a 0,3: una oruga son eslabones con huecos, no hay tapón coherente que arrancar.
Mismo argumento que su `resistance` de 0,7.

`Engine` y `Diesel` siguen sin usarlos ningún objeto del `.glb` y están pendientes de borrarse;
llevan valor para que la tabla no tenga huecos, no porque hagan falta.

**[S] `Wheel`, añadido el 29/10/2026** y asignado a las veinte ruedas (dieciséis de rodadura, dos
motrices y dos tensoras). Es el mismo caso que `Track`: **la simplificación está en la geometría y
la corrección va en el material** (§9). Una rueda real son dos chapas estampadas con aire en medio,
unos 20 mm de acero que atravesar; la malla la hace maciza, así que el camino medido es de 150 mm
y hay que corregirlo. El nombre no afirma que la rueda no sea de acero: `RHA` vale 1,0 y `Steel`
0,6 y los dos son acero, así que la tabla ya distingue aceros por su comportamiento balístico y no
por su composición.

**[A] Las dos columnas de `Wheel` no son coherentes entre sí.** `spall` = 0,13 está calculado sobre
los 20 mm de acero real (20/150, sin factor de calidad porque el tapón es masa). `resistance` = 0,40
implicaría 100 mm de acero real, que es cinco veces más:

```
resistance = acero_real_mm × 0,6 / camino_modelado_mm       ->  20 mm da 0,08
```

Con 0,40 el flanco suma 14 mm de oruga + 60 de rueda + 30 de costado = **104 mm de RHA
equivalente**, contra los 81 mm del frontal de 80 mm a 9°: el modelo diría que el Pz IV está mejor
protegido por el costado que por el morro. Hay que fijar el número a partir de los milímetros de
acero que se crea que hay, y que las dos columnas salgan del mismo supuesto. Pendiente en §10.

### 2.4 Objetos del modelo

**Placas** (`ARM_*`): `Thickness_mm` (float), `Armour_Material` (texto, id de materiales).

**Módulos** (`MOD_*`): `Module_Type` (texto, con mayuscula inicial: `Crew`, `Engine`, `Transmission`, `Ammo`, `Fuel`, `Gun`), `Health` (**[D] float**), `Armour_Material` (texto, misma tabla).

**[D] Los módulos no llevan propiedad de espesor**: la longitud de camino por dentro de su caja ya la da la malla. Un fragmento que entra de refilón por una esquina del motor atraviesa menos que uno que lo cruza entero.

**[D]** El código distingue por propiedades, no por colección ni por prefijo: glTF no transporta las colecciones de Blender. Los prefijos del nombre son una red de seguridad.

---

## 3. Flujo de un disparo cinético (AP, APCBC-HE, APCR)

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

**[D] Módulos con `Armour_Material` y la cadena de capacidad. Resuelto el 29/10/2026.** Las orugas son un módulo (`Track`, §3.7.1), no una placa, y `validate_glb.py` rechaza un objeto con `Thickness_mm` y `Module_Type` a la vez. Como módulo, la oruga frena el rayo por energía (§3.7); si además no consumiera capacidad, un disparo lateral que la cruza llegaría al flanco con la capacidad intacta y la oruga no protegería de nada.

**Decisión: todo tramo con `Armour_Material` resta capacidad, sea placa o módulo**, con `t_equivalente = camino × resistance`. No es una excepción para las orugas sino el caso general, y es la misma regla que gobierna la parada de §3.4.2.

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

### 3.4.2 Qué detiene al proyectil

**[D] Una sola cuenta de estado: la energía. La capacidad se deduce de ella. Resuelto el
29/10/2026** tras el primer disparo completo, que es lo que documenta §3.4.3. Hasta entonces el
modelo llevaba **dos contabilidades en paralelo** por rutas distintas —la capacidad en milímetros
de §3.4.1 y la energía en julios de §3.7— y se contradecían.

Con `P ∝ vⁿ` y `E = ½mv²`, las dos son la misma magnitud en unidades distintas:

```
P = P0 · (E / E0)^(n/2)                 E = E0 · (P / P0)^(2/n)
```

| | Decide si atraviesa | Decide cuánto daño hace |
|---|---|---|
| **Núcleo** | La capacidad deducida de su energía | Esa misma energía |
| **Fragmentos** | Energía (§3.7) | Energía (§3.7) |

Los fragmentos siguen gobernados solo por energía: no figuran en las tablas de penetración, así que
no tienen capacidad y la energía es lo único que hay para ellos.

**Tres consecuencias, todas a favor:**

1. El presupuesto cerrado de §1 se cumple **por construcción**, no por comprobación.
2. Las tablas de penetración quedan como **único anclaje** del modelo.
3. **`σ_RHA` deja de intervenir en el núcleo**, y con ella `k_absorcion` de §6. Queda solo como
   anclaje posible de `sigma_fragmento`, que es lo que hará falta al implementar §3.6.

Lo que no cambia: el núcleo **no se detiene por energía agotada en medio del compartimento**. Lo que
lo detiene sigue siendo que el camino equivalente de la capa supere su capacidad, y ahora las dos
magnitudes se agotan juntas, así que la distinción ya no puede producir el desacuerdo que la
motivaba. `tools/disparo.py` lo comprueba en cada disparo y avisa si ocurriera.

**[D] Condición de parada del núcleo.** Al llegar a una capa nueva:

```
si t_equivalente(capa) > P_residual  →  evento `stopped`
```

**[D] El proyectil se queda clavado, no desaparece.** Entra en la capa la profundidad que le
permitía su capacidad restante y se detiene ahí. Cuesta lo mismo que hacerlo desaparecer, conserva
la información de dónde acabó el disparo, y *muestra* por qué no pasó en vez de solo decirlo. Es
además lo que ya decía §3.7 («el rayo se detiene dentro del objeto»).

### 3.4.3 Por qué se unificaron las dos cuentas *(29/10/2026, con `tools/disparo.py`)*

**[D] Resuelto: se adopta la cuenta única de §3.4.2.** Lo que sigue es el diagnóstico que lo forzó,
y se conserva porque es el ejemplo más claro de que escribir el núcleo antes de modelar el interior
completo era la decisión correcta: sobre el papel las dos cuentas convivieron cuatro revisiones del
documento, y el primer disparo real las rompió en treinta segundos.

El primer disparo completo se hizo con el PzGr. 39 a 100 m, origen (0,50, −2,00, 1,30) y
dirección +Y: frontal de 80 mm, el compartimento delantero con tripulantes y cartuchos, separador y
placa trasera. Con §3.4.1 y §3.7 **tal como están escritos** da un resultado imposible. El núcleo
se queda sin energía en el tercer cartucho, a los 2,9 ms, y aun así sigue «perforando» el
separador y la placa trasera con 56 mm de capacidad. A 1 m/s eso son 2 932 ms hasta la salida.

La causa son las dos cuentas de §3.4.2, que usan **dos leyes distintas** para el mismo gasto:

- **Capacidad (§3.4.1):** Recht-Ipson, `P^(2/n) − t^(2/n)`. Una capa delgada cuesta poco, porque
  la energía que se lleva crece como `(t/P)^1,4`.
- **Energía (§3.7):** lineal en el espesor, `σ · A · t`, y calibrada justo en `t = P`. Para una capa
  delgada sobrestima. Un cartucho (76 mm de camino a `resistance` 0,2, o sea 15 mm de RHA
  equivalente) cuesta 208 kJ por σ y 65 kJ por Recht-Ipson.
- Además la cadena de §3.4.1 usa `a = 1` y la energía de §3.5 usa la `a` real (0,71 en el frontal).
  Tras los 81 mm de camino del frontal la capacidad es 74,9 mm por la cadena y 58,5 mm por la
  velocidad real del núcleo.

Con `a = 1` las dos cuentas son **la misma ley**: `E_sale/E_entra = (P_sale/P_entra)^(2/n)`. Por
eso se puede llevar un solo estado, la energía, y deducir la capacidad de ella:
`P = P0 · (E/E0)^(n/2)`. `disparo.py --modelo unificado` lo hace; `--modelo doc` es el texto actual.

| Mismo disparo | `doc` | `unificado` |
|---|---|---|
| Energía del núcleo tras los tres cartuchos | 0 | 337 kJ |
| Salida por la placa trasera | con 0 J, a los 2 932 ms | con 107 kJ y 16,7 mm, a los 13,0 ms |
| Tripulantes fuera de servicio | conductor | conductor y artillero |
| Cartuchos detonados | 3 | 4 |

**[D] Adoptado el modelo unificado el 29/10/2026.** `tools/disparo.py` ya no tiene interruptor: la
rama `doc` y el parámetro `--modelo` se han eliminado, y `sigma_rha()` se conserva en el fichero
solo como anclaje futuro de `sigma_fragmento`, sin intervenir en el cálculo.

Dos efectos que hay que arrastrar al resto del documento:

- **σ_RHA deja de intervenir en el núcleo** y queda solo para los fragmentos, que no tienen
  capacidad. Baja `k_absorcion` de §6 y entra `sigma_fragmento`, sin fijar.
- **Cambia el `Health` calibrado con la ley lineal.** El «núcleo de 75 mm, 10 cm dentro del motor»
  de §3.7.1 pasa de 425 kJ a unos 225 kJ, así que los valores de partida de `Engine` y
  `Transmission` están calibrados contra una ley que ya no se usa. Pendiente en §10.

### 3.5 Energía residual

**[S]** Límite balístico de la capa derivado de la tabla (tipo De Marre, exponente ≈0,7 — verificar), y velocidad residual por Recht-Ipson. **Es el punto de calibración del modelo entero**, y desde el 29/10/2026 es además el único: la capacidad se deduce de la energía que sale de aquí (§3.4.2), no se lleva por separado.

Recht-Ipson con `p = 2`:

```
v_residual² = a · (v_impacto² − v_límite²)      con  a = m_p / (m_p + m_tapón)
```

**[D] La `a` de Recht-Ipson no es una constante de ajuste.** Es la masa del proyectil sobre la del
proyectil más el **tapón** que arranca de la placa, y sale de su propio balance de energía: el
tapón se va a la misma `v_residual` que el núcleo, y el trabajo de cizallarlo es justo el término
`½·m_p·v_límite²`. Consecuencia directa: la energía residual es la de los dos, no solo la del
núcleo, y la definición anterior (`½·m·v_residual²` con `m` la masa del proyectil) se dejaba fuera
la del tapón.

```
E_residual = ½ · (m_p + m_tapón) · v_residual²
```

**[D] `m_tapón` es geometría, no un parámetro libre:**

```
m_tapón = ρ_acero · camino · (π/4)·d² · spall        ρ_acero = 7850 kg/m³
```

con el `camino` de §3.1, que ya lleva la inclinación de la placa dentro, `d` el diámetro del
penetrador —el del **núcleo** en el APCR, no el calibre del casquillo— y `spall` el multiplicador
por material de §2.3, que vale 1 para el RHA. Para el PzGr. 39 contra los 80 mm del frontal son
2,77 kg de tapón contra 6,8 kg de proyectil.

El `spall` entra aquí y no en el reparto de §3.6 por una razón: así `Flesh` a 0 significa «no hay
tapón», que es lo que pasa de verdad, y no «hay tapón pero su energía desaparece», que rompería el
presupuesto cerrado de §1.

### 3.6 Núcleo y fragmentos

**[D] El núcleo sigue.** Un AP macizo que perfora no se convierte entero en metralla: el núcleo continúa como un rayo más, con la mayor parte de la energía, y puede atravesar el motor y salir por el otro lado.

**[D] El reparto de la energía residual sale de la misma `a` de §3.5 y no de un parámetro libre.**
Núcleo y tapón salen a la misma velocidad, así que la energía se reparte por masa:

```
E_núcleo    = E_residual · a        =  E_residual · m_p     / (m_p + m_tapón)
E_astillado = E_residual · (1 − a)  =  E_residual · m_tapón / (m_p + m_tapón)
```

**El núcleo no le cede energía al tapón.** El coste de arrastrarlo ya está pagado dentro de
`v_límite`, así que el núcleo se queda con `½·m_p·v_residual²` entera. La versión anterior de este
apartado restaba el astillado del núcleo (`E_núcleo = E_residual − E_astillado`), lo que
contradecía a Recht-Ipson y contaba dos veces el mismo trabajo.

El presupuesto cerrado de §1 se cumple y es comprobable: PzGr. 39 a 750 m/s contra una capa de
600 m/s de límite, y los 1,913 MJ de entrada salen como 0,489 MJ de núcleo + 0,200 MJ de tapón +
1,224 MJ de cizalla.

Lo que da con los espesores del Pz IV H para el PzGr. 39 (75 mm, 6,8 kg) sobre RHA:

| Espesor | t/d | m_tapón | `1 − a` |
|---|---|---|---|
| 20 mm (faldón) | 0,27 | 0,69 kg | 0,093 |
| 30 mm (costado) | 0,40 | 1,04 kg | 0,133 |
| 50 mm | 0,67 | 1,73 kg | 0,203 |
| 80 mm (frontal) | 1,07 | 2,77 kg | 0,290 |

Con el PzGr. 40 (núcleo de ~30 mm y 0,85 kg) va de 0,115 a 0,343 en el mismo rango de espesores,
que es lo esperable: un núcleo ligero arrastra un tapón comparable a su propia masa. Ese 9–34 %
cae dentro del rango que cita la literatura de *behind-armour debris*, así que el anclaje no es
solo interno al modelo.

Los fragmentos son el astillado de la placa más los trozos que pierde el proyectil. Se generan `N` rayos dentro de un cono alrededor de la dirección de salida, repartiéndose `E_astillado`.

### 3.7 Pérdida de energía y daño

**[D] La energía perdida depende del área frontal del penetrador, no solo del camino.** Una constante global por unidad de longitud no vale: un núcleo de 75 mm y una esquirla de 3 mm no depositan lo mismo por milímetro recorrido, porque la resistencia del material actúa sobre la sección que empuja.

**[D] El núcleo: la pérdida sale de la cadena de capacidad (§3.4.2, 29/10/2026).** Para cada tramo,
con `t_eq = camino × resistance`:

```
P_entrada = P0 · (E / E0)^(n/2)                     la capacidad que le corresponde a su energía
P_salida  = (P_entrada^(2/n) − t_eq^(2/n))^(n/2)    la cadena de §3.4.1
E_salida  = E · (P_salida / P_entrada)^(2/n)
si el módulo es acumulativo (§3.7.1):  Health -= (E − E_salida)
```

Y al perforar una placa, la energía que sale es la `E_núcleo` de §3.6, con el tapón ya descontado,
de la que se vuelve a deducir la capacidad. Así el reparto de Recht-Ipson y la cadena no son dos
cuentas que haya que conciliar: la segunda es consecuencia de la primera.

**El núcleo no se detiene por energía agotada**, sino porque el camino equivalente de la capa supera
su capacidad (§3.4.2). Ahora las dos se agotan juntas.

**Fragmentos.** No tienen capacidad, así que conservan la ley por recorrido:

```
E -= camino × resistance_material × σ_fragmento × (π/4)·d²
si E <= 0: se detiene dentro del objeto
```

con `camino` en metros, `d` el diámetro del fragmento en metros y `σ_fragmento` una resistencia
dinámica en Pa. **[A] Está sin fijar** (§6): una esquirla no figura en ninguna tabla de penetración,
así que no se puede derivar por el procedimiento de abajo y hay que declararla o anclarla de otro
modo.

**[D] De dónde salía `σ_RHA`, que el núcleo ya no usa pero sigue siendo el único anclaje
disponible.** En el límite balístico el proyectil deposita toda su energía en el espesor que justo perfora:

```
σ_RHA = E_impacto / (espesor_perforado × área_frontal)
```

Con el PzGr. 39 perforando 135 mm a 100 m y 0°, sobre sus 44,18 cm² de sección y con la velocidad
real de impacto a esa distancia (738 m/s, 1,852 MJ): **σ_RHA ≈ 3,10 GPa**.

**Recalculado el 29/10/2026.** La versión anterior daba 3,21 GPa porque usaba la velocidad de boca
(750 m/s) para la penetración a 100 m, a falta de un cargador de `velocity.csv`. Ya existe (§2.2.1),
así que el valor correcto es 3,10 y el pendiente queda cerrado.

**[D] Y el anclaje resiste un contraste independiente.** Repitiendo la misma cuenta con el
PzGr. 40, que es un proyectil completamente distinto —0,348 MJ de energía penetrante frente a
1,852, un núcleo de 28 mm frente a 75 mm de calibre, y 176 mm perforados frente a 135— sale
**σ_RHA ≈ 3,21 GPa**:

| Proyectil | E a 100 m | Perfora | d penetrador | σ_RHA |
|---|---|---|---|---|
| PzGr. 39 | 1,852 MJ | 135 mm | 75 mm | 3,10 GPa |
| PzGr. 40 | 0,348 MJ | 176 mm | 28 mm | 3,21 GPa |

Dos proyectiles con un factor cinco de diferencia en energía dan σ dentro de un 3,5 %. Eso **sí es
validación**, del mismo tipo que el resultado del exponente de De Marre de §2.2.1: σ no se ha
ajustado a ninguno de los dos, y aun así los dos coinciden. Conviene presentarlo como tal en la
memoria, porque es uno de los pocos resultados del proyecto que no es circular (§8).

Queda una limitación del anclaje, que va a la memoria: en el límite no *toda* la energía va a la
placa, algo queda como velocidad residual, así que σ sale ligeramente sobrestimada en los dos
casos.

**Corregido el 29/10/2026.** Esta tabla decía 2,80 GPa para el PzGr. 40, que sale con un núcleo
de 30 mm; con los 28 mm de `shells.csv` sale 3,21 (lo calcula `disparo.py`). **Ojo con lo que vale el
contraste:** σ es inversamente proporcional a `d²`, y los 28 mm son [S] (§2.1, derivados de la masa
y de un L/d supuesto). El acuerdo entre 3,10 y 3,21 es real, pero depende de ese diámetro sin fuente;
con 30 mm saldrían los 2,80 de antes.

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
| `Track` | **[S]** Igual que `Crew`: inmovilizado si un penetrador **cruza** el objeto con energía de entrada por encima de **su** `Health`, que es un umbral propio de cada objeto. Lo llevan la cinta de la oruga y la rueda motriz |
| `Ammo`, `Fuel` | Umbral de detonación / ignición (§4, §7) |

El rayo sigue frenándose igual en todos los casos: lo único que cambia es cómo se traduce eso en daño.

**[D] `Health` significa dos cosas según la regla, y solo una se decrementa.** Decidido el
29/10/2026, al tropezar con que §3.7 resta `Health` en todo módulo que lo tenga, lo que choca con
las cuatro filas de umbral de la tabla de arriba:

| Regla | Qué es `Health` | Qué le pasa durante el disparo |
|---|---|---|
| Acumulativa (`Engine`, `Transmission`, `Gun`) | **Reserva** en julios | Se decrementa. El estado es la fracción que queda |
| Umbral (`Crew`, `Track`, `Ammo`, `Fuel`) | **Umbral** de energía de entrada | **No se decrementa nunca.** El estado es un booleano |

Si en los tipos de umbral se restara, el número resultante no significaría nada: ni reserva
restante, porque no hay reserva, ni distancia al umbral, porque el umbral se compara contra la
energía de **entrada de un solo impacto** y no contra una suma acumulada. Sería un residuo, y
cualquier cosa que lo leyera estaría trabajando con ruido: el color de §7.2 el primero, pero
también las reglas de «fuera de combate» de §7 y la agregación de §3.7.3.

Es el mismo argumento que ya justificaba el umbral de la oruga en esta misma sección —una cinta no
se rompe por la suma de muchas esquirlas, sino cuando algo corta un eslabón— aplicado al campo en
vez de a la regla.

**[D] La oruga es un módulo porque su avería inmoviliza el vehículo**, y por eso no es una placa. **[S] Umbral y no acumulación**, por una razón de modelado y otra física. La de modelado: las orugas son 21 piezas por lado solo porque cada una debe ser convexa (§3.1), y con daño acumulativo el resultado dependería de cómo se ha cortado la cinta. La física: una oruga no se rompe por la suma de muchas esquirlas pequeñas, sino cuando algo corta un eslabón o un pasador. **[S] `Health` = 5 kJ**, orden de magnitud propio, sin fuente: cizalla doble de un pasador de Ø25 mm (≈ 400 MPa × 2 × 4,9·10⁻⁴ m² ≈ 400 kN sobre ≈ 8 mm de recorrido ≈ 3 kJ). Cualquier AP que la cruce lo supera con holgura; el astillado, que llega con cientos de julios, no. Parámetro libre del análisis de sensibilidad (§6).

**[D] La rueda motriz también es `Track`, con `Health` = 20 kJ.** Decisión del autor: sin la motriz la oruga no recibe potencia, así que su avería inmoviliza igual que cortar la cinta. **[S] 20 kJ** sin fuente: cuatro veces el de la cinta, por ser una pieza maciza y no un eslabón con pasador. Parámetro libre (§6). Cada objeto `Track` conserva su propio umbral, así que mezclar valores dentro del tipo no plantea ningún problema.

**[A] La tensora.** En el `.glb` del 27/10 tiene `Health` = 16 kJ y **ningún `Module_Type`**, así que hoy el validador la rechaza: no es ni módulo ni placa. La propuesta es que sea módulo `Track`, porque sin ella la cinta pierde tensión y se sale. **[A] Las ruedas de rodadura**, que aún no están modeladas, serían placas: perder una no inmoviliza. Todas las ruedas necesitan un material propio de `resistance` baja, o quedar huecas: una rueda real son dos chapas estampadas con aire en medio. Ver §9.

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
| `Ammo` | **OR**: basta con que uno detone |
| `Gun` | **OR**: tubo y recámara son piezas funcionalmente distintas, y con cualquiera de las dos fuera de servicio el vehículo no puede devolver el fuego. Cada una gasta su propio `Health` |
| `Track` | **OR** entre todos los objetos del tipo, cinta y motriz de ambos lados: basta con que uno caiga. El lado (`_L`/`_R` del nombre) solo sirve para informar de cuál fue |
| `Crew` | OR dentro de cada tripulante, pero cada tripulante cuenta por separado (§7) |
| `Engine`, `Transmission` | **SUMA**: las piezas son un corte de convexidad de una sola máquina, así que su `Health` se suma y la máquina cae cuando el daño acumulado llega al total |
| `Fuel` | Cada objeto, por su cuenta. Hoy hay uno |

Esto evita tener que inventar un tipo nuevo por cada cosa que se modele en varias piezas, y es lo que hace que la decisión de «tubo y recámara separados en el 3D pero un solo módulo lógico» no necesite código especial.

**[D] Hay dos preguntas distintas y antes estaban mezcladas** (corregido el 29/10/2026). Una es
**cómo se acumula el daño dentro de un objeto**, que la responde §3.7.1: acumulativo o umbral. La
otra es **cómo se combinan los veredictos de varios objetos** en uno del módulo, que es esta
sección. Son independientes, y de ahí que `Gun` sea acumulativo dentro de cada pieza y OR entre
ellas.

**[D] Para combinar, lo que decide es por qué hay varias piezas.** Si cada objeto es una unidad
real e independiente (los tripulantes, los depósitos) o una pieza funcionalmente distinta (tubo y
recámara), el veredicto es por objeto y se combinan con OR. Si la división es un artefacto de la
convexidad o del modelado, entonces:

- Con **daño de umbral** (orugas, munición), **OR**. El umbral se compara contra la energía de
  entrada de un solo impacto, así que el resultado no depende de en cuántos trozos se cortó la
  pieza. Es el argumento que ya justificaba las 22 piezas de la oruga en §3.7.1.
- Con **daño acumulativo** (motor, transmisión), **SUMA**. Aquí el OR sí depende del corte, y por
  eso estaba mal. La transmisión son cinco cajas de 30 kJ: con OR, agotar una sola de ellas
  inutilizaría la transmisión entera, o sea 30 kJ en vez de los 150 kJ de la máquina, y cortarla
  en dos cajas de 75 kJ daría otra respuesta. El motor, desde el 29/10, son tres piezas convexas
  (`MOD_Engine_1`, `_2` y `_3`) con los 300 kJ repartidos por volumen en 228,0 / 36,0 / 36,0 kJ:
  con OR, una esquirla afortunada en una pata de 36 kJ dejaría el tanque inmóvil.

Al repartir un módulo acumulativo en varias piezas, **el `Health` se divide por volumen** para que
la suma sea el del conjunto, como hace `tools/crear_canon_motor.py`. Es la pregunta que hay que
hacerse al modelar cualquier cosa nueva en varias piezas.

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
parámetros que no dependen del proyectil van en un `data/parametros.csv` de pares clave-valor (existe desde el 29/10/2026, con `n_de_marre` y `contact_gap_mm`),
y los `Health` de los módulos salen del `.glb`.

| Parámetro | Depende de | Qué controla |
|---|---|---|
| `n_fragments` | tipo, espesor/calibre, energía residual | cuántos rayos se lanzan |
| `cone_half_angle` | tipo | cuánto se abre la metralla |
| `ricochet_angle` | tipo, calibre/espesor | umbral de rebote |
| `sigma_fragmento` | — | pérdida de energía por recorrido, **solo de los fragmentos** (§3.7). **[A] Sin fijar**: 3,10 GPa si se adopta el valor del núcleo como aproximación declarada |
| `umbral_crew_torso` | — | energía de entrada que incapacita (§3.7.2). **Sin validar**, y el que más probabilidades tiene de cambiar |
| `umbral_crew_piernas` | — | múltiplo del umbral del torso (§3.7.1) |
| `fuze_arm_threshold` | solo APHE | espesor mínimo para armar |
| `standoff_curve` | solo HEAT | penetración frente a distancia de detonación |

**Esta tabla es la sección de limitaciones de la memoria.** Cuantos menos parámetros, más defendible el modelo.

**Bajas de la tabla.** `k_absorcion` sale el 29/10/2026 con la unificación de §3.4.2: la pérdida de
energía del núcleo ya no es un coeficiente por recorrido, sino la caída que resulta de la cadena de
capacidad, así que no hay nada que calibrar. Lo que queda es la ley de los fragmentos, que no tienen
capacidad, y de ahí la fila `sigma_fragmento` de arriba. Los parámetros que no dependen del
proyectil viven en `data/parametros.csv` desde el 29/10 (`n_de_marre`, `contact_gap_mm`,
`rho_acero`).

`spall_fraction` sale el 28/10/2026: el reparto entre metralla y núcleo lo
fija la `a` de Recht-Ipson y la masa del tapón, que es geometría (§3.5 y §3.6). De la columna
`spall` de `materials.csv` solo quedan dos números supuestos, `Cast_Iron` y `Track`, y el resto son
0 o 1 por razón física (§2.3). Figuraba además en dos sitios a la vez, aquí por proyectil y en
`materials.csv` por material, y la versión de aquí no podía funcionar: un fichero por proyectil no
sabe en qué material está pegando.

`n_fragments` tampoco es del todo libre, aunque sigue en la tabla: con `m_tapón` conocido y una
distribución de tamaños de Mott, la que ya se usa para la carcasa del HE en §4, el número sale de
`m_tapón / masa_media_fragmento`.

Fuentes a consultar, verificando rangos de validez: Recht e Ipson, *Ballistic Perforation Dynamics*,
J. Appl. Mech. 30(3), 1963 (de donde sale la `a` de §3.5); Backman y Goldsmith, *The mechanics of
penetration of projectiles into targets*, Int. J. Eng. Sci., 1978 (mapa de modos de fallo frente a
t/d); Rosenberg y Dekel, *Terminal Ballistics*; Zukas, *Impact Dynamics*; Bird y Livingston,
*WWII Ballistics: Armor and Gunnery*.

---

## 7. Salida: línea temporal

El cálculo devuelve una lista de eventos con instante y posición, que el render reproduce a cámara lenta. Formato JSON, que es también lo que comparan las pruebas.

Tipos de evento: `impact`, `ricochet`, `stopped`, `perforation`, `fragment_spawn`, `module_hit`, `detonation`, `exit`.

**[D] El esquema se fija antes de escribir el núcleo**, no al llegar a la interfaz. Es el contrato
entre cálculo y render **y** el formato de los casos de prueba de §8: cambiarlo en marzo obliga a
rehacer todos los casos.

**Estado final del vehículo. [D]** Por ahora solo se muestra el daño acumulado por módulo. **[A]** Más adelante, reglas de «fuera de combate»: munición alcanzada, o muerte de un tripulante crítico. Hay que definirlas antes de la entrega. **Inmovilizado** (propuesta): motor o transmisión fuera de servicio, o cualquier objeto `Track` (cinta o motriz, de cualquiera de los dos lados) fuera de servicio (§3.7.3).

### 7.1 Campos de un evento

| Campo | Para qué |
|---|---|
| `type` | uno de los ocho tipos de arriba |
| `t_s` | instante, en segundos desde el primer contacto |
| `ray_id` | identificador del rayo. **Sin él el recorrido no se puede dibujar** |
| `parent_id` | rayo del que nació, o `null` para el núcleo |
| `object` | nombre del objeto del `.glb`, o `null` si el tramo es aire |
| `pos` | punto del evento, en coordenadas del modelo |
| `normal` | normal de entrada de la cara. Hace falta para orientar la marca del agujero de §9 |
| `path_mm`, `angle_deg` | camino dentro de la capa y ángulo respecto a la normal |
| `capacity_in_mm`, `capacity_out_mm` | capacidad antes y después (§3.4.1). Solo en el núcleo |
| `energy_in_J`, `energy_out_J` | energía antes y después (§3.7) |
| `health_in_J`, `health_out_J` | vida del módulo antes y después. Solo en `module_hit` |
| `out_of_service` | **[A]** bool, solo en `module_hit` y `detonation`. En los tipos de umbral `health_out_J` no cambia, así que esto es lo único que dice el estado |
| `plug_mass_kg`, `spall_energy_J`, `shear_energy_J` | **[A]** solo en `perforation`: masa del tapón (§3.5), energía que se lleva (alimentará los fragmentos de §3.6) y energía de cizalla. Con `energy_out_J` cierran el presupuesto de §1 |

**[D] El recorrido es un árbol, no una lista.** En cada `fragment_spawn` nacen N rayos y el núcleo
continúa, así que sin `ray_id` y `parent_id` el render no sabe qué segmento une con cuál. Son dos
campos ahora o espaguetis después.

**[D] La vida del módulo va en el evento aunque sea redundante.** El render podría arrancar de los
`Health` del `.glb` e ir restando, que es lo que hará para pintar el color. Se guarda igual por dos
razones: permite **saltar a un instante cualquiera** de la barra de tiempo sin reproducir desde
cero, y deja que las pruebas de §8 comprueben el daño directamente en vez de recalcularlo.

**[D] Instantes derivados del camino.** `t += camino / v_media_del_tramo`, con las velocidades de
§3.5. §3.4.1 va en capacidad y no produce tiempos por sí sola, así que sin esto la línea temporal
no tiene nada que interpolar.

### 7.2 Reproducción

**[D] Tiempo no uniforme, en tres fases.** El evento dentro del vehículo dura unos 7,5 ms y la
perforación de la placa frontal 120 µs, el 1,6 % del total. Un frame a 60 fps son 16,7 ms, así que
**el disparo entero ocurre dentro de medio frame**. Con una escala única o la perforación es
invisible o el interior es interminable:

| Fase | Duración real | En pantalla | Factor |
|---|---|---|---|
| Aproximación (últimos ~5 m) | 6,7 ms | 1,5 s | ×225 |
| Perforación de la capa | 120 µs | 1,5 s | ×12 500 |
| Interior y fragmentos | 5 ms | 2 s | ×400 |

La aproximación arranca a unos metros del vehículo, no a la distancia de disparo: a 1000 m, mostrar
el vuelo a escala es un minuto de cielo vacío. El vuelo libre no tiene física en el modelo, porque
la penetración sale de la tabla indexada por distancia (§2.2), así que es decorado y puede ir a la
escala que convenga.

**[D] Vista de rayos X al contacto**, con el blindaje en torno al 20 % de opacidad, salvo dos
excepciones:

- **La capa golpeada se queda opaca**, y solo el resto se vuelve translúcido. Si todo se transparenta
  a la vez se pierde justo lo que hay que ver, que es el agujero abriéndose.
- La transparencia **entra desvaneciéndose durante** la fase de perforación, ya estirada a 1,5 s, no
  de golpe antes del impacto.

Con 263 objetos, ordenar transparencias por profundidad se pone caro: el blindaje se dibuja sin
escritura en el búfer de profundidad y sin ordenar, que es suficiente para una cáscara translúcida.

**[D] El color del daño sale de `Health`, pero no todos los módulos llevan degradado.** §3.7.1
define dos reglas de daño y eso parte el mapeo en dos:

| `Module_Type` | Visual |
|---|---|
| `Engine`, `Transmission`, `Gun` | Degradado continuo de `Health / Health_inicial`: gris claro intacto, rojizo al acercarse a cero |
| `Crew`, `Track`, `Ammo`, `Fuel` | **Dos estados**, no degradado: intacto o fuera de servicio |

La razón es del modelo, no del render: en esos cuatro tipos el `Health` es un **umbral** y no una
reserva (§3.7.1), así que no existe nada entre el 100 % y el 0 %. Un degradado ahí mentiría, porque
daría a entender que un tripulante está «medio incapacitado» cuando el modelo solo conoce dos
estados. Gris claro y no blanco puro, que se lava contra el blindaje translúcido.

**[D] Cuatro mallas de proyectil, por revolución de un perfil:** PzGr. 39, PzGr. 40 completo, el
**núcleo desnudo** del PzGr. 40 y el Gr. 38 Hl/C. En el `perforation` de la primera capa el render
cambia la malla del APCR por la del núcleo, porque el penetrador es el núcleo de tungsteno y no el
casquillo (§3.5): mostrar los 75 mm enteros cruzando el interior contradiría la propia física del
modelo. Son objetos **puramente visuales**, sin `Thickness_mm`, sin `Module_Type` y sin material de
§2.3, y van en ficheros aparte (`models/PzGr_39.glb` y compañía), no dentro del vehículo.

---

## 8. Validación

**Pruebas como datos.** Cada caso es un JSON con el rayo de entrada y el resultado esperado. Cuando se elija motor y se porte el núcleo, los mismos ficheros validan la versión nueva. Eso convierte la elección de motor en algo casi secundario: el motor solo dibuja la línea temporal.

**Prueba de regresión ya verificada** (22/10/2026; reejecutada el 29/10/2026 con `tools/disparo.py --selftest`) sobre `models/Pz IV H.glb`:

| | |
|---|---|
| Origen / dirección | (0,50, −2,00, 1,30) / (0, 1, 0) |
| Primer impacto | `Upper_Front_Plate` |
| Entrada / salida (Y) | −0,01831 / +0,06268 |
| Longitud de camino | **81,00 mm** |
| Ángulo respecto a la normal | **9,00°** |
| Propiedades | `Thickness_mm` 80, `Armour_Material` RHA |

Los 81,00 mm son los 80 nominales divididos por el coseno de 9°. Si el cálculo devuelve 80,0 es que está midiendo con la propiedad y no con la geometría.

**El origen cambió el 29/10/2026.** Con la torreta modelada, el rayo a z = 1,90 ya no toca el casco sino `ARM_Turret_Front_Upper` (50,77 mm a 10°), así que la prueba de 22/10 dejó de reproducirse tal cual. A z = 1,30 vuelve a dar `Upper_Front_Plate` con 81,00 mm y 9,00°, y esa comprobación está ahora dentro de `disparo.py --selftest`.

**Validación contra las tablas.** Pruebas automáticas que disparen contra una placa plana a los ángulos y distancias tabulados y comprueben que el resultado reproduce la tabla. **Hecho el 29/10/2026** en `disparo.py --selftest`: para cada una de las 19 celdas de `penetration.csv` de los dos proyectiles cinéticos, una placa del espesor tabulado perfora justo por debajo y se queda clavada un 0,1 % por encima. Confirma la afirmación de §3.4 de que en placa plana el modelo reproduce exactamente la tabla, y hay que reejecutarlo cada vez que se toque `penetration.csv` o el exponente `n`.

**Invariante que la autoprueba comprueba desde el 29/10/2026:** ningún disparo puede acabar con el
núcleo sin energía y con capacidad disponible. Es lo que fallaba con las dos cuentas en paralelo
(§3.4.3), y con la cuenta única no puede ocurrir, así que la prueba está ahí para detectar que
alguien reintroduzca una segunda ley.

**[A] Pero esto por sí solo es circular, y hay que decirlo.** `penetration.csv` es la *entrada* del modelo, así que reproducir la tabla demuestra que la interpolación y la geometría funcionan, no que el modelo acierte. Es una prueba de regresión necesaria, no una validación.

Para que haya validación hacen falta datos **independientes de los que alimentan el modelo**. La vía más practicable aprovecha la columna `criterion` de §2.2: alemanes, británicos y estadounidenses midieron el mismo cañón con criterios de penetración distintos. Si el modelo, alimentado con la tabla alemana, reproduce las mediciones aliadas del KwK 40 dentro de un margen declarado, eso ya no es circular. Localizar esas mediciones es tarea abierta y es la pregunta que va a hacer el tribunal.

El resultado de §2.2.1 sobre el exponente de De Marre **sí** es validación real, y conviene presentarlo como tal: dos conjuntos de datos históricos independientes coinciden con una relación teórica que no interviene en la elaboración de ninguno de los dos.

---

## 9. Limitaciones declaradas

- Un APHE que no perfora puede romperse o detonar en superficie; no se modela.
- Una placa gruesa golpeada cerca de su límite puede astillar por dentro sin ser perforada; no se modela.
- Sin deformación real del blindaje ni del proyectil: solo una marca del agujero.
- **No se modela la rotura del proyectil.** Cuando la capacidad residual no alcanza para la capa siguiente, el núcleo se detiene y se queda clavado (§3.4.2) en vez de fragmentarse. Un núcleo que llega al límite suele romperse de verdad, y eso generaría fragmentos que aquí no existen. La decisión favorece lo conservador: menos daño del real, no más.
- Las caras de canto dan un ángulo y un espesor no representativos. Hay que tratar aparte las caras cuya normal es casi perpendicular a la normal exterior de su placa.
- La suposición de convexidad (§3.1).
- **[D] Los torsos y las piernas del artillero y del cargador se solapan** (47,8 y 33,9 mm) y se dejan así para no rehacer la malla de los tripulantes. No afecta al resultado: §3.7.3 agrega con OR dentro de cada tripulante, así que descontar del torso y de las piernas a la vez da el mismo incapacitado. Sí afecta el solape de dos cartuchos con las piernas del artillero (32,9 y 35,7 mm), porque ahí el camino se cuenta para dos módulos distintos.
- **[D] Las ruedas del tren de rodaje se quedan como prismas macizos**, motriz, tensora y rodadura. Vaciarlas sería mucho modelado para un detalle que no cambia el daño, que es lo que decide el tipo de módulo y no la forma. **Pero entonces el material no puede ser `Steel`**: un disparo lateral cruza una rueda a lo ancho, 150 mm en las de rodadura y 250 mm en la motriz, que con 0,6 son 90 y 150 mm de RHA equivalente sumados al flanco. El costado del casco tiene 30 mm. Una rueda real son dos chapas estampadas con aire en medio, y el acero que cruza de verdad un disparo lateral son unos 20 mm. Hace falta un material `Wheel`, igual que `Track` vale 0,7 para una cinta que en realidad son eslabones con huecos: **la simplificación está en la geometría y la corrección va en el material**. **Resuelto a medias el 29/10/2026**: el material existe y está asignado a las veinte ruedas, pero su `resistance` está puesto a 0,40 de forma orientativa, lo que deja el flanco en 104 mm de RHA equivalente contra los 81 del frontal. El orden sigue invertido y el número está pendiente de fijar (§2.3, §10).
- **La cinta de la oruga es una plancha continua de 20 mm**, y la real son eslabones con huecos. Lo compensa en parte la `resistance` de 0,7 de `Track`, que es un promedio, no una geometría.
- **La distinción entre torso y piernas de §3.7.1 no está en el modelo.** Los diez objetos de tripulación llevan 80 J, piernas incluidas, así que hoy el modelo hace justo lo que ese apartado dice que no hay que hacer.
- Los parámetros de §6 no están calibrados contra datos de efectos tras el blindaje.
- **El tapón cilíndrico de §3.5 es una cota superior fuera del régimen de cizalla.** La fórmula vale mientras la placa falle arrancando un tapón, que es hasta t/d ≈ 1. La placa frontal está justo en el borde (80 mm contra 75 mm de calibre, t/d = 1,07), pero el frontal de torreta y las ruedas de 150 mm están en t/d ≈ 2, donde el fallo real es ensanchamiento dúctil con erosión del núcleo y no hay tapón coherente. Ahí el modelo **sobrestima** el astillado. Referencia del mapa de modos de fallo frente a t/d en §6.
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
- [x] ~~Corregir la masa del núcleo del PzGr. 40~~ (27/10/2026: 0,85 kg en `shells.csv`).
- [x] ~~Decidir qué hacer con la columna `cd`~~ (27/10/2026: se queda como respaldo documentado, rellenada en los dos cinéticos).
- [x] ~~Solicitud para el tutor~~ (27/10/2026).

**Datos**

- [x] ~~Que `ballistic_data.py` lea `data/velocity.csv`~~ (29/10/2026: `velocity(pid, distancia)` e `impact_energy(pid, distancia)`, con validación de que la velocidad no suba con la distancia y de que cuadre con `muzzle_velocity_ms`).
- [x] ~~Recalcular σ_RHA con la velocidad real de impacto~~ (29/10/2026: 3,10 GPa, §3.5, y contraste con el PzGr. 40, que el 29/10 se corrigió de 2,80 a 3,21 GPa, §3.7).
- [x] ~~Diámetro del penetrador del APCR~~ (29/10/2026: `core_diameter_mm`, §2.1). **Falta la fuente**: los 28 mm son derivados de la masa del núcleo, no medidos.
- [ ] **Fijar el `resistance` de `Wheel`.** Está a 0,40 de forma orientativa y deja el flanco por encima del frontal; su `spall` de 0,13 sale de otro supuesto (20 mm de acero real). Las dos columnas tienen que salir del mismo número de milímetros (§2.3).
- [ ] **El renombrado a `APCBC-HE` hace más urgente la contradicción del `fuze_delay_ms`.** El tipo ahora afirma que el PzGr. 39 lleva explosivo, así que le aplica §4 y esa celda gobierna el punto de detonación.
- [ ] `tools/spall.py` y `ballistic_data.spall_fraction()` implementan la misma fórmula de §3.5 en dos sitios. Borrar el primero, que era un borrador, o dejarlo importando del segundo. Contradice el principio de §1.
- [ ] Velocidad real del Gr. 38 Hl/C. Mientras tanto está a 450 m/s constante en las seis filas de `velocity.csv`, declarado en §9.
- [ ] Dar claves a `data/sources.md` y rellenar `source_id` en las tres tablas. Hoy es una lista plana de URL, así que ninguna cifra es trazable a su fuente.
- [ ] Columna de 60° para los dos proyectiles cinéticos. Vendrá de ensayos aliados, que son además los datos independientes que pide §8.
- [ ] **Resolver la contradicción del `fuze_delay_ms` del PzGr. 39.** `shells.csv` dice 3 ms desde el 27/10 y este documento dice que la Bd.Z. 5103 no lleva retardo de diseño. O el 3 tiene fuente y se corrige el documento, o sobra el 3. Gobierna el punto de detonación de §4, así que no es un decimal: decide si el APHE revienta en el compartimento o fuera.
- [x] ~~Literatura de *behind-armour debris* para justificar el rango del `spall`~~ (28/10/2026: el nivel absoluto se deriva de Recht-Ipson en §3.5 y la columna queda con dos supuestos, §2.3).
- [ ] Validar el 9–34 % de §3.6 contra una medida publicada. El que más se parece al caso es *Experimental and analytical study of behind armor debris after perforation of a steel plate by an AP projectile* (FME Transactions, Belgrado); pendiente de conseguir el texto.
- [ ] Confirmar el exponente de Recht-Ipson. §3.5 usa `p = 2`, que es el valor del artículo original para fallo por cizalla, pero conviene verificar que sigue siendo el recomendado para este rango de t/d.

**Modelo y alcance**

- [x] ~~Prueba de extremo a extremo en Python puro~~ (29/10/2026: `tools/disparo.py`, sin rebote, fragmentos ni explosivo).
- [ ] **Decidir el modelo de estado, `doc` o `unificado`** (§3.4.3). Con `doc` el núcleo puede quedarse sin energía y seguir perforando.
- [ ] **Capa compuesta con placas de orientación distinta.** §3.2 suma los caminos, pero la tabla de §3.4 se consulta con un ángulo y `disparo.py` usa el de la primera placa. Caso real: `ARM_Front_Track_Addon_Upper` (70°) delante de `ARM_Middle_Front_Plate`.
- [ ] Rebote (§3.3). A más de 30° la tabla está vacía y `disparo.py` extrapola linealmente; a 70° da 218 mm de capacidad, que no es un dato sino un aviso de que falta el umbral de rebote.
- [ ] Aprobar los cuatro campos nuevos del esquema de §7.1 (`out_of_service`, `plug_mass_kg`, `spall_energy_J`, `shear_energy_J`).
- [ ] `ballistic_data.spall_fraction()` llama `path_eq_mm` a su tercer parámetro, pero §3.5 pide el camino **geométrico**. `disparo.py` le pasa el geométrico. Renombrar el parámetro.
- [ ] **Consultar con el tutor el criterio de incapacitación** (§3.7.2), planteado como cuestión de alcance.
- [ ] Datos de penetración independientes para romper la circularidad de §8.
- [ ] Regla de detonación de APHE fuera del vehículo (§4).
- [x] ~~Orugas: decidir si un módulo con `Armour_Material` consume capacidad en la cadena de §3.4.1~~ (29/10/2026: sí, todo tramo con material de blindaje resta capacidad, §3.4).
- [ ] Dar fuente a los `Health` de `Track`: 5 kJ la cinta, 20 kJ la motriz (§3.7.1).
- [x] ~~Fijar el esquema de la línea temporal~~ (29/10/2026, §7.1), y ~~las reglas de reproducción~~ (§7.2).
- [x] ~~Decidir cuál de las dos cuentas manda~~ (29/10/2026: una sola cuenta, la energía, y la capacidad se deduce de ella; §3.4.2 y §3.4.3).
- [ ] **Recalibrar el `Health` de `Engine` y `Transmission`** (§3.7.1). Los 300 y 150 kJ se fijaron con la ley lineal de `σ_RHA`, que ya no se usa: el «núcleo de 75 mm, 10 cm dentro del motor» pasa de 425 kJ a unos 225 kJ, así que los dos valores están calibrados contra una ley muerta.
- [ ] **Fijar `sigma_fragmento`** (§3.7, §6). Es el único coeficiente de pérdida que queda tras unificar las cuentas, y solo afecta a los fragmentos.
- [ ] **Crear `data/fragmentation.csv`** e implementar los fragmentos de §3.6 y el rebote de §3.3. `tools/disparo.py` no hace ninguna de las dos cosas a 29/10/2026, así que hoy el único daño que se calcula es el del núcleo.
- [ ] **El material `Engine` (0,10) de `materials.csv` no lo usa ningún objeto**: las tres piezas del motor van con `Cast_Iron` (0,30), que es con lo que cuadra la tabla de §3.7.1. Lo que sobra es la fila; mientras esté, alguien la pondrá por el nombre.
- [ ] Perfiles y cotas reales de los cuatro proyectiles para modelar las mallas de §7.2: longitud, calibre, radio de ojiva y dimensiones del núcleo del PzGr. 40. Es investigación de datos, no modelado.
- [ ] Comprobar que `validate_glb.py` ignora los objetos puramente visuales de §7.2, que no llevan `Thickness_mm` ni `Module_Type`, o darles un prefijo `VIS_` que el validador salte.
- [ ] Reglas de «fuera de combate» (§7), incluida la agregación de §3.7.3.
- [ ] Resolver las **ocho** piezas no convexas (§3.1): `ARM_Addon_L`/`_R`, `ARM_Front_Top_Plate`, `ARM_Lower_Side_L`/`_R_Plate`, `ARM_Upper_Back_Plate`, `MOD_Barrel` y `MOD_Engine`.
- [ ] Vaciar las ruedas del tren de rodaje o darles material propio (§9), y modelar las ocho de rodadura por lado, los rodillos de retorno y la suspensión.
- [ ] Poner `Module_Type` a la tensora, o convertirla en placa (§3.7.1).
- [ ] Aplicar la escala del mantelete en Blender: la geometría da 47,01 y 46,01 mm contra los 50 declarados.
- [ ] Separar el `Health` de piernas y torso en el `.glb`, o quitar ese argumento de §3.7.1.
- [ ] Abrir el hueco del anillo de torreta en el techo del casco si vuelve a hacer falta: `ARM_Top_Plate` fue sustituida por 12 cuñas más la pieza trasera el 24/10/2026.

**Segundo vehículo [A]**

- [ ] Decidir si el T-44 entra, y si entra, si es **sólo blanco** (no requiere ni un dato nuevo de munición) o también **tirador** (duplica la tabla de proyectiles con el ZiS-S-53 de 85 mm). Casco sencillo y muy inclinado, torreta fundida redondeada: ejercita justo la parte del modelo que justifica medir la geometría, y por eso vale más como demostración que un segundo vehículo de planchas planas.
