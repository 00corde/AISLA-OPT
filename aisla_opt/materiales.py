"""Propiedades técnicas de referencia y categorías comerciales."""
from __future__ import annotations

FUENTE_ASHRAE_NOMBRE = "ASHRAE Handbook—Refrigeration 2026, Chapter 24, Table 1"
FUENTE_ASHRAE_URL = "https://handbook.ashrae.org/Handbooks/R26/SI/r26_ch24/r26_ch24_si.aspx"
FUENTE_ASHRAE_NOTA = "Valores a temperatura media de 24 °C y aislamiento envejecido 180 días."

# Rango aceptado para k de ficha: control de plausibilidad para detectar
# errores de unidades, no un límite físico de todos los aislantes.
K_MINIMA_W_mK = 0.01
K_MAXIMA_W_mK = 0.20

# Todos los valores provienen de la misma tabla ASHRAE de almacenamiento
# refrigerado. Para PU la tabla da 0.023–0.026 W/(m·K); se usa 0.026 como
# valor de diseño conservador.
MATERIALES_ASHRAE: dict[str, dict] = {
    "Poliuretano (PU)": {
        "k": 0.026,
        "k_texto": "0.023–0.026",
        "nota": "Se usa 0.026 W/m·K como valor conservador de diseño.",
    },
    "Poliisocianurato (PIR)": {
        "k": 0.027,
        "k_texto": "0.027",
        "nota": "Valor de referencia ASHRAE para aislamiento de almacenamiento refrigerado.",
    },
    "Poliestireno extruido (XPS)": {
        "k": 0.035,
        "k_texto": "0.035",
        "nota": "Valor de referencia ASHRAE para aislamiento de almacenamiento refrigerado.",
    },
    "Poliestireno expandido (EPS)": {
        "k": 0.037,
        "k_texto": "0.037",
        "nota": "Valor de referencia ASHRAE para aislamiento de almacenamiento refrigerado.",
    },
    "Corcho": {
        "k": 0.043,
        "k_texto": "0.043",
        "nota": "ASHRAE lo incluye como referencia y señala que actualmente se usa poco.",
    },
    "Vidrio celular": {
        "k": 0.044,
        "k_texto": "0.044",
        "nota": "ASHRAE señala efectos de envejecimiento prácticamente despreciables.",
    },
}

SISTEMA_PANEL = "Panel frigorífico completo"
SISTEMA_AISLANTE = "Aislante independiente"
SISTEMAS = (SISTEMA_AISLANTE, SISTEMA_PANEL)

# Materiales que se ofrecen en cada categoría y su selección inicial.
MATERIALES_POR_SISTEMA: dict[str, tuple[str, ...]] = {
    SISTEMA_PANEL: ("Poliuretano (PU)", "Poliisocianurato (PIR)"),
    SISTEMA_AISLANTE: (
        "Poliestireno expandido (EPS)",
        "Poliestireno extruido (XPS)",
        "Poliuretano (PU)",
        "Corcho",
        "Vidrio celular",
    ),
}
MATERIALES_INICIALES: dict[str, tuple[str, ...]] = {
    SISTEMA_PANEL: ("Poliuretano (PU)", "Poliisocianurato (PIR)"),
    SISTEMA_AISLANTE: ("Poliestireno expandido (EPS)", "Poliestireno extruido (XPS)"),
}


def k_generica(material: str) -> float:
    return float(MATERIALES_ASHRAE[material]["k"])


def k_es_plausible(k: float) -> bool:
    return K_MINIMA_W_mK <= float(k) <= K_MAXIMA_W_mK
