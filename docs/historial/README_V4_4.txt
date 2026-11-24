AISLA-OPT V4.4 — CÓDIGO CERRADO
================================

PROPÓSITO
AISLA-OPT es una herramienta académica para analizar el aislamiento de la envolvente de cuartos refrigerados mediante un modelo térmico estacionario, alternativas comerciales documentadas y costo de ciclo de vida.

CRITERIO DE DECISIÓN
1. El motor calcula la transmisión térmica por paredes, techo y piso.
2. La restricción de capacidad para transmisión es opcional y está desactivada por defecto.
3. Cuando esa restricción se activa, se calcula un límite continuo usando la k genérica del material y se muestra el primer espesor comercial documentado que lo cubre.
4. Para la comparación económica, cada producto se evalúa de nuevo con su k de ficha cuando está disponible.
5. La salida económica es la “mejor alternativa comercial evaluada” dentro del catálogo con precio comparable; no se afirma un óptimo global fuera del rango estudiado.
6. El catálogo es editable y contiene referencias iniciales del mercado costarricense; no pretende representar de forma exhaustiva todos los proveedores.
7. Paneles frigoríficos completos y aislantes independientes se analizan en categorías separadas.

ALCANCE
- Transmisión estacionaria a través de la envolvente.
- Dimensiones exteriores de referencia.
- Mismo material y espesor uniforme en paredes, techo y piso para cada alternativa.
- COP efectivo promedio para estimar energía atribuible a transmisión.
- Valor presente de energía + costo de aislamiento.
- No incluye infiltración, producto, personas, iluminación, deshielo, dimensionamiento completo del sistema frigorífico ni costos no registrados explícitamente.

VALIDACIÓN
Ejecute:
py pruebas_validacion.py

EJECUCIÓN
py -m pip install -r requirements_aisla_opt.txt
py -m streamlit run app_aisla_opt.py

ESTADO
Código funcional cerrado tras auditoría V4.3. Los datos comerciales pueden ampliarse posteriormente mediante cotizaciones documentadas sin modificar el modelo físico.
