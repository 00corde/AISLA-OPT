"""Análisis complementarios: sensibilidad, inversión incremental y desglose térmico."""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, replace

import pandas as pd

from .caso import ParametrosCaso
from .motor import (
    Economia,
    MaterialAislante,
    Recinto,
    SistemaRefrigeracion,
    evaluar_alternativa,
    factor_valor_presente_anualidad,
    perfil_temperatura_C,
)
from .seleccion import comparar_alternativas


def abreviatura(material: str) -> str:
    """'Poliestireno expandido (EPS)' → 'EPS'; 'Corcho' → 'Corcho'."""
    coincidencia = re.search(r"\(([^)]+)\)", material)
    return coincidencia.group(1) if coincidencia else material


def etiqueta_alternativa(fila: dict | pd.Series) -> str:
    espesor = f"{fila['espesor_mm']:g}".replace(".", ",")
    return f"{abreviatura(fila['material'])} {espesor} mm · {fila['proveedor']}"


# --------------------------------------------------------------------------- #
# Sensibilidad
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ParametroSensible:
    clave: str
    etiqueta: str
    unidad: str
    variar: Callable[[float, float], tuple[float, float]]  # (base, variación) → (bajo, alto)


def _relativo(base: float, v: float) -> tuple[float, float]:
    return base * (1 - v), base * (1 + v)


def _vida(base: float, v: float) -> tuple[float, float]:
    delta = max(1, round(base * v))
    return max(1, base - delta), base + delta


def _tasa(base: float, v: float) -> tuple[float, float]:
    if base <= 0:
        return 0.0, 10 * v
    return max(0.0, base * (1 - v)), base * (1 + v)


PARAMETROS_SENSIBLES = {
    "tarifa_CRC_kWh": ParametroSensible("tarifa_CRC_kWh", "Tarifa eléctrica", "CRC/kWh", _relativo),
    "cop": ParametroSensible("cop", "COP", "", _relativo),
    "precio_aislamiento": ParametroSensible("precio_aislamiento", "Precio del aislamiento", "%", _relativo),
    "vida_util_anios": ParametroSensible("vida_util_anios", "Vida útil", "años", _vida),
    "tasa_descuento_pct": ParametroSensible("tasa_descuento_pct", "Tasa de descuento", "%", _tasa),
}


def _con_parametro(
    p: ParametrosCaso, catalogo: pd.DataFrame, clave: str, valor: float
) -> tuple[ParametrosCaso, pd.DataFrame]:
    """Caso y catálogo con un parámetro modificado. El precio se expresa en % del original."""
    if clave == "precio_aislamiento":
        cat = catalogo.copy()
        cat["Precio_CRC_m2"] = pd.to_numeric(cat["Precio_CRC_m2"], errors="coerce") * valor / 100
        return p, cat
    if clave == "vida_util_anios":
        valor = round(valor)
    return replace(p, **{clave: valor}), catalogo


def _mejor(p: ParametrosCaso, catalogo: pd.DataFrame) -> dict | None:
    _, mejor = comparar_alternativas(
        p.recinto(), p.materiales_modelo(), p.refrigeracion(), p.economia(), catalogo, p.sistema
    )
    return mejor


def valor_base(p: ParametrosCaso, clave: str) -> float:
    return 100.0 if clave == "precio_aislamiento" else float(getattr(p, clave))


def sensibilidad(p: ParametrosCaso, catalogo: pd.DataFrame, variacion: float = 0.2) -> pd.DataFrame:
    """Costo total de la mejor alternativa al mover cada parámetro hacia abajo y hacia arriba.

    Indica además si la mejor alternativa cambia en algún extremo.
    """
    base = _mejor(p, catalogo)
    if base is None:
        return pd.DataFrame()
    filas = []
    for clave, parametro in PARAMETROS_SENSIBLES.items():
        v0 = valor_base(p, clave)
        bajo, alto = parametro.variar(v0, variacion)
        mejores = {}
        for extremo, valor in (("bajo", bajo), ("alto", alto)):
            caso, cat = _con_parametro(p, catalogo, clave, valor)
            mejores[extremo] = _mejor(caso, cat)
        if mejores["bajo"] is None or mejores["alto"] is None:
            continue
        filas.append({
            "parametro": parametro.etiqueta,
            "unidad": parametro.unidad,
            "valor_base": v0,
            "valor_bajo": round(bajo) if clave == "vida_util_anios" else bajo,
            "valor_alto": round(alto) if clave == "vida_util_anios" else alto,
            "costo_bajo_CRC": mejores["bajo"]["costo_total_vp_CRC"],
            "costo_alto_CRC": mejores["alto"]["costo_total_vp_CRC"],
            "mejor_bajo": etiqueta_alternativa(mejores["bajo"]),
            "mejor_alto": etiqueta_alternativa(mejores["alto"]),
            "cambia_mejor": etiqueta_alternativa(mejores["bajo"]) != etiqueta_alternativa(base)
                            or etiqueta_alternativa(mejores["alto"]) != etiqueta_alternativa(base),
        })
    df = pd.DataFrame(filas)
    if df.empty:
        return df
    df["costo_base_CRC"] = base["costo_total_vp_CRC"]
    df["rango_CRC"] = (df["costo_alto_CRC"] - df["costo_bajo_CRC"]).abs()
    return df.sort_values("rango_CRC", ascending=False).reset_index(drop=True)


def barrido(
    p: ParametrosCaso, catalogo: pd.DataFrame, clave: str, valores: list[float], maximo_alternativas: int = 5
) -> pd.DataFrame:
    """Costo total de las mejores alternativas del caso base a lo largo de un parámetro.

    Se limita a las ``maximo_alternativas`` mejores del caso base para que las
    curvas sigan siendo legibles; los cruces muestran cuándo cambia la decisión.
    """
    base_df, _ = comparar_alternativas(
        p.recinto(), p.materiales_modelo(), p.refrigeracion(), p.economia(), catalogo, p.sistema
    )
    if base_df.empty:
        return pd.DataFrame()
    seguidas = {etiqueta_alternativa(f) for _, f in base_df.head(maximo_alternativas).iterrows()}

    filas = []
    for valor in valores:
        caso, cat = _con_parametro(p, catalogo, clave, valor)
        df, mejor = comparar_alternativas(
            caso.recinto(), caso.materiales_modelo(), caso.refrigeracion(), caso.economia(), cat, caso.sistema
        )
        etiqueta_mejor = etiqueta_alternativa(mejor) if mejor else None
        for _, fila in df.iterrows():
            etiqueta = etiqueta_alternativa(fila)
            if etiqueta in seguidas:
                filas.append({
                    "valor": round(valor) if clave == "vida_util_anios" else valor,
                    "alternativa": etiqueta,
                    "material": fila["material"],
                    "costo_total_vp_CRC": fila["costo_total_vp_CRC"],
                    "es_mejor": etiqueta == etiqueta_mejor,
                })
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------- #
# Inversión incremental entre espesores
# --------------------------------------------------------------------------- #
def analisis_incremental(alternativas: pd.DataFrame, material: str, economia: Economia) -> pd.DataFrame:
    """Compara cada espesor con el anterior: inversión extra frente a ahorro de energía.

    Para cada espesor se toma el producto de menor precio. El VPN incremental
    positivo indica que el paso al espesor mayor se paga dentro de la vida útil.
    """
    df = alternativas[alternativas["material"] == material]
    if df.empty:
        return pd.DataFrame()
    df = df.sort_values(["espesor_mm", "precio_CRC_m2"]).drop_duplicates("espesor_mm").reset_index(drop=True)
    fvp = factor_valor_presente_anualidad(economia.tasa_descuento_real, economia.vida_util_anios)

    filas = []
    for anterior, siguiente in zip(df.iloc[:-1].itertuples(), df.iloc[1:].itertuples(), strict=True):
        inversion = siguiente.costo_aislamiento_CRC - anterior.costo_aislamiento_CRC
        ahorro_anual = anterior.costo_energia_anual_CRC - siguiente.costo_energia_anual_CRC
        filas.append({
            "proveedor_desde": anterior.proveedor,
            "proveedor_hasta": siguiente.proveedor,
            "espesor_desde_mm": anterior.espesor_mm,
            "espesor_hasta_mm": siguiente.espesor_mm,
            "inversion_adicional_CRC": inversion,
            "ahorro_energia_kWh_anio": anterior.energia_kWh_anio - siguiente.energia_kWh_anio,
            "ahorro_anual_CRC": ahorro_anual,
            "recuperacion_simple_anios": inversion / ahorro_anual if ahorro_anual > 0 and inversion > 0 else None,
            "vpn_incremental_CRC": ahorro_anual * fvp - inversion,
        })
    resultado = pd.DataFrame(filas)
    if not resultado.empty:
        resultado["conviene"] = resultado["vpn_incremental_CRC"] > 0
    return resultado


# --------------------------------------------------------------------------- #
# Comportamiento térmico
# --------------------------------------------------------------------------- #
def curva_termica(
    recinto: Recinto,
    materiales: dict[str, MaterialAislante],
    refrigeracion: SistemaRefrigeracion,
    economia: Economia,
    espesores_mm: range | list[float] = range(10, 201, 5),
) -> pd.DataFrame:
    filas = []
    for nombre, material in materiales.items():
        for espesor in espesores_mm:
            r = evaluar_alternativa(recinto, material, float(espesor), refrigeracion, economia)
            filas.append({
                "material": nombre,
                "espesor_mm": float(espesor),
                "carga_pico_kW": r.carga_critica_total_W / 1000,
                "energia_kWh_anio": r.energia_anual_kWh,
            })
    return pd.DataFrame(filas)


def desglose_superficies(
    recinto: Recinto,
    material: MaterialAislante,
    espesor_mm: float,
    refrigeracion: SistemaRefrigeracion,
    economia: Economia,
) -> pd.DataFrame:
    r = evaluar_alternativa(recinto, material, espesor_mm, refrigeracion, economia)
    g = recinto.geometria
    filas = [
        ("Paredes", g.area_paredes_m2, r.U_paredes_W_m2K, r.carga_critica_paredes_W, r.carga_operacion_paredes_W),
        ("Techo", g.area_techo_m2, r.U_techo_W_m2K, r.carga_critica_techo_W, r.carga_operacion_techo_W),
        ("Piso", g.area_piso_m2, r.U_piso_W_m2K, r.carga_critica_piso_W, r.carga_operacion_piso_W),
    ]
    df = pd.DataFrame(filas, columns=["superficie", "area_m2", "U_W_m2K", "carga_pico_W", "carga_operacion_W"])
    total = df["carga_pico_W"].clip(lower=0).sum()
    df["participacion_pct"] = 100 * df["carga_pico_W"].clip(lower=0) / total if total > 0 else 0.0
    return df


def perfil_pared(
    recinto: Recinto, material: MaterialAislante, espesor_mm: float, condicion: str = "critica"
) -> dict[str, float]:
    """Perfil de temperatura de las paredes para la condición crítica u operación."""
    paredes = recinto.paredes
    t_ext = (
        paredes.temperatura_exterior_critica_C if condicion == "critica"
        else paredes.temperatura_exterior_operacion_C
    )
    return perfil_temperatura_C(paredes, material, espesor_mm, recinto.temperatura_interior_C, t_ext)
