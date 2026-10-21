---
name: tfg
description: "TFG de Fata — simulador de perforación de blindaje de vehículos de combate de la WW2. Decisiones tomadas, arquitectura, convenciones de modelado y pendientes. Actualizado 2026-10-21."
---

# TFG — Simulador de perforación de blindaje (WW2)

> Cómo leer este archivo: las secciones 1-4 son **decisiones y datos del usuario**. La 5 son **recomendaciones de Claude** aún sin confirmar. Si algo cambia, se edita aquí y se anota la fecha.

## 1. Datos generales

- **Proyecto elegido:** propuesta propia, simulador de perforación de blindaje. Las demás ideas quedan descartadas.
- **18 créditos.** ≈450 h si se cuenta a 25 h/crédito (estimación de Claude).
- **Fecha límite: 17 de mayo de 2027.** El desarrollo de software no empieza hasta mediados de noviembre de 2026; hasta entonces, modelado 3D.
- Exclusiones generales del usuario: nada de desarrollo para móviles, VR o desarrollo de juegos; nada con asignaturas DAD I / DAD II.
- Punto de partida: sin experiencia previa en modelado 3D ni en desarrollo de juegos. Aprende Blender sobre la marcha.
- Material que ya tiene: planos de tanques, tablas de penetración de varios proyectiles, disposición de tripulación y módulos internos.

## 2. Qué es el simulador

Programa para PC en 3D que simula el impacto de proyectiles contra vehículos blindados de la Segunda Guerra Mundial.

El vehículo es un **modelo estático**: no se mueve, no hay IA. El usuario lo gira con el ratón para cambiar el ángulo de ataque y apunta a una sección concreta; el ratón marca el punto de disparo. Elige proyectil y distancia de impacto.

Al disparar, el programa calcula el evento completo y lo reproduce en **cámara lenta**: se ve el proyectil atravesar el blindaje, fragmentarse, dañar módulos internos y, si lleva explosivo, detonar dentro. Una **vista de rayos X** muestra el interior y el daño causado, e indica si la tripulación ha sido eliminada.

Se presenta como herramienta de análisis y divulgación histórica, no como un juego.

## 3. Decisiones tomadas

### 3.1 Munición

- **Cinética:** AP, APCBC, APCR (macizos) y APHE (con explosivo).
- **Química:** HEAT.
- Datos por proyectil: velocidad de salida, masa, calibre, si lleva explosivo y masa explosiva. El usuario elige la distancia de impacto, que para la munición cinética determina la velocidad de llegada.

### 3.2 Vehículo

- Exterior medianamente detallado, modelado a mano.
- Interior con **módulos simplificados**: motor, transmisión, munición y tripulación, cada uno con su vitalidad.
- Blindaje dividido en placas, cada una con su espesor y su material.
- Materiales iniciales: **RHA**, **Steel**, **Track**. Pendiente definir sus coeficientes y a qué corresponde exactamente cada uno.

### 3.3 Cálculo: por geometría, no por propiedad *(decidido 2026-10-21)*

El espesor atravesado se obtiene **midiendo la distancia real que el rayo recorre dentro de cada volumen** (intersección de entrada menos intersección de salida), no aplicando `Thickness_mm / cos θ`.

Motivo: así salen gratis la oblicuidad, las esquinas convexas (que son realmente más gruesas), las orugas usadas como blindaje extra y el blindaje espaciado. Y es menos código, porque la intersección de entrada y salida ya hace falta para saber por dónde sale el proyectil al interior.

Consecuencias:

- **La malla pasa a ser la fuente de verdad.** Un hueco hace atravesar menos acero del real; un solape, de más. La geometría tiene que estar limpia, y el script de validación gana importancia.
- Uso de las tablas: si dan milímetros **nominales** perforados a ángulo θ y distancia d, se convierten a línea de visión con `LOS(θ,d) = tabla(θ,d) / cos θ` y se compara contra la longitud de camino medida. En una placa plana el resultado es idéntico al de la tabla; en esquinas y capas, generaliza.
  - **Pendiente de verificar:** si las tablas dan espesor nominal o en línea de visión. Si fuera LOS, la división sobra.
- El **ángulo sigue siendo necesario aparte**: el rebote y el efecto de inclinación dependen del ángulo, no de la distancia recorrida.
- **Varias capas consumen penetración progresivamente** (orugas, faldones, blindaje espaciado), con velocidad residual entre capa y capa.
- `Thickness_mm` se conserva: valida que la geometría coincide, sirve para la relación espesor/calibre en la fragmentación, y de respaldo.

### 3.4 Penetración, rebote y resultados

- La penetración sale de **tablas históricas** (proyectil, mm atravesados, ángulo, distancia, tipo de blindaje). Criterio de las tablas: **perforación completa**.
- Cada impacto termina en uno de tres resultados: **perforación**, **retenido/roto** o **rebote**.
- **Si no perfora, no genera fragmentación** (simplificación aceptada).
- Daño a módulos según la energía con la que entra, el ángulo y la masa.
- **Fragmentación** del propio proyectil y de la placa; una placa fina fragmenta distinto que una gruesa.
- **APHE:** espoleta con retardo; el proyectil recorre una distancia dentro del vehículo antes de detonar. Onda expansiva **a 360°** en la primera versión; se mejorará si sobra tiempo.
- **Sin deformación real** del blindaje: basta una marca del agujero sobre la placa.

### 3.5 Modelado

- A mano, en Blender. Primer vehículo: **Pz IV H**.
- Un archivo por vehículo, con muchos objetos dentro (nunca unir placas con Ctrl+J: se perderían las propiedades).
- Propiedades por placa, en el **objeto** (no en la malla ni en el material), con estos nombres exactos: `Thickness_mm` (decimal) y `Armour_Material` (texto).
- Escena en metros, escala 1:1, escala aplicada (Ctrl+A) en cada objeto.
- Normales hacia fuera.
- **El morro apunta a −Y.**
- Formato de intercambio: **`.glb`**. Es lo que lee el simulador y lo que se revisa.

## 4. Estado del modelado (2026-10-21)

Archivo `Pz IV H.blend` / `Pz IV H.glb` en `C:\Users\Juan Carlos\Documents\L1U`.

Tres placas frontales, las tres de RHA y 1825 mm de ancho en su base:

| Placa | Espesor | Inclinación vs vertical | Notas |
|---|---|---|---|
| `Lower_Front_Plate` | 80 mm | 14° | |
| `Middle_Front_Plate` | 20 mm | 72° | plancha casi horizontal del morro |
| `Upper_Front_Plate` | 80 mm | 10° | trapecio isósceles: 1825 mm abajo, 1855 mm arriba |

Verificado: espesores geométricos coinciden con las propiedades (79,99 / 19,98 / 79,98 mm), normales hacia fuera, superficie exterior cerrada sin huecos, y 2 vértices compartidos en cada junta.

**Pendiente:** cerrar las cuñas interiores de las dos juntas.

## 5. Recomendaciones de Claude (pendientes de confirmar)

### 5.1 Arquitectura

- Separar **cálculo** y **reproducción**: al disparar, una función calcula el evento entero y devuelve una **línea temporal de eventos** (impacto, perforación/rebote, fragmentos, impactos en módulos, detonación, daño). El render la reproduce a la velocidad que se quiera. Evita atravesar placas sin detectarlas, permite calibrar con las tablas y probar sin gráficos.
- No usar un motor de físicas general para la perforación.
- **Motor recomendado: Unity (C#)**, con el núcleo de simulación en C# puro, independiente del motor, y pruebas automáticas (NUnit). Alternativas: Godot, three.js. Unreal descartado. Cambiar si el tutor domina otro.
- Intersección rayo-triángulo implementada en el núcleo (≈20 líneas), no dependiente de los colliders del motor.

### 5.2 Modelo balístico

- **Rebote:** reflejar la velocidad sobre la normal, con la componente normal casi anulada y pérdida en la tangencial; máximo 1-2 rebotes; el proyectil rebotado puede golpear otra placa. Umbral de ángulo **por tipo de proyectil** y relación calibre/grosor; nunca un umbral global. Variación aleatoria pequeña con semilla fija.
- Fijar una **convención única de ángulo** (desde la normal o desde la superficie); las fuentes difieren.
- **Velocidad residual:** derivar un límite balístico por placa desde la tabla (tipo De Marre, exponente ≈0,7; verificar) y aplicar Recht-Ipson. Es el punto de calibración.
- **Fragmentos:** de la placa (astillado) y del proyectil, generados al azar en un cono con la energía residual repartida. Explosivo con Gurney (velocidad) y Mott (tamaños). Onda expansiva con distancia escalada de Hopkinson-Cranz, esfera de rayos con oclusión por módulos y factor de confinamiento. Fragmento = rayo fino; daño = energía frente a umbral restada a la vida. HEAT: chorro como rayo estrecho, penetración hidrodinámica.
- **Verificar todas las fórmulas en las fuentes:** Rosenberg y Dekel, *Terminal Ballistics*; Zukas, *Impact Dynamics*; Bird y Livingston, *WWII Ballistics: Armor and Gunnery*.
- **Proyectil con volumen:** nivel 1 recomendado, un haz de rayos (central + 6-8 en círculo de radio calibre/2). Detecta impactos en bordes y juntas y permite dañar varios módulos. Los fragmentos y el chorro HEAT siguen siendo rayos finos.
- **Orugas como blindaje:** una oruga no es un bloque macizo; el coeficiente de `Track` debe quedar bastante por debajo de 1 y hay que justificar de dónde sale. Contra HEAT el blindaje espaciado actúa por **distancia de detonación**, no por material: eso no lo captura la longitud de camino y va en el modelo de carga hueca.

### 5.3 Límites a declarar en la memoria

- Un APHE que no perfora puede romperse o detonar en superficie.
- Una placa gruesa golpeada cerca de su límite puede astillar por dentro sin ser perforada.
- El HEAT detona al contacto.
- Caras de canto: un rayo que entra por el canto de una placa recibe un ángulo y un espesor no representativos. Tratar aparte en el código las caras cuya normal es casi perpendicular a la normal exterior de su placa.

### 5.4 Convenciones de modelado

- Colecciones en Blender: `VISUAL`, `ARMOR` (una placa = un objeto), `MODULES`.
- **Prefijos en el nombre del objeto**, porque las colecciones pueden perderse al exportar a `.glb`: `ARM_`, `MOD_`, `VIS_`. Ejemplo: `ARM_hull_front_lower`.
- El vehículo lo identifica el archivo, no el nombre de cada placa.
- Punto de origen común para todo el vehículo (p. ej. el centro del suelo del casco).
- **Agrupar las placas por espesor** al construir: cáscara continua de todo lo de 80 mm → *Solidify* a 0,08 → separar; luego la de 20 mm. Las juntas dentro de cada grupo salen ingleteadas automáticamente; solo hay que tocar a mano las juntas entre espesores distintos.
- Orden de trabajo: casco → torreta → cañón y mantelete → ruedas y orugas al final. Primero el modelo de daño, la estética después.

### 5.5 Alcance y plan

- Presupuesto estimado: ~450 h − ~100 de memoria − ~50 de aprendizaje ≈ **300 h de desarrollo**. Modelado: ~60-80 h el primer vehículo, ~40-50 el segundo.
- **2 vehículos completos** de blindaje contrastado (uno con placas inclinadas tipo T-34, otro más cuadrado como el Pz IV). Un tercero solo si hay margen.
- **~8 variantes de proyectil** en 2-3 calibres, al menos una por tipo. Son 3 mecánicas (cinético macizo, cinético con explosivo, carga hueca); el resto son datos.
- Calendario orientativo (mediados de noviembre a mayo): 1-3 prototipo; 4-8 vehículo 1 con penetración, rebote y rayos X; 9-13 fragmentos, daño a módulos y APHE; 14-17 HEAT y vehículo 2; 18-21 validación, interfaz y pulido; 22-26 memoria y margen.
- **Validación como valor académico:** pruebas automáticas que comparen la penetración simulada con los resultados de las tablas.

## 6. Pendientes y preguntas abiertas

- [ ] Confirmar con el tutor que el simulador se acepta como propuesta propia, y revisar el plazo de presentación.
- [ ] Elegir motor (recomendado Unity).
- [ ] Verificar si las tablas dan espesor nominal o en línea de visión.
- [ ] Verificar la convención de ángulo de las tablas (desde la normal o desde la superficie).
- [ ] Comprobar si las tablas incluyen datos de rebote o solo llegan hasta cierto ángulo; lo que haya por encima es decisión propia y debe documentarse.
- [ ] Definir los coeficientes de RHA, Steel y Track, con su fuente.
- [ ] Cerrar las cuñas interiores de las dos juntas frontales del Pz IV H.
- [ ] Renombrar las placas con los prefijos `ARM_`.
- [ ] Escribir el script de validación de `.glb` (propiedades, normales, nombres, espesor, huecos y solapes) y, más adelante, un script de Blender que ingletee las juntas automáticamente.
- [ ] Comprobar en los planos el ancho de la superestructura: 1825 mm encaja con la cuba del casco, pero el Pz IV H mide unos 2880 mm de ancho total y la placa del conductor pertenece a la superestructura, que vuela sobre las orugas.
- [ ] Ir anotando las horas por placa para contrastar la estimación de modelado.
