# Estado del proyecto

## Hecho

- **Modelo 3D del Pz.Kpfw. IV Ausf. H** (`models/Pz IV H.glb`): 281 objetos. Cada placa lleva espesor y material, y el interior tiene módulos de daño: tripulación, motor, transmisión, cañón, munición, depósito y tren de rodaje.
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

- Motor gráfico y simulador con reproducción en cámara lenta y vista de rayos X (`src/`).
- Rebote del proyectil.
- Explosivo del PzGr. 39 (APHE).
- Carga hueca del Gr. 38 Hl/C (HEAT).
- Reglas de «fuera de combate» del vehículo.
- Fuente documentada para cada dato de las tablas (`data/sources.md`).
- Validación contra datos independientes de las tablas de entrada.
- Ajustar la resistencia de las ruedas de rodaje.

## Decidido

- El espesor atravesado se mide en la geometría del modelo, no con espesor / cos(ángulo). Así se cubren esquinas, capas múltiples y orugas usadas como blindaje.
- La energía del proyectil se deriva de su capacidad de perforación restante, con una sola cuenta.
- En el APCR perfora el núcleo, que se desengancha en la primera perforación.
- Cálculo y visualización van separados: el motor reproduce la línea temporal que calcula el núcleo.
- No se representa el vehículo que dispara: se eligen cañón, proyectil y distancia.
- Mínimo un vehículo; un segundo, solo si queda margen.

## Valores provisionales

Se usan mientras no haya fuente, y se revisarán en el análisis de sensibilidad:

- Fragmentos: 5 g cada uno, cono de 30° y resistencia de 3,10 GPa.
- Diámetro del núcleo del PzGr. 40: 28 mm.
- Umbral de incapacitación de un tripulante: 80 J.
- Salud de los módulos (motor, transmisión, cañón, orugas, munición, depósito).

## Por decidir

- Motor gráfico (propuesta: Unity).
- Retardo de la espoleta del PzGr. 39.
- Si la torreta gira.
