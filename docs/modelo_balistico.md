# Modelo Balístico

Documento de diseño del núcleo de cálculo. Define qué se simula, con qué datos y con qué fórmulas, antes de programarlo.

Convención: **[S]** supuesto, pendiente de fuente/verificación · **[A]** abierto.

Última revisión: 2026-11-04 (8ª).

---
## 1. Principios

El espesor atravesado se mide en la geometría, no en las propiedades. Para cada objeto que el rayo cruza se calcula la longitud de camino entre la intersección de entrada y la de salida.

**Thickness_mm** se conserva en cada placa para validar que la geometría coincide, relación espesor/calibre en la fragmentación, y como respaldo. **No se usa para calcular la penetración.**

Un hueco hace atravesar menos acero del real.

Tras perforar, el núcleo y todos los fragmentos se reparten la energía residual, la suma nunca puede superarla.

Blindaje y módulos hacen lo mismo, algo entra con energía, recorre un camino dentro de él, y pierde energía. Un módulo anota el daño en su atributo Health.

Toda la aleatoriedad (dispersión de fragmentos, umbrales de rebote) usa una semilla fija derivada del disparo, el mismo disparo da siempre el mismo resultado.

El disparo se calcula entero de golpe y devuelve una línea temporal de eventos, el render la reproduce a la velocidad para que se vea.

Datos fuera del código, todo sale de los ficheros de data/ y del modelo glb:
1. Cambiar un vehículo, un proyectil o un criterio no toca código.
2. El análisis de sensibilidad (§6) consiste en variar esos ficheros, así que tienen que ser el único sitio donde están los números.
3. Un dato que cambie con una fuente nueva se corrige en un solo sitio.
## 2. Datos de entrada

### 2.1 Proyectil - data/shells.csv

| Campo | Unidad | Notas |
|---|---|---|
| shell_id | — | Ammo_Caliber_Cannon |
| name | — | |
| type | — | APCBC, APCBC-HE, APCR, APHE, HEAT |
| caliber_mm | mm | calibre del cañón |
| core_diameter_mm | mm | para proyectiles sabot, vacío, se usa caliber_mm |
| mass_kg | kg | proyectil completo |
| core_mass_kg | kg | para proyectiles sabot |
| muzzle_velocity_ms | m/s | |
| explosive_mass_g | g | equivalente en TNT, 0 si no lleva |
| fuze_delay_ms | ms | solo con explosivo |
| cd | — | coeficiente de arrastre, si no hay fila en velocity.csv (§2.2.1) |
| source_id | — | clave en data/sources.md |

Magnitudes: kg, m, m/s, J, y mm únicamente para espesores y calibres, por ser la convención de las fuentes.

El APCR (y sabot) es un cuerpo de 75 mm que lleva dentro un núcleo de carburo de tungsteno, lo que perfora es el núcleo. Así que hay dos pares de columnas y el cargador deriva de cada par el valor que usa la física:

penetrating_mass_kg     = core_mass_kg     o mass_kg     si está vacía <br>
penetrating_diameter_mm = core_diameter_mm o caliber_mm  si está vacía

Lo que cuesta confundirlos: contra la placa frontal de 80 mm, usar 75 mm en vez de 28 multiplica
la masa de tapón de §3.5 por (75/28)² = 7,2, y la fracción de astillado del PzGr. 40 pasa de 0,313
a 0,765. El número equivocado sale plausible, que es lo que lo hace peligroso, así que
disparo.py saca el diámetro del propio proyectil (penetrating_diameter_mm) en vez de dejarlo a
elección de quien llama, y ballistic_data.py se niega a cargar un APCR sin core_diameter_mm.

[S] El core_diameter_mm del PzGr. 40, 28 mm, no está localizado en ninguna fuente: la ficha del KwK 40 da masa, velocidad y penetración pero no toca el núcleo. Se deriva de core_mass_kg = 0,85 kg con carburo de tungsteno a ~15 000 kg/m³ suponiendo un núcleo cilíndrico, lo que da 27-31 mm según la esbeltez que se adopte (L/d de 3,5 a 2,5); 28 mm corresponde a L/d ≈ 3,3. Lo supuesto es la esbeltez, no el diámetro. Pendiente de fuente en §10.

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
| source_id | — | clave en data/sources.md |

#### 2.2.1 Velocidad de impacto

Hace falta para evaluar la perforación de **cualquier capa que no sea la primera**: el mamparo interno, el blindaje espaciado o las orugas reciben el proyectil con velocidad residual, y esa velocidad no corresponde a ninguna distancia de la tabla.

El modelo de arrastre v(x) = v₀·e^{-Kx}, con K = ρ·Cd·A/(2m), queda como respaldo para proyectiles sin tabla, y como el método con el que se obtuvieron los puntos que faltaban del PzGr. 39.

| Distancia | m/s (PzGr. 39) | Origen |
|---|---|---|
| 100 m | 738 | del modelo |
| 500 m | 691 | medido |
| 1000 m | 636 | medido |
| 1500 m | 585 | del modelo |
| 2000 m | 537 | medido |

El Cd despejado tramo a tramo no es constante:

| Tramo (PzGr. 40) | Cd implicado |
|---|---|
| 0–100 m | 0,413 |
| 100–500 m | 0,515 |
| 500–1000 m | 0,545 |
| 1000–1500 m | 0,608 |
| 1500–2000 m | 0,690 |

La subida es física, el proyectil baja de Mach 2,7 a Mach 1,26 y el Cd crece al acercarse a la transónica. Con un Cd único ajustado a todo el rango (0,584) el error llega al −4,2 % en velocidad y −8,2 % en energía a 1000 m, que es la distancia más usada, el cd de shells.csv es respaldo, no fuente.

Dato para la memoria: el primer tramo del PzGr. 40 da Cd 0,413, prácticamente el 0,415 del PzGr. 39. Las 2 formas arrastran igual, la caída mucho más rápida del APCR viene de su masa, 4,1 kg frente a 6,8 para el mismo calibre, y eso ya lo recoge la masa en K.

Gr. 38 Hl/C, la tabla está rellena con 450 m/s constantes, es un marcador, no un dato. El proyectil decelera como cualquier otro. Se acepta porque la penetración de una carga hueca no depende de la velocidad de impacto (§5), así que el valor sólo entra en la energía del cuerpo del proyectil, que no es el penetrador. Declarado en §9.

Comprobación cruzada con la caída. Los datos de caída de la misma fuente (−2,4 m a 500 m,
−10,0 a 1000, −44,8 a 2000) son independientes de la velocidad. Derivando el tiempo de vuelo
del modelo y aplicando solo gravedad, la caída sale con un −1 % de error a 500 m, +3 % a 1000
y +9 % a 2000. La desviación a larga distancia es esperable, porque ese cálculo supone
trayectoria plana.

El exponente de De Marre, P ∝ vⁿ, se mide cruzando las velocidades reales con la tabla de penetración a 0°, tramo a tramo de distancia. ballistic_data.exponente() lo calcula así para cada proyectil, y disparo.py usa el del tramo que contiene la distancia del disparo:

| Tramo | PzGr. 39 | PzGr. 40 |
|---|---|---|
| 100-500 m | 1,415 | 0,983 |
| 500-1000 m | 1,457 | 0,942 |
| 1000-1500 m | 1,395 | 0,878 |
| 1500-2000 m | 1,406 | 0,744 |

El PzGr. 39 coincide con el valor teórico de De Marre, 1,4283, una relación teórica que no interviene en la elaboración de ninguno de los dos conjuntos de datos. El PzGr. 40 no: su exponente es menor y baja con la distancia, así que su tabla no sigue una ley de potencia única. Por eso el exponente no es un parámetro global sino una medida por proyectil y por tramo. [A] Falta saber por qué el APCR se separa de De Marre: si es física del núcleo o cómo se construyó la tabla de la fuente.

Si un proyectil cinético no tiene al menos dos distancias con penetración a 0° y velocidad, el cálculo da error en vez de usar un valor por defecto. El Gr. 38 Hl/C no lo necesita, porque la penetración de la carga hueca no depende de la velocidad (§5).

El cargador resuelve la velocidad a una distancia así, y en este orden:

1. Interpolación de velocity.csv si el shell_id tiene filas, es el caso normal.
2. Si no las tiene, v₀·e^{-Kx} con el cd de shells.csv, marcando el valor como estimado en la salida.
3. Si tampoco hay cd, error en la carga.

Para un proyectil nuevo sin datos basta un solo punto publicado de velocidad restante para despejar su Cd, a falta de eso, estimarlo por forma, declararlo supuesto y meterlo en el análisis de sensibilidad.
Si se consiguen tres puntos o más, pasa a velocity.csv y el cd deja de usarse.

### 2.3 Materiales - data/materials.csv

Una sola tabla para blindaje y módulos. El blindaje de referencia es RHA, con coeficiente 1,0.

| Campo | Notas |
|---|---|
| id | RHA, Steel, Track, Wheel, Flesh, Cast_Iron, Ammo, Gasoline, Diesel. Mayúscula inicial |
| resistance | Resistencia relativa a RHA, multiplica la longitud de camino para obtener el equivalente en RHA |
| spall | Multiplicador de masa de tapón relativo a RHA, que es 1,0. |
| source_id | clave en data/sources.md, o supuesto |

El nivel absoluto del astillado lo fija Recht-Ipson (§3.5 y §3.6) <br>
La columna cuenta cuánta masa de tapón arranca este material comparado con el RHA, con la misma convención relativa que resistance.

Seis de los nueve valores son 0 o 1 por una razón física declarable, los líquidos y la carne no arrancan tapón ni lanzan fragmentos metálicos, un impacto en munición lo resuelve la detonación de §4, y no hay base para distinguir Steel del RHA en esto, así que fingir un 0,8 sería ruido. Los discutibles son tres: Cast_Iron y Track, que se explican aquí, y Wheel, que va en el párrafo siguiente porque sus dos columnas se contradicen:

1. Cast_Iron a 1,5: frágil, rompe en fragmentos en vez de sacar un tapón limpio, así que la
masa que sale por detrás es mayor que la del cilindro geométrico.

2. Track a 0,3: una oruga son eslabones con huecos, no hay tapón coherente que arrancar.
Mismo argumento que su resistance de 0,7.

Las 2 columnas de Wheel no son coherentes entre sí. spall = 0,13 está calculado sobre los 20 mm de acero real (20/150, sin factor de calidad porque el tapón es masa). resistance = 0,40 implicaría 100 mm de acero real, que es cinco veces más:

resistance = acero_real_mm × 0,6 / camino_modelado_mm -> 20 mm da 0,08

Con 0,40 el flanco suma 14 mm de oruga + 60 de rueda + 30 de costado = **104 mm de RHA equivalente**, contra los 81 mm del frontal de 80 mm a 9°, el modelo diría que el Pz IV está mejor protegido por el costado que por el morro. Hay que fijar el número a partir de los milímetros de acero que se crea que hay, y que las dos columnas salgan del mismo supuesto. Pendiente en §10.

### 2.4 Objetos del modelo

Placas (ARM_*):
* Thickness_mm (float)
* Armour_Material (texto, id de materiales)

Módulos (MOD_*):
* Module_Type (mayúscula inicial: Crew, Engine, Transmission, Ammo, Fuel, Gun, Track)
* Health (float)
* Armour_Material (texto, misma tabla)

Los módulos no llevan propiedad de espesor, la longitud de camino por dentro de su caja ya la da la malla. Un fragmento que entra de refilón por una esquina del motor atraviesa menos que uno que lo cruza entero.

El código distingue por propiedades, no por colección ni por prefijo, glTF no transporta las colecciones de Blender. Los prefijos del nombre son una red de seguridad.

## 3. Flujo de un disparo cinético (AP, APCBC-HE, APCR)

### 3.1 Tramos

Se lanza el rayo y se obtiene la lista ordenada de tramos: objeto, punto de entrada, punto de salida, longitud, normal de entrada.

[S] Suposición de convexidad. La entrada es la primera intersección y la salida la última, lo que vale para cualquier objeto convexo. Una pieza en L o una lámina curva la rompería en silencio, así que validate_glb.py lo comprueba.

El caso que más duele es la lámina curva, y conviene entenderlo antes de modelar manteletes, cúpulas o una torreta fundida. Una lámina curva no es convexa, y con un rayo rasante a la curvatura puede dar 4 intersecciones: entra por la cara exterior, sale por la interior, vuelve a entrar por la interior y sale por la exterior. Primera y última abarcan entonces el hueco de aire intermedio, y el camino sale casi el doble del real. Con rayos aproximadamente radiales no ocurre.

Solución general, facetar. Todo lo curvo se parte en tramos casi planos, suficientes para que ningún rayo pueda cruzar dos superficies interiores dentro de la misma pieza. Es lo que se hizo con los cilindros de la transmisión, el anillo de torreta del techo del casco y el mantelete.

Las piezas se generan como intersección de semiespacios, no uniendo vértices. Cuatro puntos en el espacio no son coplanarios salvo que se les obligue, así que una placa construida a mano sale con las caras grandes alabeadas, el espesor medido no es el declarado y la pieza deja de ser convexa. Definida como intersección de planos (exterior, interior, suelo, techo y los planos de las piezas vecinas), la convexidad y la planitud salen por definición, y dos piezas contiguas comparten cara exacta porque el límite de una es el plano de la otra.

Hoy validate_glb.py no encuentra ninguna pieza no convexa. Quedan tres con una cara ligeramente alabeada, ARM_Upper_Back_Plate (5,59 mm) y ARM_Lower_Side_L_Plate y _R_Plate (1,10 mm), convexas salvo ese pliegue, que solo afecta a los rayos que pasan por ese borde (§9).

### 3.2 Agrupación por contacto

Entre tramos consecutivos se mide el hueco, entrada_siguiente − salida_actual.

El hueco se mide perpendicular a las placas, no a lo largo del rayo. Un rayo oblicuo que cruza un hueco de 0,78 mm a 70° recorre 2,27 mm de aire, y usar esa distancia haría que dos placas estuvieran en contacto para un disparo perpendicular y espaciadas para uno oblicuo. Que dos placas estén unidas o separadas es propiedad de la geometría, no del disparo:

hueco_perpendicular = hueco_a_lo_largo_del_rayo × cos(ángulo con la normal de entrada de la capa siguiente)

* [S] Hueco perpendicular < 1 mm: placas en contacto, forman una capa compuesta. Se suman los caminos equivalentes y la perforación se evalúa sobre el total.
* Hueco perpendicular ≥ 1 mm: blindaje espaciado. Se perfora la primera, se generan fragmentos en el hueco, y lo que llegue a la segunda lo resuelve el propio trazado sin código especial.

Esto resuelve además las esquinas: las bandas estrechas donde un rayo frontal cruza dos placas de una misma esquina se agrupan y se cuentan una sola vez como capa compuesta.

### 3.3 Rebote

Antes de evaluar la perforación, con el ángulo entre el rayo y la normal de entrada:

* Por encima del umbral rebota, la componente normal de la velocidad se anula casi entera y la tangencial pierde energía. El proyectil desviado sigue como un rayo nuevo, con un máximo de 2 rebotes.
* [S] El umbral depende del tipo de proyectil y de la relación calibre/espesor. Un APCBC con casquete balístico aguanta ángulos más cerrados que un APCR, nunca un umbral global.
* [S] Pequeña variación aleatoria alrededor del umbral, con semilla fija, para que no sea todo o nada.

Sin implementar, ver §10.

### 3.4 Perforación

Camino equivalente en RHA de la capa: Σ (longitud_tramo × resistance_material).

Capacidad del proyectil, desde la tabla interpolada a la distancia y al ángulo de impacto:

* Si la tabla da espesor nominal: capacidad_LOS = tabla(θ, d) / cos θ
* Si la tabla da línea de visión: capacidad_LOS = tabla(θ, d)

Perfora si camino_equivalente ≤ capacidad_LOS. En una placa plana esto reproduce exactamente la tabla, y en esquinas y capas generaliza.

Si no perfora, el disparo termina ahí y no genera fragmentos. Simplificación aceptada.

Todo tramo con Armour_Material resta capacidad, sea placa o módulo, con t_equivalente = camino × resistance. Las orugas son un módulo (Track, §3.7.1) y no una placa, porque el validador rechaza un objeto con Thickness_mm y Module_Type a la vez; si un módulo no consumiera capacidad, un disparo lateral que cruza la oruga llegaría al flanco con la capacidad intacta y la oruga no protegería de nada. No es una excepción para las orugas sino el caso general.

### 3.4.1 Capas posteriores a la primera

La cadena de perforación se lleva en capacidad, no en velocidad. Lo que necesita una segunda capa no son los m/s del proyectil sino cuántos milímetros de RHA le quedan por perforar. Recht-Ipson transplantado a esas unidades con P ∝ vⁿ:

P_residual = (P_impacto^(2/n) − t_equivalente^(2/n))^(n/2)

con n el exponente de De Marre del proyectil en el tramo de distancia del disparo (§2.2.1). El proyectil llega con la capacidad que da la tabla, la capa le consume su espesor equivalente, y el resto va contra la siguiente, sin velocidades de por medio.

La velocidad sigue haciendo falta para 2 cosas, y solo 2: la energía de núcleo y fragmentos (½mv², §3.7) y el recorrido de la espoleta del APHE (§4). Las dos toleran más error que la perforación.

### 3.4.2 Qué detiene al proyectil

Una sola cuenta de estado, la energía, y la capacidad se deduce de ella. Con P ∝ vⁿ y E = ½mv², las dos son la misma magnitud en unidades distintas:

P = P0 · (E / E0)^(n/2)  <br>
E = E0 · (P / P0)^(2/n)

| | Decide si atraviesa | Decide cuánto daño hace |
|---|---|---|
| Núcleo | La capacidad deducida de su energía | Esa misma energía |
| Fragmentos | Energía (§3.7) | Energía (§3.7) |

Los fragmentos van solo por energía, no figuran en las tablas de penetración así que no tienen capacidad y la energía es lo único que hay para ellos.

Tres consecuencias: el presupuesto cerrado de §1 se cumple por construcción y no por comprobación, las tablas de penetración quedan como único anclaje del modelo, y σ_RHA deja de intervenir en el núcleo, con lo que baja un parámetro libre de §6 y queda solo como anclaje posible de sigma_fragmento.

Por qué una sola cuenta y no dos. Llevar la capacidad de §3.4.1 y una pérdida de energía propia en paralelo da dos leyes distintas para el mismo gasto: la cadena es una ley de potencias, mientras que una pérdida lineal en el espesor sobrestima las capas delgadas. Un cartucho de 15 mm equivalentes cuesta 208 kJ por la ley lineal y 65 kJ por Recht-Ipson. El primer disparo completo lo rompió, el núcleo se quedaba sin energía en el tercer cartucho y seguía perforando el mamparo y la placa trasera con 56 mm de capacidad disponible. Con a = 1 las dos cuentas son la misma ley, E_sale/E_entra = (P_sale/P_entra)^(2/n), así que basta un estado.

Condición de parada del núcleo, al llegar a una capa nueva:

si t_equivalente(capa) > P_residual -> evento stopped

El proyectil se queda clavado, no desaparece. Entra en la capa la profundidad que le permitía su capacidad restante y se detiene ahí. Cuesta lo mismo que hacerlo desaparecer, conserva la información de dónde acabó el disparo, y muestra por qué no pasó en vez de solo decirlo.

[S] La cadena usa a = 1, sin la masa del tapón, porque es así como reproduce las tablas. La energía que da se interpreta entonces como la del núcleo más el tapón, que es lo que dice E_residual en §3.5, y el reparto de §3.6 se aplica sobre ella. La velocidad residual no lleva por tanto el factor √a, se deduce de la capacidad y no al revés.

### 3.5 Energía residual

La energía residual se calcula en §3.4.2, a partir de la cadena de capacidad. Lo que vive aquí es la masa del tapón, que §3.6 necesita para repartirla.

Límite balístico de la capa derivado de la tabla (De Marre, con el exponente verificado en §2.2.1), y velocidad residual por Recht-Ipson con p = 2 ([S], §10):

v_residual² = a · (v_impacto² − v_límite²)      con a = m_p / (m_p + m_tapón)

La a de Recht-Ipson no es una constante de ajuste. Es la masa del proyectil sobre la del proyectil más el tapón que arranca de la placa, y sale de su propio balance de energía: el tapón se va a la misma v_residual que el núcleo, y el trabajo de cizallarlo es justo el término ½·m_p·v_límite². Consecuencia directa, la energía residual es la de los dos y no solo la del núcleo:

E_residual = ½ · (m_p + m_tapón) · v_residual²

m_tapón es geometría, no un parámetro libre:

m_tapón = ρ_acero · camino · (π/4)·d² · spall        ρ_acero = 7850 kg/m³

con el camino de §3.1, que ya lleva la inclinación de la placa dentro, d el diámetro del penetrador (el del núcleo en el APCR, no el calibre del casquillo) y spall el multiplicador por material de §2.3, que vale 1 para el RHA. Para el PzGr. 39 contra los 80 mm del frontal son 2,77 kg de tapón contra 6,8 kg de proyectil.

El spall entra aquí y no en el reparto de §3.6 por una razón: así Flesh a 0 significa que no hay tapón, que es lo que pasa de verdad, y no que haya tapón pero su energía desaparezca, que rompería el presupuesto cerrado de §1.

### 3.6 Núcleo y fragmentos

El núcleo sigue. Un AP macizo que perfora no se convierte entero en metralla, el núcleo continúa como un rayo más con la mayor parte de la energía, y puede atravesar el motor y salir por el otro lado.

El reparto de la energía residual sale de la misma a de §3.5 y no de un parámetro libre. Núcleo y tapón salen a la misma velocidad, así que la energía se reparte por masa:

E_núcleo    = E_residual · a        =  E_residual · m_p     / (m_p + m_tapón)  <br>
E_astillado = E_residual · (1 − a)  =  E_residual · m_tapón / (m_p + m_tapón)

El núcleo no le cede energía al tapón, el coste de arrastrarlo ya está pagado dentro de v_límite, así que se queda con ½·m_p·v_residual² entera.

El presupuesto cerrado de §1 se cumple y es comprobable: PzGr. 39 a 750 m/s contra una capa de 600 m/s de límite, y los 1,913 MJ de entrada salen como 0,489 MJ de núcleo + 0,200 MJ de tapón + 1,224 MJ de cizalla.

Lo que da con los espesores del Pz IV H para el PzGr. 39 (75 mm, 6,8 kg) sobre RHA:

| Espesor | t/d | m_tapón | 1 − a |
|---|---|---|---|
| 20 mm (faldón) | 0,27 | 0,69 kg | 0,093 |
| 30 mm (costado) | 0,40 | 1,04 kg | 0,133 |
| 50 mm | 0,67 | 1,73 kg | 0,203 |
| 80 mm (frontal) | 1,07 | 2,77 kg | 0,290 |

Con el PzGr. 40 va de 0,115 a 0,343 en el mismo rango, que es lo esperable, un núcleo ligero arrastra un tapón comparable a su propia masa. Ese 9-34 % cae dentro del rango que cita la literatura de behind-armour debris, así que el anclaje no es solo interno al modelo.

Fragmentos, versión provisional (04/11). Solo el astillado de la placa: el proyectil no se rompe (§9), así que los fragmentos son el tapón partido en trozos.

* N = m_tapón / masa_fragmento, redondeado, con masa_fragmento = 5 g [S]. Todos de la misma masa, m_tapón / N; todavía sin distribución de Mott.
* Salen del punto de salida de la capa a la misma velocidad que el núcleo, como dice §3.5, así que se reparten E_astillado a partes iguales: E_fragmento = E_astillado / N. La suma es exacta y el presupuesto de §1 sigue cerrado.
* Dirección al azar, uniforme en ángulo sólido, dentro de un cono alrededor de la dirección del núcleo cuyo semiángulo depende del tipo de proyectil (`cono_fragmentos_<tipo>_deg`; de momento 30° [S] en APCBC-HE y APCR), con la semilla del disparo (§1).
* Cada fragmento es un rayo con la ley de pérdida por recorrido de §3.7 y el diámetro de una esfera de acero de su masa, d = (6m / (π·ρ))^(1/3), 10,7 mm para 5 g. Se da por detenido cuando le quedaría menos de 1 J [S], que no supera ningún umbral ni deposita nada apreciable.
* Daña con las mismas reglas que el núcleo (§3.7.1). Como núcleo y fragmentos pueden tocar el mismo módulo, la salud se aplica al final, ordenando todos los eventos por tiempo.
* Un fragmento no genera fragmentos al atravesar una placa, no rebota y no se rompe.

Lo que da en el disparo de referencia, PzGr. 39 a 100 m contra el frontal: 562 fragmentos de 5 g y 458 J del frontal, 69 del mamparo y 141 de la placa trasera. Con ellos quedan fuera cuatro de los cinco tripulantes y 18 cartuchos, frente a dos tripulantes y cuatro cartuchos con el núcleo solo. El resultado depende mucho de la masa del fragmento y del cono (§6): con menos fragmentos y más grandes, el daño se concentra en menos objetos.

Rendimiento: un rayo por fragmento, unos 5 ms por rayo en Python y unos 4 s por disparo. Un barrido masivo necesitaría rayos representativos con peso.

### 3.7 Pérdida de energía y daño

La energía perdida depende del área frontal del penetrador, no solo del camino. Una constante global por unidad de longitud no vale, un núcleo de 75 mm y una esquirla de 3 mm no depositan lo mismo por milímetro recorrido, porque la resistencia del material actúa sobre la sección que empuja.

Para el núcleo la pérdida sale de la cadena de capacidad (§3.4.2). Para cada tramo, con t_eq = camino × resistance:

P_entrada = P0 · (E / E0)^(n/2)                     la capacidad que le corresponde a su energía  <br>
P_salida  = (P_entrada^(2/n) − t_eq^(2/n))^(n/2)    la cadena de §3.4.1  <br>
E_salida  = E · (P_salida / P_entrada)^(2/n)  <br>
si el módulo es acumulativo (§3.7.1):  Health -= (E − E_salida)

Al perforar una placa, la energía que sale es la E_núcleo de §3.6, con el tapón ya descontado, de la que se vuelve a deducir la capacidad. Así el reparto de Recht-Ipson y la cadena no son dos cuentas que haya que conciliar, la segunda es consecuencia de la primera.

Dentro de una capa compuesta la pérdida se reparte entre los tramos en proporción a la capacidad que consume cada uno. La cadena no se aplica tramo a tramo porque §3.2 evalúa la capa sobre el total, y la ley de potencias no es aditiva, (a+b)^k > a^k + b^k, que es justo por lo que una capa compuesta cuesta más que dos placas separadas.

El núcleo no se detiene por energía agotada, sino porque el camino equivalente de la capa supera su capacidad (§3.4.2). Las dos se agotan juntas.

Los fragmentos no tienen capacidad, así que conservan la ley por recorrido:

E -= camino × resistance_material × σ_fragmento × (π/4)·d²  <br>
si E < energia_minima_fragmento_J (1 J): se detiene dentro del objeto

con camino en metros, d el diámetro del fragmento en metros y σ_fragmento una resistencia dinámica en Pa. [S] Fijada provisionalmente en 3,10 GPa, el σ_RHA del PzGr. 39, en parametros.csv. Una esquirla no figura en ninguna tabla de penetración, así que no se puede derivar como σ_RHA; el valor es una aproximación declarada y va al análisis de sensibilidad (§6).

De dónde salía σ_RHA, que el núcleo ya no usa pero sigue siendo el único anclaje disponible. En el límite balístico el proyectil deposita toda su energía en el espesor que justo perfora:

σ_RHA = E_impacto / (espesor_perforado × área_frontal)

| Proyectil | E a 100 m | Perfora | d penetrador | σ_RHA |
|---|---|---|---|---|
| PzGr. 39 | 1,852 MJ | 135 mm | 75 mm | 3,10 GPa |
| PzGr. 40 | 0,348 MJ | 176 mm | 28 mm | 3,21 GPa |

Dos proyectiles con un factor 5 de diferencia en energía dan σ dentro de un 3,5 %, y σ no se ha ajustado a ninguno de los dos. Eso sí es validación, del mismo tipo que el exponente de De Marre de §2.2.1, y conviene presentarlo como tal en la memoria porque es uno de los pocos resultados del proyecto que no es circular (§8).

Dos avisos sobre lo que vale el contraste. σ es inversamente proporcional a d², y los 28 mm del núcleo del PzGr. 40 son [S] (§2.1, derivados de la masa y de un L/d supuesto): con 30 mm saldrían 2,80 GPa en vez de 3,21. Y en el límite no toda la energía va a la placa, algo queda como velocidad residual, así que σ sale ligeramente sobrestimada en los dos casos.

Health se expresa en julios, así que no hay constante de conversión entre energía depositada y daño: el daño es la energía depositada.

### 3.7.1 La regla de daño depende del tipo de módulo

La energía depositada vale para máquinas, no para personas. Un motor se avería absorbiendo energía, cuanto más lo atraviesa el proyectil más destroza, y acumular tiene sentido. A una persona no la incapacita la cantidad de tejido recorrido sino alcanzar algo vital.

El problema se ve con números. Las piernas de un tripulante sentado se extienden 0,82 m hacia delante y el torso tiene 0,27 m de fondo, así que un fragmento frontal recorre el triple de carne en las piernas:

| Fragmento | Torso (0,27 m) | Piernas (0,82 m) |
|---|---|---|
| 3 mm | 61 J | 186 J |
| 5 mm | 170 J | 517 J |
| 10 mm | 681 J | 2067 J |

Con el mismo Health en ambos, el modelo diría que un disparo frontal destroza las piernas 3 veces más que el torso, lo contrario de la realidad. Subir el Health de las piernas solo taparía el síntoma.

Por tanto, una rutina de recorrido y dos reglas de daño:

| Module_Type | Regla |
|---|---|
| Engine, Transmission, Gun | Daño = energía depositada, acumulativa |
| Crew | Incapacitado si un fragmento entra con energía por encima del umbral, la energía que deposite después no cuenta |
| Track | [S] Igual que Crew, inmovilizado si un penetrador cruza el objeto con energía de entrada por encima de su Health, que es un umbral propio de cada objeto |
| Ammo, Fuel | Umbral de detonación / ignición (§4, §7) |

El rayo se frena igual en todos los casos, lo único que cambia es cómo se traduce eso en daño.

Health significa dos cosas según la regla, y solo una se decrementa:

| Regla | Qué es Health | Qué le pasa durante el disparo |
|---|---|---|
| Acumulativa (Engine, Transmission, Gun) | Reserva en julios | Se decrementa, el estado es la fracción que queda |
| Umbral (Crew, Track, Ammo, Fuel) | Umbral de energía de entrada | No se decrementa nunca, el estado es un booleano |

Si en los tipos de umbral se restara, el número resultante no significaría nada: ni reserva restante porque no hay reserva, ni distancia al umbral porque el umbral se compara contra la energía de entrada de un solo impacto y no contra una suma. Sería un residuo, y cualquier cosa que lo leyera trabajaría con ruido, el color de §7.2 el primero, pero también las reglas de fuera de combate de §7 y la agregación de §3.7.3.

La oruga es un módulo porque su avería inmoviliza el vehículo, y por eso no es una placa. [S] Umbral y no acumulación, por una razón de modelado y otra física. La de modelado: las orugas son 22 piezas por lado solo porque cada una debe ser convexa (§3.1), y con daño acumulativo el resultado dependería de cómo se ha cortado la cinta. La física: una oruga no se rompe por la suma de muchas esquirlas pequeñas, sino cuando algo corta un eslabón o un pasador.

[S] Health de la cinta = 5 kJ, orden de magnitud propio y sin fuente: cizalla doble de un pasador de Ø25 mm (≈ 400 MPa × 2 × 4,9·10⁻⁴ m² ≈ 400 kN sobre ≈ 8 mm de recorrido ≈ 3 kJ). Cualquier AP que la cruce lo supera con holgura, el astillado que llega con cientos de julios no.

[S] La rueda motriz también es Track, con Health = 20 kJ: sin la motriz la oruga no recibe potencia, así que su avería inmoviliza igual que cortar la cinta. Cuatro veces el de la cinta por ser una pieza maciza y no un eslabón con pasador, sin fuente. Cada objeto Track conserva su propio umbral, así que mezclar valores dentro del tipo no plantea ningún problema. La tensora es Track por el mismo argumento, con Health = 16 kJ y sin fuente: sin ella la cinta pierde tensión y se sale. Las ruedas de rodadura, en cambio, son placas y no módulos: perder una no inmoviliza el vehículo.

Órdenes de magnitud que produce el modelo, útiles para fijar los valores:

| Caso | Energía depositada |
|---|---|
| Esquirla de 3 mm cruzando 30 cm de torso | 68 J |
| Esquirla de 5 mm, mismo torso | 189 J |
| Esquirla de 10 mm, mismo torso | 756 J |
| Núcleo de 75 mm, 10 cm dentro del motor | 225 kJ |

[S] Valores de partida de Health:

| Module_Type | Health | Criterio |
|---|---|---|
| Crew torso y cabeza | 80 J | Umbral de energía de entrada del fragmento. Convención declarada, no criterio validado, ver §3.7.2 |
| Crew piernas | 3-5× el del torso | La dependencia de la región del cuerpo está reconocida en los modelos de vulnerabilidad militares, así que el efecto es citable; el factor concreto es supuesto y va al análisis de sensibilidad (§6) |
| Transmission | ~150 kJ | Menor que el motor, un impacto de lleno la inutiliza |
| Engine | ~300 kJ | Un núcleo que llega con esa energía se detiene dentro del motor y la deposita entera |
| Gun tubo | ~40 kJ | Acero macizo de pared gruesa, y sale por delante del mantelete. El más robusto de los dos |
| Gun recámara | ~25 kJ | Mecanismo de precisión, se agarrota mucho antes de destruirse. Los dos valores son parámetros libres (§6) sin fuente; lo razonado es el orden, tubo por encima de recámara |
| Ammo | 150 J por cartucho | Umbral de detonación, no reserva. Sin fuente |
| Fuel | 5000 J | Umbral de ignición, no reserva. Sin fuente. El incendio no es destrucción instantánea (§7) |

Los dos valores acumulativos se fijaron con la ley lineal de σ_RHA, que ya no se usa, así que hay que recalibrarlos (§10).

### 3.7.2 El umbral de 80 J es una convención sin validar

Hay que escribirlo con precisión, porque la bibliografía dice algo distinto de lo que suele citarse.

Qué se creía: que 80 J (58 ft·lb) es el umbral de incapacitación por fragmento. Nota de unidades, 58 ft·lb son 80 J, no son dos criterios distintos ni los extremos de un rango.

Qué dice la fuente. El artículo PMID 28505551, en data/sources.md, rastrea el origen del criterio hasta Rohne y concluye tres cosas:

1. Ni Rohne ni los balísticos de la década siguiente explicaron de dónde salía el valor de 8 mkg ni qué entendían por inmovilización.
2. El poder de penetración de la bala M/88 a 80 J se reprodujo en laboratorio sobre jabón balístico, y la profundidad alcanzada es llamativamente alta, lo que respalda la afirmación de Rohne.
3. Pero no fue posible validar el criterio, y el artículo recomienda explícitamente no usar un límite de energía para definir ningún tipo de incapacitación.

Dos saltos, no uno. Aunque el criterio fuese válido, se refiere a una bala M/88 penetrando tejido. Aquí se aplica a fragmentos de blindaje: irregulares, volteando, con otra relación entre energía y daño. Trasladarlo es una segunda suposición sin validar, que el artículo ni aborda.

Se mantienen los 80 J como valor de partida porque dentro del alcance de este trabajo no hay sustituto mejor, cualquier criterio más fino es balística de heridas y no penetración de blindaje. Pero cambia de categoría: deja de presentarse como dato con fuente y pasa a convención con origen documentado y sin validación, citada en §9 y ajustable desde fichero (§1, §6). Declararlo así es mejor defensa que citarlo con aplomo.

[A] Pendiente de consulta con el tutor, y la pregunta es de alcance y no de balística: ¿se acepta un criterio de daño a la tripulación que es una convención sin validar y declarada como tal, o el proyecto necesita otro criterio?

### 3.7.3 Un Module_Type puede abarcar varios objetos

Algunos tipos se evalúan en conjunto y no pieza a pieza. La munición ya funcionaba así, hay 87 cartuchos como objetos independientes y la detonación de cualquiera inutiliza el vehículo. En vez de un caso especial por tipo, una sola regla:

| Module_Type | Agregación entre objetos del mismo tipo |
|---|---|
| Ammo | OR, basta con que uno detone |
| Gun | OR, tubo y recámara son piezas funcionalmente distintas y con cualquiera de las dos fuera de servicio el vehículo no puede devolver el fuego. Cada una gasta su propio Health |
| Track | OR entre todos los objetos del tipo, cinta y motriz de ambos lados. El lado (_L/_R del nombre) solo sirve para informar de cuál fue |
| Crew | OR dentro de cada tripulante, pero cada tripulante cuenta por separado (§7) |
| Engine, Transmission | SUMA, las piezas son un corte de convexidad de una sola máquina, así que su Health se suma y la máquina cae cuando el daño acumulado llega al total |
| Fuel | Cada objeto por su cuenta, hoy hay uno |

Hay dos preguntas distintas y conviene no mezclarlas. Una es cómo se acumula el daño dentro de un objeto, que la responde §3.7.1, acumulativo o umbral. La otra es cómo se combinan los veredictos de varios objetos en uno del módulo, que es esta sección. Son independientes, y de ahí que Gun sea acumulativo dentro de cada pieza y OR entre ellas.

Para combinar, lo que decide es por qué hay varias piezas. Si cada objeto es una unidad real e independiente (los tripulantes, los depósitos) o una pieza funcionalmente distinta (tubo y recámara), el veredicto es por objeto y se combinan con OR. Si la división es un artefacto de la convexidad o del modelado, entonces:

* Con daño de umbral (orugas, munición), OR. El umbral se compara contra la energía de entrada de un solo impacto, así que el resultado no depende de en cuántos trozos se cortó la pieza.
* Con daño acumulativo (motor, transmisión), SUMA. Aquí el OR sí depende del corte: la transmisión son 5 cajas de 30 kJ, y con OR agotar una sola inutilizaría la transmisión entera, o sea 30 kJ en vez de los 150 kJ de la máquina, mientras que cortarla en dos cajas de 75 kJ daría otra respuesta. El motor son 3 piezas convexas con los 300 kJ repartidos por volumen en 228,0 / 36,0 / 36,0 kJ, y con OR una esquirla afortunada en una pata de 36 kJ dejaría el tanque inmóvil.

Al repartir un módulo acumulativo en varias piezas, el Health se divide por volumen para que la suma sea el del conjunto, como hace tools/crear_canon_motor.py. Es la pregunta que hay que hacerse al modelar cualquier cosa nueva en varias piezas.

## 4. APHE

Perfora igual que un cinético (§3.3 a §3.5). La diferencia viene después.

1. [S] Armado de la espoleta. Si el camino equivalente de la capa queda por debajo de un umbral, la espoleta no se arma y el proyectil sigue sin detonar.
2. Recorrido con retardo, distancia = v_residual × fuze_delay, medida desde el punto de salida de la capa. [S] Se supone velocidad constante durante el retardo, que es muy corto.
3. Punto de detonación. Si cae dentro del vehículo, detona ahí. [A] Si cae fuera porque lo ha atravesado entero, hay que definir la regla; lo razonable es que detone fuera y no cause daño interior.
4. Explosión, con la energía del explosivo repartida entre fragmentos de la carcasa en 360° ([S] velocidad por Gurney, distribución de tamaños por Mott) y onda expansiva, una esfera de rayos con oclusión por los módulos ([S] distancia escalada de Hopkinson-Cranz, más un factor de confinamiento por estar en un espacio cerrado).

Primera versión 360° uniforme, se mejora si sobra tiempo.

## 5. HEAT

La carga hueca cambia la moneda del cálculo.

* Detona al contacto con la primera superficie, sin perforación previa.
* [S] La penetración no depende de la velocidad de impacto ni de la distancia de tiro. Depende del calibre, del ángulo y de la distancia de detonación (standoff).
* El chorro es un rayo estrecho desde el punto de detonación, a lo largo de la dirección de impacto.
* El chorro tiene una capacidad en mm de RHA equivalente que se va consumiendo con camino × resistance de cada tramo. Cuando se agota, se detiene.
* El ángulo lo resuelve la geometría, para un chorro no hay efecto de inclinación más allá de la línea de visión.

[S] Blindaje espaciado contra HEAT. No actúa por material sino por distancia de detonación, el chorro detona antes y llega disperso. Esto no lo captura la longitud de camino y hay que tratarlo aparte con una curva de penetración frente a standoff. Es la única parte del modelo donde el blindaje espaciado necesita código propio.

[S] Conversión a energía. Para que la rutina de daño de §3.7 sea única, al salir del blindaje la capacidad restante del chorro se convierte a energía con una constante declarada. A partir de ahí, chorro y fragmentos se tratan igual.

## 6. Parámetros libres

Es la parte más difícil de defender, porque no hay datos para calibrarla: las tablas solo cubren la perforación, no los efectos tras el blindaje. Cada parámetro es un número que hay que justificar o declarar como supuesto.

Los que no dependen del proyectil van en data/parametros.csv como pares clave-valor. Los que dependen de él irán en data/fragmentation.csv, una fila por tipo, cuando haga falta distinguirlos; hoy los de fragmentos son únicos y están en parametros.csv. Nunca escondidos en el código (§1). Los Health de los módulos salen del modelo glb.

| Parámetro | Depende de | Qué controla |
|---|---|---|
| masa_fragmento_g | — | masa de cada fragmento; fija cuántos salen, N = m_tapón / masa. [S] 5 g provisional (§3.6) |
| cono_fragmentos_<tipo>_deg | tipo | semiángulo del cono de fragmentos, uno por tipo de proyectil (falta la clave → error). [S] 30° provisional en APCBC-HE y APCR, falta el valor propio del APCR |
| ricochet_angle | tipo, calibre/espesor | umbral de rebote |
| sigma_fragmento_GPa | — | pérdida de energía por recorrido, solo de los fragmentos (§3.7). [S] 3,10 GPa, el valor del núcleo como aproximación declarada |
| energia_minima_fragmento_J | — | por debajo, el fragmento se da por detenido (§3.6). [S] 1 J |
| umbral_crew_torso | — | energía de entrada que incapacita (§3.7.2). Sin validar, y el que más probabilidades tiene de cambiar |
| umbral_crew_piernas | — | múltiplo del umbral del torso (§3.7.1) |
| fuze_arm_threshold | solo APHE | espesor mínimo para armar |
| standoff_curve | solo HEAT | penetración frente a distancia de detonación |

Esta tabla es la sección de limitaciones de la memoria, cuantos menos parámetros más defendible el modelo.

El número de fragmentos no es libre: sale de m_tapón / masa_fragmento. Lo libre es la masa, y con una distribución de tamaños de Mott, la que ya se usa para la carcasa del HE en §4, pasaría a ser la masa media.

Dos parámetros que estuvieron en esta tabla y ya no hacen falta, porque conviene saber por qué no están. Un coeficiente de absorción por recorrido para el núcleo: la pérdida es ahora la caída de la cadena de capacidad (§3.4.2), así que no hay nada que calibrar. Y una fracción de astillado por proyectil: la fija la a de Recht-Ipson y la masa del tapón, que es geometría (§3.5 y §3.6), y además no podía funcionar porque un fichero por proyectil no sabe en qué material está pegando.

Fuentes a consultar, verificando rangos de validez: Recht e Ipson, Ballistic Perforation Dynamics, J. Appl. Mech. 30(3), 1963, de donde sale la a de §3.5; Backman y Goldsmith, The mechanics of penetration of projectiles into targets, Int. J. Eng. Sci., 1978, con el mapa de modos de fallo frente a t/d; Rosenberg y Dekel, Terminal Ballistics; Zukas, Impact Dynamics; Bird y Livingston, WWII Ballistics: Armor and Gunnery.

## 7. Salida: línea temporal

El cálculo devuelve una lista de eventos con instante y posición, que el render reproduce a cámara lenta. Formato JSON, que es también lo que comparan las pruebas.

Tipos de evento: impact, ricochet, stopped, perforation, fragment_spawn, module_hit, detonation, exit.

El esquema se fija antes de escribir el núcleo, no al llegar a la interfaz. Es el contrato entre cálculo y render, y el formato de los casos de prueba de §8: cambiarlo en marzo obliga a rehacer todos los casos.

Estado final del vehículo. Por ahora solo se muestra el daño acumulado por módulo. [A] Más adelante, reglas de fuera de combate: munición alcanzada, o muerte de un tripulante crítico. Hay que definirlas antes de la entrega. Inmovilizado, propuesta: motor o transmisión fuera de servicio, o cualquier objeto Track fuera de servicio (§3.7.3).

### 7.1 Campos de un evento

| Campo | Para qué |
|---|---|
| type | uno de los ocho tipos de arriba |
| t_s | instante, en segundos desde el primer contacto |
| ray_id | identificador del rayo. Sin él el recorrido no se puede dibujar |
| parent_id | rayo del que nació, o null para el núcleo |
| object | nombre del objeto del glb, o null si el tramo es aire |
| pos | punto del evento, en coordenadas del modelo |
| normal | normal de entrada de la cara. Hace falta para orientar la marca del agujero de §9 |
| path_mm, angle_deg | camino dentro de la capa y ángulo respecto a la normal |
| capacity_in_mm, capacity_out_mm | capacidad antes y después (§3.4.1). Solo en el núcleo |
| energy_in_J, energy_out_J | energía antes y después (§3.7) |
| health_in_J, health_out_J | vida del módulo antes y después. Solo en module_hit |
| out_of_service | [A] bool, solo en module_hit y detonation. En los tipos de umbral health_out_J no cambia, así que esto es lo único que dice el estado |
| plug_mass_kg, spall_energy_J, shear_energy_J | [A] solo en perforation: masa del tapón (§3.5), energía que se lleva (alimentará los fragmentos de §3.6) y energía de cizalla. Con energy_out_J cierran el presupuesto de §1 |
| n_fragments, fragment_mass_kg, fragment_diameter_mm | solo en fragment_spawn: cuántos fragmentos salen, de qué masa y de qué diámetro (§3.6). Cada fragmento es un rayo con su propio ray_id y con parent_id el rayo que perforó la capa |

El recorrido es un árbol, no una lista. En cada fragment_spawn nacen N rayos y el núcleo continúa, así que sin ray_id y parent_id el render no sabe qué segmento une con cuál.

La vida del módulo va en el evento aunque sea redundante. El render podría arrancar de los Health del glb e ir restando, que es lo que hará para pintar el color, pero guardarla permite saltar a un instante cualquiera de la barra de tiempo sin reproducir desde cero, y deja que las pruebas de §8 comprueben el daño directamente en vez de recalcularlo.

Instantes derivados del camino, t += camino / v_media_del_tramo, con las velocidades de §3.5. §3.4.1 va en capacidad y no produce tiempos por sí sola, así que sin esto la línea temporal no tiene nada que interpolar.

[A] Cuando un módulo detiene al proyectil se emiten dos eventos, module_hit con toda la energía depositada y stopped, que repite esa misma energy_in_J. Hay que decidir cuál de los dos la lleva antes de que el render dependa del JSON, o quien sume la energía depositada leyendo eventos la contará dos veces.

### 7.2 Reproducción

Tiempo no uniforme, en tres fases. En el disparo de referencia (PzGr. 39 a 100 m contra el frontal, disparo.py sin argumentos) el núcleo tarda 12,8 ms desde el primer contacto hasta salir por la placa trasera, y perforar el frontal le lleva 139 µs, el 1,1 % del total. Un frame a 60 fps son 16,7 ms, así que el disparo entero ocurre dentro de un solo frame. Con una escala única, o la perforación es invisible o el interior es interminable:

| Fase | Duración real | En pantalla | Factor |
|---|---|---|---|
| Aproximación (últimos ~5 m) | 6,7 ms | 1,5 s | ×225 |
| Perforación de la capa | 139 µs | 1,5 s | ×10 800 |
| Interior y fragmentos | 13 ms | 2 s | ×150 |

La aproximación arranca a unos metros del vehículo, no a la distancia de disparo: a 1000 m, mostrar el vuelo a escala es un minuto de cielo vacío. El vuelo libre no tiene física en el modelo, porque la penetración sale de la tabla indexada por distancia (§2.2), así que es decorado y puede ir a la escala que convenga.

Vista de rayos X al contacto, con el blindaje en torno al 20 % de opacidad, salvo dos excepciones:

* La capa golpeada se queda opaca, y solo el resto se vuelve translúcido. Si todo se transparenta a la vez se pierde justo lo que hay que ver, que es el agujero abriéndose.
* La transparencia entra desvaneciéndose durante la fase de perforación, ya estirada a 1,5 s, no de golpe antes del impacto.

Con 281 objetos, ordenar transparencias por profundidad se pone caro: el blindaje se dibuja sin escritura en el búfer de profundidad y sin ordenar, que es suficiente para una cáscara translúcida.

El color del daño sale de Health, pero no todos los módulos llevan degradado, porque §3.7.1 define dos reglas de daño y eso parte el mapeo en dos:

| Module_Type | Visual |
|---|---|
| Engine, Transmission, Gun | Degradado continuo de Health / Health_inicial: gris claro intacto, rojizo al acercarse a cero |
| Crew, Track, Ammo, Fuel | Dos estados, no degradado: intacto o fuera de servicio |

La razón es del modelo, no del render. En esos cuatro tipos el Health es un umbral y no una reserva (§3.7.1), así que no existe nada entre el 100 % y el 0 %. Un degradado ahí mentiría, porque daría a entender que un tripulante está medio incapacitado cuando el modelo solo conoce dos estados. Gris claro y no blanco puro, que se lava contra el blindaje translúcido.

Tres mallas de proyectil, por revolución de un perfil: PzGr. 39, PzGr. 40 y Gr. 38 Hl/C. En los APCR el núcleo se desengancha en la primera perforación: con el evento perforation de la primera capa la malla del PzGr. 40 desaparece y el núcleo sigue como su rayo (parent_id null, §7.1), sin malla propia, que no se modela por simplificación. Es lo que calcula el modelo, porque el penetrador es el núcleo de tungsteno y no el cuerpo (penetrating_mass_kg, §2.1); mostrar los 75 mm enteros cruzando el interior contradiría esa física. Licencia visual declarada: el cálculo usa el núcleo desde el primer contacto, y el render mantiene la malla completa mientras perfora la primera capa. Si el APCR no perfora la primera capa, la malla completa se queda clavada (evento stopped). Son objetos puramente visuales, sin Thickness_mm, sin Module_Type y sin material de §2.3, y van en ficheros aparte, uno por malla, no dentro del vehículo. El nombre del fichero es el shell_id de shells.csv más .glb, para que el motor cargue la malla a partir del identificador del proyectil sin tabla de equivalencias: models/PzGr39_75_L48.glb, models/PzGr40_75_L48.glb y models/Gr38HlC_75_L48.glb.

Convenio de ejes de esas mallas: la punta del proyectil está en el origen (0, 0, 0) y el cuerpo se extiende hacia -Y, de modo que el eje de revolución es el eje Y y la malla queda centrada en X y Z. Así el motor coloca la malla directamente en el pos de un evento de §7.1, que es el punto de intersección del rayo con la superficie, y la punta cae sobre el impacto sin ningún desfase que compensar. Unidades en metros, las mismas del vehículo.

## 8. Validación

Pruebas como datos. Cada caso es un JSON con el rayo de entrada y el resultado esperado. Cuando se elija motor y se porte el núcleo, los mismos ficheros validan la versión nueva. Eso convierte la elección de motor en algo casi secundario, el motor solo dibuja la línea temporal.

Prueba de regresión, dentro de disparo.py --selftest, sobre models/Pz IV H.glb:

| | |
|---|---|
| Origen / dirección | (0,50, −2,00, 1,30) / (0, 1, 0) |
| Primer impacto | ARM_Upper_Front_Plate |
| Longitud de camino | 81,00 mm |
| Ángulo respecto a la normal | 9,00° |
| Propiedades | Thickness_mm 80, Armour_Material RHA |

Los 81,00 mm son los 80 nominales divididos por el coseno de 9°. Si el cálculo devuelve 80,0 es que está midiendo con la propiedad y no con la geometría.

Validación contra las tablas, también en disparo.py --selftest. Para cada una de las 19 celdas de penetration.csv de los dos proyectiles cinéticos, una placa plana del espesor tabulado perfora justo por debajo y se queda clavada un 0,1 % por encima. Confirma la afirmación de §3.4 de que en placa plana el modelo reproduce exactamente la tabla, y hay que reejecutarlo cada vez que se toque penetration.csv o el exponente n.

Invariante que comprueba la autoprueba: ningún disparo puede acabar con el núcleo sin energía y con capacidad disponible. Es lo que fallaba con dos cuentas en paralelo (§3.4.2), y con la cuenta única no puede ocurrir, así que la prueba está ahí para detectar que alguien reintroduzca una segunda ley.

Barrido de coherencia, 1416 disparos: dos proyectiles, cuatro distancias, cuatro caras del vehículo y tres giros de dirección. Comprueba que el tiempo no retrocede, que la energía y la capacidad nunca suben, que un proyectil parado acaba con 0 J, que uno que sale lleva energía, y que el Health acumulativo solo baja mientras el de umbral no cambia. Ninguna excepción y ninguna incoherencia. Dice que el modelo es coherente, no que acierte.

[A] Pero todo esto por sí solo es circular, y hay que decirlo. penetration.csv es la entrada del modelo, así que reproducir la tabla demuestra que la interpolación y la geometría funcionan, no que el modelo acierte. Es una prueba de regresión necesaria, no una validación.

Para que haya validación hacen falta datos independientes de los que alimentan el modelo. La vía más practicable aprovecha la columna criterion de §2.2: alemanes, británicos y estadounidenses midieron el mismo cañón con criterios de penetración distintos. Si el modelo, alimentado con la tabla alemana, reproduce las mediciones aliadas del KwK 40 dentro de un margen declarado, eso ya no es circular. Localizar esas mediciones es tarea abierta y es la pregunta que va a hacer el tribunal.

El resultado de §2.2.1 sobre el exponente de De Marre es validación real para el PzGr. 39, y conviene presentarlo como tal: dos conjuntos de datos históricos independientes coinciden con una relación teórica que no interviene en la elaboración de ninguno de los dos. Para el PzGr. 40 la misma comprobación falla, y también hay que presentarlo: por eso el modelo no supone De Marre, sino que mide el exponente en los datos de cada proyectil. El contraste de σ_RHA entre los dos proyectiles de §3.7 es del mismo tipo, con la reserva del diámetro del núcleo.

## 9. Limitaciones declaradas

* Un APHE que no perfora puede romperse o detonar en superficie, no se modela.
* Una placa gruesa golpeada cerca de su límite puede astillar por dentro sin ser perforada, no se modela.
* Sin deformación real del blindaje ni del proyectil, solo una marca del agujero.
* No se modela la rotura del proyectil. Cuando la capacidad residual no alcanza para la capa siguiente, el núcleo se detiene y se queda clavado (§3.4.2) en vez de fragmentarse. Un núcleo que llega al límite suele romperse de verdad, y eso generaría fragmentos que aquí no existen. La decisión favorece lo conservador, menos daño del real y no más.
* Las caras de canto dan un ángulo y un espesor no representativos. Un rayo que entra por el borde de una chapa horizontal de 8 mm puede recorrer 245 mm por dentro de ella. Hay que tratar aparte las caras cuya normal es casi perpendicular a la normal exterior de su placa.
* La suposición de convexidad (§3.1), que incumplen en un borde las tres caras alabeadas de esa sección.
* [S] La cadena de capacidad usa a = 1 (§3.4.2), así que la velocidad residual que se deduce de ella no lleva el factor √a que sí lleva la fórmula de §3.5. La alternativa, meter a dentro de la cadena, apartaría la predicción de perforación de las tablas, que son el único anclaje del modelo.
* [S] La ley de pérdida de los fragmentos usa sigma_fragmento = 3,10 GPa, tomado del núcleo (§3.7, §6). El núcleo se libró de ese coeficiente al derivar la energía de la capacidad, pero una esquirla no figura en ninguna tabla de penetración, así que para ella no hay anclaje equivalente.
* Los torsos y las piernas del artillero y del cargador se solapan (40,0 y 8,8 mm) y se dejan así para no rehacer la malla de los tripulantes. No afecta al resultado porque §3.7.3 agrega con OR dentro de cada tripulante. Sí afectaría un solape entre objetos de módulos distintos, porque ahí el camino se contaría dos veces.
* Las ruedas del tren de rodaje se quedan como prismas macizos, motriz, tensora y rodadura. Vaciarlas sería mucho modelado para un detalle que no cambia el daño, que lo decide el tipo de módulo y no la forma. Pero entonces el material no puede ser Steel: un disparo lateral cruza una rueda a lo ancho, 150 mm en las de rodadura y 250 mm en la motriz, que con 0,6 serían 90 y 150 mm de RHA equivalente sumados al flanco, contra los 30 mm del costado del casco. Una rueda real son dos chapas estampadas con aire en medio, y el acero que cruza de verdad un disparo lateral son unos 20 mm. De ahí el material Wheel, igual que Track vale 0,7 para una cinta que en realidad son eslabones con huecos: la simplificación está en la geometría y la corrección va en el material. Su resistance está a 0,40 de forma orientativa y el orden sigue invertido, pendiente de fijar (§2.3, §10).
* La cinta de la oruga es una plancha continua de 20 mm, y la real son eslabones con huecos. Lo compensa en parte la resistance de 0,7 de Track, que es un promedio y no una geometría.
* La distinción entre torso y piernas de §3.7.1 no está en el modelo. Los diez objetos de tripulación llevan 80 J, piernas incluidas, así que hoy el modelo hace justo lo que ese apartado dice que no hay que hacer.
* Los parámetros de §6 no están calibrados contra datos de efectos tras el blindaje.
* El tapón cilíndrico de §3.5 es una cota superior fuera del régimen de cizalla. La fórmula vale mientras la placa falle arrancando un tapón, que es hasta t/d ≈ 1. La placa frontal está justo en el borde (80 mm contra 75 mm de calibre, t/d = 1,07), pero el frontal de torreta y las ruedas de 150 mm están en t/d ≈ 2, donde el fallo real es ensanchamiento dúctil con erosión del núcleo y no hay tapón coherente. Ahí el modelo sobrestima el astillado. Referencia del mapa de modos de fallo en §6.
* El criterio de incapacitación de la tripulación es una convención sin validar (§3.7.2). La fuente que documenta su origen recomienda explícitamente no usar umbrales de energía para esto. Se usa por falta de alternativa dentro del alcance, no por estar respaldado.
* La velocidad del Gr. 38 Hl/C está puesta como constante y no lo es (§2.2.1). Irrelevante para su penetración, que no depende de la velocidad.
* La validación contra tablas es circular mientras no haya datos independientes (§8).
* El rebote (§3.3) no está implementado. Los fragmentos (§3.6) son provisionales: solo los del tapón, todos de la misma masa, sin fragmentos secundarios ni rotura del proyectil, y con la masa, el cono y σ_fragmento supuestos.

## 10. Pendientes

Datos

* [ ] Fijar el resistance de Wheel. Está a 0,40 de forma orientativa y deja el flanco por encima del frontal, y su spall de 0,13 sale de otro supuesto, 20 mm de acero real. Las dos columnas tienen que salir del mismo número de milímetros (§2.3).
* [ ] Resolver la contradicción del fuze_delay_ms del PzGr. 39. shells.csv dice 3 ms y este documento dice que la Bd.Z. 5103 no lleva retardo de diseño. O el 3 tiene fuente y se corrige el documento, o sobra el 3. Gobierna el punto de detonación de §4, así que decide si el APHE revienta en el compartimento o fuera. El renombrado a APCBC-HE lo hace más urgente, porque el tipo ahora afirma que lleva explosivo.
* [ ] Fuente para los 28 mm del núcleo del PzGr. 40, hoy derivados de la masa y de un L/d supuesto (§2.1). El contraste de σ_RHA de §3.7 depende de ese número.
* [ ] Dar claves a data/sources.md y rellenar source_id en las tres tablas. Hoy es una lista plana de URL, así que ninguna cifra es trazable a su fuente. De paso, la columna source de data/parametros.csv usa la marca [D], que este documento ya no define.
* [ ] Columna de 60° para los dos proyectiles cinéticos. Vendrá de ensayos aliados, que son además los datos independientes que pide §8.
* [ ] Velocidad real del Gr. 38 Hl/C. Mientras tanto está a 450 m/s constante en velocity.csv, declarado en §9.
* [ ] Validar el 9-34 % de §3.6 contra una medida publicada. El caso más parecido es Experimental and analytical study of behind armor debris after perforation of a steel plate by an AP projectile (FME Transactions, Belgrado), pendiente de conseguir el texto.
* [ ] Confirmar el exponente de Recht-Ipson. §3.5 usa p = 2, el valor del artículo original para fallo por cizalla, pero conviene verificar que sigue siendo el recomendado para este rango de t/d.

Modelo y código

* [ ] Implementar el rebote de §3.3.
* [ ] Dar fuente a la masa de fragmento (5 g) y al cono (30°) de §3.6 con datos de behind-armour debris, y pasar a una distribución de tamaños de Mott.
* [ ] Dar fuente a sigma_fragmento (§3.7, §6), hoy 3,10 GPa provisional.
* [ ] [A] Explicar por qué el exponente de De Marre del PzGr. 40 baja de 0,98 a 0,74 con la distancia (§2.2.1).
* [ ] Recalibrar el Health de Engine y Transmission (§3.7.1). Los 300 y 150 kJ se fijaron con la ley lineal de σ_RHA, que ya no se usa.
* [ ] Capa compuesta con placas de orientación distinta. §3.2 suma los caminos, pero la tabla de §3.4 se consulta con un ángulo y disparo.py usa el de la primera placa. Caso real, ARM_Front_Track_Addon_Upper a 70° delante de ARM_Middle_Front_Plate.
* [ ] Decidir cuál de los dos eventos lleva la energía cuando un módulo detiene al proyectil, module_hit o stopped (§7.1).
* [ ] Aprobar los cuatro campos nuevos del esquema de §7.1: out_of_service, plug_mass_kg, spall_energy_J, shear_energy_J.
* [ ] Reglas de fuera de combate (§7). La agregación de §3.7.3 ya está en el código (estado_final de disparo.py); faltan las reglas que deciden con ella si el vehículo queda fuera de combate.
* [ ] Regla de detonación de APHE fuera del vehículo (§4).
* [ ] Datos de penetración independientes para romper la circularidad de §8.

Modelo 3D

* [ ] Modelar los rodillos de retorno y la suspensión. Las ruedas ya tienen material propio, Wheel (§9); lo que falta es fijar su resistance (ver Datos).
* [ ] Separar el Health de piernas y torso en el glb, o quitar ese argumento de §3.7.1.
* [ ] Dar fuente a los umbrales de Track (5 kJ la cinta, 20 kJ la motriz y 16 kJ la tensora), Ammo (150 J) y Fuel (5000 J) (§3.7.1).
* [ ] Cotas reales para las mallas de §7.2. Resueltas las del PzGr. 39 y el PzGr. 40 con los dibujos 13 C 1235 y 13 C 1236 (§2.1). Falta un dibujo acotado del Gr. 38 Hl/C: la malla actual sale de una figura comparativa sin cotas, escalada suponiendo que el ancho máximo es el calibre, así que su longitud de 343 mm es [S]. El núcleo del PzGr. 40 no tiene malla (§7.2), pero sus cotas en 13 C 1236, que lo dibuja en corte, siguen sirviendo para dar fuente a los 28 mm de §2.1.

Alcance

* [ ] Consultar con el tutor el criterio de incapacitación (§3.7.2), planteado como cuestión de alcance.
* [ ] [A] Segundo vehículo, opcional: la solicitud exige un mínimo de uno y el Pz IV lo cubre. Candidato, el T-44: casco sencillo y muy inclinado y torreta fundida redondeada, que ejercita justo la parte del modelo que justifica medir la geometría, y por eso vale más como demostración que un segundo vehículo de planchas planas. Va después de fragmentos, rebote, APHE y HEAT. Antes de modelarlo entero, dos comprobaciones: que existan planos acotados (si no, el T-34-85, mejor documentado) y un prototipo de la torreta facetada que pase validate_glb.py.
* [ ] [A] Ampliar los cañones del selector. El vehículo que dispara no se dibuja, solo se eligen cañón y proyectil, así que añadir el ZiS-S-53 de 85 mm es independiente del segundo vehículo: duplica la tabla de proyectiles con sus datos de penetración y velocidad.
