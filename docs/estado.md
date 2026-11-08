# Estado del proyecto

## Hecho

- **Modelo 3D de vehiculo** (`models/Pz IV H.glb`): cada placa lleva espesor y material, y el interior tiene módulos de daño, tripulación, motor, transmisión, cañón, munición, depósito y tren de rodaje.
- **Mallas visuales de los tres proyectiles**: PzGr. 39, PzGr. 40 y Gr. 38 Hl/C, con la punta en el origen.
- **Tablas de datos** (`data/`): proyectiles, penetración por distancia y ángulo, velocidad por distancia, materiales y parámetros del modelo.
- **Núcleo de cálculo** (`tools/disparo.py`), en Python como implementación de referencia:
  - recorrido del rayo por la geometría real del modelo;
  - perforación capa a capa y energía residual;
  - tapón arrancado y fragmentos;
  - daño a los módulos y estado final del vehículo;
  - línea temporal del impacto en JSON, lista para reproducirla en el motor.
- **Validador del modelo** (`tools/validate_glb.py`): comprueba que las mallas estén cerradas y sean convexas, que no se solapen y que espesores y materiales cuadren con las tablas.
- **Autopruebas** de las tres herramientas (`--selftest`).

## Pendiente

- Motor grafico y simulador con reproducción en cámara lenta y vista de rayos X (`src/`) (Unity?).
- Rebotes del proyectil.
- Explosivo del PzGr. 39 (APHE).
- Carga hueca del Gr. 38 Hl/C (HEAT).
- Reglas de fuera de combate del vehiculo.
- Fuente documentada para cada dato de las tablas (`data/sources.md`).
- Validación contra datos independientes de las tablas de entrada.
- Explicar por qué el PzGr. 40 no sigue la ley de De Marre (su exponente baja de 0,98 a 0,74 con la distancia).
- Ajustar la resistencia de las ruedas de rodaje.

## Valores provisionales

Hasta que tenga fuentes:
- Fragmentos: 5 g cada uno, cono de 30° (una clave por tipo de proyectil; falta el valor del APCR) y resistencia de 3,10 GPa.
- Umbral de incapacitación de un tripulante, 80 J.
- Salud de los módulos motor, transmisión, cañón, orugas, munición, depósito.

## Por decidir

- Motor grafico.
- Retardo de la espoleta del PzGr. 39.
- La torreta gira.
