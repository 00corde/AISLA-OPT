"""Pestañas de reporte, escenarios y alcance del modelo."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from aisla_opt import analisis, formato
from aisla_opt.caso import ResultadoCaso
from aisla_opt.materiales import FUENTE_ASHRAE_NOMBRE, FUENTE_ASHRAE_NOTA, FUENTE_ASHRAE_URL, MATERIALES_ASHRAE
from aisla_opt.reporte import generar_excel

from . import estado


def _fila_escenario(nombre: str, resultado: ResultadoCaso) -> dict:
    p, mejor = resultado.parametros, resultado.mejor
    return {
        "Escenario": nombre,
        "Recinto": f"{formato.numero(p.largo_m, 1)} × {formato.numero(p.ancho_m, 1)} × {formato.numero(p.alto_m, 1)} m",
        "Interior": f"{formato.numero(p.t_interior_C, 1)} °C",
        "Tarifa": f"{formato.colones(p.tarifa_CRC_kWh)}/kWh",
        "COP": formato.numero(p.cop, 2),
        "Vida útil": f"{p.vida_util_anios} años",
        "Mejor alternativa": analisis.etiqueta_alternativa(mejor) if mejor else "Sin comparación",
        "Costo total VP": formato.colones(mejor["costo_total_vp_CRC"]) if mejor else "—",
        "Carga pico": formato.unidad(mejor["carga_pico_kW"], "kW", 2) if mejor else "—",
    }


def pestana_reporte(
    resultado: ResultadoCaso,
    catalogo: pd.DataFrame,
    sensibilidad: pd.DataFrame | None,
    incremental: pd.DataFrame | None,
) -> None:
    st.subheader("Reporte del caso")
    st.markdown('<p class="nota">Libro de Excel con resumen, entradas, alternativas, sensibilidad, inversión por '
                'espesor, advertencias y el catálogo usado, listo para anexar al informe.</p>', unsafe_allow_html=True)
    st.download_button(
        "Descargar reporte (Excel)",
        generar_excel(resultado, catalogo, sensibilidad, incremental),
        f"aisla_opt_{date.today().isoformat()}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

    st.subheader("Escenarios")
    guardar, cargar = st.columns(2, gap="large")
    with guardar:
        st.markdown("**Guardar las entradas actuales**")
        st.download_button("Descargar escenario (JSON)", resultado.parametros.a_json().encode("utf-8"),
                           "escenario_aisla_opt.json", "application/json")
        nombre = st.text_input("Nombre para comparar en esta sesión",
                               value=f"Escenario {len(st.session_state[estado.CLAVE_ESCENARIOS]) + 1}")
        if st.button("Agregar a la comparación"):
            st.session_state[estado.CLAVE_ESCENARIOS].append(_fila_escenario(nombre.strip() or "Sin nombre", resultado))
            st.toast(f"«{nombre}» agregado a la comparación")
    with cargar:
        st.markdown("**Cargar un escenario guardado**")
        st.file_uploader("Archivo JSON de AISLA-OPT", type="json", key="archivo_escenario",
                         label_visibility="collapsed")
        st.button("Cargar escenario", on_click=estado.al_cargar_escenario,
                  disabled=st.session_state.get("archivo_escenario") is None)
        mensaje = st.session_state.pop("mensaje_escenario", None)
        if mensaje:
            (st.success if mensaje[0] == "exito" else st.error)(mensaje[1])

    escenarios = st.session_state[estado.CLAVE_ESCENARIOS]
    if escenarios:
        st.markdown("**Comparación de escenarios**")
        st.dataframe(pd.DataFrame(escenarios), hide_index=True, width="stretch")
        if st.button("Vaciar comparación"):
            st.session_state[estado.CLAVE_ESCENARIOS] = []
            st.rerun()
    else:
        st.caption("Agregue escenarios para compararlos lado a lado; por ejemplo, el mismo cuarto con dos tarifas.")


def pestana_alcance() -> None:
    st.markdown(
        """
**Qué resuelve.** El espesor calculado puede no existir en el mercado, y la opción más barata al inicio puede
salir más cara por consumo eléctrico. AISLA-OPT une cálculo térmico, disponibilidad comercial y costo de ciclo
de vida para apoyar esa decisión.

**Qué incluye**
- Recinto rectangular en estado estacionario, con dimensiones exteriores de referencia.
- Un mismo material y espesor uniforme en paredes, techo y piso para cada alternativa.
- Conducción por el aislamiento y convección interior y exterior con coeficientes h efectivos.
- Carga por transmisión de la envolvente; no es la carga frigorífica total.
- Energía con un COP efectivo promedio y costo de ciclo de vida en valor presente.

**Qué no incluye**
- Infiltración por puertas, carga latente, producto, personas, iluminación ni deshielo.
- Dimensionamiento del sistema frigorífico ni costo del equipo o cargos por demanda.
- Conducción detallada al terreno: el piso usa una temperatura equivalente.
- Instalación, flete, desperdicio o impuestos que no estén en el precio registrado.
"""
    )
    st.subheader("Conductividad térmica de referencia")
    st.dataframe(
        pd.DataFrame([
            {"Material": nombre, "k de diseño [W/m·K]": datos["k"], "Valor ASHRAE": datos["k_texto"],
             "Criterio": datos["nota"]}
            for nombre, datos in MATERIALES_ASHRAE.items()
        ]),
        hide_index=True, width="stretch",
    )
    st.caption(f"{FUENTE_ASHRAE_NOMBRE}. {FUENTE_ASHRAE_NOTA} El acceso en línea puede requerir suscripción.")
    st.link_button("Abrir referencia ASHRAE", FUENTE_ASHRAE_URL)
