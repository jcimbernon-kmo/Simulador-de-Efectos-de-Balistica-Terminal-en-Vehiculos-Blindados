# Estado y lista de verificación

Revisión del 29/10/2026, 15:15. Generada comprobando el repositorio, los CSV con
`tools/ballistic_data.py` y el modelo con `tools/validate_glb.py` (281 objetos: 2 errores,
20 avisos).

---

## 1. Bloqueantes

- [ ] **Tres días sin versionar, y el repositorio remoto está a punto de vaciarse.** El último
  commit es del 26/10 a las 23:31 («Added Cannon, cuppula, crew and extra armour to Pz IV»). Sin
  versionar: las orugas, las ruedas motriz y tensora, los cinco CSV, la columna `spall`, el cañón y
  el motor regenerados, `core_diameter_mm`, el cargador de velocidad, tres scripts nuevos y cuatro
  reescrituras de `modelo_balistico.md`. **Es el único punto de esta lista que no se puede
  rehacer.** Reestructurar el repositorio no exige dejar el trabajo sin commitear: se puede
  commitear en una rama ahora y reescribir la historia después.
- [ ] **Ninguna cifra del proyecto es trazable a su fuente.** `data/sources.md` son cuatro URL
  sueltas y ninguna de las cuatro tablas tiene columna `source_id`. Cuanto más se tarde, menos se
  va a acordar de dónde salió cada número. Hoy se han añadido dos valores más sin fuente
  (`core_diameter_mm` y el `resistance` de `Wheel`).
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
- [ ] **Fuente para los 28 mm del núcleo.** No está en la ficha del KwK 40, que da masa, velocidad
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
- [ ] `Engine` (0,1) y `Diesel` (0,1) están definidos y no los usa ningún objeto del `.glb`: el
  motor va con `Cast_Iron` (0,3) y el depósito con `Gasoline`. O se usan o se borran.
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
- [ ] `ARM_Lower_Side_L_Plate.001` conserva el nombre que le puso Blender al espejar. Es la pieza
  derecha; renombrar a `ARM_Lower_Side_R_Plate`. No afecta a la física, porque el código distingue
  por propiedades (§2.4), pero un `.001` en el entregable canta.
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
- [ ] **`MOD_Fuel_Tank_1` tiene `Health` = 150 J**, el mismo número que un cartucho. §3.7.1 dice
  que `Fuel` usa `Health` como umbral de ignición, no como reserva; con ese valor, cualquier
  esquirla incendia el depósito. Revisar o declarar.
- [x] Munición: 87 cartuchos, la dotación real del Pz IV H.
- [x] Transmisión en cinco cajas, motor en tres piezas (228,0 / 36,0 / 36,0 kJ), cañón en tubo
  (40 kJ) y recámara (25 kJ).
- [x] **Regla de agregación corregida** (29/10, §3.7.3): los módulos acumulativos repartidos en
  varias piezas por convexidad (motor, transmisión) se **suman**, no se agregan con OR. Con OR,
  agotar una pata de 36 kJ inutilizaría un motor de 300 kJ, y el resultado dependería de en cuántos
  trozos se cortó la malla.

## 4. Repositorio

### Reestructuración del 29/10
El repositorio remoto se vacía y se vuelve a subir con esta regla: **todo lo de `L1U/` menos
`CLAUDE.md`**, y en `tools/` solo las tres herramientas que corren fuera de Blender
(`validate_glb.py`, `ballistic_data.py`, `revisar_vertices.py`). Implementado en `.gitignore`.

Lo que sube: `data/` (5 ficheros), `docs/` (2), `models/` (el `.blend`, el `.glb` y las dos
imágenes de referencia), `README.md`, `tfg.md`, `.gitignore` y las tres herramientas. Algo más de
1 MB en total.

- [ ] **[A] Punto abierto: la regla deja fuera dos cosas que probablemente deberían subir.**
  - `tools/raycast_test.py` **no es un generador**: es el caso de regresión de §8, verificado el
    22/10 (81,00 mm y 9,00° contra `ARM_Upper_Front_Plate`), y es contra lo que se validará el
    núcleo al portarlo al motor. Dejándolo fuera, el repositorio no tiene ninguna prueba.
  - Los diecinueve scripts de Blender son **80 KB** —un tercio de lo que pesa un solo `.blend`— y
    son el único sitio donde existen las medidas tomadas de los planos: las coordenadas en píxeles,
    `ESCALA_Y` = 0,010854 m/px y `Z_TOP` = 0,90629 viven en `crear_orugas.py` y en ningún otro
    lado. Son también lo que permite afirmar que el modelo se generó con scripts parametrizados y
    no a ojo, y lo que responde en una línea a «¿cómo construiste las orugas?».
  - Alternativa sin pérdida: mover los diecinueve a `tools/blender/` y dejar en `tools/` las tres
    herramientas más `raycast_test.py`. Mismo orden visual, y el criterio pasa a ser «qué dolería
    perder» en vez de «qué se ejecuta fuera de Blender».

### Resuelto
- [x] `Claude outputs/` borrada.
- [x] `.gitignore` con `*.blend1`, `*.blend2` y `__pycache__/`.
- [x] `data/Documento sin título.md` → `data/sources.md`.
- [x] `Template` ya no se exporta.
- [x] `ARM_Back_Upper_Plate_L` y `_R` eliminadas; `ARM_Side_Front_L` y `_R` rehechas y simétricas.
- [x] `ARM__Roadwheel_*` renombradas sin el doble guión bajo (29/10).

### Pendiente
- [ ] `README.md` tiene 72 bytes y es solo el título entrecomillado. Debería decir qué es el
  proyecto, cómo se ejecutan las tres herramientas y en qué estado está. **Con la solicitud al
  tutor ya entregada, es lo primero que va a abrir cuando os reunáis**, y con el repositorio recién
  reestructurado es el momento de escribirlo.
- [ ] `tools/spall.py` y `ballistic_data.spall_fraction()` implementan la misma fórmula de §3.5 en
  dos sitios. Borrar el primero, que era un borrador. Contradice el principio de §1 del modelo.
- [ ] `tools/crear_issues.sh` y `tools/create_issues.py` siguen siendo dos versiones de lo mismo.
- [ ] `models/0359546535291c84baaa31c498396ee5.jpg` y `models/2615436_...webp`: son los planos de
  los que salieron las medidas, así que merecen nombres descriptivos, no borrarse.
- [ ] `tfg.md` sigue en la raíz; su sitio es `docs/`.
- [ ] `Pz IV H.blend` / `.glb`: sin espacios en el nombre.
- [ ] `src/` está vacía y git no versiona directorios vacíos. No pasa nada hasta noviembre.

## 5. Código del núcleo

Nada empezado, y sigue siendo correcto: estaba previsto para mediados de noviembre. Lo que hay son
las herramientas de apoyo y los datos, que ya están listos.

- [x] `tools/raycast_test.py` — caso de regresión verificado: 81,00 mm y 9,00° contra
  `ARM_Upper_Front_Plate`.
- [x] `tools/ballistic_data.py` — carga las cuatro tablas, valida referencias cruzadas, interpola
  penetración y velocidad, y da energía de impacto y reparto de astillado. `--selftest` pasa.
- [x] `tools/validate_glb.py` — validación completa del modelo, con `--selftest`.
- [x] `tools/revisar_vertices.py` — duplicados, caras degeneradas y aristas sueltas.
- [x] Generadores: torreta, anillo, mejillas, cúpula, lateral de torreta, orugas, munición,
  tripulación, módulos, freno de boca, cañón y motor.
- [x] `docs/modelo_balistico.md` — diseño del núcleo, con cada afirmación marcada como decidida,
  supuesta o abierta. Incluye ya el esquema JSON de la línea temporal (§7.1) y las reglas de
  reproducción (§7.2).
- [x] **σ_RHA recalculado con la velocidad real de impacto** (29/10): 3,10 GPa en vez de 3,21. Y un
  contraste independiente que merece ir a la memoria: el PzGr. 40, con cinco veces menos energía
  penetrante y un núcleo de 28 mm, da 2,80 GPa. Dos proyectiles muy distintos coinciden dentro de un
  10 % sin que σ se haya ajustado a ninguno.

### Siguiente hito
El disparo completo de extremo a extremo, en Python puro y sin gráficos, como marca `tfg.md`:
rayo → capas → cadena de capacidad → energía residual → tapón → fragmentos → daño a módulos → JSON
de §7.1. Todas las piezas están decididas y los datos están cargados.

## 6. Proyecto

- [x] **Solicitud para el tutor entregada.**
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
