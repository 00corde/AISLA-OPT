"""Exportación del caso a Excel: entradas, resultados, análisis y advertencias."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pandas as pd

from . import __version__
from .caso import ResultadoCaso
from .materiales import FUENTE_ASHRAE_NOMBRE

ETIQUETAS_ALTERNATIVAS = {
    "material": "Material",
    "proveedor": "Proveedor",
    "producto": "Producto",
    "espesor_mm": "Espesor [mm]",
    "precio_CRC_m2": "Precio [CRC/m²]",
    "k_W_mK": "k usada [W/m·K]",
    "k_de_ficha": "k de ficha",
    "carga_pico_kW": "Carga pico transmisión [kW]",
    "transmision_con_margen_kW": "Transmisión + margen [kW]",
    "energia_kWh_anio": "Energía transmisión [kWh/año]",
    "costo_aislamiento_CRC": "Costo aislamiento [CRC]",
    "costo_energia_anual_CRC": "Costo energía anual [CRC]",
    "costo_energia_vp_CRC": "Costo energía VP [CRC]",
    "costo_total_vp_CRC": "Costo total VP [CRC]",
    "diferencia_vs_mejor_CRC": "Diferencia vs. mejor [CRC]",
    "iva": "IVA",
    "condicion": "Condición",
    "fecha": "Fecha",
    "fuente": "Fuente",
}

ETIQUETAS_PARAMETROS = {
    "sistema": "Tipo de solución",
    "materiales": "Materiales estudiados",
    "k_ficha_W_mK": "k de ficha usada [W/m·K]",
    "largo_m": "Largo exterior [m]",
    "ancho_m": "Ancho exterior [m]",
    "alto_m": "Alto exterior [m]",
    "t_interior_C": "Temperatura interior [°C]",
    "t_paredes_critica_C": "Paredes, crítica [°C]",
    "t_paredes_operacion_C": "Paredes, operación [°C]",
    "t_techo_critica_C": "Techo, crítica [°C]",
    "t_techo_operacion_C": "Techo, operación [°C]",
    "t_piso_critica_C": "Piso, crítica [°C]",
    "t_piso_operacion_C": "Piso, operación [°C]",
    "cop": "COP efectivo promedio",
    "margen_pct": "Margen de diseño [%]",
    "usar_capacidad": "Restricción de capacidad activa",
    "capacidad_kW": "Capacidad disponible para transmisión [kW]",
    "tarifa_CRC_kWh": "Tarifa eléctrica [CRC/kWh]",
    "horas_anio": "Horas al año a temperatura objetivo",
    "vida_util_anios": "Vida útil [años]",
    "tasa_descuento_pct": "Tasa de descuento real [%]",
    "h_interior_W_m2K": "h interior [W/m²·K]",
    "h_exterior_paredes_W_m2K": "h exterior paredes [W/m²·K]",
    "h_exterior_techo_W_m2K": "h exterior techo [W/m²·K]",
    "h_piso_W_m2K": "h equivalente piso [W/m²·K]",
    "r_adicional_paredes_m2K_W": "R'' adicional paredes [m²·K/W]",
    "r_adicional_techo_m2K_W": "R'' adicional techo [m²·K/W]",
    "r_adicional_piso_m2K_W": "R'' adicional piso [m²·K/W]",
}


def _tabla_entradas(resultado: ResultadoCaso) -> pd.DataFrame:
    filas = []
    for clave, valor in resultado.parametros.a_dict().items():
        if isinstance(valor, list):
            valor = "; ".join(valor)
        elif isinstance(valor, dict):
            valor = "; ".join(f"{k}: {v}" for k, v in valor.items()) or "Valores genéricos ASHRAE"
        elif isinstance(valor, bool):
            valor = "Sí" if valor else "No"
        filas.append({"Parámetro": ETIQUETAS_PARAMETROS.get(clave, clave), "Valor": valor})
    return pd.DataFrame(filas)


def _tabla_resumen(resultado: ResultadoCaso) -> pd.DataFrame:
    filas = [
        ("Aplicación", f"AISLA-OPT {__version__}"),
        ("Generado", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ("Fuente de k genérica", FUENTE_ASHRAE_NOMBRE),
    ]
    mejor = resultado.mejor
    if mejor is None:
        filas.append(("Mejor alternativa comercial evaluada", "Sin comparación económica (faltan precios)"))
    else:
        filas += [
            ("Mejor alternativa comercial evaluada", mejor["producto"]),
            ("Material", mejor["material"]),
            ("Proveedor", mejor["proveedor"]),
            ("Espesor [mm]", mejor["espesor_mm"]),
            ("Carga pico de transmisión [kW]", round(mejor["carga_pico_kW"], 3)),
            ("Energía anual por transmisión [kWh]", round(mejor["energia_kWh_anio"], 1)),
            ("Costo del aislamiento [CRC]", round(mejor["costo_aislamiento_CRC"])),
            ("Costo total en valor presente [CRC]", round(mejor["costo_total_vp_CRC"])),
        ]
    filas.append(("Alcance", "Transmisión estacionaria por la envolvente; no es la carga frigorífica total."))
    return pd.DataFrame(filas, columns=["Concepto", "Valor"])


def generar_excel(
    resultado: ResultadoCaso,
    catalogo: pd.DataFrame,
    sensibilidad: pd.DataFrame | None = None,
    incremental: pd.DataFrame | None = None,
) -> bytes:
    hojas: dict[str, pd.DataFrame] = {
        "Resumen": _tabla_resumen(resultado),
        "Entradas": _tabla_entradas(resultado),
        "Alternativas": resultado.alternativas.rename(columns=ETIQUETAS_ALTERNATIVAS),
    }
    if resultado.limites is not None:
        hojas["Límite por capacidad"] = resultado.limites
    if sensibilidad is not None and not sensibilidad.empty:
        hojas["Sensibilidad"] = sensibilidad
    if incremental is not None and not incremental.empty:
        hojas["Incremental"] = incremental
    hojas["Advertencias"] = pd.DataFrame(
        [{"Nivel": a.nivel, "Mensaje": a.texto} for a in resultado.avisos], columns=["Nivel", "Mensaje"]
    )
    hojas["Catálogo"] = catalogo

    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as escritor:
        for nombre, df in hojas.items():
            df.to_excel(escritor, sheet_name=nombre, index=False)
            hoja = escritor.sheets[nombre]
            for columna in hoja.columns:
                ancho = max(len(str(celda.value or "")) for celda in columna)
                hoja.column_dimensions[columna[0].column_letter].width = min(60, max(10, ancho + 2))
            hoja.freeze_panes = "A2"
    return salida.getvalue()
