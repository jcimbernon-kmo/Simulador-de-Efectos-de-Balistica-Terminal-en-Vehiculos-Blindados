# Estado del proyecto

## Hecho

- **Modelo 3D de vehículo** (`models/Pz IV H.glb`): cada placa lleva espesor y material, y el interior tiene módulos de daño, tripulación, motor, transmisión, cañón, munición, depósito y tren de rodaje.
- **Mallas visuales de los tres proyectiles**: PzGr. 39, PzGr. 40 y Gr. 38 Hl/C, con la punta en el origen.
- **Tablas de datos** (`data/`): proyectiles, penetración por distancia y ángulo, velocidad por distancia, materiales y parámetros del modelo.
- **Núcleo de cálculo** (`tools/disparo.py`), en Python como implementación de referencia:
  - recorrido del rayo por la geometría real del modelo;
  - perforación capa a capa y energía residual;
  - tapón arrancado y fragmentos;
  - daño a los módulos y estado final del vehículo;
  - línea temporal del impacto en JSON, lista para reproducirla en el motor;
  - exponente de De Marre medido en las tablas de cada proyectil, por tramo de distancia.
- **Autopruebas** de las tres herramientas (`--selftest`).

## Pendiente

- Motor grafico y simulador (Unity?).
- Rebotes del proyectil (deg).
- Carga del Gr. 38 Hl/C (HEAT).
- Reglas de fuera de combate del vehículo.
- Fuente documentadas para las tablas.
- Validación contra datos independientes de las tablas de entrada.
- PzGr. 40 no sigue la ley de De Marre.
- Ajustar la resistencia de las ruedas de rodaje y tensoras.

## Valores provisionales

- Fragmentos: 5 g cada uno, cono de 30° y resistencia de 3,10 GPa.
- Umbral de incapacitación de un tripulante, 80 J.
- Salud de los módulos motor, transmisión, cañón, orugas, munición, depósito.

## Por decidir

- Motor grafico.
- Retardo de la espoleta del PzGr. 39.
- Giro de torreta.
- `sigma_fragmento`: dejarlo fijo en `parametros.csv` o calcularlo de las tablas, como el exponente de De Marre.
- Si el `spall` del acero de las faldillas y el cañón debe ser distinto del RHA (ahora los dos 1,0, sin fuente).