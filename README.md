# AISLA-OPT

Herramienta académica para seleccionar el aislamiento de la envolvente de cuartos refrigerados. Combina un
modelo térmico estacionario, productos comerciales documentados del mercado costarricense y el costo de ciclo
de vida para identificar la **mejor alternativa comercial evaluada**.

> AISLA-OPT calcula la carga por **transmisión** de paredes, techo y piso. No calcula la carga frigorífica
> total ni dimensiona el equipo. El alcance completo está en el [manual](docs/MANUAL.md).

## Inicio rápido

Requiere Python 3.11 o superior.

```bash
python -m pip install -r requirements.txt
```

```bash
streamlit run app.py
```

En Windows use `py -m pip …` y `py -m streamlit run app.py`.

## Qué hace la aplicación

| Pestaña | Contenido |
|---|---|
| Resultado | Mejor alternativa, corte de la pared con su perfil de temperatura, costo de ciclo de vida y carga por superficie |
| Alternativas | Ranking de todos los productos con precio y su diferencia frente a la mejor |
| Sensibilidad | Gráfico de tornado (tarifa, COP, precio, vida útil, tasa) y barrido de un parámetro con los cruces de decisión |
| Inversión por espesor | VPN incremental y recuperación simple de pasar de un espesor al siguiente |
| Comportamiento térmico | Carga pico continua frente al espesor para cada material |
| Catálogo | Disponibilidad por material, cotizaciones con conversión de lámina o paquete a CRC/m², precios web de EPS y editor del catálogo |
| Reporte y escenarios | Reporte en Excel, escenarios en JSON y comparación de escenarios lado a lado |
| Alcance del modelo | Supuestos, exclusiones y conductividades ASHRAE |

Los resultados se recalculan solos al cambiar cualquier entrada.

## Estructura del repositorio

```
app.py                     Punto de entrada de Streamlit
aisla_opt/                 Lógica de cálculo, sin dependencia de la interfaz
  motor.py                 Red de resistencias, cargas, energía y valor presente
  materiales.py            Conductividades ASHRAE y categorías comerciales
  catalogo.py              Lectura, normalización, altas y conversión de precios
  seleccion.py             Límite por capacidad, primer comercial y comparación económica
  caso.py                  Entradas del caso, plantillas, escenarios JSON y advertencias
  analisis.py              Sensibilidad, inversión incremental y desglose térmico
  mercado.py               Consulta opcional de precios web de EPS
  reporte.py               Exportación a Excel
  formato.py               Números en convención costarricense
interfaz/                  Componentes de Streamlit (tema, gráficas y pestañas)
data/                      Catálogo comercial editable (CSV)
docs/                      Manual, convenciones e historial de versiones
tests/                     Validación V1–V7, pruebas de módulos y prueba de la interfaz
.streamlit/config.toml     Tema visual claro y oscuro
```

## Desarrollo

```bash
python -m pip install -r requirements-dev.txt
```

```bash
ruff check .
```

```bash
pytest
```

Las pruebas incluyen la validación numérica V1–V7 heredada de la V4.4: cálculo manual, bisección contra
solución cerrada, valor presente, k de ficha, interpretación de precios, Ejemplo 3-17 de Çengel y capacidad con
k específica. GitHub Actions las ejecuta en cada push. Las convenciones de código están en
[docs/CONVENCIONES.md](docs/CONVENCIONES.md) y los cambios por versión en [CHANGELOG.md](CHANGELOG.md).

## Fuentes técnicas

- ASHRAE Handbook—Refrigeration 2026, cap. 24, tabla 1: conductividad del aislamiento de almacenamiento refrigerado.
- Çengel y Ghajar, *Heat and Mass Transfer: Fundamentals & Applications*, 6.ª ed.
