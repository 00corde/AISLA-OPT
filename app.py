"""AISLA-OPT: interfaz Streamlit.

Ejecutar con:  streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from aisla_opt import __version__
from aisla_opt.caso import evaluar_caso
from aisla_opt.materiales import (
    MATERIALES_POR_SISTEMA,
    SISTEMA_PANEL,
    SISTEMAS,
    K_MAXIMA_W_mK,
    K_MINIMA_W_mK,
    k_generica,
)
from interfaz import barra_lateral, estado, pestana_catalogo, pestana_reporte, pestanas_resultados
from interfaz.tema import css_global, paleta_actual

DESCRIPCION_SISTEMA = {
    SISTEMA_PANEL: "Paneles terminados para cuarto frío (PUR o PIR). No se mezclan con láminas aislantes desnudas.",
    "Aislante independiente": "Láminas o planchas aislantes (EPS, XPS y otras). Los productos sin precio se "
                              "evalúan térmicamente pero no entran al ranking económico.",
}

st.set_page_config(page_title="AISLA-OPT", page_icon="❄️", layout="wide")
estado.inicializar()
paleta = paleta_actual()
st.markdown(css_global(paleta), unsafe_allow_html=True)

st.markdown(
    '<header class="encabezado"><span class="marca">AISLA-OPT</span>'
    '<span class="proposito">Aislamiento de cuartos refrigerados: carga por transmisión, productos del mercado '
    'costarricense y costo de ciclo de vida.</span></header>',
    unsafe_allow_html=True,
)

barra_lateral.dibujar()

# --- Solución comercial ------------------------------------------------------
izquierda, derecha = st.columns([1, 1.4], gap="large")
with izquierda:
    st.radio("Tipo de solución", SISTEMAS, key="sistema", horizontal=True, on_change=estado.al_cambiar_sistema)
    st.caption(DESCRIPCION_SISTEMA[st.session_state["sistema"]])
with derecha:
    st.multiselect("Materiales a comparar", MATERIALES_POR_SISTEMA[st.session_state["sistema"]], key="materiales",
                   placeholder="Elija uno o más materiales")
    st.checkbox("Usar la k de una ficha técnica en lugar de la k genérica ASHRAE", key=estado.CLAVE_USAR_K_FICHA)
    if st.session_state[estado.CLAVE_USAR_K_FICHA] and st.session_state["materiales"]:
        columnas = st.columns(min(3, len(st.session_state["materiales"])))
        for i, material in enumerate(st.session_state["materiales"]):
            clave = estado.clave_k(material)
            st.session_state.setdefault(clave, k_generica(material))
            columnas[i % len(columnas)].number_input(
                f"k {material} [W/m·K]", key=clave, min_value=K_MINIMA_W_mK, max_value=K_MAXIMA_W_mK,
                step=0.001, format="%.3f",
            )

parametros = estado.leer_parametros()
catalogo = st.session_state[estado.CLAVE_CATALOGO]

pestanas = st.tabs([
    "Resultado", "Alternativas", "Sensibilidad", "Inversión por espesor", "Comportamiento térmico",
    "Catálogo", "Reporte y escenarios", "Alcance del modelo",
])

if not parametros.materiales:
    resultado = None
    pestanas[0].info("Elija al menos un material para comparar.")
else:
    try:
        resultado = evaluar_caso(parametros, catalogo)
    except ValueError as error:
        resultado = None
        pestanas[0].error(f"No se pudo evaluar el caso: {error}")

sensibilidad = incremental = None
if resultado is not None:
    with pestanas[0]:
        pestanas_resultados.pestana_resultado(resultado, paleta)
    with pestanas[1]:
        pestanas_resultados.pestana_alternativas(resultado)
    with pestanas[2]:
        sensibilidad = pestanas_resultados.pestana_sensibilidad(resultado, catalogo, paleta)
    with pestanas[3]:
        incremental = pestanas_resultados.pestana_incremental(resultado, paleta)
    with pestanas[4]:
        pestanas_resultados.pestana_termica(resultado, paleta)
    with pestanas[6]:
        pestana_reporte.pestana_reporte(resultado, catalogo, sensibilidad, incremental)
else:
    for indice in (1, 2, 3, 4, 6):
        pestanas[indice].info("Complete las entradas para ver esta sección.")

with pestanas[5]:
    pestana_catalogo.dibujar(st.session_state["sistema"], list(st.session_state["materiales"]))
with pestanas[7]:
    pestana_reporte.pestana_alcance()

st.caption(f"AISLA-OPT {__version__}. Herramienta académica de apoyo al diseño; no sustituye el cálculo "
           "completo de carga frigorífica.")
