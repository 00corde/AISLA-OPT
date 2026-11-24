from __future__ import annotations

from datetime import date
from pathlib import Path
import math

import pandas as pd
import streamlit as st

from aisla_opt_v2 import (
    GeometriaCuarto,
    Superficie,
    CondicionesInterior,
    MaterialAislante,
    SistemaRefrigeracion,
    Economia,
    evaluar_alternativa,
)
from datos_tecnicos import MATERIALES_ASHRAE, ASHRAE_SOURCE_NAME, ASHRAE_SOURCE_URL, ASHRAE_SOURCE_NOTE
from seleccion_ingenieril import (
    espesor_minimo_termico_mm,
    primer_comercial_que_cumple,
    seleccionar_economicamente,
    inventario_material,
    evaluar_producto,
)
from mercado_cr import consultar_eps

CAT_PATH = Path(__file__).resolve().parent / "catalogo_comercial_cr.csv"
CAT_COLS = [
    "Activo","Sistema","Material","Proveedor","Producto","Espesor_mm",
    "Precio_CRC_m2","k_W_mK","Densidad_kg_m3","IVA_incluido","Condicion_precio",
    "Estado_precio","Fecha","Fuente"
]


def cargar_catalogo():
    df = pd.read_csv(CAT_PATH)
    for c in CAT_COLS:
        if c not in df.columns:
            df[c] = None
    return df[CAT_COLS]


def guardar_catalogo(df):
    x = df.copy()
    # Normaliza fechas legibles por humanos/Excel a ISO cuando sea posible.
    def fecha_iso(valor):
        if pd.isna(valor) or not str(valor).strip():
            return ""
        dt = pd.to_datetime(str(valor).strip(), errors="coerce")
        return dt.date().isoformat() if not pd.isna(dt) else str(valor).strip()

    x["Fecha"] = x["Fecha"].map(fecha_iso)
    x[CAT_COLS].to_csv(CAT_PATH, index=False, encoding="utf-8-sig", lineterminator="\n")


def limpiar_catalogo(df):
    x = df.copy()
    x["Activo"] = x["Activo"].fillna(False).astype(bool)
    x["Espesor_mm"] = pd.to_numeric(x["Espesor_mm"], errors="coerce")
    x["Precio_CRC_m2"] = pd.to_numeric(x["Precio_CRC_m2"], errors="coerce")
    x["k_W_mK"] = pd.to_numeric(x["k_W_mK"], errors="coerce")
    x["Densidad_kg_m3"] = pd.to_numeric(x["Densidad_kg_m3"], errors="coerce")
    return x


def upsert(base, rows, solo_precio_si_existe=False):
    """Upsert sin mezclar espesores; una actualización web puede tocar solo precio/fecha/fuente."""
    df = base.copy()
    for row in rows:
        e_new = pd.to_numeric(pd.Series([row.get("Espesor_mm")]), errors="coerce").iloc[0]
        e_df = pd.to_numeric(df["Espesor_mm"], errors="coerce")
        same_e = (e_df - float(e_new)).abs() < 1e-9 if pd.notna(e_new) else e_df.isna()
        mask = (
            (df["Sistema"].astype(str) == str(row.get("Sistema","")))
            & (df["Material"].astype(str) == str(row.get("Material","")))
            & (df["Proveedor"].astype(str) == str(row.get("Proveedor","")))
            & (df["Producto"].astype(str) == str(row.get("Producto","")))
            & same_e
        )
        if mask.any():
            idx = df[mask].index[0]
            cols = ["Precio_CRC_m2", "Estado_precio", "Fecha", "Fuente"] if solo_precio_si_existe else CAT_COLS
            for c in cols:
                if c in row:
                    df.at[idx, c] = row[c]
        else:
            df = pd.concat(
                [df, pd.DataFrame([{c: row.get(c) for c in CAT_COLS}])],
                ignore_index=True
            )
    return df


def material_obj(nombre, override=None):
    k = MATERIALES_ASHRAE[nombre]["k"] if override is None else float(override)
    return MaterialAislante(nombre, k, 0.0, (1.0,))


def formato_mm(x):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "—"
    return f"{x:.1f} mm"


st.set_page_config(page_title="AISLA-OPT", page_icon="❄️", layout="wide")
st.markdown("""
<style>
.block-container{padding-top:1.4rem;padding-bottom:3rem;max-width:1500px}
.hero{font-size:2.45rem;font-weight:800;letter-spacing:.01em}
.sub{opacity:.72;margin-top:-.25rem;margin-bottom:1rem}
.note{padding:.8rem 1rem;border-left:4px solid #4f8bf9;background:rgba(79,139,249,.08);border-radius:8px}
.muted{opacity:.7}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero">AISLA-OPT</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub">Dimensionamiento térmico y selección comercial de aislamiento para cuartos refrigerados</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Datos de diseño")

    st.subheader("Geometría")
    largo = st.number_input("Largo exterior de referencia [m]", min_value=0.1, value=4.0, step=0.1)
    ancho = st.number_input("Ancho exterior de referencia [m]", min_value=0.1, value=3.0, step=0.1)
    alto = st.number_input("Alto exterior de referencia [m]", min_value=0.1, value=2.5, step=0.1)

    st.caption("Las dimensiones se interpretan como exteriores de la envolvente para el cálculo de área de transmisión.")

    st.subheader("Temperaturas")
    t_int = st.number_input("Interior objetivo [°C]", value=5.0, step=0.5)
    t_ext_crit = st.number_input("Exterior crítica [°C]", value=35.0, step=0.5)
    t_ext_op = st.number_input("Exterior equivalente de operación [°C]", value=28.0, step=0.5)
    t_techo_crit = st.number_input("Techo crítica equivalente [°C]", value=38.0, step=0.5)
    t_techo_op = st.number_input("Techo equivalente de operación [°C]", value=30.0, step=0.5)
    t_piso_crit = st.number_input("Piso crítica [°C]", value=25.0, step=0.5)
    t_piso_op = st.number_input("Piso equivalente de operación [°C]", value=24.0, step=0.5)
    st.caption("Para estimar energía anual, interprete las temperaturas de operación como condiciones medias representativas ponderadas en el tiempo; las temperaturas críticas se reservan para carga pico.")

    st.subheader("Refrigeración")
    cop = st.number_input("COP efectivo promedio", min_value=0.1, value=3.0, step=0.1, help="COP representativo para estimar la energía atribuible a la carga de transmisión.")
    margen_pct = st.slider("Margen de diseño [%]", 0, 50, 10)
    usar_cap = st.checkbox("Aplicar restricción de capacidad disponible para transmisión", value=False)
    cap_kw = st.number_input(
        "Capacidad disponible para la envolvente [kW]",
        min_value=0.1, value=2.5, step=0.1, disabled=not usar_cap,
        help="Si parte de una capacidad total de equipo, reste antes infiltración, producto, iluminación y otras cargas."
    )
    st.caption("Esta restricción es opcional. No representa por sí sola la capacidad total requerida por una cámara frigorífica.")

    st.subheader("Economía")
    costo_kwh = st.number_input("Electricidad [CRC/kWh]", min_value=0.0, value=120.0, step=1.0)
    horas = st.number_input("Horas/año con el recinto a la temperatura objetivo", min_value=0.0, max_value=8760.0, value=8760.0, step=100.0, help="Use 8760 h/año para operación continua; reduzca el valor solo si el recinto no se mantiene frío todo el año.")
    vida = st.number_input("Vida útil [años]", min_value=1, value=10, step=1)
    descuento = st.number_input("Tasa de descuento real [%]", min_value=0.0, value=5.0, step=0.5)

    with st.expander("Parámetros térmicos avanzados"):
        st.caption("Los coeficientes h son parámetros efectivos de película y deben ajustarse a las condiciones del caso. Los valores por defecto son referencias de trabajo editables, no constantes universales.")
        hi = st.number_input("h interior [W/m²·K]", min_value=0.1, value=9.1, step=0.1)
        ho_pared = st.number_input("h exterior paredes [W/m²·K]", min_value=0.1, value=9.1, step=0.1)
        ho_techo = st.number_input("h exterior techo [W/m²·K]", min_value=0.1, value=9.1, step=0.1)
        ho_piso = st.number_input("h equivalente piso [W/m²·K]", min_value=0.1, value=9.1, step=0.1)
        r_pared = st.number_input("R'' adicional paredes [m²·K/W]", min_value=0.0, value=0.00, step=0.01)
        r_techo = st.number_input("R'' adicional techo [m²·K/W]", min_value=0.0, value=0.00, step=0.01)
        r_piso = st.number_input("R'' adicional piso [m²·K/W]", min_value=0.0, value=0.00, step=0.01)
        st.caption("R'' adicional representa capas conocidas aparte del aislamiento seleccionado. Para paneles prefabricados, no agregue resistencia arbitraria de las láminas metálicas.")

st.markdown(
    '<div class="note"><b>Cómo decide AISLA-OPT:</b> evalúa la transmisión térmica de la envolvente para productos comerciales documentados. '
    'Si el usuario define una capacidad disponible exclusivamente para transmisión, también calcula el espesor continuo que satisface esa restricción. '
    'Con precios comparables identifica la <b>mejor alternativa comercial evaluada</b> por costo de ciclo de vida; no afirma un óptimo global fuera del catálogo estudiado.</div>',
    unsafe_allow_html=True,
)

with st.expander("Problema de diseño y alcance del modelo", expanded=False):
    st.markdown(
        """
**Problema que resuelve.** La selección de aislamiento no depende solo de la conductividad térmica:
el espesor calculado puede no existir comercialmente y una opción más barata inicialmente puede resultar
más costosa por consumo eléctrico durante su vida útil. AISLA-OPT integra cálculo térmico,
disponibilidad comercial y costo de ciclo de vida para apoyar esa decisión.

**Alcance térmico**
- Recinto rectangular en estado estacionario y dimensiones exteriores de referencia.
- Un mismo material y espesor uniforme se aplica a paredes, techo y piso en cada alternativa.
- Conducción a través del aislamiento y convección interior/exterior.
- Carga por **transmisión a través de la envolvente**; no es la carga frigorífica total.
- Propiedades base tomadas de ASHRAE; una ficha técnica específica puede sustituir `k`.

**Fuera del alcance actual**
- Infiltración por puertas.
- Cargas de producto, personas, iluminación y deshielo.
- Dimensionamiento completo del sistema frigorífico.
- Modelo detallado de conducción hacia el terreno; el piso usa una condición equivalente definida por el usuario.
- Costos que no estén incluidos explícitamente en los precios comerciales registrados.

AISLA-OPT es una herramienta de **selección termo-económica del aislamiento de la envolvente**,
no un software completo de cálculo de carga frigorífica.
        """
    )

st.subheader("1. Solución comercial")

sistema = st.radio(
    "Tipo de solución a comparar",
    ["Panel frigorífico completo", "Aislante independiente"],
    horizontal=True,
)

if sistema == "Panel frigorífico completo":
    opciones_default = ["Poliuretano (PU)", "Poliisocianurato (PIR)"]
    opciones = ["Poliuretano (PU)", "Poliisocianurato (PIR)"]
    st.caption("Comparación entre sistemas de panel para cuarto frío. Evita mezclar el precio de un panel terminado con el de una lámina aislante desnuda.")
else:
    opciones_default = ["Poliestireno expandido (EPS)", "Poliestireno extruido (XPS)"]
    opciones = ["Poliuretano (PU)", "Poliestireno extruido (XPS)", "Poliestireno expandido (EPS)", "Corcho", "Vidrio celular"]
    st.caption("Comparación de materiales aislantes independientes. Los productos sin precio pueden dimensionarse técnicamente, pero no rankearse económicamente.")

seleccion = st.multiselect(
    "Materiales a estudiar",
    options=opciones,
    default=opciones_default,
)

with st.expander("Propiedades térmicas ASHRAE", expanded=False):
    rows = []
    for nombre in seleccion:
        d = MATERIALES_ASHRAE[nombre]
        rows.append({
            "Material": nombre,
            "k de diseño [W/m·K]": d["k"],
            "Valor ASHRAE": d["k_texto"],
            "Criterio": d["nota"],
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(f"Fuente técnica base: {ASHRAE_SOURCE_NAME}. {ASHRAE_SOURCE_NOTE} Una ficha técnica específica puede sustituir el valor genérico. El acceso web al Handbook puede requerir suscripción institucional.")
    st.link_button("Referencia ASHRAE", ASHRAE_SOURCE_URL)

usar_override = st.checkbox("Usar k de una ficha técnica específica", value=False)
overrides = {}
if usar_override:
    with st.expander("Conductividades personalizadas", expanded=True):
        for nombre in seleccion:
            overrides[nombre] = st.number_input(
                f"{nombre} · k [W/m·K]",
                min_value=0.01,
                max_value=0.20,
                value=float(MATERIALES_ASHRAE[nombre]["k"]),
                step=0.001,
                format="%.3f",
                key=f"k_override_{nombre}",
            )

materiales = {
    nombre: material_obj(nombre, overrides.get(nombre) if usar_override else None)
    for nombre in seleccion
}

st.subheader("2. Catálogo comercial")

if "catalogo_v4" not in st.session_state:
    st.session_state.catalogo_v4 = cargar_catalogo()

catalogo = limpiar_catalogo(st.session_state.catalogo_v4)
cat_sistema = catalogo[(catalogo["Activo"]) & (catalogo["Sistema"] == sistema)].copy()
st.caption("El catálogo incluye referencias iniciales del mercado costarricense y puede ampliarse con cotizaciones documentadas. No pretende ser un censo exhaustivo de proveedores.")

# Resumen comercial sin exponer la base completa de entrada.
m1, m2, m3 = st.columns(3)
m1.metric("Productos documentados", int(len(cat_sistema)))
m2.metric("Con precio en CRC/m²", int(cat_sistema["Precio_CRC_m2"].notna().sum()))
m3.metric("Requieren cotización", int(cat_sistema["Precio_CRC_m2"].isna().sum()))

with st.expander("Registrar una cotización", expanded=False):
    st.caption("Ideal para las cotizaciones de Aislamart u otro proveedor. Ingrese siempre el precio ya normalizado a CRC/m².")
    q1, q2 = st.columns(2)
    with q1:
        q_material = st.selectbox("Material", seleccion if seleccion else opciones, key="q_mat")
        q_proveedor = st.text_input("Proveedor", value="Aislamart Costa Rica")
        q_producto = st.text_input("Producto / descripción", value="")
    with q2:
        q_espesor = st.number_input("Espesor [mm]", min_value=0.1, value=60.0, step=1.0)
        q_precio = st.number_input("Precio [CRC/m²]", min_value=0.0, value=0.0, step=100.0)
        q_fecha = st.date_input("Fecha de cotización", value=date.today())

    q3, q4 = st.columns(2)
    with q3:
        q_k_txt = st.text_input("k de la ficha técnica [W/m·K] (opcional)", value="", help="Si se deja vacío se usa el valor técnico base del material.")
        q_densidad_txt = st.text_input("Densidad [kg/m³] (opcional)", value="")
    with q4:
        q_iva = st.selectbox("IVA en el precio", ["No indicado", "Sí", "No"])
        q_condicion = st.text_input("Condición del precio", value="Solo material; verificar instalación/flete")

    q_fuente = st.text_input("Referencia / contacto / URL", value="")
    if st.button("Guardar cotización", use_container_width=True):
        if not q_producto.strip() or q_precio <= 0:
            st.error("Ingrese descripción del producto y un precio mayor que cero.")
        else:
            try:
                q_k = float(q_k_txt.replace(",", ".")) if q_k_txt.strip() else None
                q_densidad = float(q_densidad_txt.replace(",", ".")) if q_densidad_txt.strip() else None
                if q_k is not None and not (0.01 <= q_k <= 0.20):
                    raise ValueError("k debe estar entre 0.01 y 0.20 W/m·K; revise unidades si queda fuera de ese rango")
                if q_densidad is not None and q_densidad <= 0:
                    raise ValueError("la densidad debe ser mayor que cero")
            except ValueError as exc:
                st.error(f"Dato técnico inválido: {exc}")
                st.stop()

            row = {
                "Activo": True,
                "Sistema": sistema,
                "Material": q_material,
                "Proveedor": q_proveedor.strip() or "Proveedor",
                "Producto": q_producto.strip(),
                "Espesor_mm": float(q_espesor),
                "Precio_CRC_m2": float(q_precio),
                "k_W_mK": q_k,
                "Densidad_kg_m3": q_densidad,
                "IVA_incluido": q_iva,
                "Condicion_precio": q_condicion.strip(),
                "Estado_precio": "Cotización ingresada",
                "Fecha": q_fecha.isoformat(),
                "Fuente": q_fuente.strip(),
            }
            st.session_state.catalogo_v4 = upsert(st.session_state.catalogo_v4, [row])
            guardar_catalogo(st.session_state.catalogo_v4)
            st.success("Cotización guardada.")
            st.rerun()

if sistema == "Aislante independiente":
    with st.expander("Actualizar precios web compatibles", expanded=False):
        st.caption("Función opcional. Solo propone precios que pueden convertirse responsablemente a SI y CRC/m². Si un sitio bloquea la consulta, AISLA-OPT conserva el catálogo existente.")
        if st.button("Consultar mercado", use_container_width=True):
            with st.spinner("Consultando proveedores..."):
                st.session_state["mercado_v4"] = consultar_eps()

        data = st.session_state.get("mercado_v4")
        if data:
            for msg in data.get("mensajes", []):
                st.write("• " + msg)

            ofertas = data.get("ofertas", [])
            if ofertas:
                prev = pd.DataFrame(ofertas)
                prev.insert(0, "Aplicar", True)
                edited = st.data_editor(
                    prev,
                    hide_index=True,
                    use_container_width=True,
                    disabled=[c for c in prev.columns if c != "Aplicar"],
                    column_config={
                        "Aplicar": st.column_config.CheckboxColumn("Aplicar", default=True),
                        "Espesor_mm": st.column_config.NumberColumn("Espesor [mm]", format="%.1f"),
                        "Precio_CRC_m2": st.column_config.NumberColumn("Precio [CRC/m²]", format="₡ %.2f"),
                        "Fuente": st.column_config.LinkColumn("Fuente"),
                    },
                    key="market_preview_v4",
                )
                if st.button("Aplicar precios seleccionados", use_container_width=True):
                    rows = edited[edited["Aplicar"] == True].drop(columns=["Aplicar"]).to_dict("records")
                    st.session_state.catalogo_v4 = upsert(st.session_state.catalogo_v4, rows, solo_precio_si_existe=True)
                    guardar_catalogo(st.session_state.catalogo_v4)
                    st.success("Catálogo actualizado.")
                    st.rerun()
else:
    st.caption("La actualización web automática disponible corresponde a EPS como aislante independiente. Para paneles frigoríficos use cotizaciones directas y documentadas.")

with st.expander("Administrar catálogo completo", expanded=False):
    edited_cat = st.data_editor(
        st.session_state.catalogo_v4,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Activo": st.column_config.CheckboxColumn("Activo", default=True),
            "Sistema": st.column_config.SelectboxColumn("Sistema", options=["Panel frigorífico completo","Aislante independiente"]),
            "Material": st.column_config.SelectboxColumn("Material", options=list(MATERIALES_ASHRAE.keys())),
            "Espesor_mm": st.column_config.NumberColumn("Espesor [mm]", min_value=0.1, format="%.1f"),
            "Precio_CRC_m2": st.column_config.NumberColumn("Precio [CRC/m²]", min_value=0.0, format="₡ %.2f"),
            "k_W_mK": st.column_config.NumberColumn("k ficha [W/m·K]", min_value=0.01, max_value=0.20, format="%.3f"),
            "Densidad_kg_m3": st.column_config.NumberColumn("Densidad [kg/m³]", min_value=0.1, format="%.1f"),
            "IVA_incluido": st.column_config.SelectboxColumn("IVA", options=["No indicado","Sí","No"]),
            "Fuente": st.column_config.LinkColumn("Fuente"),
        },
        key="catalog_admin_v4",
    )
    st.session_state.catalogo_v4 = edited_cat
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Guardar catálogo completo", use_container_width=True):
            k_editor = pd.to_numeric(edited_cat["k_W_mK"], errors="coerce")
            invalidos = k_editor.notna() & ~k_editor.between(0.01, 0.20, inclusive="both")
            if invalidos.any():
                st.error("Hay valores de k fuera del rango 0.01–0.20 W/m·K. Revise unidades antes de guardar.")
            else:
                guardar_catalogo(edited_cat)
                st.success("Catálogo guardado.")
    with c2:
        csv_data = edited_cat.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Descargar catálogo CSV", csv_data, "catalogo_comercial_cr.csv", "text/csv", use_container_width=True)

st.subheader("3. Evaluación térmica y selección")

calcular = st.button("Calcular y seleccionar", type="primary", use_container_width=True)

if calcular:
    try:
        if not materiales:
            raise ValueError("Seleccione al menos un material.")

        temp_pairs = [
            ("paredes crítica", t_ext_crit), ("paredes operación", t_ext_op),
            ("techo crítica", t_techo_crit), ("techo operación", t_techo_op),
            ("piso crítica", t_piso_crit), ("piso operación", t_piso_op),
        ]
        no_cooling = [nombre for nombre, text in temp_pairs if text <= t_int]
        if no_cooling:
            st.warning(
                "Revise las temperaturas: en " + ", ".join(no_cooling) +
                " la temperatura exterior/equivalente no supera la interior. El modelo permite el valor, "
                "pero esa superficie puede representar pérdida de calor y no una carga de refrigeración positiva."
            )

        g = GeometriaCuarto(largo, ancho, alto)
        interior = CondicionesInterior(t_int)
        paredes = Superficie("Paredes", hi, ho_pared, r_pared, t_ext_crit, t_ext_op)
        techo = Superficie("Techo", hi, ho_techo, r_techo, t_techo_crit, t_techo_op)
        piso = Superficie("Piso", hi, ho_piso, r_piso, t_piso_crit, t_piso_op)
        refrig = SistemaRefrigeracion(
            COP=cop,
            margen_diseno=1 + margen_pct/100,
            capacidad_equipo_existente_W=(cap_kw*1000 if usar_cap else None),
        )
        econ = Economia(costo_kwh, horas, int(vida), descuento/100)

        catalogo = limpiar_catalogo(st.session_state.catalogo_v4)
        k_catalogo = catalogo["k_W_mK"]
        k_invalidas = k_catalogo.notna() & ~k_catalogo.between(0.01, 0.20, inclusive="both")
        if k_invalidas.any():
            raise ValueError("El catálogo contiene valores de k fuera del rango 0.01–0.20 W/m·K. Revise unidades antes de calcular.")

        requeridos = {}
        resumen = []

        for nombre, mat in materiales.items():
            e_req = espesor_minimo_termico_mm(
                g, interior, paredes, techo, piso, mat, refrig, econ
            )
            requeridos[nombre] = e_req

            if e_req is None:
                e_text = "No aplicado"
                first = None
            elif math.isinf(e_req):
                e_text = "> 400 mm"
                first = None
            else:
                e_text = f"{e_req:.1f} mm"
                first = primer_comercial_que_cumple(
                    catalogo, nombre, sistema, e_req
                )

            if first is None:
                resumen.append({
                    "Material": nombre,
                    "Límite continuo por capacidad": e_text,
                    "Límite por capacidad [mm]": None if (e_req is None or math.isinf(e_req)) else float(e_req),
                    "Primer comercial que cubre": "—",
                    "Espesor comercial [mm]": None,
                    "Margen comercial [mm]": None,
                    "Margen sobre mínimo [%]": None,
                    "Sensibilidad comercial": "—",
                    "Proveedor": "—",
                    "Precio": "—",
                    "Estado": (
                        "Restricción de capacidad no activada" if e_req is None else
                        "No existe producto documentado que cubra" if not math.isinf(e_req) else
                        "No cumple hasta 400 mm"
                    ),
                })
            else:
                e_com = float(first["Espesor_mm"])
                e_req_num = None if (e_req is None or math.isinf(e_req)) else float(e_req)
                margen = None if e_req_num is None else max(0.0, e_com - e_req_num)
                sobredim = None if (e_req_num is None or e_req_num <= 0) else 100.0 * margen / e_req_num

                if margen is None:
                    sensibilidad = "—"
                else:
                    # Poco margen antes de superar este tamaño comercial:
                    # una pequeña variación del diseño puede obligar al siguiente espesor disponible.
                    limite_cercano = max(2.0, 0.05 * e_com)
                    limite_moderado = max(5.0, 0.15 * e_com)
                    if margen <= limite_cercano:
                        sensibilidad = "⚠ Cerca del salto"
                    elif margen <= limite_moderado:
                        sensibilidad = "Margen moderado"
                    else:
                        sensibilidad = "Margen amplio"

                p = first.get("Precio_CRC_m2")
                precio_txt = "Cotización requerida" if pd.isna(p) else f"₡{float(p):,.0f}/m²"
                resumen.append({
                    "Material": nombre,
                    "Límite continuo por capacidad": e_text,
                    "Límite por capacidad [mm]": e_req_num,
                    "Primer comercial que cubre": f"{e_com:.1f} mm",
                    "Espesor comercial [mm]": e_com,
                    "Margen comercial [mm]": margen,
                    "Margen sobre mínimo [%]": sobredim,
                    "Sensibilidad comercial": sensibilidad,
                    "Proveedor": first.get("Proveedor","—"),
                    "Precio": precio_txt,
                    "Estado": first.get("Estado_precio",""),
                })

        st.success("Dimensionamiento completado.")

        df_resumen = pd.DataFrame(resumen)
        if usar_cap:
            st.subheader("Del cálculo al componente comercial")
            st.caption("El límite continuo por capacidad usa la k genérica seleccionada para cada material. La factibilidad económica de cada producto se vuelve a comprobar con su k de ficha cuando está disponible.")

            columnas_principales = [
                "Material",
                "Límite continuo por capacidad",
                "Primer comercial que cubre",
                "Margen comercial [mm]",
                "Margen sobre mínimo [%]",
                "Sensibilidad comercial",
                "Proveedor",
                "Precio",
            ]

            st.dataframe(
                df_resumen[columnas_principales].style.format({
                    "Margen comercial [mm]": lambda x: "—" if pd.isna(x) else f"{x:.1f}",
                    "Margen sobre mínimo [%]": lambda x: "—" if pd.isna(x) else f"{x:.0f} %",
                }),
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "Cuando se activa la restricción opcional de capacidad para transmisión, el margen comercial compara el límite continuo calculado "
                "con el primer tamaño documentado que lo cubre. Sin esa restricción no se inventa un espesor mínimo."
            )

            comparables = df_resumen.dropna(
                subset=["Límite por capacidad [mm]", "Espesor comercial [mm]"]
            ).copy()

            if not comparables.empty:
                st.markdown("#### Límite continuo vs. primer tamaño comercial")
                chart_df = comparables.set_index("Material")[
                    ["Límite por capacidad [mm]", "Espesor comercial [mm]"]
                ]
                st.bar_chart(chart_df)

                cerca = comparables[
                    comparables["Sensibilidad comercial"] == "⚠ Cerca del salto"
                ]
                if not cerca.empty:
                    nombres = ", ".join(cerca["Material"].astype(str))
                    st.warning(
                        "Atención de diseño: " + nombres +
                        " queda muy cerca de un límite comercial. "
                        "Una pequeña variación de carga térmica podría obligar a seleccionar el siguiente espesor disponible."
                    )
                else:
                    st.info(
                        "Con las condiciones actuales, ningún material seleccionado queda peligrosamente cerca "
                        "del límite de su espesor comercial elegido."
                    )

        # Economic comparison among all priced products that meet the theoretical requirement.
        df_econ, mejor = seleccionar_economicamente(
            g, interior, paredes, techo, piso,
            materiales, refrig, econ, catalogo, sistema, requeridos
        )

        if mejor is not None:
            st.subheader("Mejor alternativa comercial evaluada")

            metric_a, metric_b, metric_c, metric_d = st.columns(4)
            metric_a.metric("Material", mejor["Material"])
            metric_b.metric("Producto", mejor["Producto"])
            metric_c.metric("Espesor", f'{mejor["Espesor [mm]"]:.1f} mm')
            metric_d.metric("Proveedor", mejor["Proveedor"])

            metric_e, metric_f, metric_g, metric_h = st.columns(4)
            metric_e.metric("Carga pico de transmisión", f'{mejor["Carga pico transmisión [kW]"]:.2f} kW')
            metric_f.metric("Energía anual por transmisión", f'{mejor["Energía transmisión [kWh/año]"]:,.0f} kWh')
            metric_g.metric("Costo aislamiento", f'₡{mejor["Costo aislamiento [CRC]"]:,.0f}')
            metric_h.metric("Costo total VP", f'₡{mejor["Costo total VP [CRC]"]:,.0f}')

            st.caption(
                "Esta es la alternativa de menor costo total únicamente dentro de los productos comerciales con precio comparable que fueron evaluados. "
                "No se presenta como óptimo global fuera del catálogo disponible."
            )

            same_material = df_econ[df_econ["Material"] == mejor["Material"]].copy()
            e_best = float(mejor["Espesor [mm]"])
            e_max = float(same_material["Espesor [mm]"].max())
            e_min = float(same_material["Espesor [mm]"].min())
            n_sizes = int(same_material["Espesor [mm]"].nunique())

            if n_sizes < 2:
                st.warning(
                    "Solo existe un espesor con precio comparable para el material seleccionado. "
                    "No hay rango suficiente para afirmar que ese espesor sea un mínimo económico robusto."
                )
            elif abs(e_best - e_max) < 1e-9:
                st.warning(
                    "La mejor alternativa evaluada está en el espesor máximo con precio disponible para este material. "
                    "El costo podría seguir disminuyendo con espesores mayores; el catálogo está limitando la conclusión."
                )
            elif abs(e_best - e_min) < 1e-9:
                st.info(
                    "La mejor alternativa evaluada coincide con el menor espesor con precio disponible para este material. "
                    "Con las condiciones económicas actuales, el ahorro energético de espesores mayores no compensa su mayor costo inicial dentro del catálogo."
                )
            else:
                st.success(
                    "La mejor alternativa evaluada se encuentra dentro del rango comercial con precio disponible, no en uno de sus extremos."
                )

            iva_vals = df_econ["IVA"].fillna("No indicado").astype(str).str.strip().replace("", "No indicado")
            if (iva_vals == "No indicado").any() or iva_vals.nunique() > 1:
                st.warning(
                    "Los precios evaluados no están todos en una base tributaria homogénea (IVA incluido, excluido o no indicado). "
                    "La comparación económica es preliminar hasta normalizar esa condición."
                )

            st.subheader("Alternativas comerciales evaluadas con precio")
            columnas_econ = [
                "Material","Proveedor","Producto","Espesor [mm]","Precio [CRC/m²]","k usada [W/m·K]",
                "Carga pico transmisión [kW]","Transmisión + margen [kW]","Energía transmisión [kWh/año]",
                "Costo aislamiento [CRC]","Costo energía VP [CRC]","Costo total VP [CRC]",
                "IVA","Condición","Fecha","Fuente"
            ]
            st.dataframe(
                df_econ.sort_values("Costo total VP [CRC]")[columnas_econ].style.format({
                    "Espesor [mm]": "{:.1f}",
                    "Precio [CRC/m²]": "₡{:,.2f}",
                    "k usada [W/m·K]": "{:.3f}",
                    "Carga pico transmisión [kW]": "{:.3f}",
                    "Transmisión + margen [kW]": "{:.3f}",
                    "Energía transmisión [kWh/año]": "{:,.0f}",
                    "Costo aislamiento [CRC]": "₡{:,.0f}",
                    "Costo energía VP [CRC]": "₡{:,.0f}",
                    "Costo total VP [CRC]": "₡{:,.0f}",
                }),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("#### Costo de ciclo de vida dentro del catálogo evaluado")
            st.scatter_chart(
                df_econ,
                x="Espesor [mm]",
                y="Costo total VP [CRC]",
                color="Material",
            )
        else:
            hay_precio = False
            for nombre in materiales:
                inv = inventario_material(catalogo, nombre, sistema)
                precios = pd.to_numeric(inv["Precio_CRC_m2"], errors="coerce") if not inv.empty else pd.Series(dtype=float)
                if (precios > 0).any():
                    hay_precio = True
                    break

            if usar_cap and hay_precio:
                st.warning(
                    "No existen productos comerciales con precio documentado que satisfagan la restricción de capacidad seleccionada. "
                    "Aumente la capacidad disponible para transmisión o incorpore productos de mayor desempeño/espesor."
                )
            else:
                st.warning(
                    "No hay productos con precios normalizados y comparables en CRC/m² para realizar el análisis económico. "
                    "La evaluación térmica sigue disponible; agregue cotizaciones documentadas sin modificar el modelo físico."
                )

        # Continuous thermal behavior remains a physics graph, not a market graph.
        curves = []
        for nombre, mat in materiales.items():
            for e_mm in range(10, 201, 5):
                r = evaluar_alternativa(g, interior, paredes, techo, piso, mat, float(e_mm), refrig, econ)
                curves.append({
                    "Material": nombre,
                    "Espesor [mm]": e_mm,
                    "Carga pico transmisión [kW]": r.carga_critica_total_W/1000,
                })

        st.subheader("Comportamiento térmico continuo")
        dc = pd.DataFrame(curves)
        st.line_chart(
            dc.pivot(index="Espesor [mm]", columns="Material", values="Carga pico transmisión [kW]")
        )

    except Exception as exc:
        st.error(f"No fue posible completar el cálculo: {exc}")
else:
    st.caption(
        "El modelo térmico define la transmisión; el catálogo documenta alternativas reales. "
        "AISLA-OPT compara únicamente lo que puede justificar con datos de entrada y precios disponibles."
    )
