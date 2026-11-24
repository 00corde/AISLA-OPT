"""Identidad visual: paleta clara/oscura, colores por material y estilos globales.

La paleta categórica (series de gráficas) se validó con el script del skill
de visualización de datos para daltonismo y contraste, en claro y oscuro.
"""
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class Paleta:
    nombre: str
    fondo: str
    superficie: str
    texto: str
    texto_secundario: str
    borde: str
    primario: str
    frio: str  # zona interior del diagrama de pared
    calor: str  # zona exterior y flujo de calor
    aislante: str
    series: tuple[str, ...]
    positivo: str
    negativo: str


CLARA = Paleta(
    nombre="light",
    fondo="#F3F6F7",
    superficie="#FFFFFF",
    texto="#172A33",
    texto_secundario="#4E626C",
    borde="#C9D6DC",
    primario="#0E6E8C",
    frio="#D7EAF2",
    calor="#C2410C",
    aislante="#E9EEF0",
    series=("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"),
    positivo="#2a78d6",
    negativo="#e34948",
)

OSCURA = Paleta(
    nombre="dark",
    fondo="#0F1B21",
    superficie="#172832",
    texto="#E3ECEF",
    texto_secundario="#A9BCC4",
    borde="#2A3F4A",
    primario="#46A9C9",
    frio="#16384A",
    calor="#F08A4B",
    aislante="#22343E",
    series=("#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"),
    positivo="#3987e5",
    negativo="#e66767",
)

# El color sigue al material, no a su posición en la tabla: cada material
# conserva su color aunque cambie la selección.
INDICE_COLOR_MATERIAL = {
    "Poliestireno expandido (EPS)": 0,
    "Poliuretano (PU)": 1,
    "Poliestireno extruido (XPS)": 2,
    "Corcho": 3,
    "Vidrio celular": 4,
    "Poliisocianurato (PIR)": 6,
}


def paleta_actual() -> Paleta:
    try:
        tipo = st.context.theme.type
    except AttributeError:
        tipo = None
    return OSCURA if tipo == "dark" else CLARA


def color_material(material: str, paleta: Paleta) -> str:
    return paleta.series[INDICE_COLOR_MATERIAL.get(material, 7)]


def escala_materiales(materiales: list[str], paleta: Paleta) -> tuple[list[str], list[str]]:
    """Dominio y rango para una escala de color Altair por material."""
    dominio = list(dict.fromkeys(materiales))
    return dominio, [color_material(m, paleta) for m in dominio]


def css_global(p: Paleta) -> str:
    return f"""
<style>
.block-container {{ padding-top: 3.2rem; padding-bottom: 4rem; max-width: 1320px; }}
h1, h2, h3, h4 {{ letter-spacing: -0.005em; }}

.encabezado {{ display: flex; align-items: baseline; gap: 1rem; flex-wrap: wrap;
  border-bottom: 2px solid {p.primario}; padding-bottom: .55rem; margin-bottom: 1.1rem; }}
.encabezado .marca {{ font-size: 2.1rem; font-weight: 700; line-height: 1; color: {p.texto}; }}
.encabezado .proposito {{ color: {p.texto_secundario}; font-size: 1.02rem; max-width: 62ch; }}

.mejor {{ border: 1px solid {p.borde}; border-left: 6px solid {p.primario}; border-radius: 6px;
  background: {p.superficie}; padding: 1.1rem 1.3rem 1rem; }}
.mejor .rotulo {{ color: {p.texto_secundario}; font-size: .9rem; margin: 0; }}
.mejor .producto {{ font-size: 1.55rem; font-weight: 700; color: {p.texto}; margin: .1rem 0 .15rem;
  line-height: 1.2; overflow-wrap: anywhere; }}
.mejor .detalle {{ color: {p.texto_secundario}; margin: 0 0 .9rem; }}
.cifras {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(128px, 1fr)); gap: .9rem 1.4rem; }}
.cifra .valor {{ font-size: 1.35rem; font-weight: 600; color: {p.texto}; font-variant-numeric: tabular-nums;
  white-space: nowrap; }}
.cifra .nombre {{ color: {p.texto_secundario}; font-size: .86rem; }}
.cifra.principal .valor {{ color: {p.primario}; font-size: 1.6rem; }}

.diagrama {{ width: 100%; box-sizing: border-box; margin: 0; border: 1px solid {p.borde}; border-radius: 6px;
  background: {p.superficie}; padding: .7rem .9rem .3rem; }}
.diagrama figcaption {{ color: {p.texto_secundario}; font-size: .86rem; margin-top: .2rem; }}
.diagrama svg {{ width: 100%; height: auto; display: block; }}

.nota {{ color: {p.texto_secundario}; font-size: .9rem; max-width: 80ch; }}
</style>
"""
