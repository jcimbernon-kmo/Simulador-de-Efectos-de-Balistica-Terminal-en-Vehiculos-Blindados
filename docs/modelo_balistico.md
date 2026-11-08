# Modelo Balístico

Documento de diseño del núcleo de cálculo: qué se simula, con qué datos y con qué fórmulas.

Convención: **[S]** supuesto, pendiente de fuente/verificación · **[A]** abierto.

Última revisión: 2026-11-08 (10ª).

---
## 1. Principios

* **El espesor sale de la geometría.** Para cada objeto que cruza el rayo se mide el camino entre la entrada y la salida. Thickness_mm solo sirve para validar la geometría y como respaldo, **no entra en el cálculo**. Un hueco en la malla hace atravesar menos acero del real, así que el validador del glb es parte del núcleo.
* **Presupuesto cerrado.** Tras perforar, núcleo y fragmentos se reparten la energía residual y la suma nunca la supera.
* **Blindaje y módulos se tratan igual.** Algo entra con energía, recorre un camino y pierde energía. Un módulo anota además el daño en Health.
* **Determinista.** Toda la aleatoriedad (dispersión de fragmentos, umbrales de rebote) usa una semilla derivada del disparo.
* **Se calcula de golpe.** El disparo devuelve una línea temporal de eventos que el render reproduce a la velocidad que convenga.
* **Datos fuera del código.** Todo número sale de data/ o del glb: cambiar un vehículo o un proyectil no toca código, el análisis de sensibilidad (§6) consiste en variar esos ficheros, y cada dato se corrige en un solo sitio.

## 2. Datos de entrada

### 2.1 Proyectil - data/shells.csv

| Campo | Unidad | Notas |
|---|---|---|
| shell_id | — | Ammo_Caliber_Cannon |
| name | — | |
| type | — | AP, APCBC, APCBC-HE, APCR, HEAT |
| caliber_mm | mm | calibre del cañón |
| core_diameter_mm | mm | solo en subcalibre (APCR); vacío, se usa caliber_mm |
| mass_kg | kg | proyectil completo |
| core_mass_kg | kg | solo en subcalibre (APCR) |
| muzzle_velocity_ms | m/s | |
| explosive_mass_g | g | equivalente en TNT, 0 si no lleva |
| fuze_delay_ms | ms | solo con explosivo |
| cd | — | coeficiente de arrastre, si no hay fila en velocity.csv (§2.2.1) |
| source_id | — | [A] clave en data/sources.md; la columna aún no existe (§10) |

Magnitudes: kg, m, m/s, J, y mm únicamente para espesores y calibres, por ser la convención de las fuentes.

El APCR es un proyectil de subcalibre: un cuerpo de 75 mm que lleva dentro un núcleo de carburo de tungsteno y que, a diferencia del APDS (sabot), no se desprende en vuelo. Lo que perfora es el núcleo, así que el cargador deriva:

`penetrating_mass_kg     = core_mass_kg     o mass_kg     si está vacía`
`penetrating_diameter_mm = core_diameter_mm o caliber_mm  si está vacía`

### 2.2 Tabla de penetración - data/penetration.csv

| Campo | Unidad | Notas |
|---|---|---|
| shell_id | — | enlaza con shells.csv |
| distance_m | m | |
| angle_deg | ° | 0° es impacto perpendicular |
| penetration_mm | mm | espesor perforado completo |
| armour_type | — | contra qué blindaje se midió |
| angle_from | — | desde dónde mide el ángulo la fuente de esa fila |
| thickness_basis | — | nominal o los, decide si §3.4 divide por el coseno |
| criterion | — | criterio de penetración de la fuente (complete, etc.)|
| source_id | — | [A] clave en data/sources.md; la columna aún no existe (§10) |

#### 2.2.1 Velocidad de impacto y exponente de De Marre

La velocidad hace falta para toda capa que no sea la primera (el mamparo, el blindaje espaciado, las orugas), que recibe el proyectil con una velocidad que no corresponde a ninguna distancia de la tabla. Sale de data/velocity.csv. El modelo de arrastre v(x) = v₀·e^{-Kx}, con K = ρ·Cd·A/(2m), queda como respaldo y es con el que se completaron dos puntos del PzGr. 39:

| Distancia | m/s (PzGr. 39) | Origen |
|---|---|---|
| 100 m | 738 | del modelo |
| 500 m | 691 | medido |
| 1000 m | 636 | medido |
| 1500 m | 585 | del modelo |
| 2000 m | 537 | medido |

Un Cd único no basta. El del PzGr. 40, despejado tramo a tramo, sube de 0,413 a 0,690 al bajar de Mach 2,7 a 1,26, y con un valor ajustado a todo el rango (0,584) el error llega al −4,2 % en velocidad y −8,2 % en energía a 1000 m. Por eso el cd de shells.csv es respaldo, no fuente. Su primer tramo, 0,413, es prácticamente el 0,415 del PzGr. 39: las dos formas arrastran igual, y la caída más rápida del APCR viene de su masa.

Comprobación cruzada: la caída que da la misma fuente (−2,4 m a 500 m, −10,0 a 1000, −44,8 a 2000) es independiente de la velocidad, y derivando el tiempo de vuelo del modelo sale con un −1 % de error a 500 m, +3 % a 1000 y +9 % a 2000, desviación esperable porque el cálculo supone trayectoria plana.

El Gr. 38 Hl/C lleva 450 m/s constantes, un marcador y no un dato. Se acepta porque la penetración de una carga hueca no depende de la velocidad (§5). Declarado en §9.

El exponente de De Marre, P ∝ vⁿ, se mide cruzando las velocidades con la tabla de penetración a 0°, tramo a tramo. ballistic_data.exponente() lo calcula para cada proyectil y disparo.py usa el del tramo que contiene la distancia del disparo:

| Tramo | PzGr. 39 | PzGr. 40 |
|---|---|---|
| 100-500 m | 1,415 | 0,983 |
| 500-1000 m | 1,457 | 0,942 |
| 1000-1500 m | 1,395 | 0,878 |
| 1500-2000 m | 1,406 | 0,744 |

El PzGr. 39 coincide con el valor teórico de De Marre, 1,4283, que no interviene en la elaboración de ninguno de los dos conjuntos de datos. Las diferencias entre sus tramos son redondeo: la tabla da milímetros enteros, lo que deja cada tramo con un margen de ±0,12, y de 100 a 2000 m sale 1,418. El PzGr. 40 no: su exponente es menor y baja con la distancia, así que no sigue una ley de potencia única. Por eso el exponente se mide por proyectil y por tramo y no es un parámetro global. [A] Falta saber si es física del núcleo o cómo se construyó la tabla de la fuente.

Si un proyectil cinético no tiene al menos dos distancias con penetración a 0° y velocidad, el cálculo da error en vez de usar un valor por defecto. El HEAT no lo necesita.

El cargador resuelve la velocidad a una distancia en este orden:
1. Interpolación de velocity.csv, el caso normal.
2. Si el proyectil no tiene filas, v₀·e^{-Kx} con el cd de shells.csv, marcado como estimado.
3. Si tampoco hay cd, error.

Para un proyectil nuevo basta un punto publicado de velocidad restante para despejar su Cd, con 3 o más, pasa a velocity.csv.

### 2.3 Materiales - data/materials.csv

Una sola tabla para blindaje y módulos. El blindaje de referencia es RHA, con coeficiente 1,0.

| Campo | Notas |
|---|---|
| id | RHA, Steel, Track, Wheel, Flesh, Cast_Iron, Ammo, Gasoline, Diesel. Mayúscula inicial |
| resistance | Resistencia relativa a RHA, multiplica la longitud de camino para obtener el equivalente en RHA |
| spall | Masa de tapón que arranca el material, relativa a RHA (1,0). El nivel absoluto lo fija Recht-Ipson (§3.5) |
| source_id | [A] clave en data/sources.md, o supuesto; la columna aún no existe (§10) |

Los valores discutibles son tres:

1. Cast_Iron a 1,5: frágil, se rompe en fragmentos en vez de sacar un tapón limpio.
2. Track a 0,3: una oruga son eslabones con huecos, sin tapón coherente.
3. Wheel, cuyas dos columnas se contradicen. spall = 0,13 sale de 20 mm de acero real sobre los 150 mm modelados, pero resistance = 0,40 implicaría 100 mm:

resistance = acero_real_mm × 0,6 / camino_modelado_mm -> 20 mm da 0,08

Con 0,40 el flanco suma 14 mm de oruga + 60 de rueda + 30 de costado = **104 mm de RHA equivalente**, contra los 81 mm del frontal: el modelo diría que el Pz IV está mejor protegido por el costado que por el morro. Las dos columnas tienen que salir del mismo número de milímetros (§10).

### 2.4 Objetos del modelo

Placas (ARM_*): Thickness_mm (float) y Armour_Material (id de materiales).

Módulos (MOD_*): Module_Type (Crew, Engine, Transmission, Ammo, Fuel, Gun, Track), Health (float) y Armour_Material. Sin espesor: el camino por dentro de su caja ya lo da la malla.

El código distingue por propiedades, no por colección, porque glTF no transporta las colecciones de Blender. Los prefijos del nombre son una red de seguridad.

## 3. Flujo de un disparo cinético (AP, APCBC, APCBC-HE, APCR)

### 3.1 Tramos

El disparo es un rayo: una línea en 3D, con origen y dirección, sin grosor. Toca cada superficie en un solo punto, y el calibre no interviene en dónde impacta, solo en la masa del tapón y en los fragmentos. El trazado da la lista ordenada de tramos: objeto, punto de entrada, punto de salida, longitud y normal de entrada.

[S] Suposición de convexidad. La entrada es la primera intersección y la salida la última, lo que vale para cualquier objeto convexo. validate_glb.py lo comprueba.

Una lámina curva no es convexa: un rayo rasante puede cortarla cuatro veces, y primera y última abarcarían el hueco de aire, casi el doble del camino real. Por eso todo lo curvo se faceta en piezas planas y convexas; la cúpula, por ejemplo, son 12 caras. Las piezas se generan como intersección de semiespacios, no uniendo vértices a mano, así que la convexidad y la planitud salen por definición y dos piezas vecinas comparten cara exacta.

El precio del facetado es que el ángulo salta en las juntas. En la cúpula, dos caras vecinas difieren 30°, así que según el milímetro en que caiga el rayo el ángulo puede estar hasta ±15° del de la curva real. Hoy solo cambia la consulta de la tabla; con el rebote (§3.3) decidirá si el proyectil rebota o perfora (§9, §10).

### 3.2 Agrupación por contacto

Entre tramos consecutivos se mide el hueco perpendicular a las placas, no a lo largo del rayo, para que estar unidas o separadas sea propiedad de la geometría y no del ángulo del disparo:

hueco_perpendicular = hueco_a_lo_largo_del_rayo × cos(ángulo con la normal de entrada de la capa siguiente)

* [S] Hueco < 1 mm (contact_gap_mm): placas en contacto, forman una capa compuesta. Se suman los caminos equivalentes y la perforación se evalúa sobre el total.
* Hueco ≥ 1 mm: blindaje espaciado. Se perfora la primera, se generan fragmentos en el hueco, y lo que llegue a la segunda lo resuelve el propio trazado.

Así se resuelven también las esquinas: las dos placas que cruza un rayo en una esquina cuentan como una capa.

### 3.3 Rebote

Antes de evaluar la perforación, con el ángulo entre el rayo y la normal de entrada:

* Por encima del umbral rebota: la componente normal de la velocidad se anula casi entera y la tangencial pierde energía. El proyectil desviado sigue como un rayo nuevo, con un máximo de 2 rebotes.
* [S] El umbral depende del tipo de proyectil y de la relación calibre/espesor; un APCBC con casquete aguanta ángulos más cerrados que un APCR. Nunca un umbral global.
* [S] Pequeña variación aleatoria alrededor del umbral, con semilla fija, para que no sea todo o nada.

Sin implementar (§10).

### 3.4 Perforación

Camino equivalente en RHA de la capa: Σ (longitud_tramo × resistance_material).

Capacidad del proyectil, de la tabla interpolada a la distancia y al ángulo de impacto:

* Si la tabla da espesor nominal: capacidad_LOS = tabla(θ, d) / cos θ
* Si la tabla da línea de visión: capacidad_LOS = tabla(θ, d)

Perfora si camino_equivalente ≤ capacidad_LOS. En una placa plana reproduce exactamente la tabla. Si no perfora, el disparo termina ahí sin fragmentos.

Todo tramo con Armour_Material resta capacidad, placa o módulo. Las orugas son un módulo (Track) y no una placa, así que si un módulo no consumiera capacidad no protegerían de nada.

### 3.4.1 Capas posteriores a la primera

La cadena se lleva en capacidad, no en velocidad: a la segunda capa le importa cuántos milímetros de RHA le quedan al proyectil. Recht-Ipson transplantado a esas unidades con P ∝ vⁿ:

P_residual = (P_impacto^(2/n) − t_equivalente^(2/n))^(n/2)

con n el exponente de De Marre del proyectil en el tramo de distancia del disparo (§2.2.1).

La velocidad del proyectil sigue haciendo falta para tres cosas: la energía de núcleo y fragmentos (½mv², §3.7), los instantes de la línea temporal (§7.1) y el recorrido de la espoleta del APHE (§4). Las tres toleran más error que la perforación.

### 3.4.2 Qué detiene al proyectil

Una sola cuenta de estado, la energía, y la capacidad se deduce de ella. Con P ∝ vⁿ y E = ½mv² son la misma magnitud en unidades distintas:

P = P0 · (E / E0)^(n/2)  <br>
E = E0 · (P / P0)^(2/n)

| | Decide si atraviesa | Decide cuánto daño hace |
|---|---|---|
| Núcleo | La capacidad deducida de su energía | Esa misma energía |
| Fragmentos | Energía (§3.7) | Energía (§3.7) |

Los fragmentos no figuran en las tablas, así que para ellos solo hay energía.

Consecuencias: el presupuesto cerrado de §1 se cumple por construcción, las tablas de penetración son el único anclaje del modelo, y σ_RHA deja de intervenir en el núcleo.

Por qué no dos cuentas en paralelo: la cadena es una ley de potencias y una pérdida lineal en el espesor sobrestima las capas delgadas (un cartucho de 15 mm equivalentes costaba 208 kJ por la lineal y 65 kJ por Recht-Ipson). El primer disparo completo lo demostró: el núcleo se quedaba sin energía en el tercer cartucho y seguía perforando con 56 mm de capacidad.

El núcleo se detiene cuando el camino equivalente de una capa supera su capacidad residual (evento stopped). Se queda clavado a la profundidad que le permitía su capacidad, no desaparece, así que el resultado muestra dónde y por qué se paró.

[S] La cadena usa a = 1, sin la masa del tapón, porque así reproduce las tablas. La energía que da se interpreta como la del núcleo más el tapón (E_residual de §3.5), y el reparto de §3.6 se aplica sobre ella.

### 3.5 Energía residual y tapón

Límite balístico de la capa derivado de la tabla (De Marre, con el exponente medido en §2.2.1), y velocidad residual por Recht-Ipson con p = 2 ([S], §10):

v_residual² = a · (v_impacto² − v_límite²)      con a = m_p / (m_p + m_tapón)

a no es una constante de ajuste: sale del balance de energía, con el tapón saliendo a la misma v_residual que el núcleo y el trabajo de cizallarlo igual a ½·m_p·v_límite². La energía residual es la de los dos:

E_residual = ½ · (m_p + m_tapón) · v_residual²

m_tapón es geometría, no un parámetro libre:

m_tapón = ρ_acero · camino · (π/4)·d² · spall        ρ_acero = 7850 kg/m³

con el camino de §3.1, que ya incluye la inclinación, d el diámetro del penetrador (el núcleo en el APCR) y spall el de §2.3. Para el PzGr. 39 contra los 80 mm del frontal son 2,77 kg de tapón contra 6,8 kg de proyectil. El spall va aquí y no en el reparto de §3.6 para que Flesh a 0 signifique que no hay tapón, y no que su energía desaparezca.

### 3.6 Núcleo y fragmentos

El núcleo sigue como un rayo con la mayor parte de la energía, y puede atravesar el motor y salir por el otro lado. Núcleo y tapón salen a la misma velocidad, así que la energía se reparte por masa con la misma a de §3.5:

E_núcleo    = E_residual · a        =  E_residual · m_p     / (m_p + m_tapón)  <br>
E_astillado = E_residual · (1 − a)  =  E_residual · m_tapón / (m_p + m_tapón)

Comprobación del presupuesto: PzGr. 39 a 750 m/s contra una capa de 600 m/s de límite, los 1,913 MJ de entrada salen como 0,489 MJ de núcleo + 0,200 MJ de tapón + 1,224 MJ de cizalla.

Con los espesores del Pz IV H, para el PzGr. 39 (75 mm, 6,8 kg) sobre RHA:

| Espesor | t/d | m_tapón | 1 − a |
|---|---|---|---|
| 20 mm (faldón) | 0,27 | 0,69 kg | 0,093 |
| 30 mm (costado) | 0,40 | 1,04 kg | 0,133 |
| 50 mm | 0,67 | 1,73 kg | 0,203 |
| 80 mm (frontal) | 1,07 | 2,77 kg | 0,290 |

Con el PzGr. 40 va de 0,102 a 0,313: un núcleo ligero arrastra un tapón comparable a su propia masa. Ese 9-31 % cae dentro del rango que cita la literatura de behind-armour debris.

Fragmentos, versión provisional. Solo el astillado de la placa, porque el proyectil no se rompe (§9):

* N = m_tapón / masa_fragmento, redondeado, con masa_fragmento = 5 g [S]. Todos de la misma masa; todavía sin distribución de Mott.
* Salen del punto de salida de la capa a la velocidad del núcleo y se reparten E_astillado a partes iguales. La suma es exacta.
* Dirección al azar, uniforme en ángulo sólido, dentro de un cono alrededor de la dirección del núcleo cuyo semiángulo depende del tipo de proyectil (`cono_fragmentos_<tipo>_deg`; de momento 30° [S] en APCBC-HE y APCR), con la semilla del disparo.
* Cada fragmento es un rayo con la ley de pérdida de §3.7 y el diámetro de una esfera de acero de su masa, d = (6m / (π·ρ))^(1/3), 10,7 mm para 5 g. Se detiene cuando le quedaría menos de 1 J [S].
* Daña con las mismas reglas que el núcleo (§3.7.1). La salud se aplica al final, con todos los eventos ordenados por tiempo, porque núcleo y fragmentos pueden tocar el mismo módulo.
* Un fragmento no genera fragmentos, no rebota y no se rompe.

En el disparo de referencia (PzGr. 39 a 100 m contra el frontal) salen 562 fragmentos de 5 g del frontal con 458 J cada uno, 69 del mamparo con 201 J y 141 de la placa trasera con 90 J. Con ellos quedan fuera cuatro de los cinco tripulantes y 18 cartuchos, frente a dos tripulantes y cuatro cartuchos con el núcleo solo. El resultado depende mucho de la masa del fragmento y del cono (§6).

Rendimiento: un rayo por fragmento, unos 5 ms por rayo en Python, unos 4 s por disparo.

### 3.7 Pérdida de energía y daño

Para el núcleo la pérdida sale de la cadena de capacidad (§3.4.2). Para cada tramo, con t_eq = camino × resistance:

P_entrada = P0 · (E / E0)^(n/2)  <br>
P_salida  = (P_entrada^(2/n) − t_eq^(2/n))^(n/2)  <br>
E_salida  = E · (P_salida / P_entrada)^(2/n)  <br>
si el módulo es acumulativo (§3.7.1):  Health -= (E − E_salida)

Al perforar una placa, la energía que sale es la E_núcleo de §3.6, de la que se vuelve a deducir la capacidad. Dentro de una capa compuesta la pérdida se reparte entre los tramos en proporción a la capacidad que consume cada uno: la ley de potencias no es aditiva, (a+b)^k > a^k + b^k, y por eso una capa compuesta cuesta más que dos placas separadas.

Los fragmentos no tienen capacidad, así que pierden energía por recorrido, proporcional al área que empuja:

E -= camino × resistance_material × σ_fragmento × (π/4)·d²  <br>
si E < energia_minima_fragmento_J (1 J): se detiene dentro del objeto

[S] σ_fragmento = 3,10 GPa, el σ_RHA del PzGr. 39, como aproximación declarada (§6, §9).

σ_RHA sale de suponer que en el límite balístico el proyectil deposita toda su energía en el espesor que justo perfora:

σ_RHA = E_impacto / (espesor_perforado × área_frontal)

| Proyectil | E a 100 m | Perfora | d penetrador | σ_RHA |
|---|---|---|---|---|
| PzGr. 39 | 1,852 MJ | 135 mm | 75 mm | 3,10 GPa |
| PzGr. 40 | 0,348 MJ | 176 mm | 28 mm | 3,21 GPa |

Dos proyectiles con un factor 5 de diferencia en energía dan σ dentro de un 3,5 % sin ajustarlo a ninguno, uno de los pocos resultados no circulares del proyecto (§8). Dos reservas: σ va con 1/d² y los 28 mm son [S] (§10; con 30 mm saldrían 2,80 GPa), y en el límite no toda la energía va a la placa, así que σ sale algo sobrestimada.

Health se expresa en julios: el daño es la energía depositada, sin constante de conversión.

### 3.7.1 La regla de daño depende del tipo de módulo

La energía depositada vale para máquinas, no para personas. Un motor se avería absorbiendo energía, pero a una persona no la incapacita la cantidad de tejido recorrido sino alcanzar algo vital. Un fragmento frontal recorre el triple de carne en las piernas de un tripulante sentado (0,82 m) que en el torso (0,27 m), así que acumulando, el modelo diría que las piernas sufren tres veces más. Por eso hay una sola rutina de recorrido y dos reglas de daño:

| Module_Type | Regla | Qué es Health |
|---|---|---|
| Engine, Transmission, Gun | Acumulativa: daño = energía depositada | Reserva en julios, se decrementa |
| Crew | Umbral: incapacitado si algo entra con energía por encima de Health | Umbral, no se decrementa |
| Track | [S] Umbral, como Crew | Umbral, no se decrementa |
| Ammo, Fuel | Umbral de detonación / ignición (§4, §7) | Umbral, no se decrementa |

En los tipos de umbral restar no tendría sentido, porque no hay reserva: el estado es un booleano (out_of_service, §7.1).

La oruga es un módulo porque su avería inmoviliza el vehículo. [S] Umbral y no acumulación porque son 22 piezas por lado solo por convexidad (§3.1), y con acumulación el resultado dependería del corte; además una oruga no cae por la suma de esquirlas sino cuando algo corta un eslabón o un pasador. La rueda motriz y la tensora también son Track, porque sin ellas la oruga no recibe potencia o se sale. Las ruedas de rodadura son placas: perder una no inmoviliza.

[S] Valores de partida de Health, todos sin fuente salvo donde se dice:

| Module_Type | Health | Criterio |
|---|---|---|
| Crew torso y cabeza | 80 J | Convención declarada, no criterio validado (§3.7.2) |
| Crew piernas | 3-5× el del torso | El efecto de la región del cuerpo es citable de los modelos de vulnerabilidad militares; el factor es supuesto (§6) |
| Transmission | ~150 kJ | Menor que el motor, un impacto de lleno la inutiliza |
| Engine | ~300 kJ | Un núcleo que llega con esa energía se detiene dentro del motor |
| Gun tubo | ~40 kJ | Acero macizo de pared gruesa |
| Gun recámara | ~25 kJ | Mecanismo de precisión, se agarrota antes. Lo razonado es el orden, tubo por encima |
| Track cinta | 5 kJ | Cizalla doble de un pasador de Ø25 mm, ≈ 400 kN sobre ≈ 8 mm ≈ 3 kJ. Cualquier AP lo supera, el astillado no |
| Track motriz / tensora | 20 / 16 kJ | Piezas macizas, más que la cinta |
| Ammo | 150 J por cartucho | Umbral de detonación |
| Fuel | 5000 J | Umbral de ignición. El incendio no es destrucción instantánea (§7) |

Engine y Transmission se fijaron con la ley lineal de σ_RHA, que ya no se usa (un núcleo de 75 mm que recorre 10 cm del motor deposita hoy unos 225 kJ), así que hay que recalibrarlos (§10).

### 3.7.2 El umbral de 80 J es una convención sin validar

Se cita como umbral de incapacitación por fragmento (80 J = 58 ft·lb, el mismo criterio en otras unidades). El artículo PMID 28505551 (data/sources.md) lo rastrea hasta Rohne y concluye que nadie explicó de dónde salía el valor, que su capacidad de penetración se reproduce en jabón balístico, pero que no fue posible validarlo, y recomienda no usar un límite de energía para definir la incapacitación.

Además, aunque valiera, se refiere a una bala M/88 en tejido, y aquí se aplica a fragmentos de blindaje irregulares que voltean: una segunda suposición sin validar.

Se mantiene como valor de partida porque dentro del alcance no hay sustituto mejor, pero como convención con origen documentado y sin validación, declarada en §9 y ajustable desde fichero.

[A] Pregunta de alcance para el tutor: ¿se acepta un criterio de daño a la tripulación que es una convención declarada, o el proyecto necesita otro?

### 3.7.3 Un Module_Type puede abarcar varios objetos

| Module_Type | Agregación entre objetos del mismo tipo |
|---|---|
| Ammo | OR, basta con que uno detone (87 cartuchos) |
| Gun | OR: tubo y recámara son piezas distintas y con cualquiera fuera de servicio no se puede devolver el fuego. Cada una gasta su propio Health |
| Track | OR entre cinta, motriz y tensora de ambos lados. El lado (_L/_R) solo informa |
| Crew | OR dentro de cada tripulante, cada tripulante cuenta por separado (§7) |
| Engine, Transmission | SUMA: las piezas son un corte de convexidad de una sola máquina |
| Fuel | Cada objeto por su cuenta, hoy hay uno |

Cómo se acumula el daño dentro de un objeto (§3.7.1) y cómo se combinan los objetos (aquí) son preguntas independientes. Lo que decide la combinación es por qué hay varias piezas. Si son unidades reales o piezas funcionalmente distintas, OR. Si la división es un artefacto del modelado, OR con daño de umbral (el resultado no depende del corte) y SUMA con daño acumulativo: con OR, agotar una de las cinco cajas de 30 kJ de la transmisión la inutilizaría entera, y el resultado dependería de en cuántas piezas se cortó.

Al repartir un módulo acumulativo en varias piezas, el Health se divide por volumen para que la suma sea la del conjunto (motor: 228,0 / 36,0 / 36,0 kJ, como hace tools/crear_canon_motor.py).

## 4. APHE

Perfora igual que un cinético (§3.3 a §3.5). La diferencia viene después.

1. [S] Armado de la espoleta. Si el camino equivalente de la capa queda por debajo de un umbral, la espoleta no se arma y el proyectil sigue sin detonar.
2. Recorrido con retardo, distancia = v_residual × fuze_delay, desde el punto de salida de la capa. [S] Velocidad constante durante el retardo, que es muy corto.
3. Punto de detonación. Si cae dentro del vehículo, detona ahí. [A] Si lo ha atravesado entero, lo razonable es que detone fuera sin daño interior.
4. Explosión, con la energía del explosivo repartida entre fragmentos de la carcasa en 360° ([S] velocidad por Gurney, tamaños por Mott) y onda expansiva como esfera de rayos con oclusión por los módulos ([S] distancia escalada de Hopkinson-Cranz, con un factor de confinamiento).

Primera versión 360° uniforme.

## 5. HEAT

La carga hueca cambia la moneda del cálculo.

* Detona al contacto con la primera superficie, sin perforación previa.
* [S] La penetración no depende de la velocidad de impacto ni de la distancia de tiro, sino del calibre, del ángulo y de la distancia de detonación (standoff).
* El chorro es un rayo estrecho desde el punto de detonación, con una capacidad en mm de RHA que se consume con camino × resistance de cada tramo. El ángulo lo resuelve la geometría.

[S] Contra HEAT el blindaje espaciado actúa por distancia de detonación, no por material: el chorro llega disperso. Hay que tratarlo con una curva de penetración frente a standoff, la única parte del modelo donde el blindaje espaciado necesita código propio.

[S] Al salir del blindaje, la capacidad restante del chorro se convierte a energía con una constante declarada, y a partir de ahí se trata como los fragmentos.

## 6. Parámetros libres

Es la parte más difícil de defender: las tablas cubren la perforación, no los efectos tras el blindaje. Cada parámetro hay que justificarlo o declararlo como supuesto. Van en data/parametros.csv como pares clave-valor; los que dependen del tipo de proyectil llevan el tipo en la clave, como el cono. Los Health de los módulos van en el glb. Nunca en el código (§1).

| Parámetro | Depende de | Qué controla |
|---|---|---|
| contact_gap_mm | — | hueco por debajo del cual dos placas forman una capa compuesta (§3.2). [S] 1 mm |
| masa_fragmento_g | — | masa de cada fragmento; fija cuántos salen, N = m_tapón / masa. [S] 5 g |
| cono_fragmentos_<tipo>_deg | tipo | semiángulo del cono de fragmentos (falta la clave → error). [S] 30° en APCBC-HE y APCR, falta el valor propio del APCR |
| ricochet_angle | tipo, calibre/espesor | umbral de rebote |
| sigma_fragmento_GPa | — | pérdida de energía por recorrido de los fragmentos (§3.7). [S] 3,10 GPa |
| energia_minima_fragmento_J | — | por debajo, el fragmento se da por detenido. [S] 1 J |
| Health de Crew, torso (glb) | — | energía de entrada que incapacita (§3.7.2). Sin validar, el que más probabilidades tiene de cambiar |
| Health de Crew, piernas (glb) | — | múltiplo del umbral del torso (§3.7.1) |
| fuze_arm_threshold | solo APHE | espesor mínimo para armar |
| standoff_curve | solo HEAT | penetración frente a distancia de detonación |

Esta tabla es la sección de limitaciones de la memoria: cuantos menos parámetros, más defendible el modelo. El número de fragmentos no es libre, lo libre es la masa, que con una distribución de Mott pasaría a ser la masa media. Ya no hacen falta un coeficiente de absorción del núcleo (lo sustituye la cadena de §3.4.2) ni una fracción de astillado por proyectil (la fijan la a de Recht-Ipson y la masa del tapón).

Fuentes a consultar: Recht e Ipson, Ballistic Perforation Dynamics, J. Appl. Mech. 30(3), 1963; Backman y Goldsmith, The mechanics of penetration of projectiles into targets, Int. J. Eng. Sci., 1978, con el mapa de modos de fallo frente a t/d; Rosenberg y Dekel, Terminal Ballistics; Zukas, Impact Dynamics; Bird y Livingston, WWII Ballistics: Armor and Gunnery.

## 7. Salida: línea temporal

El cálculo devuelve una lista de eventos con instante y posición, en JSON, que el render reproduce a cámara lenta y que comparan las pruebas. Es el contrato entre cálculo y render y el formato de los casos de §8, así que se fija antes que la interfaz.

Tipos de evento: impact, ricochet, stopped, perforation, fragment_spawn, module_hit, detonation, exit.

Estado final del vehículo: por ahora el daño por módulo con la agregación de §3.7.3. [A] Faltan las reglas de fuera de combate: munición alcanzada o muerte de un tripulante crítico; inmovilizado, propuesta: motor o transmisión fuera de servicio, o cualquier Track.

### 7.1 Campos de un evento

| Campo | Para qué |
|---|---|
| type | uno de los ocho tipos de arriba |
| t_s | instante, en segundos desde el primer contacto |
| ray_id | identificador del rayo. Sin él el recorrido no se puede dibujar |
| parent_id | rayo del que nació, o null para el núcleo |
| object | nombre del objeto del glb, o null si el tramo es aire |
| pos | punto del evento, en coordenadas del modelo |
| normal | normal de entrada de la cara, para orientar la marca del agujero |
| path_mm, angle_deg | camino dentro de la capa y ángulo respecto a la normal |
| capacity_in_mm, capacity_out_mm | capacidad antes y después (§3.4.1). Solo en el núcleo |
| energy_in_J, energy_out_J | energía antes y después (§3.7) |
| health_in_J, health_out_J | vida del módulo antes y después. Solo en module_hit y detonation |
| out_of_service | [A] bool, solo en module_hit y detonation. En los tipos de umbral es lo único que dice el estado |
| plug_mass_kg, spall_energy_J, shear_energy_J | [A] solo en perforation: masa del tapón (§3.5), energía que se lleva y energía de cizalla. Con energy_out_J cierran el presupuesto de §1 |
| n_fragments, fragment_mass_kg, fragment_diameter_mm | solo en fragment_spawn (§3.6). Cada fragmento es un rayo con su ray_id y con parent_id el rayo que perforó |

El recorrido es un árbol, no una lista: en cada fragment_spawn nacen N rayos y el núcleo continúa. La vida del módulo va en el evento aunque sea redundante, para poder saltar a cualquier instante sin reproducir desde cero y para que las pruebas comprueben el daño directamente.

Los instantes salen del camino, t += camino / v_media_del_tramo, con las velocidades de §3.5.

[A] Cuando un módulo detiene al proyectil se emiten module_hit y stopped con la misma energy_in_J. Hay que decidir cuál la lleva antes de que el render dependa del JSON, o quien sume la energía depositada la contará dos veces.

### 7.2 Reproducción

Tiempo no uniforme, en tres fases. En el disparo de referencia (disparo.py sin argumentos) el núcleo tarda 12,8 ms desde el primer contacto hasta salir por la placa trasera, el último fragmento se detiene a los 13,7 ms, y perforar el frontal lleva 139 µs, el 1 % del total. Un frame a 60 fps son 16,7 ms, así que con una escala única o la perforación es invisible o el interior es interminable:

| Fase | Duración real | En pantalla | Factor |
|---|---|---|---|
| Aproximación (últimos ~5 m) | 6,7 ms | 1,5 s | ×225 |
| Perforación de la capa | 139 µs | 1,5 s | ×10 800 |
| Interior y fragmentos | 13,6 ms | 2 s | ×147 |

La aproximación arranca a unos metros del vehículo: el vuelo libre no tiene física en el modelo (la penetración sale de la tabla por distancia), así que es decorado.

Vista de rayos X al contacto, con el blindaje en torno al 20 % de opacidad, salvo la capa golpeada, que se queda opaca para que se vea el agujero abriéndose. La transparencia entra desvaneciéndose durante la fase de perforación. Con 281 objetos, el blindaje se dibuja sin escritura en el búfer de profundidad y sin ordenar.

El color del daño sale de Health y sigue las dos reglas de §3.7.1:

| Module_Type | Visual |
|---|---|
| Engine, Transmission, Gun | Degradado de Health / Health_inicial: gris claro intacto, rojizo al acercarse a cero |
| Crew, Track, Ammo, Fuel | Dos estados, intacto o fuera de servicio. Un degradado daría a entender estados intermedios que el modelo no tiene |

Mallas de proyectil, por revolución de un perfil, una por fichero y con el shell_id como nombre, para que el motor las cargue sin tabla de equivalencias: models/PzGr39_75_L48.glb, models/PzGr40_75_L48.glb y models/Gr38HlC_75_L48.glb. Son puramente visuales, sin Thickness_mm, Module_Type ni material. Convenio de ejes: punta en el origen (0, 0, 0), cuerpo hacia -Y, centradas en X y Z, en metros, así la punta cae en el pos del evento sin desfase.

En los APCR el núcleo se desengancha en la primera perforación: la malla del PzGr. 40 desaparece y el núcleo sigue como su rayo, sin malla propia. Licencia visual declarada: el cálculo usa el núcleo desde el primer contacto y el render mantiene la malla completa mientras perfora la primera capa. Si no la perfora, la malla se queda clavada.

## 8. Validación

Pruebas como datos: cada caso es un JSON con el rayo de entrada y el resultado esperado, así que al portar el núcleo al motor los mismos ficheros validan la versión nueva. El motor solo dibuja la línea temporal.

Prueba de regresión, dentro de disparo.py --selftest, sobre models/Pz IV H.glb:

| | |
|---|---|
| Origen / dirección | (0,50, −2,00, 1,30) / (0, 1, 0) |
| Primer impacto | ARM_Upper_Front_Plate |
| Longitud de camino | 81,00 mm |
| Ángulo respecto a la normal | 9,00° |
| Propiedades | Thickness_mm 80, Armour_Material RHA |

Los 81,00 mm son los 80 nominales divididos por el coseno de 9°. Si da 80,0 está midiendo con la propiedad y no con la geometría.

Validación contra las tablas, también en --selftest: para cada una de las 19 celdas de penetration.csv de los dos cinéticos, una placa plana del espesor tabulado perfora justo por debajo y se queda clavada un 0,1 % por encima. Hay que reejecutarlo cada vez que se toque penetration.csv o velocity.csv, de la que sale n.

Invariante: ningún disparo puede acabar con el núcleo sin energía y con capacidad disponible, que es lo que fallaba con dos cuentas (§3.4.2).

Barrido de coherencia, 1416 disparos (dos proyectiles, cuatro distancias, cuatro caras y tres giros): el tiempo no retrocede, energía y capacidad nunca suben, un proyectil parado acaba con 0 J, y el Health acumulativo solo baja mientras el de umbral no cambia. Sin excepciones. Dice que el modelo es coherente, no que acierte.

[A] Todo esto es circular: penetration.csv es la entrada del modelo, así que reproducirla demuestra que la interpolación y la geometría funcionan, no que el modelo acierte. Hacen falta datos independientes. La vía más practicable aprovecha la columna criterion: alemanes, británicos y estadounidenses midieron el mismo cañón con criterios distintos, y si el modelo alimentado con la tabla alemana reproduce las mediciones aliadas del KwK 40 dentro de un margen declarado, eso ya no es circular. Es la pregunta que va a hacer el tribunal.

Lo que sí es validación:

* De Marre en el PzGr. 39 (§2.2.1): velocidad y penetración coinciden con una relación teórica que no interviene en ninguno de los dos conjuntos. Con una reserva declarada: dos de sus cinco velocidades (100 y 1500 m) salen del modelo de arrastre, así que solo el tramo de 500 a 1000 m cruza dos medidas. En el PzGr. 40 la comprobación falla, y por eso el modelo no supone De Marre sino que mide el exponente.
* El contraste de σ_RHA entre los dos proyectiles (§3.7), con la reserva del diámetro del núcleo.

## 9. Limitaciones declaradas

* Un APHE que no perfora puede romperse o detonar en superficie, no se modela.
* Una placa gruesa golpeada cerca de su límite puede astillar por dentro sin ser perforada, no se modela.
* Sin deformación real del blindaje ni del proyectil, solo una marca del agujero.
* Sin rotura del proyectil: el núcleo sin capacidad se queda clavado (§3.4.2) en vez de fragmentarse. Es la opción conservadora, menos daño del real.
* El disparo es un único rayo sin grosor (§3.1). En las juntas de las piezas facetadas el ángulo salta de una cara a otra, hasta ±15° en la cúpula, y un proyectil de 75 mm sobre la junta tocaría las dos.
* Las caras de canto dan un ángulo y un espesor no representativos: un rayo que entra por el borde de una chapa horizontal de 8 mm puede recorrer 245 mm por dentro de ella.
* La suposición de convexidad (§3.1), que incumplen en un borde tres piezas con una cara alabeada, ARM_Upper_Back_Plate (5,59 mm) y ARM_Lower_Side_L_Plate y _R_Plate (1,10 mm).
* [S] La cadena de capacidad usa a = 1 (§3.4.2), así que su velocidad residual no lleva el factor √a de §3.5. Meter a en la cadena apartaría la perforación de las tablas, que son el único anclaje.
* [S] sigma_fragmento = 3,10 GPa está tomado del núcleo (§3.7). Una esquirla no figura en ninguna tabla, así que no tiene anclaje propio, y probablemente frena más que un proyectil de calibre completo.
* Los torsos y las piernas del artillero y del cargador se solapan (40,0 y 8,8 mm). No afecta porque §3.7.3 agrega con OR dentro de cada tripulante.
* Las ruedas son prismas macizos (150 mm la de rodadura, 250 mm la motriz) cuando una real son dos chapas con aire en medio, unos 20 mm de acero. Por eso llevan el material Wheel y no Steel, que con 0,6 sumaría 90 y 150 mm de RHA al flanco. La corrección va en el material, con su resistance pendiente (§2.3).
* La cinta de la oruga es una plancha continua de 20 mm en vez de eslabones con huecos. Lo compensa en parte su resistance de 0,7.
* La distinción entre torso y piernas de §3.7.1 no está en el modelo: los diez objetos de tripulación llevan 80 J.
* Los parámetros de §6 no están calibrados contra datos de efectos tras el blindaje.
* El tapón cilíndrico de §3.5 vale mientras la placa falle arrancando un tapón, hasta t/d ≈ 1. El frontal está en el borde (t/d = 1,07); el frontal de torreta y las ruedas de 150 mm están en t/d ≈ 2, donde el fallo real es ensanchamiento dúctil y el modelo sobrestima el astillado.
* El criterio de incapacitación de la tripulación es una convención sin validar (§3.7.2), que su propia fuente desaconseja.
* La velocidad del Gr. 38 Hl/C es constante (§2.2.1), irrelevante para su penetración.
* La validación contra tablas es circular mientras no haya datos independientes (§8).
* Rebote sin implementar (§3.3). Fragmentos provisionales: solo los del tapón, todos de la misma masa, sin fragmentos secundarios, y con masa, cono y σ_fragmento supuestos.

## 10. Pendientes

Datos

* [ ] Fijar el resistance de Wheel. Está a 0,40 de forma orientativa y deja el flanco por encima del frontal; las dos columnas tienen que salir del mismo número de milímetros (§2.3).
* [ ] Resolver el fuze_delay_ms del PzGr. 39: shells.csv dice 3 ms y la Bd.Z. 5103 no lleva retardo de diseño. O el 3 tiene fuente o sobra. Decide si el proyectil revienta dentro del compartimento o fuera (§4).
* [ ] [S] Fuente para los 28 mm del núcleo del PzGr. 40, hoy derivados de core_mass_kg = 0,85 kg con carburo de tungsteno a ~15 000 kg/m³ y un L/d ≈ 3,3 supuesto (con L/d de 3,5 a 2,5 saldrían de 27 a 31 mm). El dibujo 13 C 1236 lo muestra en corte y se puede medir ahí. El contraste de σ_RHA depende de ese número.
* [ ] Dar claves a data/sources.md y rellenar source_id en las cuatro tablas. Hoy es una lista plana de URL, y la columna source de data/parametros.csv está vacía.
* [ ] Columna de 60° para los dos proyectiles cinéticos, de ensayos aliados, que son además los datos independientes que pide §8.
* [ ] Velocidad real del Gr. 38 Hl/C.
* [ ] Validar el 9-31 % de §3.6 contra una medida publicada. Candidato: Experimental and analytical study of behind armor debris after perforation of a steel plate by an AP projectile (FME Transactions, Belgrado).
* [ ] Confirmar el exponente de Recht-Ipson, p = 2 en §3.5, para este rango de t/d.

Modelo y código

* [ ] Implementar el rebote de §3.3.
* [ ] [A] Rayos volumétricos: sustituir el rayo único por varios rayos repartidos por la sección del proyectil, para que un impacto en la junta de dos piezas facetadas tome el ángulo de las dos y no salte (§3.1, §9). Se hará con el motor 3D, pero el cálculo tiene que ir en el núcleo, porque el motor solo dibuja (§8). Antes hay que decidir cómo se combinan los rayos: qué decide la perforación, qué pasa si parte de ellos no toca el vehículo y quién genera los fragmentos, que hoy ya cuestan unos 4 s por disparo. Alternativa más barata: promediar la normal en las juntas. A consultar con el tutor.
* [ ] Capa compuesta con placas de orientación distinta: §3.2 suma los caminos, pero la tabla se consulta con el ángulo de la primera placa. Caso real, ARM_Front_Track_Addon_Upper a 70° delante de ARM_Middle_Front_Plate. Los rayos volumétricos no lo resuelven.
* [ ] Dar fuente a la masa de fragmento (5 g) y a los conos por tipo de proyectil de §3.6, con datos de behind-armour debris, y pasar a una distribución de Mott.
* [ ] Dar fuente a sigma_fragmento (§3.7), o calcularlo de las tablas como el exponente de De Marre.
* [ ] [A] Explicar por qué el exponente de De Marre del PzGr. 40 baja de 0,98 a 0,74 con la distancia (§2.2.1).
* [ ] Recalibrar el Health de Engine y Transmission (§3.7.1).
* [ ] Decidir qué evento lleva la energía cuando un módulo detiene al proyectil, module_hit o stopped (§7.1).
* [ ] Aprobar los cuatro campos nuevos del esquema de §7.1: out_of_service, plug_mass_kg, spall_energy_J, shear_energy_J.
* [ ] Reglas de fuera de combate (§7).
* [ ] Regla de detonación de APHE fuera del vehículo (§4).

Modelo 3D

* [ ] Modelar los rodillos de retorno y la suspensión.
* [ ] Separar el Health de piernas y torso en el glb, o quitar ese argumento de §3.7.1.
* [ ] Dar fuente a los umbrales de Track, Ammo y Fuel (§3.7.1).
* [ ] Dibujo acotado del Gr. 38 Hl/C para su malla (§7.2). La actual sale de una figura sin cotas, escalada suponiendo que el ancho máximo es el calibre, así que sus 343 mm son [S]. Las del PzGr. 39 y el PzGr. 40 salen de los dibujos 13 C 1235 y 13 C 1236.

Alcance

* [ ] Consultar con el tutor el criterio de incapacitación (§3.7.2), como cuestión de alcance.
* [ ] [A] Segundo vehículo, opcional: la solicitud exige un mínimo de uno y el Pz IV lo cubre. Candidato, el T-44: casco muy inclinado y torreta fundida redondeada, que ejercita justo la parte del modelo que justifica medir la geometría. Va después de fragmentos, rebote, APHE y HEAT, y antes hay que comprobar que existan planos acotados (si no, el T-34-85) y que una torreta facetada pase validate_glb.py.
* [ ] [A] Ampliar los cañones del selector. El vehículo que dispara no se dibuja, así que añadir el ZiS-S-53 de 85 mm es independiente del segundo vehículo: duplica la tabla de proyectiles con sus datos.
