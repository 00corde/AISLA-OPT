# Registro de cambios

## 4.5.0

El modelo físico y económico no cambia. Para los escenarios de prueba, la V4.5 reproduce exactamente los
resultados de la V4.4, verificado contra una instantánea de la versión anterior.

### Nuevas funciones
- **Sensibilidad:** gráfico de tornado para tarifa eléctrica, COP, precio del aislamiento, vida útil y tasa de
  descuento, con aviso cuando la mejor alternativa cambia.
- **Barrido de un parámetro:** costo de las cinco mejores alternativas a lo largo de un rango, con los cruces
  de decisión.
- **Inversión por espesor:** VPN incremental y recuperación simple de cada paso al siguiente espesor.
- **Corte de la pared:** diagrama con el perfil de temperatura real de la mejor alternativa.
- **Carga por superficie:** participación de paredes, techo y piso en la carga pico.
- **Conversión de precios:** las cotizaciones aceptan precio por m², por lámina o panel y por paquete.
- **Reporte en Excel** con resumen, entradas, alternativas, análisis, advertencias y catálogo.
- **Escenarios:** guardar y cargar en JSON, y comparación lado a lado en la sesión.
- **Plantillas** de conservación (5 °C) y congelación (−18 °C).
- Carga y descarga del catálogo completo en CSV.

### Interfaz
- Los resultados se recalculan al cambiar cualquier entrada y ya no desaparecen.
- La aplicación abre en «Aislante independiente», que tiene precios, en lugar de paneles sin precio.
- Aviso explícito para los materiales sin productos con precio (antes desaparecían de la comparación).
- Tabla de alternativas compacta, con el costo total y la diferencia frente a la mejor primero.
- Tema propio claro y oscuro, tipografía Barlow, números con convención costarricense y gráficas con unidades,
  colores fijos por material y paleta validada para daltonismo.
- Se corrigió el título recortado y el texto truncado en las cifras principales.

### Código y repositorio
- Estructura en paquetes: `aisla_opt/` (lógica, sin Streamlit), `interfaz/`, `data/`, `docs/` y `tests/`.
- Archivos renombrados: `aisla_opt_v2.py` → `aisla_opt/motor.py`, `seleccion_ingenieril.py` →
  `aisla_opt/seleccion.py`, `datos_tecnicos.py` → `aisla_opt/materiales.py`, `mercado_cr.py` →
  `aisla_opt/mercado.py`, `app_aisla_opt.py` → `app.py`.
- Motor reescrito legible y tipado. `Recinto` agrupa geometría, temperatura interior y superficies.
- Nombres de funciones y variables en español con sufijos de unidad. Ver `docs/CONVENCIONES.md`.
- Se eliminaron el ejemplo de demostración con matplotlib, el parámetro sin uso `espesores_requeridos` y el
  archivo duplicado `requirements_aisla_opt.txt`.
- Pruebas con pytest: V1–V7 más pruebas de catálogo, análisis, escenarios, reporte e interfaz. Análisis
  estático con Ruff y CI en GitHub Actions.
- Se reemplazó `use_container_width`, obsoleto en Streamlit, por `width`.

## 4.4

Cierre de código tras la auditoría final (N1–N7) y validación V1–V7. Ver
`docs/historial/CIERRE_CODIGO_V4_4.txt`.
