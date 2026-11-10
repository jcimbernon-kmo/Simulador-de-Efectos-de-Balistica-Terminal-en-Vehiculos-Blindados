# Simulador de Efectos de Balística Terminal en Vehículos Blindados

Simulador 3D para PC que calcula un impacto de proyectil contra un vehículo blindado, perforación del blindaje, fragmentación, daño a los módulos internos y a la tripulación.

## Estructura

| Ruta | Contenido |
|---|---|
| `docs/modelo_balistico.md` | Índice del modelo de cálculo, con los principios y la tabla de secciones |
| `docs/modelo/` | El modelo por secciones: datos, rayo, perforación, fragmentos, daño, explosivos, parámetros, línea temporal, validación, limitaciones y pendientes. Es la referencia de lo que implementa el código |
| `docs/estado.md` | Qué funciona y qué falta |
| `data/` | Tablas de entrada: proyectiles, penetracion, velocidad, materiales y parametros |
| `models/` | Modelos 3D |
| `tools/` | Nucleo de calculo y herramientas de comprobacion |
| `src/` | Simulador con motor grafico. |

## Herramientas

Python 3, solo biblioteca estándar. Se ejecutan desde la raíz del repositorio.

```
python tools/disparo.py --selftest               #Autoprueba del nucleo de calculo
python tools/disparo.py                          #Disparo de prueba con resumen
python tools/disparo.py --shell PzGr40_75_L48 --distance 500 --out disparo.json

python tools/ballistic_data.py --selftest        #Autoprueba de la carga de datos
python tools/ballistic_data.py data/             #Lista lo cargado

python tools/validate_glb.py --selftest          #Autoprueba del validador
python tools/validate_glb.py "models/Pz IV H.glb" data
```

`disparo.py` basandose en `docs/modelo_balistico.md` tramos del rayo, capas, perforación, energía residual, daño a módulos y estado final. Su autoprueba comprueba que reproduce las tablas de penetración y el caso de regresión contra la placa frontal (81,00 mm a 9º).

`validate_glb.py` comprueba que cada pieza del modelo sea convexa y cerrada, sin solapes entre objetos y que cada material exista en `data/materials.csv`.

`tools/revisar_vertices.py` se ejecuta **dentro de Blender** (pestaña *Scripting* → pegar → *Run*). Solo informa de vértices duplicados y agujeros de malla; no modifica nada.
