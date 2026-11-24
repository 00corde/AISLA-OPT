from __future__ import annotations

from dataclasses import replace
from typing import Optional
import math
import pandas as pd

from aisla_opt_v2 import MaterialAislante, evaluar_alternativa


def material_para_calculo(material: MaterialAislante) -> MaterialAislante:
    """Material dummy for thermal evaluation; commercial cost is applied later."""
    return MaterialAislante(
        nombre=material.nombre,
        conductividad_W_mK=material.conductividad_W_mK,
        costo_CRC_m3=0.0,
        espesores_comerciales_mm=(1.0,),
    )


def espesor_minimo_termico_mm(
    geometria,
    interior,
    paredes,
    techo,
    piso,
    material,
    refrigeracion,
    economia,
    e_max_mm: float = 400.0,
) -> Optional[float]:
    """
    Continuous minimum thickness that makes the recommended refrigeration
    capacity <= the user-specified available equipment capacity.

    Returns:
      - None if no equipment-capacity constraint is defined.
      - float if a solution exists.
      - math.inf if even e_max_mm does not meet the constraint.
    """
    if refrigeracion.capacidad_equipo_existente_W is None:
        return None

    m = material_para_calculo(material)

    r_lo = evaluar_alternativa(
        geometria, interior, paredes, techo, piso, m, 0.1, refrigeracion, economia
    )
    if r_lo.cumple_capacidad_equipo:
        return 0.1

    r_hi = evaluar_alternativa(
        geometria, interior, paredes, techo, piso, m, e_max_mm, refrigeracion, economia
    )
    if not r_hi.cumple_capacidad_equipo:
        return math.inf

    lo, hi = 0.1, e_max_mm
    for _ in range(50):
        mid = (lo + hi) / 2.0
        r = evaluar_alternativa(
            geometria, interior, paredes, techo, piso, m, mid, refrigeracion, economia
        )
        if r.cumple_capacidad_equipo:
            hi = mid
        else:
            lo = mid

    return hi


def evaluar_producto(
    geometria,
    interior,
    paredes,
    techo,
    piso,
    material,
    refrigeracion,
    economia,
    espesor_mm: float,
    precio_crc_m2: Optional[float],
):
    """Evaluate exact commercial thickness; apply actual market price if available."""
    r = evaluar_alternativa(
        geometria, interior, paredes, techo, piso,
        material_para_calculo(material),
        float(espesor_mm),
        refrigeracion,
        economia,
    )

    if precio_crc_m2 is None or pd.isna(precio_crc_m2) or float(precio_crc_m2) <= 0:
        return r

    costo_aisl = geometria.area_total_m2 * float(precio_crc_m2)
    return replace(
        r,
        costo_aislamiento_CRC=costo_aisl,
        costo_total_valor_presente_CRC=costo_aisl + r.costo_energia_valor_presente_CRC,
    )


def inventario_material(catalogo: pd.DataFrame, material: str, sistema: str) -> pd.DataFrame:
    x = catalogo.copy()
    x["Activo"] = x["Activo"].fillna(False).astype(bool)
    x["Espesor_mm"] = pd.to_numeric(x["Espesor_mm"], errors="coerce")
    x["Precio_CRC_m2"] = pd.to_numeric(x["Precio_CRC_m2"], errors="coerce")

    return x[
        x["Activo"]
        & (x["Material"].astype(str) == str(material))
        & (x["Sistema"].astype(str) == str(sistema))
        & x["Espesor_mm"].notna()
        & (x["Espesor_mm"] > 0)
    ].copy()


def primer_comercial_que_cumple(
    catalogo: pd.DataFrame,
    material: str,
    sistema: str,
    espesor_requerido_mm: Optional[float],
):
    """Smallest documented commercial size >= theoretical required thickness."""
    if espesor_requerido_mm is None or math.isinf(espesor_requerido_mm):
        return None

    inv = inventario_material(catalogo, material, sistema)
    if inv.empty:
        return None

    cubren = inv[inv["Espesor_mm"] + 1e-9 >= float(espesor_requerido_mm)]
    if cubren.empty:
        return None

    e_min = float(cubren["Espesor_mm"].min())
    same = cubren[abs(cubren["Espesor_mm"] - e_min) < 1e-9].copy()

    # If multiple vendors offer the same first size, prefer one with a documented
    # price, then the lowest price. This does not affect the required thickness.
    same["_precio_ok"] = same["Precio_CRC_m2"].notna() & (same["Precio_CRC_m2"] > 0)
    same["_precio_sort"] = same["Precio_CRC_m2"].fillna(float("inf"))
    same = same.sort_values(["_precio_ok", "_precio_sort"], ascending=[False, True])

    row = same.iloc[0].drop(labels=["_precio_ok", "_precio_sort"]).to_dict()
    return row


def candidatos_comerciales_que_cumplen(
    catalogo: pd.DataFrame,
    material: str,
    sistema: str,
    espesor_requerido_mm: Optional[float],
) -> pd.DataFrame:
    """
    Con restricción térmica: devuelve productos que la cumplen.
    Sin capacidad de equipo definida: no inventa un mínimo y permite
    comparar económicamente todos los productos documentados del material.
    """
    if espesor_requerido_mm is not None and math.isinf(espesor_requerido_mm):
        return pd.DataFrame(columns=catalogo.columns)

    inv = inventario_material(catalogo, material, sistema)

    if espesor_requerido_mm is None:
        return inv.copy()

    return inv[inv["Espesor_mm"] + 1e-9 >= float(espesor_requerido_mm)].copy()


def seleccionar_economicamente(
    geometria,
    interior,
    paredes,
    techo,
    piso,
    materiales_por_nombre: dict,
    refrigeracion,
    economia,
    catalogo: pd.DataFrame,
    sistema: str,
    espesores_requeridos: dict[str, Optional[float]],
):
    """
    Compare every priced commercial product that meets the theoretical
    requirement for its material. Return all evaluated rows and the minimum
    life-cycle-cost alternative.
    """
    filas = []

    for material_nombre, material in materiales_por_nombre.items():
        # La factibilidad por capacidad se decide con la k real de cada producto.
        # El límite continuo mostrado en la UI usa la k genérica del material y no
        # debe prefiltrar productos que podrían cumplir con una ficha técnica mejor.
        candidatos = candidatos_comerciales_que_cumplen(
            catalogo, material_nombre, sistema, None
        )

        for _, row in candidatos.iterrows():
            precio = row.get("Precio_CRC_m2")
            if pd.isna(precio) or float(precio) <= 0:
                continue

            k_producto = pd.to_numeric(pd.Series([row.get("k_W_mK")]), errors="coerce").iloc[0]
            material_producto = material
            if pd.notna(k_producto) and float(k_producto) > 0:
                material_producto = replace(
                    material,
                    conductividad_W_mK=float(k_producto),
                )

            r = evaluar_producto(
                geometria, interior, paredes, techo, piso,
                material_producto, refrigeracion, economia,
                float(row["Espesor_mm"]),
                float(precio),
            )

            if not r.cumple_capacidad_equipo:
                continue

            filas.append({
                "Material": material_nombre,
                "Proveedor": row.get("Proveedor", "—"),
                "Producto": row.get("Producto", "—"),
                "Espesor [mm]": float(row["Espesor_mm"]),
                "Precio [CRC/m²]": float(precio),
                "k usada [W/m·K]": float(material_producto.conductividad_W_mK),
                "Carga pico transmisión [kW]": r.carga_critica_total_W / 1000.0,
                "Transmisión + margen [kW]": r.capacidad_recomendada_W / 1000.0,
                "Energía transmisión [kWh/año]": r.energia_anual_kWh,
                "Costo aislamiento [CRC]": r.costo_aislamiento_CRC,
                "Costo energía VP [CRC]": r.costo_energia_valor_presente_CRC,
                "Costo total VP [CRC]": r.costo_total_valor_presente_CRC,
                "IVA": row.get("IVA_incluido", "No indicado") or "No indicado",
                "Condición": row.get("Condicion_precio", "") or "",
                "Fecha": row.get("Fecha", ""),
                "Fuente": row.get("Fuente", ""),
            })

    df = pd.DataFrame(filas)
    if df.empty:
        return df, None

    idx = df["Costo total VP [CRC]"].astype(float).idxmin()
    return df, df.loc[idx].to_dict()
