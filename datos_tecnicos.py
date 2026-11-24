from __future__ import annotations

ASHRAE_SOURCE_NAME = "ASHRAE Handbook—Refrigeration 2026, Chapter 24, Table 1"
ASHRAE_SOURCE_URL = "https://handbook.ashrae.org/Handbooks/R26/SI/r26_ch24/r26_ch24_si.aspx"
ASHRAE_SOURCE_NOTE = "Valores a temperatura media de 24 °C y aislamiento envejecido 180 días."

# All design values below come from the same ASHRAE cold-storage table.
# PU is reported as a range 0.023–0.026 W/(m·K); AISLA-OPT uses the
# conservative upper value 0.026 as its default design value.
MATERIALES_ASHRAE = {
    "Poliuretano (PU)": {
        "k": 0.026,
        "k_texto": "0.023–0.026",
        "nota": "Se usa 0.026 W/m·K como valor conservador de diseño.",
        "principal_panel": True,
        "principal_aislante": True,
    },
    "Poliisocianurato (PIR)": {
        "k": 0.027,
        "k_texto": "0.027",
        "nota": "Valor de referencia ASHRAE para aislamiento de almacenamiento refrigerado.",
        "principal_panel": True,
        "principal_aislante": False,
    },
    "Poliestireno extruido (XPS)": {
        "k": 0.035,
        "k_texto": "0.035",
        "nota": "Valor de referencia ASHRAE para aislamiento de almacenamiento refrigerado.",
        "principal_panel": False,
        "principal_aislante": True,
    },
    "Poliestireno expandido (EPS)": {
        "k": 0.037,
        "k_texto": "0.037",
        "nota": "Valor de referencia ASHRAE para aislamiento de almacenamiento refrigerado.",
        "principal_panel": False,
        "principal_aislante": True,
    },
    "Corcho": {
        "k": 0.043,
        "k_texto": "0.043",
        "nota": "ASHRAE lo incluye como referencia y señala que actualmente se usa poco.",
        "principal_panel": False,
        "principal_aislante": False,
    },
    "Vidrio celular": {
        "k": 0.044,
        "k_texto": "0.044",
        "nota": "ASHRAE señala efectos de envejecimiento prácticamente despreciables.",
        "principal_panel": False,
        "principal_aislante": False,
    },
}
