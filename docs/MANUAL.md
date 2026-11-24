# AISLA-OPT — Manual de usuario y alcance técnico

**Versión:** 4.5  
**Estado:** modelo validado (V1–V7); la V4.5 agrega análisis y mejoras de interfaz sin cambiar el modelo físico  
**Propósito del documento:** explicar qué resuelve AISLA-OPT, cómo funciona el modelo, cómo usar la interfaz y cómo interpretar correctamente los resultados.

---

## 0. Lectura rápida: qué es AISLA-OPT

AISLA-OPT es una herramienta académica de apoyo al diseño para realizar un **análisis termo-económico del aislamiento de la envolvente de un cuarto refrigerado**.

La herramienta integra tres niveles de decisión:

1. **Física:** estima la transferencia de calor por conducción y convección a través de paredes, techo y piso.
2. **Mercado:** trabaja con productos comerciales discretos, espesores reales, precios y propiedades específicas cuando están documentadas.
3. **Economía:** compara el costo inicial del aislamiento con el costo de la energía atribuible a transmisión durante la vida útil.

El flujo conceptual es:

`condiciones del recinto → transmisión térmica → alternativas comerciales → energía → costo de ciclo de vida → mejor alternativa evaluada`

AISLA-OPT **no calcula la carga frigorífica total de una cámara**, no reemplaza un diseño HVAC detallado y no afirma encontrar un óptimo universal fuera de los productos estudiados.

La salida económica principal se denomina:

> **Mejor alternativa comercial evaluada**

Ese nombre es intencional: el programa solo puede concluir sobre los productos y precios que fueron documentados.

---

## 1. Problema de ingeniería

Aumentar el espesor del aislamiento reduce la transferencia de calor hacia el recinto refrigerado. Sin embargo, un mayor espesor también aumenta la inversión inicial.

En términos generales:

`mayor espesor → menor transmitancia → menor carga por transmisión → menor consumo energético`

pero también:

`mayor espesor → mayor costo inicial`

Además, el espesor que surge de un cálculo continuo no necesariamente existe en el mercado. Un cálculo puede indicar, por ejemplo, 54 mm, mientras los productos comerciales disponibles son 50, 76 y 102 mm.

Por eso el problema no consiste únicamente en calcular una carga térmica. AISLA-OPT busca conectar:

- el comportamiento térmico;
- la disponibilidad comercial;
- el costo energético;
- y el costo de inversión.

---

## 2. Alcance del modelo

AISLA-OPT considera:

- un recinto rectangular;
- transferencia de calor en estado estacionario;
- transmisión a través de paredes, techo y piso;
- conducción a través del aislamiento;
- convección interior y exterior mediante coeficientes efectivos `h`;
- dimensiones exteriores de referencia;
- un mismo material y espesor uniforme en paredes, techo y piso para cada alternativa;
- condición crítica para carga pico;
- condición representativa de operación para energía anual;
- COP efectivo promedio;
- costo de ciclo de vida mediante valor presente;
- productos comerciales documentados en un catálogo editable.

### Fuera del alcance

La versión 4.5 no modela explícitamente:

- infiltración por apertura de puertas;
- humedad o carga latente;
- producto almacenado;
- personas;
- iluminación;
- motores internos;
- deshielo;
- ciclo frigorífico detallado;
- selección de refrigerante;
- variación horaria del COP;
- régimen transitorio;
- puentes térmicos 2D o 3D;
- conducción detallada hacia el terreno;
- costo del equipo de refrigeración;
- cargos por demanda eléctrica;
- instalación, desperdicio, flete o impuestos si no están incluidos en el precio registrado.

Por ello, los resultados deben describirse como un **análisis de transmisión de la envolvente**, no como un dimensionamiento completo de la cámara frigorífica.

---

## 3. Geometría utilizada

La interfaz solicita:

- largo exterior de referencia;
- ancho exterior de referencia;
- alto exterior de referencia.

Las áreas se calculan como:

`A_paredes = 2 H (L + W)`

`A_techo = L W`

`A_piso = L W`

`A_total = A_paredes + A_techo + A_piso`

AISLA-OPT utiliza estas áreas exteriores de referencia de forma constante durante la comparación.

### Limitación geométrica

Al aumentar el espesor, una formulación geométrica más refinada podría considerar factores de forma o áreas medias. El modelo mantiene el área exterior fija para conservar un modelo simple y reproducible. Esta aproximación tiende a ser conservadora para la transmisión, especialmente a espesores altos.

---

## 4. Modelo de resistencia térmica

Para cada superficie se utiliza una red de resistencias térmicas por unidad de área:

`R''_total = 1/h_i + R''_adicional + e/k + 1/h_o`

donde:

- `h_i` = coeficiente efectivo de transferencia de calor interior [W/m²·K];
- `h_o` = coeficiente efectivo exterior o equivalente [W/m²·K];
- `R''_adicional` = resistencia conocida de otras capas [m²·K/W];
- `e` = espesor del aislamiento [m];
- `k` = conductividad térmica del aislamiento [W/m·K].

El coeficiente global se calcula como:

`U = 1 / R''_total`

y la transferencia de calor en cada superficie como:

`Q = U A ΔT`

La carga total por transmisión es la suma de paredes, techo y piso.

---

## 5. Coeficientes `h` y resistencia adicional

Los coeficientes `h` de la interfaz son **parámetros efectivos de película editables**.

Los valores por defecto son:

- `h interior = 9.1 W/m²·K`;
- `h exterior paredes = 9.1 W/m²·K`;
- `h exterior techo = 9.1 W/m²·K`;
- `h equivalente piso = 9.1 W/m²·K`.

Estos valores son referencias de trabajo y **no deben interpretarse como constantes universales**. Deben ajustarse si se dispone de condiciones de diseño más específicas.

`R'' adicional` tiene valor por defecto cero.

Solo debe utilizarse para representar resistencias conocidas aparte del aislamiento seleccionado. No debe agregarse una resistencia arbitraria para “mejorar” el resultado ni duplicar capas que ya estén incluidas en un panel o producto.

---

## 6. Tratamiento del techo y del piso

Las temperaturas del techo y piso son condiciones equivalentes definidas por el usuario.

### Techo

Puede utilizarse una temperatura equivalente que incorpore, de manera simplificada, efectos adicionales como radiación solar.

AISLA-OPT no resuelve la radiación solar de forma separada.

### Piso

El piso se trata mediante una resistencia y una temperatura equivalente.

AISLA-OPT **no implementa un modelo detallado de conducción acoplada al terreno**. Esta simplificación debe declararse en el informe y en la defensa.

---

## 7. Propiedades térmicas de los materiales

La fuente técnica base es:

**ASHRAE Handbook—Refrigeration 2026, Chapter 24, Table 1: Thermal Conductivity of Cold Storage Insulation.**

Referencia web:

`https://handbook.ashrae.org/Handbooks/R26/SI/r26_ch24/r26_ch24_si.aspx`

El acceso en línea al Handbook puede requerir suscripción institucional.

Las condiciones declaradas por la tabla utilizada son:

- temperatura media: 24 °C;
- aislamiento envejecido: 180 días.

### Valores base incluidos

| Material | k base [W/m·K] | Nota |
|---|---:|---|
| Poliuretano (PU) | 0.026 | ASHRAE reporta 0.023–0.026; se usa 0.026 como valor conservador |
| Poliisocianurato (PIR) | 0.027 | Valor técnico base |
| Poliestireno extruido (XPS) | 0.035 | Valor técnico base |
| Poliestireno expandido (EPS) | 0.037 | Valor técnico base |
| Corcho | 0.043 | Valor técnico base |
| Vidrio celular | 0.044 | Valor técnico base |

Estos valores son genéricos. La conductividad real puede variar con formulación, densidad, temperatura, envejecimiento, humedad y fabricante.

### `k` específica de producto

Si una ficha técnica o una cotización documentada proporciona una conductividad específica, AISLA-OPT puede utilizarla para ese producto.

La lógica es:

`k de ficha disponible → usar k específica`

`k de ficha no disponible → usar k base del material`

La interfaz admite valores de `k` entre `0.01` y `0.20 W/m·K` como control de plausibilidad y para detectar errores de unidades. Este rango es una protección de entrada, no una afirmación de que todos los materiales aislantes posibles deban encontrarse dentro de él.

---

## 8. Condición crítica y condición de operación

AISLA-OPT separa dos condiciones térmicas.

### Condición crítica

Se utiliza para calcular:

- carga pico de transmisión;
- transmisión más margen de diseño;
- restricción opcional de capacidad.

### Condición de operación

Se utiliza para estimar:

- carga de operación;
- potencia eléctrica atribuible a transmisión;
- energía anual;
- costo energético.

Para la estimación anual, las temperaturas de operación deben interpretarse como **condiciones medias representativas ponderadas en el tiempo**, no como valores máximos de diseño.

Esta separación evita calcular todo el consumo anual suponiendo que el recinto permanece permanentemente bajo la condición exterior crítica.

---

## 9. Carga crítica y margen de diseño

Para paredes, techo y piso se calcula la transferencia en condición crítica y posteriormente:

`Q_crit,total = Q_paredes + Q_techo + Q_piso`

La capacidad de transmisión con margen se expresa como:

`Q_recomendada = margen × Q_crit,total`

Por ejemplo, con un margen de 10 %:

`margen = 1.10`

Este resultado sigue representando únicamente transmisión por la envolvente.

---

## 10. Restricción opcional de capacidad

La casilla:

> **Limitar por capacidad disponible para transmisión**

está desactivada por defecto.

Cuando se activa, el valor ingresado debe representar únicamente la capacidad que puede destinarse a compensar la carga de transmisión.

Si se conoce la capacidad total del equipo:

`Q_disponible,envolvente = Q_equipo,total - Q_otras cargas`

Las “otras cargas” pueden incluir infiltración, producto, iluminación, personas, motores y demás cargas que AISLA-OPT no modela.

### Qué calcula la restricción

AISLA-OPT busca mediante bisección el **límite continuo de espesor** que permite satisfacer la capacidad indicada.

El intervalo numérico de búsqueda es aproximadamente:

`0.1 mm ≤ e ≤ 400 mm`

Si ni siquiera 400 mm satisface la restricción, la interfaz reporta `> 400 mm`.

### Importante: `k` genérica vs. `k` de ficha

El límite continuo mostrado para cada material utiliza la `k` genérica seleccionada.

Posteriormente, al evaluar productos comerciales individuales, AISLA-OPT vuelve a comprobar la factibilidad con la `k` específica de la ficha cuando existe.

Por eso un producto real puede cumplir aunque su espesor sea inferior al límite continuo calculado con una `k` genérica menos favorable.

---

## 11. Del espesor continuo al producto comercial

Cuando la restricción de capacidad está activa, la herramienta muestra:

- límite continuo por capacidad;
- primer espesor comercial documentado que lo cubre;
- margen comercial en milímetros;
- margen sobre el mínimo;
- sensibilidad frente al siguiente salto comercial.

Ejemplo conceptual:

`e continuo = 54.3 mm`

Productos disponibles:

`50 mm, 76 mm, 101.6 mm`

El primer espesor comercial que cubre el límite es:

`76 mm`

Esta comparación conecta el cálculo continuo con una selección realizable.

Sin una restricción de capacidad activa, AISLA-OPT **no inventa un espesor mínimo térmico** y esta tabla no se muestra.

---

## 12. Sistemas comerciales separados

AISLA-OPT distingue dos categorías.

### Panel frigorífico completo

Productos terminados destinados a cerramientos frigoríficos, por ejemplo paneles PUR o PIR.

### Aislante independiente

Materiales comercializados como aislamiento, por ejemplo EPS o XPS.

La separación evita comparar directamente una lámina aislante desnuda con un panel terminado como si ambos representaran exactamente el mismo producto o alcance de suministro.

Cada análisis económico debe realizarse dentro de una categoría coherente.

---

## 13. Catálogo comercial

El catálogo comercial es editable.

Incluye referencias iniciales del mercado costarricense, pero **no pretende ser un censo exhaustivo de proveedores**.

Su función es proporcionar un conjunto de productos documentados y permitir que el usuario lo amplíe.

El producto de software es la herramienta de evaluación; los proveedores precargados son datos de aplicación.

### Campos principales del catálogo

- activo;
- sistema;
- material;
- proveedor;
- producto;
- espesor [mm];
- precio [CRC/m²];
- `k` de ficha [W/m·K];
- densidad [kg/m³];
- IVA incluido;
- condición del precio;
- estado del precio;
- fecha;
- fuente o referencia.

---

## 14. Registrar una cotización

La sección **Registrar una cotización** permite incorporar productos sin modificar el código.

Se recomienda registrar:

- sistema comercial correcto;
- material;
- proveedor;
- descripción exacta del producto;
- espesor;
- precio normalizado a CRC/m²;
- `k` de ficha, si existe;
- densidad, si existe;
- estado del IVA;
- condición del precio;
- fecha;
- contacto, URL o referencia.

### Identidad de una cotización

Las filas se distinguen por:

`sistema + material + proveedor + producto + espesor`

Por ello, diferentes espesores del mismo producto pueden coexistir sin sobrescribirse.

### Precio por otras unidades

El formulario acepta el precio en tres formas:

- por metro cuadrado (CRC/m²);
- por lámina o panel, indicando ancho y largo en metros;
- por paquete, indicando además las unidades por paquete.

AISLA-OPT convierte a CRC/m² con esas dimensiones. Use **solo dimensiones documentadas** por el proveedor;
no debe inventarse un factor de conversión. Los precios por metro lineal deben convertirse manualmente con el
ancho útil documentado.

---

## 15. IVA y comparabilidad económica

AISLA-OPT guarda el estado del IVA como:

- `Sí`;
- `No`;
- `No indicado`.

La tabla económica muestra el IVA y la condición del precio.

Si la comparación mezcla precios con IVA incluido, excluido o no indicado, la aplicación genera una advertencia.

AISLA-OPT **no corrige automáticamente el IVA**. La responsabilidad es comparar cotizaciones sobre una base homogénea.

Esto es importante porque una diferencia tributaria puede cambiar cuál alternativa aparenta ser la más barata.

---

## 16. Actualización opcional de precios web

La consulta automática disponible corresponde a EPS dentro de la categoría **Aislante independiente**.

Esta función:

- es opcional;
- no es necesaria para usar el programa;
- muestra una vista previa;
- no modifica silenciosamente el catálogo;
- intenta normalizar precios a CRC/m²;
- conserva el catálogo existente si una consulta falla;
- al actualizar una fila existente cambia precio, fecha y fuente sin borrar `k`, densidad, IVA o condición comercial registrados.

La extracción web debe tratarse como apoyo preliminar.

Una cotización directa o una ficha documentada tiene mayor valor que una lectura automática de una página comercial.

---

## 17. Energía atribuible a transmisión

La carga representativa de operación se transforma en potencia eléctrica mediante:

`W_el = Q_op / COP`

donde el COP ingresado se interpreta como **COP efectivo promedio**.

La energía anual se calcula como:

`E_anual = (W_el / 1000) × horas_año`

Las horas representan el tiempo anual durante el cual el recinto permanece a la temperatura objetivo.

Para operación continua:

`horas_año = 8760`

El resultado se denomina **energía anual por transmisión** porque no incluye el consumo causado por otras cargas ni auxiliares del sistema.

---

## 18. Modelo económico

El costo energético anual se calcula mediante:

`C_energía,anual = E_anual × tarifa`

Para llevar costos futuros a valor presente se utiliza:

`FVP = [1 - (1+i)^(-N)] / i`

donde:

- `i` = tasa de descuento real;
- `N` = vida útil en años.

Si `i = 0`:

`FVP = N`

Entonces:

`C_energía,VP = C_energía,anual × FVP`

Para productos comerciales con precio en CRC/m²:

`C_aislamiento = A_total × precio_m²`

y:

`C_total,VP = C_aislamiento + C_energía,VP`

### Qué no incluye el costo total

El costo calculado no debe llamarse “presupuesto total de construcción”.

No incluye automáticamente:

- instalación;
- flete;
- desperdicio;
- estructura;
- equipo de refrigeración;
- cargo por demanda;
- mantenimiento;
- impuestos no incorporados en la cotización.

La omisión del costo del equipo y de la demanda puede favorecer económicamente espesores menores, porque el modelo no monetiza una posible reducción del tamaño del sistema frigorífico.

---

## 19. Mejor alternativa comercial evaluada

AISLA-OPT compara todos los productos activos que:

- pertenecen al sistema seleccionado;
- tienen espesor válido;
- tienen precio positivo y normalizado;
- tienen `k` válida o pueden utilizar el valor base;
- cumplen la restricción de capacidad si esta se encuentra activa.

La alternativa con menor:

`C_total,VP`

se muestra como:

> **Mejor alternativa comercial evaluada**

### Resultado en el borde del catálogo

Si la mejor alternativa coincide con el espesor máximo con precio disponible, la aplicación advierte que:

- el catálogo limita la conclusión;
- el costo podría seguir disminuyendo con espesores mayores;
- no puede afirmarse un óptimo global.

### Un solo espesor con precio

Si solo existe un espesor comparable para el material seleccionado, la herramienta advierte que no existe rango suficiente para afirmar un mínimo económico robusto.

### Resultado interior

Si el mínimo aparece entre los extremos del catálogo, la conclusión económica es más fuerte dentro del rango estudiado, pero sigue limitada a los productos documentados.

---

## 19b. Análisis complementarios (V4.5)

### Sensibilidad

La pestaña **Sensibilidad** mueve cada supuesto hacia abajo y hacia arriba (por defecto ±20 %): tarifa
eléctrica, COP, precio del aislamiento, vida útil y tasa de descuento. El gráfico de tornado muestra cuánto
cambia el costo total de la mejor alternativa y la tabla indica si la mejor alternativa cambia en algún extremo.

El **barrido de un parámetro** traza el costo total de las cinco mejores alternativas a lo largo de un rango.
Donde dos curvas se cruzan, cambia la decisión.

### Inversión por espesor

Para un material, compara cada espesor con presencia comercial contra el siguiente más grueso, tomando el
producto de menor precio en cada espesor:

`VPN incremental = Δahorro_energía,anual × FVP − Δcosto_aislamiento`

Un VPN positivo indica que el paso al espesor mayor se paga dentro de la vida útil. También se informa la
recuperación simple `Δcosto / Δahorro anual`.

### Perfil de temperatura

El corte de pared de la pestaña **Resultado** usa la misma red de resistencias del modelo. Como el flujo por
unidad de área es igual en todas las capas, cada salto de temperatura es proporcional a su resistencia:

`q'' = (T_ext − T_int) / R''_total`  `ΔT_capa = q'' × R''_capa`

### Escenarios y reporte

- **Escenario JSON:** guarda todas las entradas para reproducir el caso o compartirlo.
- **Comparación de escenarios:** agrega el caso actual a una tabla de la sesión para compararlo con otros.
- **Reporte Excel:** resumen, entradas, alternativas, límites por capacidad, sensibilidad, inversión por
  espesor, advertencias y catálogo usado.

### Plantillas

Las plantillas son puntos de partida editables: conservación a 5 °C (valores iniciales) y congelación a
−18 °C (COP 1,8). No sustituyen los datos de diseño del proyecto.

---

## 20. Gráficas y resultados principales

La interfaz puede mostrar:

### Del cálculo al componente comercial

Solo cuando la restricción de capacidad está activa.

Compara:

- límite continuo;
- primer tamaño comercial;
- margen comercial.

### Mejor alternativa comercial evaluada

Resume:

- material;
- producto;
- espesor;
- proveedor;
- carga pico por transmisión;
- energía anual por transmisión;
- costo inicial del aislamiento;
- costo total en valor presente.

### Alternativas comerciales evaluadas con precio

Incluye, entre otros:

- precio;
- `k` utilizada;
- carga pico;
- transmisión con margen;
- energía;
- costo inicial;
- costo energético VP;
- costo total VP;
- IVA;
- condición;
- fecha;
- fuente.

### Costo de ciclo de vida

Muestra el costo total en valor presente dentro del catálogo evaluado.

### Comportamiento térmico continuo

Muestra cómo cambia la carga pico de transmisión al variar el espesor.

Esta última curva representa comportamiento físico continuo y no disponibilidad comercial.

---

## 21. Advertencias de entrada

### Temperaturas

Si una temperatura exterior o equivalente es menor o igual a la temperatura interior, la aplicación emite una advertencia.

El modelo permite esos valores porque pueden representar una condición de pérdida de calor, pero el usuario debe confirmar que sean intencionales.

### Conductividad

La aplicación bloquea conductividades fuera del rango de plausibilidad definido para la herramienta.

### Fechas

Cuando se edite manualmente el catálogo, se recomienda utilizar formato ISO:

`AAAA-MM-DD`

Ejemplo:

`2026-11-22`

Esto evita ambigüedades entre formatos día/mes y mes/día.

### Campos vacíos

Para IVA y condiciones comerciales se recomienda usar explícitamente `No indicado` o una descripción breve en lugar de dejar celdas vacías.

---

## 22. Validación

El archivo `tests/test_validacion.py` contiene las **siete pruebas** de validación. El resto de `tests/`
cubre catálogo, análisis, escenarios, reporte y una ejecución completa de la interfaz.

Ejecutar:

```bash
python -m pip install -r requirements-dev.txt
```

```bash
pytest
```

### V1 — Cálculo manual base

Compara el resultado del motor contra un cálculo independiente realizado con las ecuaciones del modelo.

Verifica:

- resistencias;
- coeficientes `U`;
- carga crítica;
- margen;
- energía anual.

### V2 — Bisección contra solución cerrada

Verifica que el cálculo numérico del espesor límite reproduzca la solución analítica para un caso simplificado.

### V3 — Finanzas y monotonicidad

Verifica:

- `FVP = N` cuando `i = 0`;
- disminución de carga al aumentar el espesor.

### V4 — `k` específica por producto

Verifica que una conductividad de ficha pueda sustituir el valor genérico y que exista fallback al valor técnico base cuando no se proporciona.

### V5 — Parser de precios

Verifica formatos de moneda costarricense con:

- punto;
- coma;
- espacio;
- espacio duro;
- ausencia de separador;
- texto de stock como `2 disponibles`.

La prueba comprueba que el número de stock no se concatene con el precio.

### V6 — Reproducción del Ejemplo 3-17 de Çengel

El motor reproduce un caso publicado en el texto de referencia del curso.

Resultado de referencia aproximado:

- `2730 Btu/h`;
- `19.2 kWh/día`.

Esta prueba es especialmente útil porque compara AISLA-OPT contra un resultado externo al propio programa.

### V7 — Capacidad con `k` específica

Verifica que un producto con una conductividad de ficha mejor no sea descartado por un prefiltro basado en la `k` genérica.

También comprueba que se conserven condiciones comerciales relevantes durante la evaluación.

### Estado de validación

La versión 4.5 fue verificada con:

`V1–V7: 7/7 aprobadas` y resultados idénticos a la V4.4 en los escenarios de regresión.

Además, una auditoría externa de regresión ejecutó la aplicación en distintos escenarios sin encontrar excepciones críticas ni importantes.

---

## 23. Requisitos de software

Las versiones principales probadas están en `requirements.txt`:

```text
streamlit==1.67.0
pandas==3.0.6
altair>=5.4,<7
openpyxl>=3.1,<4
requests>=2.31,<3
beautifulsoup4>=4.12,<5
```

Por compatibilidad con las versiones fijadas de Streamlit y pandas, se recomienda utilizar:

**Python 3.11 o superior**

Comprobar:

```bash
py --version
```

---

## 24. Instalación

Ubíquese en la carpeta que contiene los archivos del proyecto y ejecute:

```bash
py -m pip install -r requirements.txt
```

---

## 25. Ejecución

Desde la carpeta del proyecto:

```bash
py -m streamlit run app.py
```

Streamlit abrirá la interfaz en el navegador. En Linux o macOS use `python3` en lugar de `py`.

---

## 26. Procedimiento recomendado de uso

1. Definir la categoría comercial: panel completo o aislante independiente.
2. Seleccionar uno o más materiales.
3. Introducir dimensiones exteriores de referencia.
4. Definir temperatura interior.
5. Definir temperaturas críticas.
6. Definir condiciones representativas de operación.
7. Revisar COP, margen, tarifa, horas, vida útil y tasa de descuento.
8. Ajustar `h` y `R'' adicional` solo si existen datos que lo justifiquen.
9. Revisar el catálogo comercial.
10. Registrar cotizaciones documentadas si es necesario.
11. Verificar `k`, IVA y condición del precio.
12. Activar la restricción de capacidad únicamente si existe un valor de capacidad disponible específicamente para transmisión.
13. Revisar la pestaña **Resultado**: los cálculos se actualizan solos con cada cambio.
14. Interpretar primero la parte térmica.
15. Interpretar después la comparación comercial.
16. Revisar el costo de ciclo de vida y las advertencias del catálogo.
17. Comprobar la robustez en **Sensibilidad** e **Inversión por espesor**.
18. Descargar el reporte Excel y el escenario JSON para el informe.

---

## 27. Cómo interpretar correctamente un resultado

Supóngase que AISLA-OPT muestra:

- límite continuo: 54.3 mm;
- primer comercial que cubre: 76 mm;
- mejor alternativa comercial evaluada: 101.6 mm.

Estas tres cifras responden preguntas distintas.

### 54.3 mm

Responde:

> ¿Qué espesor continuo permitiría cumplir la restricción de capacidad ingresada bajo la `k` genérica?

### 76 mm

Responde:

> ¿Cuál es el primer producto comercial documentado que cubre ese límite continuo?

### 101.6 mm

Responde:

> Entre los productos con precio comparable y técnicamente factibles, ¿cuál presenta el menor costo total en valor presente?

No existe contradicción entre las tres respuestas.

---

## 28. Limitaciones que deben aparecer en el informe

El informe final debe declarar al menos:

1. modelo estacionario;
2. transmisión únicamente por la envolvente;
3. dimensiones exteriores y área fija;
4. espesor uniforme en todas las superficies;
5. techo y piso mediante condiciones equivalentes;
6. `h` efectivos editables;
7. COP efectivo promedio;
8. temperaturas de operación como condiciones medias representativas;
9. valores genéricos de `k` cuando no existe ficha;
10. catálogo comercial no exhaustivo;
11. comparación económica limitada a precios documentados;
12. advertencia cuando el mejor resultado cae en el borde del catálogo;
13. IVA y condiciones comerciales deben normalizarse;
14. costos de equipo, demanda, instalación y otros costos no incluidos salvo que estén incorporados explícitamente;
15. no se calcula la carga frigorífica total.

Estas limitaciones no invalidan la herramienta. Definen el dominio dentro del cual los resultados son defendibles.

---

## 29. Puntos técnicos importantes para la defensa

### “¿AISLA-OPT calcula la capacidad total del equipo?”

No. Calcula la carga por transmisión de la envolvente. La restricción de capacidad es opcional y debe representar capacidad disponible para transmisión después de descontar otras cargas.

### “¿Por qué hay temperatura crítica y temperatura de operación?”

La temperatura crítica se usa para carga pico. La de operación representa una condición media adecuada para energía anual. Utilizar la condición extrema durante todo el año sobreestimaría el consumo.

### “¿Por qué el espesor comercial puede ser mayor que el calculado?”

Porque los productos reales existen en tamaños discretos.

### “¿Por qué el programa no siempre dice ‘óptimo’?”

Porque un catálogo finito no permite demostrar un óptimo global. Si el mejor producto está en el límite superior del catálogo, solo puede afirmarse que es el mejor de los productos evaluados.

### “¿Por qué se permite una `k` específica?”

Porque la conductividad genérica de una familia de materiales no sustituye una ficha técnica real. Cuando existe un dato de producto documentado, es preferible utilizarlo.

### “¿Por qué separar paneles y aislantes?”

Porque un panel terminado y una lámina aislante no representan el mismo producto ni la misma estructura de costos.

### “¿Por qué usar valor presente?”

Porque el costo del aislamiento ocurre inicialmente mientras los costos energéticos se distribuyen durante varios años. El valor presente permite compararlos en una misma base temporal.

---

## 30. Uso del catálogo costarricense

Los productos costarricenses precargados deben entenderse como **caso de aplicación y datos iniciales**.

AISLA-OPT no depende de que esos proveedores representen todo el mercado.

El catálogo puede ampliarse con cualquier producto que disponga de suficiente información para ser evaluado:

- material;
- espesor;
- precio normalizado;
- condición comercial;
- y, preferiblemente, `k` de ficha.

Por tanto, la herramienta es generalizable aunque el caso de estudio final se realice con datos de Costa Rica.

---

## 31. Datos pendientes para el caso de estudio final

El modelo está validado, pero la calidad del caso económico final depende de los datos ingresados.

Antes de redactar resultados definitivos conviene disponer de:

- cotizaciones reales de paneles PUR/PIR;
- estado del IVA;
- dimensiones o unidad de venta;
- precio normalizado a CRC/m²;
- `k` de ficha técnica cuando exista;
- fecha de cotización;
- fuente o contacto.

La incorporación de nuevas cotizaciones **no requiere modificar el modelo físico ni el código**.

---

## 32. Referencias técnicas para el informe

### ASHRAE

**ASHRAE Handbook—Refrigeration 2026.** Chapter 24, *Refrigerated-Facility Loads*, Table 1: *Thermal Conductivity of Cold Storage Insulation*.

### Texto del curso

**Çengel & Ghajar, Heat and Mass Transfer: Fundamentals & Applications, 6th edition.**

El informe debe contrastar explícitamente las propiedades genéricas utilizadas con los valores disponibles en el texto del curso. Un ejemplo importante es EPS:

- AISLA-OPT / ASHRAE: `k = 0.037 W/m·K`;
- tabla A-6 de Çengel: valor de referencia cercano a `0.040 W/m·K`.

La diferencia debe explicarse como consecuencia de distintas fuentes y condiciones de referencia, no como una contradicción matemática.

---

## 33. Estado de la versión

La V4.4 cerró el modelo físico tras la auditoría final. La V4.5 reorganizó el código, agregó los análisis
de la sección 19b y renovó la interfaz sin modificar ecuaciones ni resultados. Los cambios están en
`CHANGELOG.md`.

La auditoría de la V4.4 confirmó:

- N1–N7 resueltos;
- V1–V7 aprobadas;
- núcleo térmico sin regresiones;
- resultados numéricos consistentes con la V4.3 corregida;
- cero excepciones en los escenarios probados;
- ausencia de hallazgos críticos o importantes nuevos.

A partir de esta versión, el trabajo restante pertenece a:

- documentación;
- datos comerciales;
- caso de estudio;
- informe;
- presentación.

Cualquier cambio futuro al modelo físico debe acompañarse de una prueba de validación nueva y conservar
V1–V7.

---

## 34. Idea central para recordar

AISLA-OPT no intenta responder:

> “¿Cuál es el espesor perfecto para cualquier cuarto refrigerado?”

Responde una pregunta más rigurosa:

> **“Bajo estas condiciones térmicas, económicas y comerciales documentadas, ¿cómo se comportan las alternativas de aislamiento disponibles y cuál presenta el menor costo de ciclo de vida dentro del conjunto evaluado?”**

Ese es el alcance correcto de la herramienta.
