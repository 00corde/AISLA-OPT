# Convenciones de código

## Idioma

Código, comentarios, mensajes y documentación en español. Las excepciones son los términos técnicos sin
traducción habitual (`COP`, `U`, `k`) y las API de bibliotecas externas.

## Nombres

| Elemento | Convención | Ejemplo |
|---|---|---|
| Módulos y paquetes | `snake_case`, sustantivo corto | `catalogo.py`, `interfaz/` |
| Funciones | `snake_case`, verbo o resultado | `evaluar_caso`, `precio_por_m2` |
| Clases y dataclasses | `PascalCase` | `ParametrosCaso`, `ResultadoAlternativa` |
| Constantes | `MAYUSCULAS_CON_GUION` | `RUTA_CATALOGO`, `K_MAXIMA_W_mK` |
| Callbacks de Streamlit | prefijo `al_` | `al_cambiar_sistema` |
| Privados del módulo | prefijo `_` | `_descargar_html` |

### Sufijos de unidad

Toda magnitud física o monetaria lleva su unidad como sufijo, con la capitalización SI. Es la única excepción
deliberada a `snake_case`, porque `W` y `w`, o `K` y `k`, no significan lo mismo.

`_m`, `_mm`, `_m2`, `_C`, `_W`, `_kW`, `_kWh`, `_W_mK` (W/m·K), `_W_m2K` (W/m²·K), `_m2K_W` (m²·K/W),
`_CRC`, `_CRC_m2`, `_CRC_kWh`, `_pct`, `_anios`, `_s`.

Las columnas del catálogo CSV (`Precio_CRC_m2`, `k_W_mK`, …) conservan su esquema original para que los
catálogos existentes sigan funcionando.

## Estructura

- `aisla_opt/` no importa Streamlit. Toda la lógica se prueba sin interfaz.
- `interfaz/` solo dibuja: lee `ParametrosCaso` del estado, llama a `aisla_opt` y muestra el resultado.
- Los widgets de entrada usan como `key` el nombre del campo de `ParametrosCaso`. Las plantillas y los
  escenarios se aplican en callbacks, antes de dibujar los widgets.
- Las tablas internas usan columnas `snake_case` con unidad. Las etiquetas legibles se asignan al mostrar o
  exportar.

## Estilo

- Formato y orden de imports con Ruff (`ruff check .`), 120 caracteres por línea.
- Anotaciones de tipo en funciones públicas. Dataclasses `frozen=True` para datos del modelo.
- Errores de entrada como `ValueError` con un mensaje que diga qué corregir.
- En la interfaz, números con la convención costarricense (`aisla_opt.formato`): espacio fino para miles y
  coma decimal.

## Pruebas

- Todo cambio en `aisla_opt/` lleva una prueba en `tests/`.
- V1–V7 (`tests/test_validacion.py`) no se modifican salvo para seguir un cambio de API. Sus valores
  esperados son independientes del código.
- `tests/test_app.py` ejecuta la interfaz completa con `streamlit.testing`.

## Commits

Mensajes en español, en imperativo y con un tema por commit: «Agrega análisis de sensibilidad», «Corrige el
formato de montos negativos».
