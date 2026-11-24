"""Pestaña Catálogo: disponibilidad, cotizaciones con conversión de unidades, precios web y edición."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from aisla_opt import catalogo as cat
from aisla_opt import formato
from aisla_opt.materiales import (
    MATERIALES_ASHRAE,
    MATERIALES_POR_SISTEMA,
    SISTEMA_AISLANTE,
    SISTEMAS,
    K_MAXIMA_W_mK,
    K_MINIMA_W_mK,
)
from aisla_opt.mercado import consultar_eps

from .estado import CLAVE_CATALOGO

UNIDADES_PRECIO = {
    "m2": "Por metro cuadrado (CRC/m²)",
    "lamina": "Por lámina o panel",
    "paquete": "Por paquete de varias láminas",
}


@st.cache_data(ttl=3600, show_spinner=False)
def _consultar_eps_cacheado() -> dict:
    return consultar_eps()


def _guardar(df: pd.DataFrame, mensaje: str) -> None:
    st.session_state[CLAVE_CATALOGO] = df
    cat.guardar(df)
    st.toast(mensaje)


def _disponibilidad(catalogo: pd.DataFrame, sistema: str, materiales: list[str]) -> None:
    del_sistema = cat.normalizar(catalogo)
    del_sistema = del_sistema[del_sistema["Activo"] & (del_sistema["Sistema"] == sistema)]
    a, b, c = st.columns(3)
    a.metric("Productos documentados", len(del_sistema))
    b.metric("Con precio en CRC/m²", int((del_sistema["Precio_CRC_m2"] > 0).sum()))
    c.metric("Requieren cotización", int(del_sistema["Precio_CRC_m2"].isna().sum()))
    resumen = cat.resumen_por_material(catalogo, sistema, materiales)
    if not resumen.empty:
        st.dataframe(resumen, hide_index=True, width="stretch")
    st.caption("El catálogo trae referencias iniciales del mercado costarricense y se amplía con cotizaciones "
               "documentadas. No es un censo de proveedores.")


def _formulario_cotizacion(sistema: str, materiales: list[str]) -> None:
    with st.expander("Registrar una cotización", expanded=False):
        with st.form("cotizacion", clear_on_submit=False, border=False):
            col1, col2 = st.columns(2)
            with col1:
                opciones = list(MATERIALES_POR_SISTEMA[sistema])
                material = st.selectbox("Material", opciones,
                                        index=opciones.index(materiales[0]) if materiales else 0)
                proveedor = st.text_input("Proveedor", placeholder="Aislamart Costa Rica")
                producto = st.text_input("Producto o descripción", placeholder="Panel PIR 100 mm, lámina 0,5 mm")
                espesor = st.number_input("Espesor [mm]", min_value=0.1, value=60.0, step=1.0)
                fecha = st.date_input("Fecha de la cotización", value=date.today())
            with col2:
                unidad = st.selectbox("El precio cotizado es", list(UNIDADES_PRECIO),
                                      format_func=UNIDADES_PRECIO.get)
                precio = st.number_input("Precio cotizado [CRC]", min_value=0.0, value=0.0, step=100.0)
                d1, d2, d3 = st.columns(3)
                ancho = d1.number_input("Ancho [m]", min_value=0.0, value=1.22, step=0.01, format="%.2f")
                largo = d2.number_input("Largo [m]", min_value=0.0, value=2.44, step=0.01, format="%.2f")
                unidades = d3.number_input("Unidades/paquete", min_value=1, value=1, step=1)
                st.caption("Ancho, largo y unidades solo se usan si el precio no viene por m². Use las "
                           "dimensiones documentadas por el proveedor.")
                iva = st.selectbox("IVA en el precio", cat.OPCIONES_IVA)
                condicion = st.text_input("Condición del precio", value="Solo material; verificar instalación y flete")

            col3, col4 = st.columns(2)
            k_texto = col3.text_input("k de ficha técnica [W/m·K] (opcional)",
                                      help="Vacío: se usa la k genérica del material.")
            densidad_texto = col4.text_input("Densidad [kg/m³] (opcional)")
            fuente = st.text_input("Referencia, contacto o URL")
            enviado = st.form_submit_button("Guardar cotización", type="primary")

        if not enviado:
            return
        try:
            if not producto.strip():
                raise ValueError("Escriba la descripción del producto.")
            precio_m2 = cat.precio_por_m2(precio, unidad, ancho, largo, int(unidades))
            k = float(k_texto.replace(",", ".")) if k_texto.strip() else None
            densidad = float(densidad_texto.replace(",", ".")) if densidad_texto.strip() else None
            if k is not None and not (K_MINIMA_W_mK <= k <= K_MAXIMA_W_mK):
                raise ValueError("k debe estar entre 0,01 y 0,20 W/m·K. Revise las unidades.")
            if densidad is not None and densidad <= 0:
                raise ValueError("La densidad debe ser mayor que cero.")
        except ValueError as error:
            st.error(f"No se guardó la cotización: {error}")
            return

        fila = {
            "Activo": True, "Sistema": sistema, "Material": material,
            "Proveedor": proveedor.strip() or "Proveedor sin nombre", "Producto": producto.strip(),
            "Espesor_mm": float(espesor), "Precio_CRC_m2": precio_m2, "k_W_mK": k, "Densidad_kg_m3": densidad,
            "IVA_incluido": iva, "Condicion_precio": condicion.strip(), "Estado_precio": "Cotización ingresada",
            "Fecha": fecha.isoformat(), "Fuente": fuente.strip(),
        }
        _guardar(cat.upsert(st.session_state[CLAVE_CATALOGO], [fila]),
                 f"Cotización guardada: {formatear_precio(precio_m2)}")
        st.rerun()


def formatear_precio(precio_m2: float) -> str:
    return f"{formato.colones(precio_m2)}/m²"


def _precios_web() -> None:
    with st.expander("Actualizar precios web de EPS", expanded=False):
        st.caption("Consulta opcional a Elky María y EPA. Solo propone precios que se pueden convertir a CRC/m² "
                   "con dimensiones documentadas. Si un sitio no responde, el catálogo no cambia.")
        if st.button("Consultar precios"):
            with st.spinner("Consultando proveedores…"):
                st.session_state["consulta_mercado"] = _consultar_eps_cacheado()
        datos = st.session_state.get("consulta_mercado")
        if not datos:
            return
        for mensaje in datos.get("mensajes", []):
            st.write(mensaje)
        ofertas = datos.get("ofertas", [])
        if not ofertas:
            return
        vista = pd.DataFrame(ofertas)
        vista.insert(0, "Aplicar", True)
        editada = st.data_editor(
            vista, hide_index=True, width="stretch",
            disabled=[c for c in vista.columns if c != "Aplicar"],
            column_config={
                "Espesor_mm": st.column_config.NumberColumn("Espesor [mm]", format="%.1f"),
                "Precio_CRC_m2": st.column_config.NumberColumn("Precio [₡/m²]", format="localized"),
                "Fuente": st.column_config.LinkColumn("Fuente"),
            },
            key="vista_precios_web",
        )
        if st.button("Aplicar precios marcados"):
            filas = editada[editada["Aplicar"]].drop(columns=["Aplicar"]).to_dict("records")
            _guardar(cat.upsert(st.session_state[CLAVE_CATALOGO], filas, solo_precio=True),
                     f"{len(filas)} precios actualizados")
            st.rerun()


def _editor_completo() -> None:
    with st.expander("Editar catálogo completo", expanded=False):
        editado = st.data_editor(
            st.session_state[CLAVE_CATALOGO],
            num_rows="dynamic", width="stretch", hide_index=True, key="editor_catalogo",
            column_config={
                "Activo": st.column_config.CheckboxColumn("Activo", default=True),
                "Sistema": st.column_config.SelectboxColumn("Sistema", options=list(SISTEMAS)),
                "Material": st.column_config.SelectboxColumn("Material", options=list(MATERIALES_ASHRAE)),
                "Espesor_mm": st.column_config.NumberColumn("Espesor [mm]", min_value=0.1, format="%.1f"),
                "Precio_CRC_m2": st.column_config.NumberColumn("Precio [₡/m²]", min_value=0.0, format="localized"),
                "k_W_mK": st.column_config.NumberColumn("k ficha [W/m·K]", min_value=K_MINIMA_W_mK,
                                                        max_value=K_MAXIMA_W_mK, format="%.3f"),
                "Densidad_kg_m3": st.column_config.NumberColumn("Densidad [kg/m³]", min_value=0.1, format="%.1f"),
                "IVA_incluido": st.column_config.SelectboxColumn("IVA", options=list(cat.OPCIONES_IVA)),
                "Fuente": st.column_config.LinkColumn("Fuente"),
            },
        )
        guardar, descargar, subir = st.columns(3)
        if guardar.button("Guardar cambios", type="primary", width="stretch"):
            if cat.k_fuera_de_rango(editado).any():
                st.error("Hay valores de k fuera de 0,01–0,20 W/m·K. Revise las unidades antes de guardar.")
            else:
                _guardar(cat.completar_columnas(editado), "Catálogo guardado")
                st.rerun()
        descargar.download_button("Descargar CSV", cat.a_csv(editado).encode("utf-8-sig"),
                                  "catalogo_comercial_cr.csv", "text/csv", width="stretch")
        archivo = subir.file_uploader("Reemplazar con un CSV", type="csv", label_visibility="collapsed")
        if archivo is not None and st.button("Usar el CSV subido"):
            try:
                _guardar(cat.leer_csv_subido(archivo), "Catálogo reemplazado")
                st.rerun()
            except (ValueError, pd.errors.ParserError) as error:
                st.error(f"No se pudo leer el CSV: {error}")
        st.caption("Los cambios se guardan en data/catalogo_comercial_cr.csv. Si la app está publicada en la "
                   "nube ese archivo puede reiniciarse: descargue el CSV para conservar una copia.")


def dibujar(sistema: str, materiales: list[str]) -> None:
    catalogo = st.session_state[CLAVE_CATALOGO]
    _disponibilidad(catalogo, sistema, materiales)
    _formulario_cotizacion(sistema, materiales)
    if sistema == SISTEMA_AISLANTE:
        _precios_web()
    else:
        st.caption("Para paneles frigoríficos use cotizaciones directas: no hay consulta web automática.")
    _editor_completo()
