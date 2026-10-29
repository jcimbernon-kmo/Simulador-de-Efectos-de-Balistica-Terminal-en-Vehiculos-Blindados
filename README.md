# Simulador de Efectos de Balística Terminal en Vehículos Blindados

Trabajo de Fin de Grado. Simulador 3D para PC que calcula un impacto de proyectil contra un vehículo blindado de la Segunda Guerra Mundial y lo reproduce en cámara lenta: perforación del blindaje, fragmentación, daño a los módulos internos y a la tripulación. El vehículo es estático; el usuario elige proyectil, distancia y punto de impacto.

Primer vehículo: Pz.Kpfw. IV Ausf. H.

## Estado

En fase de modelado y datos. **Todavía no hay simulador** (`src/` está vacío). El estado detallado, con los problemas abiertos, está en [`docs/estado.md`](docs/estado.md).

## Estructura

| Ruta | Contenido |
|---|---|
| `docs/modelo_balistico.md` | Modelo de cálculo: trayectoria del rayo, penetración, astillado, daño a módulos. Es la referencia de lo que implementa el código. |
| `docs/estado.md` | Qué funciona, qué falta y qué se ha decidido. |
| `data/` | Tablas de entrada: proyectiles, penetración, velocidad, materiales (`*.csv`) y fuentes (`sources.md`). |
| `models/` | Modelo 3D del vehículo: `.blend` editable y `.glb` exportado. |
| `tools/` | Herramientas de comprobación (ver abajo). |
| `tfg.md` | Decisiones generales del proyecto. |
| `src/` | Simulador (pendiente). |

## Herramientas

Python 3, solo biblioteca estándar. Se ejecutan desde la raíz del repositorio.

```
python tools/ballistic_data.py --selftest        # autoprueba de la carga de datos
python tools/ballistic_data.py data/             # lista lo cargado y avisa de huecos

python tools/validate_glb.py --selftest          # autoprueba del validador
python tools/validate_glb.py "models/Pz IV H.glb" data
```

`validate_glb.py` comprueba que cada pieza del modelo sea convexa y cerrada, que no haya solapes entre objetos y que cada material exista en `data/materials.csv`. Devuelve código distinto de cero si hay errores.

`tools/revisar_vertices.py` se ejecuta **dentro de Blender** (pestaña *Scripting* → pegar → *Run*). Solo informa de vértices duplicados y agujeros de malla; no modifica nada.

## Datos

Los CSV usan coma decimal. No los abras con Excel para editarlos: lo hemos visto borrar columnas al guardar. Usa un editor de texto.
