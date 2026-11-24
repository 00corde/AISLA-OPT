"""Pestañas de resultados: resumen, alternativas, sensibilidad, inversión por espesor y térmico."""
from __future__ import annotations

import html

import numpy as np
import pandas as pd
import streamlit as st

from aisla_opt import analisis, formato
from aisla_opt.caso import Aviso, ResultadoCaso
from aisla_opt.motor import MaterialAislante

from . import graficas
from .tema import Paleta

FUNCION_AVISO = {"error": st.error, "advertencia": st.warning, "info": st.info, "exito": st.success}


def mostrar_avisos(avisos: list[Aviso]) -> None:
    for aviso in avisos:
        FUNCION_AVISO[aviso.nivel](aviso.texto)


def _material_de_mejor(resultado: ResultadoCaso) -> MaterialAislante:
    mejor = resultado.mejor
    return MaterialAislante(mejor["material"], float(mejor["k_W_mK"]))


# --------------------------------------------------------------------------- #
def tarjeta_mejor(mejor: dict) -> str:
    def cifra(nombre: str, valor: str, principal: bool = False) -> str:
        clase = "cifra principal" if principal else "cifra"
        return f'<div class="{clase}"><div class="valor">{valor}</div><div class="nombre">{nombre}</div></div>'

    origen_k = "k de ficha" if mejor["k_de_ficha"] else "k genérica ASHRAE"
    return f"""
<section class="mejor" aria-label="Mejor alternativa comercial evaluada">
  <p class="rotulo">Mejor alternativa comercial evaluada</p>
  <p class="producto">{html.escape(str(mejor["producto"]))}</p>
  <p class="detalle">{html.escape(str(mejor["material"]))} de {html.escape(str(mejor["proveedor"]))},
     {formato.colones(mejor["precio_CRC_m2"])}/m², {origen_k} {formato.numero(mejor["k_W_mK"], 3)} W/m·K</p>
  <div class="cifras">
    {cifra("Costo total en valor presente", formato.colones(mejor["costo_total_vp_CRC"]), principal=True)}
    {cifra("Espesor", formato.espesor(mejor["espesor_mm"]))}
    {cifra("Carga pico de transmisión", formato.unidad(mejor["carga_pico_kW"], "kW", 2))}
    {cifra("Energía anual por transmisión", formato.unidad(mejor["energia_kWh_anio"], "kWh", 0))}
    {cifra("Costo del aislamiento", formato.colones(mejor["costo_aislamiento_CRC"]))}
    {cifra("Costo de energía en valor presente", formato.colones(mejor["costo_energia_vp_CRC"]))}
  </div>
</section>"""


def _hay_valor(valor) -> bool:
    return valor is not None and not pd.isna(valor)


def _con_unidad(valor: float, unidad: str) -> str:
    decimales = 0 if float(valor).is_integer() or valor >= 10 else 2
    return f"{formato.numero(valor, decimales)} {unidad}".strip()


def _tabla_limites(limites: pd.DataFrame) -> pd.DataFrame:
    tabla = pd.DataFrame({
        "Material": limites["material"],
        "Límite continuo": [
            "> 400 mm" if supera else formato.espesor(lim) if _hay_valor(lim) else "—"
            for lim, supera in zip(limites["limite_mm"], limites["supera_busqueda"], strict=True)
        ],
        "Primer comercial que cubre": limites["espesor_comercial_mm"].map(formato.espesor),
        "Margen [mm]": limites["margen_mm"].map(lambda v: formato.numero(v, 1)),
        "Margen sobre el mínimo": limites["margen_pct"].map(
            lambda v: f"{formato.numero(v)} %" if _hay_valor(v) else "—"
        ),
        "Sensibilidad": limites["sensibilidad"].fillna("—"),
        "Proveedor": limites["proveedor"].fillna("—"),
        "Precio": limites["precio_CRC_m2"].map(
            lambda v: f"{formato.colones(v)}/m²" if _hay_valor(v) and v > 0 else "Cotización requerida"
        ),
    })
    return tabla


def _limites(resultado: ResultadoCaso, paleta: Paleta) -> None:
    if resultado.limites is not None:
        st.subheader("Del cálculo continuo al espesor comercial")
        st.caption("El límite continuo usa la k genérica de cada material. Al comparar costos, cada producto se "
                   "vuelve a evaluar con su k de ficha cuando existe.")
        st.dataframe(_tabla_limites(resultado.limites), hide_index=True, width="stretch")
        if resultado.limites["espesor_comercial_mm"].notna().any():
            st.altair_chart(graficas.limite_vs_comercial(resultado.limites, paleta), width="stretch")


def pestana_resultado(resultado: ResultadoCaso, paleta: Paleta) -> None:
    p = resultado.parametros
    if not resultado.hay_comparacion:
        mostrar_avisos(resultado.avisos)
        _limites(resultado, paleta)
        return

    mejor = resultado.mejor
    material = _material_de_mejor(resultado)
    recinto = p.recinto()
    izquierda, derecha = st.columns([1.05, 1], gap="large")
    with izquierda:
        st.markdown(tarjeta_mejor(mejor), unsafe_allow_html=True)
        st.caption("Es la alternativa de menor costo total solo entre los productos con precio evaluados. "
                   "No es un óptimo global fuera del catálogo.")
    with derecha:
        perfil = analisis.perfil_pared(recinto, material, mejor["espesor_mm"])
        st.markdown(graficas.seccion_pared_svg(perfil, mejor["espesor_mm"], mejor["material"], paleta),
                    unsafe_allow_html=True)

    mostrar_avisos(resultado.avisos)
    _limites(resultado, paleta)

    st.subheader("Costo de ciclo de vida de cada alternativa")
    st.altair_chart(graficas.costo_vs_espesor(resultado.alternativas, mejor, paleta), width="stretch")
    st.caption("Cada punto es un producto del catálogo. La línea une el producto más barato de cada espesor.")

    st.subheader("Carga pico por superficie")
    desglose = analisis.desglose_superficies(recinto, material, mejor["espesor_mm"], p.refrigeracion(), p.economia())
    st.altair_chart(graficas.desglose(desglose, paleta), width="stretch")


# --------------------------------------------------------------------------- #
def pestana_alternativas(resultado: ResultadoCaso) -> None:
    if not resultado.hay_comparacion:
        st.info("Sin alternativas con precio para comparar. Registre cotizaciones en la pestaña Catálogo.")
        return
    df = resultado.alternativas.copy()
    df.insert(0, "posicion", np.arange(1, len(df) + 1))
    df["material_corto"] = df["material"].map(analisis.abreviatura)

    columnas = {
        "posicion": st.column_config.NumberColumn("#", width="small"),
        "producto": st.column_config.TextColumn("Producto"),
        "material_corto": st.column_config.TextColumn("Material", width="small"),
        "proveedor": st.column_config.TextColumn("Proveedor"),
        "espesor_mm": st.column_config.NumberColumn("Espesor [mm]", format="%.1f"),
        "costo_total_vp_CRC": st.column_config.NumberColumn("Costo total VP [₡]", format="localized"),
        "diferencia_vs_mejor_CRC": st.column_config.NumberColumn("Diferencia vs. mejor [₡]", format="localized"),
        "costo_aislamiento_CRC": st.column_config.NumberColumn("Costo aislamiento [₡]", format="localized"),
        "energia_kWh_anio": st.column_config.NumberColumn("Energía [kWh/año]", format="localized"),
    }
    st.dataframe(df[list(columnas)], column_config=columnas, hide_index=True, width="stretch")

    with st.expander("Todas las columnas: precios, k usada, IVA, condición y fuente"):
        completas = {
            **columnas,
            "material": st.column_config.TextColumn("Material"),
            "precio_CRC_m2": st.column_config.NumberColumn("Precio [₡/m²]", format="localized"),
            "k_W_mK": st.column_config.NumberColumn("k usada [W/m·K]", format="%.3f"),
            "k_de_ficha": st.column_config.CheckboxColumn("k de ficha"),
            "carga_pico_kW": st.column_config.NumberColumn("Carga pico [kW]", format="%.3f"),
            "transmision_con_margen_kW": st.column_config.NumberColumn("Transmisión + margen [kW]", format="%.3f"),
            "costo_energia_anual_CRC": st.column_config.NumberColumn("Energía anual [₡]", format="localized"),
            "costo_energia_vp_CRC": st.column_config.NumberColumn("Energía VP [₡]", format="localized"),
            "iva": st.column_config.TextColumn("IVA"),
            "condicion": st.column_config.TextColumn("Condición"),
            "fecha": st.column_config.TextColumn("Fecha"),
            "fuente": st.column_config.LinkColumn("Fuente"),
        }
        completas.pop("material_corto")
        st.dataframe(df[list(completas)], column_config=completas, hide_index=True, width="stretch")

    st.download_button("Descargar alternativas (CSV)", resultado.alternativas.to_csv(index=False).encode("utf-8-sig"),
                       "alternativas_aisla_opt.csv", "text/csv")


# --------------------------------------------------------------------------- #
OPCIONES_BARRIDO = {
    "tarifa_CRC_kWh": ("Tarifa eléctrica [CRC/kWh]", 0.25, 3.0),
    "cop": ("COP efectivo", 0.4, 2.0),
    "precio_aislamiento": ("Precio del aislamiento [% del catálogo]", 0.5, 2.0),
    "vida_util_anios": ("Vida útil [años]", 0.3, 3.0),
    "tasa_descuento_pct": ("Tasa de descuento real [%]", 0.0, 3.0),
}


def pestana_sensibilidad(resultado: ResultadoCaso, catalogo: pd.DataFrame, paleta: Paleta) -> pd.DataFrame | None:
    if not resultado.hay_comparacion:
        st.info("La sensibilidad necesita al menos una alternativa con precio.")
        return None
    p = resultado.parametros
    st.markdown('<p class="nota">¿Cuánto cambia el costo de la mejor alternativa, y si cambia la decisión, '
                'cuando un supuesto se mueve hacia arriba o hacia abajo?</p>', unsafe_allow_html=True)
    variacion = st.slider("Variación de cada parámetro", 5, 50, 20, step=5, format="± %d %%") / 100
    sens = analisis.sensibilidad(p, catalogo, variacion)
    if sens.empty:
        st.info("No se pudo calcular la sensibilidad con los datos actuales.")
        return None

    st.altair_chart(graficas.tornado(sens, paleta), width="stretch")
    cambian = sens[sens["cambia_mejor"]]
    if cambian.empty:
        st.success("La mejor alternativa no cambia en ningún extremo: la decisión es robusta ante estas variaciones.")
    else:
        st.warning("La decisión cambia al mover: " + ", ".join(cambian["parametro"]) + ". Revise esos supuestos "
                   "con especial cuidado.")
    tabla = pd.DataFrame({
        "Parámetro": sens["parametro"],
        "Bajo": [_con_unidad(v, u) for v, u in zip(sens["valor_bajo"], sens["unidad"], strict=True)],
        "Mejor con valor bajo": sens["mejor_bajo"],
        "Alto": [_con_unidad(v, u) for v, u in zip(sens["valor_alto"], sens["unidad"], strict=True)],
        "Mejor con valor alto": sens["mejor_alto"],
        "Cambia la decisión": sens["cambia_mejor"].map({True: "Sí", False: "No"}),
    })
    st.dataframe(tabla, hide_index=True, width="stretch")

    st.subheader("Barrido de un parámetro")
    clave = st.selectbox("Parámetro", list(OPCIONES_BARRIDO), format_func=lambda k: OPCIONES_BARRIDO[k][0])
    titulo, desde, hasta = OPCIONES_BARRIDO[clave]
    base = analisis.valor_base(p, clave)
    if clave == "tasa_descuento_pct":
        valores = list(np.linspace(0.0, max(12.0, base * hasta), 25))
    elif clave == "vida_util_anios":
        valores = sorted({max(1, round(v)) for v in np.linspace(base * desde, base * hasta, 25)})
    else:
        valores = list(np.linspace(base * desde, base * hasta, 25))
    curvas = analisis.barrido(p, catalogo, clave, valores)
    if not curvas.empty:
        st.altair_chart(graficas.barrido(curvas, base, titulo, paleta), width="stretch")
        st.caption("Se muestran las cinco mejores alternativas del caso actual. Los puntos marcan la mejor en cada "
                   "valor y la línea punteada, el valor actual. Donde las curvas se cruzan cambia la decisión.")
    return sens


# --------------------------------------------------------------------------- #
def pestana_incremental(resultado: ResultadoCaso, paleta: Paleta) -> pd.DataFrame | None:
    if not resultado.hay_comparacion:
        st.info("El análisis incremental necesita alternativas con precio.")
        return None
    materiales = list(dict.fromkeys(resultado.alternativas["material"]))
    material = st.selectbox("Material", materiales, index=materiales.index(resultado.mejor["material"]))
    inc = analisis.analisis_incremental(resultado.alternativas, material, resultado.parametros.economia())
    if inc.empty:
        st.info("Este material tiene un solo espesor con precio; no hay pasos que comparar.")
        return None
    st.markdown('<p class="nota">Cada paso compara un espesor con el siguiente más grueso (el producto de menor '
                'precio en cada espesor). Si el ahorro de energía traído a valor presente supera la inversión '
                'adicional, el VPN es positivo y conviene engrosar.</p>', unsafe_allow_html=True)
    st.altair_chart(graficas.vpn_incremental(inc, paleta), width="stretch")
    tabla = pd.DataFrame({
        "Paso": [
            f"{formato.espesor(a)} ({pa}) → {formato.espesor(b)} ({pb})"
            for a, pa, b, pb in zip(inc["espesor_desde_mm"], inc["proveedor_desde"], inc["espesor_hasta_mm"],
                                    inc["proveedor_hasta"], strict=True)
        ],
        "Inversión adicional": inc["inversion_adicional_CRC"].map(formato.colones),
        "Ahorro de energía": inc["ahorro_energia_kWh_anio"].map(lambda v: formato.unidad(v, "kWh/año", 0)),
        "Ahorro anual": inc["ahorro_anual_CRC"].map(formato.colones),
        "Recuperación simple": inc["recuperacion_simple_anios"].map(lambda v: formato.unidad(v, "años", 1)),
        "VPN incremental": inc["vpn_incremental_CRC"].map(formato.colones),
        "¿Conviene?": inc["conviene"].map({True: "Sí", False: "No"}),
    })
    st.dataframe(tabla, hide_index=True, width="stretch")
    return inc


# --------------------------------------------------------------------------- #
def pestana_termica(resultado: ResultadoCaso, paleta: Paleta) -> None:
    p = resultado.parametros
    curva = analisis.curva_termica(p.recinto(), p.materiales_modelo(), p.refrigeracion(), p.economia())
    st.altair_chart(graficas.curva_termica(curva, paleta), width="stretch")
    st.caption("Comportamiento físico continuo con la k de cada material (genérica o de ficha). No representa "
               "disponibilidad comercial. Pase el cursor para leer los valores.")
    g = p.recinto().geometria
    a, b, c = st.columns(3)
    a.metric("Área de paredes", formato.unidad(g.area_paredes_m2, "m²", 1))
    b.metric("Área de techo y piso", formato.unidad(g.area_techo_m2 + g.area_piso_m2, "m²", 1))
    c.metric("Área total de envolvente", formato.unidad(g.area_total_m2, "m²", 1))
