"""Entradas de diseño en la barra lateral."""
from __future__ import annotations

import streamlit as st

from aisla_opt.caso import PLANTILLAS

from . import estado


def _par(etiqueta: str, clave_critica: str, clave_operacion: str) -> None:
    st.markdown(f"**{etiqueta}**")
    critica, operacion = st.columns(2)
    critica.number_input("Crítica [°C]", key=clave_critica, step=0.5, format="%.1f")
    operacion.number_input("Operación [°C]", key=clave_operacion, step=0.5, format="%.1f")


def dibujar() -> None:
    with st.sidebar:
        st.header("Datos de diseño")

        with st.container(border=True):
            st.selectbox("Plantilla", list(PLANTILLAS), key="plantilla",
                         help="Punto de partida editable. Conserva el tipo de solución y los materiales elegidos.")
            st.button("Aplicar plantilla", on_click=estado.al_aplicar_plantilla, width="stretch")
            st.button("Restablecer valores iniciales", on_click=estado.al_restablecer, width="stretch",
                      type="tertiary")

        st.subheader("Recinto")
        st.number_input("Largo exterior [m]", key="largo_m", min_value=0.1, step=0.1, format="%.2f")
        st.number_input("Ancho exterior [m]", key="ancho_m", min_value=0.1, step=0.1, format="%.2f")
        st.number_input("Alto exterior [m]", key="alto_m", min_value=0.1, step=0.1, format="%.2f")
        st.caption("Dimensiones exteriores de referencia para el área de transmisión.")

        st.subheader("Temperaturas")
        st.number_input("Interior objetivo [°C]", key="t_interior_C", step=0.5, format="%.1f")
        _par("Paredes, aire exterior", "t_paredes_critica_C", "t_paredes_operacion_C")
        _par("Techo, equivalente", "t_techo_critica_C", "t_techo_operacion_C")
        _par("Piso, equivalente", "t_piso_critica_C", "t_piso_operacion_C")
        st.caption("La crítica define la carga pico. La de operación es la condición media del año "
                   "y define la energía.")

        st.subheader("Refrigeración")
        st.number_input("COP efectivo promedio", key="cop", min_value=0.1, step=0.1, format="%.2f",
                        help="COP representativo para estimar la energía atribuible a la transmisión.")
        st.slider("Margen de diseño [%]", 0.0, 50.0, key="margen_pct", step=1.0, format="%.0f %%")
        st.checkbox("Limitar por capacidad disponible para transmisión", key="usar_capacidad")
        st.number_input("Capacidad disponible para la envolvente [kW]", key="capacidad_kW", min_value=0.1,
                        step=0.1, format="%.2f", disabled=not st.session_state["usar_capacidad"],
                        help="Si parte de la capacidad total del equipo, reste antes infiltración, producto, "
                             "iluminación y demás cargas.")

        st.subheader("Economía")
        st.number_input("Tarifa eléctrica [CRC/kWh]", key="tarifa_CRC_kWh", min_value=0.0, step=1.0, format="%.1f")
        st.number_input("Horas al año a temperatura objetivo", key="horas_anio", min_value=0.0, max_value=8760.0,
                        step=100.0, format="%.0f", help="8760 h para operación continua.")
        st.number_input("Vida útil [años]", key="vida_util_anios", min_value=1, step=1)
        st.number_input("Tasa de descuento real [%]", key="tasa_descuento_pct", min_value=0.0, step=0.5,
                        format="%.1f")

        with st.expander("Parámetros térmicos avanzados"):
            st.caption("Los coeficientes h son valores efectivos de película. Ajústelos solo con datos del caso.")
            st.number_input("h interior [W/m²·K]", key="h_interior_W_m2K", min_value=0.1, step=0.1, format="%.2f")
            st.number_input("h exterior paredes [W/m²·K]", key="h_exterior_paredes_W_m2K", min_value=0.1,
                            step=0.1, format="%.2f")
            st.number_input("h exterior techo [W/m²·K]", key="h_exterior_techo_W_m2K", min_value=0.1,
                            step=0.1, format="%.2f")
            st.number_input("h equivalente piso [W/m²·K]", key="h_piso_W_m2K", min_value=0.1, step=0.1,
                            format="%.2f")
            st.number_input("R'' adicional paredes [m²·K/W]", key="r_adicional_paredes_m2K_W", min_value=0.0,
                            step=0.01, format="%.2f")
            st.number_input("R'' adicional techo [m²·K/W]", key="r_adicional_techo_m2K_W", min_value=0.0,
                            step=0.01, format="%.2f")
            st.number_input("R'' adicional piso [m²·K/W]", key="r_adicional_piso_m2K_W", min_value=0.0,
                            step=0.01, format="%.2f")
            st.caption("R'' adicional representa capas conocidas aparte del aislamiento. En paneles "
                       "prefabricados no agregue la resistencia de las láminas metálicas.")
