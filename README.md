# Simulador de Efectos de Balística Terminal en Vehículos Blindados

Trabajo de Fin de Grado. Simulador 3D para PC que calcula un impacto de proyectil contra un vehículo blindado de la Segunda Guerra Mundial y lo reproduce en cámara lenta: perforación del blindaje, fragmentación, daño a los módulos internos y a la tripulación. El vehículo es estático; el usuario elige proyectil, distancia y punto de impacto.

Primer vehículo: Pz.Kpfw. IV Ausf. H. Proyectiles: PzGr. 39 (APCBC-HE), PzGr. 40 (APCR) y Gr. 38 Hl/C (HEAT), del 7,5 cm KwK 40 L/48.

## Estado

**El cálculo de un disparo funciona de extremo a extremo**, sin motor gráfico: `tools/disparo.py` lanza un rayo contra el modelo 3D, calcula perforación, energía residual, fragmentos y daño a los módulos, y devuelve la línea temporal del impacto en JSON. Los fragmentos del tapón están en una versión provisional; falta el rebote, el explosivo y la carga hueca.

El motor gráfico está sin elegir (recomendado Unity) y `src/` sigue vacío. El estado detallado, con los problemas abiertos, está en [`docs/estado.md`](docs/estado.md).

## Estructura

| Ruta | Contenido |
|---|---|
| `docs/modelo_balistico.md` | Modelo de cálculo: trayectoria del rayo, penetración, energía, daño a módulos y formato de la línea temporal. Es la referencia de lo que implementa el código. |
| `docs/estado.md` | Qué funciona, qué falta y qué se ha decidido. |
| `data/` | Tablas de entrada: proyectiles, penetración, velocidad, materiales y parámetros (`*.csv`), y fuentes (`sources.md`). |
| `models/` | Modelo 3D del vehículo (`Pz IV H.blend` / `.glb`), mallas visuales de los proyectiles (`<shell_id>.glb`) y los planos de los que salen las medidas. |
| `tools/` | Núcleo de cálculo y herramientas de comprobación (ver abajo). |
| `tfg.md` | Decisiones generales del proyecto. |
| `src/` | Simulador con motor gráfico (pendiente). |

## Herramientas

Python 3, solo biblioteca estándar. Se ejecutan desde la raíz del repositorio.

```
python tools/disparo.py --selftest               # autoprueba del núcleo de cálculo
python tools/disparo.py                          # disparo de prueba con resumen
python tools/disparo.py --shell PzGr40_75_L48 --distance 500 --out disparo.json

python tools/ballistic_data.py --selftest        # autoprueba de la carga de datos
python tools/ballistic_data.py data/             # lista lo cargado

python tools/validate_glb.py --selftest          # autoprueba del validador
python tools/validate_glb.py "models/Pz IV H.glb" data
```

`disparo.py` es el modelo de `docs/modelo_balistico.md` hecho código: tramos del rayo, capas, perforación, energía residual, daño a módulos y estado final. Su autoprueba comprueba que reproduce las tablas de penetración y el caso de regresión contra la placa frontal (81,00 mm a 9,00°).

`validate_glb.py` comprueba que cada pieza del modelo sea convexa y cerrada, que no haya solapes entre objetos y que cada material exista en `data/materials.csv`. Devuelve código distinto de cero si hay errores.

`tools/revisar_vertices.py` se ejecuta **dentro de Blender** (pestaña *Scripting* → pegar → *Run*). Solo informa de vértices duplicados y agujeros de malla; no modifica nada.

## Datos

Los CSV usan coma decimal. No los abras con Excel para editarlos: lo hemos visto borrar columnas al guardar. Usa un editor de texto.
