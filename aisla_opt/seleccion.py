"""Del cálculo continuo al producto comercial y comparación por costo de ciclo de vida."""
from __future__ import annotations

import math
from dataclasses import replace

import pandas as pd

from .catalogo import inventario_material
from .motor import (
    Economia,
    MaterialAislante,
    Recinto,
    SistemaRefrigeracion,
    evaluar_alternativa,
)

ESPESOR_MINIMO_BUSQUEDA_mm = 0.1
ESPESOR_MAXIMO_BUSQUEDA_mm = 400.0
ITERACIONES_BISECCION = 50

COLUMNAS_ALTERNATIVAS = [
    "material", "proveedor", "producto", "espesor_mm", "precio_CRC_m2", "k_W_mK", "k_de_ficha",
    "carga_pico_kW", "transmision_con_margen_kW", "energia_kWh_anio", "costo_aislamiento_CRC",
    "costo_energia_anual_CRC", "costo_energia_vp_CRC", "costo_total_vp_CRC",
    "diferencia_vs_mejor_CRC", "iva", "condicion", "fecha", "fuente",
]


def espesor_limite_por_capacidad_mm(
    recinto: Recinto,
    material: MaterialAislante,
    refrigeracion: SistemaRefrigeracion,
    economia: Economia,
    espesor_maximo_mm: float = ESPESOR_MAXIMO_BUSQUEDA_mm,
) -> float | None:
    """Espesor continuo mínimo que hace transmisión + margen ≤ capacidad disponible.

    Devuelve ``None`` si no hay restricción de capacidad, ``math.inf`` si ni
    siquiera ``espesor_maximo_mm`` la cumple, o el espesor en mm (bisección).
    """
    if refrigeracion.capacidad_disponible_W is None:
        return None

    def cumple(espesor_mm: float) -> bool:
        return evaluar_alternativa(recinto, material, espesor_mm, refrigeracion, economia).cumple_capacidad

    bajo, alto = ESPESOR_MINIMO_BUSQUEDA_mm, espesor_maximo_mm
    if cumple(bajo):
        return bajo
    if not cumple(alto):
        return math.inf
    for _ in range(ITERACIONES_BISECCION):
        medio = (bajo + alto) / 2
        if cumple(medio):
            alto = medio
        else:
            bajo = medio
    return alto


def primer_comercial_que_cubre(
    catalogo: pd.DataFrame, material: str, sistema: str, espesor_requerido_mm: float | None
) -> dict | None:
    """Menor espesor documentado ≥ al requerido. Entre empates prefiere el que tiene precio más bajo."""
    if espesor_requerido_mm is None or math.isinf(espesor_requerido_mm):
        return None
    inventario = inventario_material(catalogo, material, sistema)
    cubren = inventario[inventario["Espesor_mm"] + 1e-9 >= float(espesor_requerido_mm)]
    if cubren.empty:
        return None

    espesor_minimo = float(cubren["Espesor_mm"].min())
    empates = cubren[(cubren["Espesor_mm"] - espesor_minimo).abs() < 1e-9].copy()
    empates["_tiene_precio"] = empates["Precio_CRC_m2"].notna() & (empates["Precio_CRC_m2"] > 0)
    empates["_precio_orden"] = empates["Precio_CRC_m2"].fillna(float("inf"))
    empates = empates.sort_values(["_tiene_precio", "_precio_orden"], ascending=[False, True])
    return empates.iloc[0].drop(labels=["_tiene_precio", "_precio_orden"]).to_dict()


def clasificar_margen_comercial(margen_mm: float, espesor_comercial_mm: float) -> str:
    """Qué tan cerca queda el límite continuo de obligar al siguiente tamaño comercial."""
    if margen_mm <= max(2.0, 0.05 * espesor_comercial_mm):
        return "Cerca del salto"
    if margen_mm <= max(5.0, 0.15 * espesor_comercial_mm):
        return "Margen moderado"
    return "Margen amplio"


def limites_por_capacidad(
    recinto: Recinto,
    materiales: dict[str, MaterialAislante],
    refrigeracion: SistemaRefrigeracion,
    economia: Economia,
    catalogo: pd.DataFrame,
    sistema: str,
) -> pd.DataFrame:
    """Tabla límite continuo → primer comercial que lo cubre, por material."""
    filas = []
    for nombre, material in materiales.items():
        limite = espesor_limite_por_capacidad_mm(recinto, material, refrigeracion, economia)
        fila = {
            "material": nombre,
            "limite_mm": None if limite is None or math.isinf(limite) else float(limite),
            "supera_busqueda": limite is not None and math.isinf(limite),
            "espesor_comercial_mm": None,
            "margen_mm": None,
            "margen_pct": None,
            "sensibilidad": None,
            "proveedor": None,
            "precio_CRC_m2": None,
        }
        primero = primer_comercial_que_cubre(catalogo, nombre, sistema, limite)
        if primero is not None:
            espesor = float(primero["Espesor_mm"])
            margen = max(0.0, espesor - float(limite))
            fila.update({
                "espesor_comercial_mm": espesor,
                "margen_mm": margen,
                "margen_pct": 100 * margen / limite if limite > 0 else None,
                "sensibilidad": clasificar_margen_comercial(margen, espesor),
                "proveedor": primero.get("Proveedor"),
                "precio_CRC_m2": primero.get("Precio_CRC_m2"),
            })
        filas.append(fila)
    return pd.DataFrame(filas)


def _texto(valor, por_defecto: str = "") -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return por_defecto
    texto = str(valor).strip()
    return texto or por_defecto


def comparar_alternativas(
    recinto: Recinto,
    materiales: dict[str, MaterialAislante],
    refrigeracion: SistemaRefrigeracion,
    economia: Economia,
    catalogo: pd.DataFrame,
    sistema: str,
) -> tuple[pd.DataFrame, dict | None]:
    """Evalúa cada producto con precio y devuelve la tabla ordenada y la mejor alternativa.

    La factibilidad por capacidad se decide con la k de ficha de cada producto
    (o la k genérica si no hay ficha); el límite continuo de la interfaz usa
    la k genérica y por eso no se usa como prefiltro.
    """
    filas = []
    for nombre, material in materiales.items():
        for _, producto in inventario_material(catalogo, nombre, sistema).iterrows():
            precio = producto["Precio_CRC_m2"]
            if pd.isna(precio) or float(precio) <= 0:
                continue

            k_ficha = producto["k_W_mK"]
            tiene_ficha = pd.notna(k_ficha) and float(k_ficha) > 0
            material_producto = (
                replace(material, conductividad_W_mK=float(k_ficha)) if tiene_ficha else material
            )
            r = evaluar_alternativa(
                recinto, material_producto, float(producto["Espesor_mm"]),
                refrigeracion, economia, float(precio),
            )
            if not r.cumple_capacidad:
                continue

            filas.append({
                "material": nombre,
                "proveedor": _texto(producto.get("Proveedor"), "—"),
                "producto": _texto(producto.get("Producto"), "—"),
                "espesor_mm": float(producto["Espesor_mm"]),
                "precio_CRC_m2": float(precio),
                "k_W_mK": material_producto.conductividad_W_mK,
                "k_de_ficha": bool(tiene_ficha),
                "carga_pico_kW": r.carga_critica_total_W / 1000,
                "transmision_con_margen_kW": r.capacidad_recomendada_W / 1000,
                "energia_kWh_anio": r.energia_anual_kWh,
                "costo_aislamiento_CRC": r.costo_aislamiento_CRC,
                "costo_energia_anual_CRC": r.costo_energia_anual_CRC,
                "costo_energia_vp_CRC": r.costo_energia_valor_presente_CRC,
                "costo_total_vp_CRC": r.costo_total_valor_presente_CRC,
                "iva": _texto(producto.get("IVA_incluido"), "No indicado"),
                "condicion": _texto(producto.get("Condicion_precio")),
                "fecha": _texto(producto.get("Fecha")),
                "fuente": _texto(producto.get("Fuente")),
            })

    if not filas:
        return pd.DataFrame(columns=COLUMNAS_ALTERNATIVAS), None

    df = pd.DataFrame(filas)
    df["diferencia_vs_mejor_CRC"] = df["costo_total_vp_CRC"] - df["costo_total_vp_CRC"].min()
    df = df.sort_values("costo_total_vp_CRC", kind="stable").reset_index(drop=True)[COLUMNAS_ALTERNATIVAS]
    return df, df.iloc[0].to_dict()
