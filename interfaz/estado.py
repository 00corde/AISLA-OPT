"""Puente entre los widgets de Streamlit y ``ParametrosCaso``.

Cada widget de entrada usa como ``key`` el nombre del campo del caso. Así una
plantilla o un escenario cargado se aplica escribiendo en ``session_state``
dentro de un callback, antes de que los widgets se dibujen.
"""
from __future__ import annotations

from dataclasses import fields

import streamlit as st

from aisla_opt import catalogo
from aisla_opt.caso import ParametrosCaso, caso_desde_plantilla
from aisla_opt.materiales import MATERIALES_INICIALES, k_generica

CLAVE_CATALOGO = "catalogo"
CLAVE_ESCENARIOS = "escenarios_guardados"
CLAVE_USAR_K_FICHA = "usar_k_ficha"
CAMPOS_ESPECIALES = {"k_ficha_W_mK"}


def clave_k(material: str) -> str:
    return f"k_ficha::{material}"


def inicializar() -> None:
    base = ParametrosCaso()
    for campo in fields(ParametrosCaso):
        if campo.name not in CAMPOS_ESPECIALES:
            st.session_state.setdefault(campo.name, getattr(base, campo.name))
    st.session_state.setdefault(CLAVE_USAR_K_FICHA, False)
    st.session_state.setdefault(CLAVE_ESCENARIOS, [])
    if CLAVE_CATALOGO not in st.session_state:
        st.session_state[CLAVE_CATALOGO] = catalogo.cargar()


def leer_parametros() -> ParametrosCaso:
    estado = st.session_state
    valores = {
        campo.name: estado[campo.name] for campo in fields(ParametrosCaso) if campo.name not in CAMPOS_ESPECIALES
    }
    valores["materiales"] = list(estado["materiales"])
    valores["vida_util_anios"] = int(estado["vida_util_anios"])
    if estado[CLAVE_USAR_K_FICHA]:
        valores["k_ficha_W_mK"] = {
            m: float(estado.get(clave_k(m), k_generica(m))) for m in valores["materiales"]
        }
    return ParametrosCaso(**valores)


def aplicar_parametros(p: ParametrosCaso) -> None:
    """Escribe un caso en el estado. Llamar solo desde un callback."""
    for campo in fields(ParametrosCaso):
        if campo.name not in CAMPOS_ESPECIALES:
            st.session_state[campo.name] = getattr(p, campo.name)
    st.session_state[CLAVE_USAR_K_FICHA] = bool(p.k_ficha_W_mK)
    for material, k in p.k_ficha_W_mK.items():
        st.session_state[clave_k(material)] = float(k)


# --------------------------------------------------------------------------- #
# Callbacks
# --------------------------------------------------------------------------- #
def al_cambiar_sistema() -> None:
    st.session_state["materiales"] = list(MATERIALES_INICIALES[st.session_state["sistema"]])


def al_aplicar_plantilla() -> None:
    nombre = st.session_state.get("plantilla")
    if nombre:
        aplicar_parametros(caso_desde_plantilla(nombre, leer_parametros()))


def al_cargar_escenario() -> None:
    archivo = st.session_state.get("archivo_escenario")
    if archivo is None:
        return
    try:
        caso = ParametrosCaso.desde_json(archivo.getvalue().decode("utf-8"))
    except (ValueError, TypeError, UnicodeDecodeError) as error:
        st.session_state["mensaje_escenario"] = ("error", f"No se pudo cargar el escenario: {error}")
        return
    aplicar_parametros(caso)
    st.session_state["mensaje_escenario"] = ("exito", f"Escenario «{archivo.name}» cargado.")


def al_restablecer() -> None:
    sistema, materiales = st.session_state["sistema"], list(st.session_state["materiales"])
    caso = ParametrosCaso(sistema=sistema, materiales=materiales)
    aplicar_parametros(caso)
