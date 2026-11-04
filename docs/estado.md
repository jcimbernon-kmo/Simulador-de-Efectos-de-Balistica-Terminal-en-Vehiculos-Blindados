# Estado y lista de verificación

Revisión del 04/11/2026. Generada comprobando el repositorio, los CSV con
`tools/ballistic_data.py`, el modelo con `tools/validate_glb.py` (281 objetos: 2 errores,
20 avisos) y el núcleo con `tools/disparo.py --selftest`.

Aviso sobre las fechas: la revisión anterior se tituló «29/10, 19:50», pero el fichero se guardó el
30/10 a las 21:57. Las marcas «(29/10)» de este documento pueden corresponder al 29 o al 30. A
partir de aquí la fecha se toma del reloj y no de memoria.

---

## 1. Bloqueantes

- [x] ~~Tres días sin versionar~~: commits del 30/10 y del 1/11 en la rama `reestructuracion`,
  subidos al remoto. `tools/disparo.py` está versionado; `tools/raycast_test.py` **no** (el
  `.gitignore` del disco no lo incluye), pero la regresión de §8 también la cubre
  `disparo.py --selftest`.
- [ ] **`main` en GitHub sigue en el 24/10.** Todo lo posterior está en `reestructuracion`. Hay que
  abrir el PR a `main` y fusionarlo: es lo primero que vería el tutor al abrir el repositorio.
- [ ] **Ninguna cifra del proyecto es trazable a su fuente.** `data/sources.md` son cuatro URL
  sueltas y ninguna de las cuatro tablas tiene columna `source_id`. Cuanto más se tarde, menos se
  va a acordar de dónde salió cada número. El 29/10 se añadieron dos valores más sin fuente
  (`core_diameter_mm` y el `resistance` de `Wheel`). **Ya hay dos fuentes primarias**: los dibujos
  13 C 1235 (7,5 cm PzGr. 39/42) y 13 C 1236 (7,5 cm PzGr. 40/42), en `models/`. Falta meterlos en
  `sources.md` con número y fecha.
- [ ] **Columna de 60° vacía en los dos proyectiles cinéticos** (10 celdas). Es el ángulo que más
  aparece en un blindaje inclinado, así que hoy todo lo que pase de 30° es extrapolación. Además
  esos datos, si se buscan en ensayos aliados, son los datos independientes que pide §8 y que
  rompen la circularidad de la validación. Un solo esfuerzo resuelve dos bloqueantes.
- [ ] **Las dos columnas de `Wheel` se contradicen.** `resistance` = 0,40 implica 100 mm de acero
  real en la rueda; `spall` = 0,13 está calculado sobre 20 mm. Con 0,40 el flanco suma 104 mm de
  RHA equivalente contra los 81 del frontal, así que el modelo dice que el Pz IV está mejor
  protegido por el costado que por el morro. Hay que fijar los milímetros de acero y que las dos
  columnas salgan de ahí (`modelo_balistico.md` §2.3).

## 2. Datos

### `shells.csv`
- [x] `core_mass_kg` del PzGr. 40 corregida a 0,85 kg.
- [x] Columna `cd` rellenada en los dos cinéticos (0,415 y 0,584). Queda como respaldo documentado.
- [x] `explosive_mass_g` del Gr. 38 Hl/C subida a 600 g.
- [x] **`core_diameter_mm` añadida** (29/10), con 28 mm en el APCR y vacía en el resto. El cargador
  deriva `penetrating_diameter_mm`, y `caliber_mm` se queda en 75 para los dos. Antes la masa de
  tapón del APCR salía 7,2 veces de más.
- [x] Tipo del PzGr. 39 renombrado a `APCBC-HE` (29/10). No afecta al código: lo único que mira
  `type` es la rama del APCR.
- [x] **`mass_kg` del PzGr. 40 se queda en 4,10 kg** (04/11). Sale de panzerworld.com (ficha del
  7,5 cm Pak 39 L/48, que comparte munición con el KwK 40 L/48), que cita a Jentz, Doyle y Badrocke,
  *New Vanguard 36*, y a Pawlas, *Waffen-Revue W 127*, sin decir cuál da el peso. El dibujo
  13 C 1236 (PzGr. 40/42) da 4,75 kg. No cambia ningún resultado: para el APCR el cálculo solo usa
  `core_mass_kg`. Falta anotarlo en `sources.md`. El del PzGr. 39 sí cuadra (6,8 kg en el dibujo 13 C 1235), aunque el explosivo
  del dibujo son 17 g y el CSV tiene 16,4.
- [ ] **Fuente para los 28 mm del núcleo.** El dibujo 13 C 1236 dibuja el núcleo en corte, con la
  ojiva de radio 45: medirlo ahí convierte el supuesto en dato. No está en la ficha del KwK 40, que da masa, velocidad
  y penetración pero no toca el núcleo. El valor está derivado de `core_mass_kg` con carburo de
  tungsteno a ~15 000 kg/m³, y la suposición declarada es la esbeltez (L/d ≈ 3,3).
- [ ] **`fuze_delay_ms` = 3 en el PzGr. 39 contradice a `modelo_balistico.md`**, que dice en §10 que
  la espoleta Bd.Z. 5103 no lleva retardo de diseño. El renombrado a `APCBC-HE` lo hace más urgente:
  el tipo ahora afirma que lleva explosivo, así que esa celda gobierna el punto de detonación de §4.
- [ ] Columna `source_id`.

### `penetration.csv`
- [x] 45 filas, `criterion`, `angle_from` y `thickness_basis` coherentes; identificadores cruzados
  con `shells.csv` correctos.
- [x] **PzGr. 40 a 2000 m y 30°: resuelto como «sin medir», no «no perfora»** (29/10). La tabla de
  la fuente se corta en 1500 m en la columna de 30°, mientras que a 0° sí llega a 2000 m.
- [ ] Columna de 60° en PzGr. 39 y PzGr. 40 (10 celdas). Ver §1.
- [ ] Columna `source_id`.

### `velocity.csv`
- [x] 18 filas: tres proyectiles × seis distancias, de 0 a 2000 m.
- [x] **Lo lee `ballistic_data.py`** (29/10): `velocity(pid, distancia)` e
  `impact_energy(pid, distancia)`, con validación de que la velocidad no suba con la distancia, de
  que cuadre con `muzzle_velocity_ms` y de que el `shell_id` exista. Desbloquea §3.4.1, §3.5 y §4.
- [x] La velocidad constante del Gr. 38 Hl/C está declarada en §9 y el cargador avisa de ella en
  cada ejecución, para que nadie la lea como una medición.
- [ ] Velocidad real del Gr. 38 Hl/C.
- [ ] Columna `source_id`.

### `materials.csv`
- [x] `resistance` en los diez materiales.
- [x] **Columna `spall` rellenada** (28/10). Siete de los diez valores son 0 o 1 por una razón
  física declarable; los discutibles son `Cast_Iron` (1,5), `Track` (0,3) y `Wheel` (0,13).
- [x] **Material `Wheel` añadido y asignado a las veinte ruedas** (29/10).
- [ ] Fijar su `resistance`. Ver §1.
- [x] ~~Fila `Engine` (0,1) sin usar~~ (31/10): borrada. Las tres piezas del motor van con
  `Cast_Iron` (0,3), que es con lo que cuadran los julios de §3.7.1.
- [ ] `Diesel` (0,1) sigue definido y no lo usa ningún objeto del `.glb`; el depósito va con
  `Gasoline`. O se usa o se borra.
- [ ] Columna `source`.
- **Nota de proceso, aprendida a golpes el 29/10: no editar estos CSV con Excel.** Se perdió la
  columna `spall` entera, Excel dejó el fichero bloqueado, y es lo que mete las comas decimales
  entrecomilladas (`"0,6"`). Diez filas no necesitan una hoja de cálculo.

## 3. Modelo 3D

`tools/validate_glb.py`: **2 errores, 20 avisos** sobre 281 objetos. Los dos errores están
aceptados.

### Errores — los dos aceptados
- [x] `MOD_Gunner_Legs` con `MOD_Gunner_Torso` (40,0 mm) y `MOD_Loader_Legs` con
  `MOD_Loader_Torso` (8,8 mm). **Aceptados**: con la agregación OR por tripulante de §3.7.3 el
  resultado no cambia. Declarado en §9.
- [x] ~~Mantelete: 47,01 y 46,01 mm de geometría contra 50 declarados~~ (29/10).
- [x] ~~Solape de los cartuchos 20 y 22 con las piernas del artillero~~ (29/10).
- [x] ~~Solape de `ARM_Back_Upper_Side_Addon_L`/`_R` con `ARM_Top_Plate_Rear` y
  `ARM_Upper_Back_Plate`~~ (29/10).
- [x] ~~Piezas cóncavas~~ (29/10). `MOD_Engine` (176,6 mm) partido en tres prismas convexos con los
  300 kJ repartidos por volumen, y `MOD_Barrel` (1,39 mm) regenerado con la tapa de popa plana, que
  además quitó un solape de 0,87 mm con la recámara. Hecho con `tools/crear_canon_motor.py`.
- [x] ~~`ARM_Front_Top_Plate` cóncava~~ (27/10) y ~~`ARM_Lower_Side_R_Plate`~~ (29/10).

### Avisos
- [ ] Tres caras alabeadas: `ARM_Upper_Back_Plate` (5,59 mm) y `ARM_Lower_Side_L_Plate` y su espejo
  (1,10 mm). La pieza es convexa salvo el pliegue, que solo afecta a los rayos que pasan por ese
  borde. **Declarados en §9 y no cambian ningún resultado**; se arreglan rehaciendo la pieza como
  extrusión de un perfil plano si algún día estorban.
- [x] ~~`ARM_Lower_Side_L_Plate.001`~~: ya se llama `ARM_Lower_Side_R_Plate`.
- [ ] Mantelete descentrado 100 mm respecto a X = 0, y diez cartuchos descentrados 362 mm.
  Comprobar si es intencionado.

### Tren de rodaje
- [x] Las dos orugas, 22 piezas convexas por lado, como módulo `Track` con 5 kJ.
- [x] Ruedas motrices: módulo `Track`, 20 kJ, 650 mm de diámetro, 250 mm de ancho.
- [x] Ruedas tensoras: módulo `Track`, 16 kJ, 520 mm de diámetro.
- [x] Ocho ruedas de rodadura por lado, blindaje de 150 mm, 370 mm de diámetro, ya con el nombre
  `ARM_Roadwheel_*` corregido y el material `Wheel` asignado.
- [x] Las ruedas se quedan macizas por simplificación (§9), con la corrección en el material.
- [ ] Faltan los rodillos de retorno y la suspensión.

### Módulos
- [ ] **Los diez objetos de tripulación tienen `Health` = 80 J**, piernas incluidas. Congelado hasta
  hablar con el tutor. Mientras tanto, el argumento de piernas y torso de §3.7.1 no está en el
  modelo.
- [ ] **`MOD_Fuel_Tank_1` tiene `Health` = 5000 J** (la revisión anterior decía 150 J por error).
  §3.7.1 dice que `Fuel` usa `Health` como umbral de ignición, no como reserva. Falta justificar de
  dónde sale el umbral.
- [x] Munición: 87 cartuchos, la dotación real del Pz IV H.
- [x] Transmisión en cinco cajas, motor en tres piezas (228,0 / 36,0 / 36,0 kJ), cañón en tubo
  (40 kJ) y recámara (25 kJ).
- [x] **Regla de agregación corregida** (29/10, §3.7.3): los módulos acumulativos repartidos en
  varias piezas por convexidad (motor, transmisión) se **suman**, no se agregan con OR. Con OR,
  agotar una pata de 36 kJ inutilizaría un motor de 300 kJ, y el resultado dependería de en cuántos
  trozos se cortó la malla.

### Mallas de proyectil (1/11)
- [x] Tres mallas visuales, una por fichero y con el `shell_id` como nombre:
  `models/PzGr39_75_L48.glb` (278 mm), `models/PzGr40_75_L48.glb` (256 mm) y
  `models/Gr38HlC_75_L48.glb` (343 mm). Las tres estancas y con las normales hacia fuera.
- [x] Convenio de ejes (§7.2): punta en (0, 0, 0), cuerpo hacia -Y, centradas en X y Z, metros.
- [x] Núcleo del PzGr. 40 sin malla propia, por simplificación (04/11): en la primera perforación la
  malla desaparece y el núcleo sigue como rayo (§7.2).
- [ ] Gr. 38 Hl/C: sale de una figura sin cotas, así que los 343 mm son [S]. No tiene bandas de
  forzamiento y el cuerpo es un cono de ⌀76,3 a ⌀71,5 en vez de un cilindro.
- [ ] El ⌀ 74,4 del PzGr. 39 está aplicado a las bandas y no al cuerpo (cuerpo a 70,7 mm). Aceptado
  como visual: no entra en el cálculo.
- [ ] Las mallas se llaman `Plane` / `Plane.001` por dentro.

## 4. Repositorio

### Reestructuración del 29/10
El repositorio remoto se vacía y se vuelve a subir con esta regla: **todo lo de `L1U/` menos
`CLAUDE.md`**, y en `tools/` solo lo que corre fuera de Blender (`validate_glb.py`,
`ballistic_data.py`, `revisar_vertices.py`, `disparo.py` y `raycast_test.py`). Implementado en
`.gitignore`.

Lo que sube: `data/` (5 ficheros), `docs/` (2), `models/` (el `.blend`, el `.glb` y las dos
imágenes de referencia), `README.md`, `tfg.md`, `.gitignore` y esas cinco herramientas. Algo más de
1 MB en total.

La regla se corrigió el 31/10: el `.gitignore` añade `!tools/disparo.py` (el núcleo de cálculo) y
`!tools/raycast_test.py` (el caso de regresión de §8), que la versión anterior dejaba fuera. Con eso
el repositorio ya contiene datos, modelo, núcleo y una prueba.

- [ ] **[A] Punto abierto: los diecinueve generadores de Blender se quedan fuera.**
  - Los diecinueve scripts de Blender son **80 KB** —un tercio de lo que pesa un solo `.blend`— y
    son el único sitio donde existen las medidas tomadas de los planos: las coordenadas en píxeles,
    `ESCALA_Y` = 0,010854 m/px y `Z_TOP` = 0,90629 viven en `crear_orugas.py` y en ningún otro
    lado. Son también lo que permite afirmar que el modelo se generó con scripts parametrizados y
    no a ojo, y lo que responde en una línea a «¿cómo construiste las orugas?».
  - Alternativa sin pérdida: mover los diecinueve a `tools/blender/` y dejar en `tools/` las cuatro
    herramientas más `raycast_test.py`. Mismo orden visual, y el criterio pasa a ser «qué dolería
    perder» en vez de «qué se ejecuta fuera de Blender».
  - **Incoherencia que hay ahora mismo**: `crear_canon_motor.py` y `crear_tripulacion_torreta.py`
    están en el índice de git desde antes de que existiera la regla, así que hay dos generadores
    versionados y diecisiete que no, sin ningún criterio que lo explique. O entran todos o salen
    esos dos del índice.

### Resuelto
- [x] `Claude outputs/` borrada.
- [x] `.gitignore` con `*.blend1`, `*.blend2` y `__pycache__/`.
- [x] `data/Documento sin título.md` → `data/sources.md`.
- [x] `Template` ya no se exporta.
- [x] `ARM_Back_Upper_Plate_L` y `_R` eliminadas; `ARM_Side_Front_L` y `_R` rehechas y simétricas.
- [x] `ARM__Roadwheel_*` renombradas sin el doble guión bajo (29/10).

### Pendiente
- [x] **`README.md` actualizado** (04/11): núcleo de cálculo, mallas de proyectil y comandos de
  `disparo.py`.
- [ ] `models/0359546535291c84baaa31c498396ee5.jpg` y `models/2615436_...webp`: son los planos de
  los que salieron las medidas, así que merecen nombres descriptivos, no borrarse.
- [ ] `tfg.md` sigue en la raíz; su sitio es `docs/`.
- [ ] `Pz IV H.blend` / `.glb`: sin espacios en el nombre.
- [ ] `src/` está vacía y git no versiona directorios vacíos. No pasa nada hasta noviembre.

## 5. Código del núcleo

**El disparo de extremo a extremo funciona desde el 29/10**, adelantado sobre el plan de
`tfg.md`, que lo situaba a mediados de noviembre.

- [x] **`tools/disparo.py`** — `.glb` + tablas → tramos (§3.1) → capas (§3.2) → perforación (§3.4) →
  energía (§3.4.2) → tapón (§3.5 y §3.6) → daño a módulos (§3.7) → agregación (§3.7.3) → línea
  temporal de §7.1 en JSON. Python puro, sin dependencias y sin motor.
- [x] **Una sola cuenta de estado: la energía, y la capacidad se deduce de ella** (§3.4.2).
  Lo forzó el primer disparo real: con las dos cuentas en paralelo el núcleo se quedaba sin energía
  en el tercer cartucho y seguía perforando con 56 mm de capacidad, saliendo por la plancha trasera
  con cero julios a los 2 932 ms. Con la cuenta única sale con 107 kJ y 16,7 mm a los 13,0 ms, e
  incapacita a conductor y artillero en vez de solo al conductor. La rama `doc` y el parámetro
  `--modelo` se han eliminado del código.
- [x] **`σ_RHA` y `k_absorcion` fuera del modelo del núcleo**: un parámetro libre menos en §6, y
  caen con ellos las dos limitaciones que §3.7 declaraba sobre ese anclaje. `sigma_rha()` se queda
  en el fichero solo como anclaje futuro de `sigma_fragmento`.
- [x] **`data/parametros.csv`** — `n_de_marre`, `contact_gap_mm` y `rho_acero`. Cumple el principio
  de §1 de que ninguna constante física viva dentro de un `.py`.
- [x] `tools/raycast_test.py` — caso de regresión verificado: 81,00 mm y 9,00° contra
  `ARM_Upper_Front_Plate`, y reejecutado desde `disparo.py --selftest`.
- [x] `tools/ballistic_data.py` — carga las cuatro tablas, valida referencias cruzadas, interpola
  penetración y velocidad, y da energía de impacto y reparto de astillado. `--selftest` pasa.
- [x] `tools/validate_glb.py` — validación completa del modelo, con `--selftest`.
- [x] `tools/revisar_vertices.py` — duplicados, caras degeneradas y aristas sueltas.
- [x] Generadores: torreta, anillo, mejillas, cúpula, lateral de torreta, orugas, munición,
  tripulación, módulos, freno de boca, cañón y motor.
- [x] `docs/modelo_balistico.md` — diseño del núcleo, con cada afirmación marcada como supuesta o
  abierta. Incluye el esquema JSON de la línea temporal (§7.1) y las reglas de reproducción (§7.2).
- [x] **`modelo_balistico.md` reformateado** (30/10): de 907 a 662 líneas y de 68 a 56 KB. Fuera las
  42 marcas `[D]`, el historial de cambios y las fechas por línea; §3.4.3 fundida en §3.4.2 y §10
  recortada a la mitad. Se conservan las 23 marcas `[S]`, las 12 `[A]` y todas las fórmulas que usa
  el código. Pendiente de repaso por Fata de §3 en adelante.
- [x] **σ_RHA recalculado con la velocidad real de impacto** (29/10): 3,10 GPa en vez de 3,21, con
  un contraste independiente que merece ir a la memoria: el PzGr. 40, con cinco veces menos energía
  penetrante y un núcleo de 28 mm, daba 2,80 GPa. Dos proyectiles muy distintos coincidían dentro
  de un 10 % sin que σ se hubiera ajustado a ninguno. **El núcleo ya no la usa**, pero el contraste
  sigue valiendo como argumento de que el anclaje de las tablas es consistente.

### Pruebas que pasan
- `tools/disparo.py --selftest`: la ida y vuelta con `penetration.csv` (19 celdas de los dos
  proyectiles cinéticos: perfora un 0,0001 % por debajo del espesor tabulado y se queda clavado un
  0,1 % por encima) y la regresión de §8 sobre el modelo real (81,00 mm y 9,00°).
- Invariante nuevo: ningún disparo puede acabar sin energía y con capacidad disponible. Es lo que
  fallaba antes, y la prueba está para detectar que alguien reintroduzca una segunda ley.
- Barrido de **1416 disparos** sobre el modelo real (30/10): ninguna incoherencia de balance. Salió
  de ahí el caso declarado en §9 de un rayo que recorre 245 mm por dentro de una chapa de 8 mm al
  entrar por el canto, que es geometría correcta y no un fallo del cálculo.
- `tools/ballistic_data.py --selftest` y `tools/validate_glb.py --selftest`.

### Pendiente en el núcleo
- [ ] **Rebote (§3.3) y fragmentos (§3.6).** Ninguno de los dos está, así que el único daño que se
  calcula hoy es el del núcleo. Las dos cosas necesitan `data/fragmentation.csv`
  (`n_fragments`, `cone_half_angle`, `ricochet_angle`), que no existe.
- [ ] **Fijar `sigma_fragmento`**, el único coeficiente de pérdida que queda tras unificar las
  cuentas, y que solo afecta a los fragmentos.
- [ ] **Recalibrar el `Health` de `Engine` (300 kJ) y `Transmission` (150 kJ)**: se fijaron con la
  ley lineal de `σ_RHA`, que ya no se usa. El «núcleo de 75 mm, 10 cm dentro del motor» de §3.7.1
  pasa de 425 kJ a unos 225 kJ, así que los dos valores están calibrados contra una ley muerta.
- [ ] **Doble conteo de energía en la línea temporal** (§7.1): un evento `module_hit` y el `stopped`
  que lo sigue llevan el mismo `energy_in_J`, así que quien lea el JSON sumando sin mirar el tipo de
  evento cuenta esa energía dos veces. Es un problema del esquema, no del cálculo: el núcleo cierra
  el balance en el `--selftest`.
- [ ] APHE (§4) y HEAT (§5) sin empezar. `disparo.py` avisa de que la carga y la espoleta del
  PzGr. 39 no se simulan.

### Siguiente hito
Los fragmentos, que es lo que falta para que el daño calculado se parezca al real. Requiere primero
`fragmentation.csv` y decidir la distribución de tamaños de Mott.

## 6. Proyecto

- [x] **Solicitud para el tutor entregada.** Sin tutor asignado hasta mediados de noviembre.
- [ ] Preparar las preguntas para la primera reunión. La principal es el criterio de incapacitación
  de 80 J (§3.7.2): la fuente localizada desaconseja usar umbrales de energía, así que es una
  cuestión de alcance y no un número que se pueda ajustar.
- [ ] Mirar la normativa de propuesta propia y su plazo.
- [ ] Decidir si la torreta tendrá rotación independiente.
- [ ] Definir las reglas de «fuera de combate» (§7).
- [ ] Fijar la distribución de tamaños de fragmento.
- [ ] Elegir motor (recomendado Unity). Abierto hasta hablar con el tutor; el núcleo en Python puro
  no depende de ello.
- [ ] Meter las fechas de los exámenes de enero en `tfg.md` para que el plan de noviembre a mayo las
  tenga en cuenta.
