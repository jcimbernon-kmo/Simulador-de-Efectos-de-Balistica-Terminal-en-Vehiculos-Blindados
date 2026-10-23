# Estado y lista de verificación

Revisión del 22/10/2026, 20:30. Generada comprobando el repositorio, los CSV con `tools/ballistic_data.py` y el modelo con `tools/validate_glb.py`.

---

## 1. Bloqueantes

- [ ] **`penetration.csv`: la columna `thickness_basis` contiene números en vez de la palabra `nominal`.** Se ha pegado ahí el cálculo de línea de visión de la hoja. Hay que borrar los números y poner `nominal` en las 45 filas. El valor LOS lo calcula `ballistic_data.los()`; no va en el fichero.
- [ ] **Dos de esos números estaban mal**: 43,70 y 34,64 en las filas de 100 m y 500 m a 30°, donde lo correcto era 122,40 y 110,85. Las de 1000 m y 1500 m sí estaban bien, lo que indica que el error de radianes se corrigió a media columna.
- [ ] **Falta `striking_velocity_ms` en `penetration.csv`.** Sin la velocidad de impacto a cada distancia no se puede evaluar la perforación de una segunda capa (mamparo interno, blindaje espaciado, orugas), porque la tabla está indexada por distancia de tiro y el proyectil llega al mamparo con velocidad residual.
- [ ] **Nada se ha subido a Git desde el 21/10 a las 21:41.** Todo el trabajo del 22 está sin versionar: documento de modelo balístico, los tres CSV, las cuatro herramientas y el modelo. Además deja un hueco de un día en el historial, que es parte de la prueba de trabajo del TFG.

## 2. Datos

### `projectiles.csv`
- [ ] `fuze_delay_ms` vacío en los dos proyectiles con explosivo (PzGr. 39 y Gr. 38 Hl/C). Necesario para el retardo de espoleta del APHE.
- [ ] `core_mass_kg` ausente en el PzGr. 40 (APCR). Sin ella, la razón de masas del spall usa los 4,1 kg del proyectil entero en vez del núcleo, y la fracción de metralla sale demasiado baja.
- [ ] Verificar `explosive_mass_g = 60` del Gr. 38 Hl/C contra la fuente: para una carga hueca de 75 mm parece bajo, y es el dato que gobierna el chorro.
- [ ] Columna `source` o `source_id` por fila.

### `penetration.csv`
- [ ] Columna de 60° vacía en PzGr. 39 y PzGr. 40 (10 filas). Es el ángulo más relevante para blindaje inclinado; mientras falte, todo lo que pase de 30° es extrapolación.
- [ ] PzGr. 40 a 2000 m y 30°: sin dato (la fuente ponía «–»). Confirmar que significa «no perfora» y no «sin medir».
- [x] `criterion = complete` en todas las filas.
- [x] `angle_from = normal` en todas las filas.
- [x] Identificadores de proyectil coherentes entre los dos ficheros.

### `materials.csv`
- [ ] `spall` vacío en los seis materiales. Es el único parámetro libre de la fórmula de fragmentación.
- [ ] Columna `source`.
- [ ] Comprobar que las mayúsculas (`RHA`, `Steel`, `Track`, `Flesh`, `Cast_Iron`, `Ammo`) coinciden exactamente con lo que se escriba en `Armour_Material` en Blender.
- [x] `resistance` rellenada en los seis.

## 3. Modelo 3D

Según `tools/validate_glb.py`: 7 errores, 6 avisos.

- [ ] **`Template` sigue exportándose** con `Thickness_mm = 30` y `Armour_Material = RHA`. Se lee como una placa de 2 m de espesor y 8 millones de cm³ en el origen.
- [ ] **`ARM_Back_Upper_Plate_L` y `_R` miden 275 mm y declaran 20.** Son sólidos macizos (113 litros, 887 kg de acero cada uno), no placas. Mientras no se rehagan, excluirlas del export.
- [ ] **`ARM_Side_Front_L` mide 11,41 mm y `ARM_Side_Front_R` 28,97, ambas declaran 30.** Además no son espejo una de otra. Regresión: en el `.glb` de las 15:03 las dos medían 30,00.
- [ ] **Dos solapes** entre los laterales del casco y las placas de 8 mm (1,0 mm y 0,1 mm). En la zona solapada el camino se cuenta dos veces.
- [ ] **Seis piezas no convexas**: `ARM_Back_Upper_Plate_R`, `ARM_Front_Top_Plate`, `ARM_Lower_Side_L_Plate`, `ARM_Lower_Side_R_Plate`, `ARM_Side_Front_L`, `ARM_Side_Front_R`. El cálculo toma la primera intersección como entrada y la última como salida, así que en una pieza cóncava mediría de más. Partirlas en trozos convexos.
- [ ] `MOD_driver` tiene `Health = 100`. Ahora que la unidad es el julio, confirmar que ese 100 sale de un criterio de incapacitación citable.
- [ ] Mamparo de separación tripulación/motor: 10 mm de RHA, rectángulo X = ±0,897, Z de 1,13959 a 2,24602, Y por decidir.
- [ ] Resto de módulos internos (motor, transmisión, munición, resto de tripulantes).
- [x] Chasis cerrado, 19 placas con espesor correcto, materiales válidos, mallas cerradas y normales hacia fuera.

## 4. Repositorio

### Sobra
- [ ] `Claude outputs/validate_glb.py` — copia antigua y duplicada de `tools/validate_glb.py`. Borrar la carpeta entera.
- [ ] `tools/crear_issues.sh` y `tools/create_issues.py` — dos versiones de lo mismo. Quedarse con una.
- [ ] `models/Pz IV H.blend1` — copia de seguridad de Blender, no debe versionarse.

### Falta
- [ ] `.gitignore` con `*.blend1`, `*.blend2`, `__pycache__/`.
- [ ] `README.md` tiene 72 bytes. Debería decir qué es el proyecto, cómo se ejecutan las herramientas y en qué estado está.

### Renombrar
- [ ] `data/Documento sin título.md` → algo como `docs/fuentes_tablas.md`. Es el registro de las tablas originales y de las de precisión; conviene conservarlo, pero no en `data/` ni con ese nombre.
- [ ] `models/0359546535291c84baaa31c498396ee5.jpg` → nombre descriptivo.
- [ ] `Pz IV H.blend` / `.glb` → sin espacios (`Pz_IV_H`).
- [ ] `tfg.md` está en la raíz; su sitio es `docs/`.

## 5. Código del núcleo

Nada empezado, y es correcto: estaba previsto para mediados de noviembre. Lo que sí existe y funciona:

- [x] `tools/raycast_test.py` — carga el `.glb`, lanza un rayo, mide camino y ángulo. Caso de regresión verificado: 81,00 mm y 9,00° contra `ARM_Upper_Front_Plate`.
- [x] `tools/ballistic_data.py` — carga los tres CSV, valida referencias cruzadas, interpola en distancia y ángulo, convierte a línea de visión y calcula `spall_fraction`.
- [x] `tools/validate_glb.py` — validación completa del modelo.
- [x] `docs/modelo_balistico.md` — diseño del núcleo, con cada afirmación marcada como decidida, supuesta o abierta.

## 6. Proyecto

- [ ] **Escribir la solicitud para el tutor.** Sigue sin hacerse. No hay tutor hasta mediados de noviembre, así que el documento tiene que estar listo para entregarlo el primer día.
- [ ] Mirar la normativa de propuesta propia y su plazo.
- [ ] Decidir si la torreta tendrá rotación independiente.
- [ ] Definir las reglas de «fuera de combate».
- [ ] Fijar la distribución de tamaños de fragmento.
