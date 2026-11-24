"""Pruebas numéricas mínimas de AISLA-OPT V4.3.
Ejecutar con: py pruebas_validacion.py
"""
from __future__ import annotations

import math
import pandas as pd

from aisla_opt_v2 import (
    GeometriaCuarto, Superficie, CondicionesInterior, MaterialAislante,
    SistemaRefrigeracion, Economia, evaluar_alternativa,
    factor_valor_presente_anualidad, coeficiente_U,
)
from seleccion_ingenieril import espesor_minimo_termico_mm, seleccionar_economicamente
from mercado_cr import _numero, CRC_RE


def close(a, b, rel=1e-6, abs_=1e-9):
    assert math.isclose(a, b, rel_tol=rel, abs_tol=abs_), f"{a} != {b}"


def caso_base():
    g = GeometriaCuarto(4, 3, 2.5)
    interior = CondicionesInterior(5)
    paredes = Superficie("Paredes", 9.1, 9.1, 0.10, 35, 28)
    techo = Superficie("Techo", 9.1, 9.1, 0.10, 38, 30)
    piso = Superficie("Piso", 9.1, 9.1, 0.15, 25, 24)
    mat = MaterialAislante("PU", 0.026, 0.0, (100.0,))
    refrig = SistemaRefrigeracion(3.0, 1.10, None)
    econ = Economia(120, 6000, 10, 0.05)
    return g, interior, paredes, techo, piso, mat, refrig, econ


def v1_calculo_manual():
    g, interior, paredes, techo, piso, mat, refrig, econ = caso_base()
    r = evaluar_alternativa(g, interior, paredes, techo, piso, mat, 100.0, refrig, econ)

    # Cálculo independiente con las ecuaciones del modelo, sin copiar salidas previas.
    e_m = 0.100
    r_p = 1/9.1 + 0.10 + e_m/0.026 + 1/9.1
    r_t = r_p
    r_i = 1/9.1 + 0.15 + e_m/0.026 + 1/9.1
    u_p, u_t, u_i = 1/r_p, 1/r_t, 1/r_i
    a_p, a_t, a_i = 35.0, 12.0, 12.0
    qcrit = u_p*a_p*(35-5) + u_t*a_t*(38-5) + u_i*a_i*(25-5)
    qrec = 1.10*qcrit
    qop = u_p*a_p*(28-5) + u_t*a_t*(30-5) + u_i*a_i*(24-5)
    energia = (qop/3.0)/1000 * 6000

    close(r.carga_critica_total_W, qcrit, rel=1e-12)
    close(r.capacidad_recomendada_W, qrec, rel=1e-12)
    close(r.energia_anual_kWh, energia, rel=1e-12)
    print("V1 OK: cálculo manual base")


def v2_biseccion_cerrada():
    # Caso construido con tres superficies iguales y áreas que suman 59 m².
    # Usamos una geometría 4×3×2.5 (59 m² total) y mismas ΔT/R en todas.
    g = GeometriaCuarto(4, 3, 2.5)
    interior = CondicionesInterior(5)
    s = Superficie("s", 9.1, 9.1, 0.10, 35, 35)
    mat = MaterialAislante("PU", 0.026, 0.0, (1.0,))
    refrig = SistemaRefrigeracion(3.0, 1.10, 800.0)
    econ = Economia(120, 6000, 10, 0.05)
    e = espesor_minimo_termico_mm(g, interior, s, s, s, mat, refrig, econ)
    r_surface = 1/9.1 + 0.10 + 1/9.1
    e_closed_m = 0.026 * ((1.10 * 59 * 30 / 800) - r_surface)
    close(e, 1000*e_closed_m, rel=1e-9)
    print("V2 OK: bisección = solución cerrada")


def v3_finanzas_y_monotonia():
    close(factor_valor_presente_anualidad(0.0, 10), 10.0)
    g, interior, paredes, techo, piso, mat, refrig, econ = caso_base()
    r50 = evaluar_alternativa(g, interior, paredes, techo, piso, mat, 50.0, refrig, econ)
    r100 = evaluar_alternativa(g, interior, paredes, techo, piso, mat, 100.0, refrig, econ)
    assert r100.carga_critica_total_W < r50.carga_critica_total_W
    assert r100.energia_anual_kWh < r50.energia_anual_kWh
    print("V3 OK: FVP i=0 y monotonicidad")


def v4_k_por_producto_y_catalogo():
    g, interior, paredes, techo, piso, _, refrig, econ = caso_base()
    mat = MaterialAislante("Poliestireno expandido (EPS)", 0.037, 0.0, (1.0,))
    cat = pd.DataFrame([
        {
            "Activo": True, "Sistema": "Aislante independiente",
            "Material": mat.nombre, "Proveedor": "Prueba", "Producto": "EPS A",
            "Espesor_mm": 50.0, "Precio_CRC_m2": 3000.0, "k_W_mK": 0.040,
            "Densidad_kg_m3": 16.0, "IVA_incluido": "Sí", "Condicion_precio": "prueba",
            "Estado_precio": "prueba", "Fecha": "2026-11-21", "Fuente": ""
        },
        {
            "Activo": True, "Sistema": "Aislante independiente",
            "Material": mat.nombre, "Proveedor": "Prueba", "Producto": "EPS B",
            "Espesor_mm": 100.0, "Precio_CRC_m2": 5000.0, "k_W_mK": None,
            "Densidad_kg_m3": None, "IVA_incluido": "Sí", "Condicion_precio": "prueba",
            "Estado_precio": "prueba", "Fecha": "2026-11-21", "Fuente": ""
        },
    ])
    df, best = seleccionar_economicamente(
        g, interior, paredes, techo, piso,
        {mat.nombre: mat}, refrig, econ, cat, "Aislante independiente", {mat.nombre: None}
    )
    assert len(df) == 2 and best is not None
    k50 = float(df.loc[df["Espesor [mm]"] == 50.0, "k usada [W/m·K]"].iloc[0])
    k100 = float(df.loc[df["Espesor [mm]"] == 100.0, "k usada [W/m·K]"].iloc[0])
    close(k50, 0.040)
    close(k100, 0.037)
    print("V4 OK: k específica por producto con fallback técnico")


def v5_parser_precio():
    casos = {
        "Precio ₡6.393 2 disponibles": 6393.0,
        "Precio ₡15 815,00": 15815.0,
        "Precio ₡15\u00a0815,00": 15815.0,
        "Precio ₡6393": 6393.0,
        "Precio ₡6 393,00 2 disponibles": 6393.0,
    }
    for txt, esperado in casos.items():
        m = CRC_RE.search(txt)
        assert m, f"No se capturó precio en: {txt!r}"
        close(_numero(m.group(1)), esperado)
    print("V5 OK: parser acepta separadores CRC sin tragarse stock")


def v6_cengel_ejemplo_3_17():
    # Çengel & Ghajar 6.ª ed., Ej. 3-17: 2730 Btu/h y 19.2 kWh/día.
    btu_h_ft2_f_a_w_m2k = 5.678263
    hi = 1.46 * btu_h_ft2_f_a_w_m2k
    ho = 6.0 * btu_h_ft2_f_a_w_m2k
    r13_m2k_w = 13 / btu_h_ft2_f_a_w_m2k
    area_m2 = 1260 * 0.09290304
    delta_t_k = 30 / 1.8

    superficie = Superficie("pared", hi, ho, 0.0, 45, 45)
    material = MaterialAislante("R-13 equivalente", 1.0, 0.0, (1.0,))
    u = coeficiente_U(superficie, material, r13_m2k_w)
    q_w = u * area_m2 * delta_t_k

    close(q_w * 3.412141, 2730.0, rel=2e-3)
    close(q_w * 24 / 1000, 19.2, rel=3e-3)
    print("V6 OK: reproducción del Ejemplo 3-17 de Çengel")


def v7_capacidad_con_k_especifica():
    g = GeometriaCuarto(4, 3, 2.5)
    interior = CondicionesInterior(5)
    s = Superficie("s", 9.1, 9.1, 0.10, 35, 35)
    mat = MaterialAislante("Prueba", 0.037, 0.0, (1.0,))
    refrig = SistemaRefrigeracion(3.0, 1.10, 1000.0)
    econ = Economia(120, 6000, 10, 0.05)

    cat = pd.DataFrame([
        {
            "Activo": True, "Sistema": "Aislante independiente", "Material": mat.nombre,
            "Proveedor": "Prueba", "Producto": "k mejor", "Espesor_mm": 50.7,
            "Precio_CRC_m2": 3000.0, "k_W_mK": 0.025, "Densidad_kg_m3": None,
            "IVA_incluido": "Sí", "Condicion_precio": "prueba",
            "Estado_precio": "prueba", "Fecha": "2026-11-22", "Fuente": ""
        },
        {
            "Activo": True, "Sistema": "Aislante independiente", "Material": mat.nombre,
            "Proveedor": "Prueba", "Producto": "k peor", "Espesor_mm": 50.7,
            "Precio_CRC_m2": 2900.0, "k_W_mK": 0.050, "Densidad_kg_m3": None,
            "IVA_incluido": "Sí", "Condicion_precio": "prueba",
            "Estado_precio": "prueba", "Fecha": "2026-11-22", "Fuente": ""
        },
    ])

    e_generico = espesor_minimo_termico_mm(g, interior, s, s, s, mat, refrig, econ)
    assert e_generico is not None and e_generico > 50.7
    df, best = seleccionar_economicamente(
        g, interior, s, s, s, {mat.nombre: mat}, refrig, econ, cat,
        "Aislante independiente", {mat.nombre: e_generico}
    )
    assert best is not None
    assert set(df["Producto"]) == {"k mejor"}
    assert {"IVA", "Condición"}.issubset(df.columns)
    assert df.iloc[0]["IVA"] == "Sí"
    print("V7 OK: capacidad usa k específica y conserva condición comercial")


if __name__ == "__main__":
    v1_calculo_manual()
    v2_biseccion_cerrada()
    v3_finanzas_y_monotonia()
    v4_k_por_producto_y_catalogo()
    v5_parser_precio()
    v6_cengel_ejemplo_3_17()
    v7_capacidad_con_k_especifica()
    print("TODAS LAS PRUEBAS V1–V7 APROBADAS")
