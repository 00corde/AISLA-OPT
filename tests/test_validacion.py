"""Validación numérica V1–V7 de AISLA-OPT (heredada de V4.4).

Ejecutar con: python -m pytest
"""
from __future__ import annotations

import math

import pandas as pd
import pytest

from aisla_opt.mercado import PATRON_COLONES, interpretar_monto
from aisla_opt.motor import (
    Economia,
    GeometriaCuarto,
    MaterialAislante,
    Recinto,
    SistemaRefrigeracion,
    Superficie,
    coeficiente_U,
    evaluar_alternativa,
    factor_valor_presente_anualidad,
)
from aisla_opt.seleccion import comparar_alternativas, espesor_limite_por_capacidad_mm

from .conftest import fila_catalogo

AISLANTE = "Aislante independiente"


def recinto_base() -> Recinto:
    return Recinto(
        geometria=GeometriaCuarto(4, 3, 2.5),
        temperatura_interior_C=5,
        paredes=Superficie("Paredes", 9.1, 9.1, 0.10, 35, 28),
        techo=Superficie("Techo", 9.1, 9.1, 0.10, 38, 30),
        piso=Superficie("Piso", 9.1, 9.1, 0.15, 25, 24),
    )


def recinto_uniforme() -> Recinto:
    s = Superficie("s", 9.1, 9.1, 0.10, 35, 35)
    return Recinto(GeometriaCuarto(4, 3, 2.5), 5, s, s, s)


ECONOMIA = Economia(120, 6000, 10, 0.05)


def test_v1_calculo_manual():
    r = evaluar_alternativa(
        recinto_base(), MaterialAislante("PU", 0.026), 100.0, SistemaRefrigeracion(3.0, 1.10), ECONOMIA
    )
    # Cálculo independiente con las ecuaciones del modelo.
    e_m = 0.100
    r_p = 1 / 9.1 + 0.10 + e_m / 0.026 + 1 / 9.1
    r_i = 1 / 9.1 + 0.15 + e_m / 0.026 + 1 / 9.1
    u_p, u_t, u_i = 1 / r_p, 1 / r_p, 1 / r_i
    a_p, a_t, a_i = 35.0, 12.0, 12.0
    q_crit = u_p * a_p * (35 - 5) + u_t * a_t * (38 - 5) + u_i * a_i * (25 - 5)
    q_op = u_p * a_p * (28 - 5) + u_t * a_t * (30 - 5) + u_i * a_i * (24 - 5)

    assert r.carga_critica_total_W == pytest.approx(q_crit, rel=1e-12)
    assert r.capacidad_recomendada_W == pytest.approx(1.10 * q_crit, rel=1e-12)
    assert r.energia_anual_kWh == pytest.approx((q_op / 3.0) / 1000 * 6000, rel=1e-12)


def test_v2_biseccion_igual_a_solucion_cerrada():
    # Tres superficies iguales, 59 m² en total y ΔT = 30 K.
    e = espesor_limite_por_capacidad_mm(
        recinto_uniforme(), MaterialAislante("PU", 0.026), SistemaRefrigeracion(3.0, 1.10, 800.0), ECONOMIA
    )
    r_superficie = 1 / 9.1 + 0.10 + 1 / 9.1
    e_cerrada_m = 0.026 * ((1.10 * 59 * 30 / 800) - r_superficie)
    assert e == pytest.approx(1000 * e_cerrada_m, rel=1e-9)


def test_v3_fvp_y_monotonicidad():
    assert factor_valor_presente_anualidad(0.0, 10) == pytest.approx(10.0)
    material, refrig = MaterialAislante("PU", 0.026), SistemaRefrigeracion(3.0, 1.10)
    r50 = evaluar_alternativa(recinto_base(), material, 50.0, refrig, ECONOMIA)
    r100 = evaluar_alternativa(recinto_base(), material, 100.0, refrig, ECONOMIA)
    assert r100.carga_critica_total_W < r50.carga_critica_total_W
    assert r100.energia_anual_kWh < r50.energia_anual_kWh


def test_v4_k_de_ficha_con_respaldo_generico():
    eps = MaterialAislante("Poliestireno expandido (EPS)", 0.037)
    catalogo = pd.DataFrame([
        fila_catalogo(eps.nombre, "EPS A", 50.0, 3000.0, k=0.040, iva="Sí"),
        fila_catalogo(eps.nombre, "EPS B", 100.0, 5000.0, iva="Sí"),
    ])
    df, mejor = comparar_alternativas(
        recinto_base(), {eps.nombre: eps}, SistemaRefrigeracion(3.0, 1.10), ECONOMIA, catalogo, AISLANTE
    )
    assert len(df) == 2 and mejor is not None
    k_por_espesor = dict(zip(df["espesor_mm"], df["k_W_mK"], strict=True))
    assert k_por_espesor[50.0] == pytest.approx(0.040)
    assert k_por_espesor[100.0] == pytest.approx(0.037)


@pytest.mark.parametrize("texto, esperado", [
    ("Precio ₡6.393 2 disponibles", 6393.0),
    ("Precio ₡15 815,00", 15815.0),
    ("Precio ₡15\u00a0815,00", 15815.0),
    ("Precio ₡6393", 6393.0),
    ("Precio ₡6 393,00 2 disponibles", 6393.0),
])
def test_v5_interpretar_precios_en_colones(texto, esperado):
    coincidencia = PATRON_COLONES.search(texto)
    assert coincidencia, f"No se capturó precio en: {texto!r}"
    assert interpretar_monto(coincidencia.group(1)) == pytest.approx(esperado)


def test_v6_ejemplo_3_17_cengel():
    # Çengel & Ghajar, 6.ª ed., Ej. 3-17: 2730 Btu/h y 19.2 kWh/día.
    btu_h_ft2_F_a_W_m2K = 5.678263
    superficie = Superficie("pared", 1.46 * btu_h_ft2_F_a_W_m2K, 6.0 * btu_h_ft2_F_a_W_m2K, 0.0, 45, 45)
    r13_m2K_W = 13 / btu_h_ft2_F_a_W_m2K
    u = coeficiente_U(superficie, MaterialAislante("R-13 equivalente", 1.0), r13_m2K_W)
    q_W = u * (1260 * 0.09290304) * (30 / 1.8)

    assert q_W * 3.412141 == pytest.approx(2730.0, rel=2e-3)
    assert q_W * 24 / 1000 == pytest.approx(19.2, rel=3e-3)


def test_v7_capacidad_con_k_de_ficha_y_condicion_comercial():
    material = MaterialAislante("Prueba", 0.037)
    refrig = SistemaRefrigeracion(3.0, 1.10, 1000.0)
    catalogo = pd.DataFrame([
        fila_catalogo(material.nombre, "k mejor", 50.7, 3000.0, k=0.025, iva="Sí"),
        fila_catalogo(material.nombre, "k peor", 50.7, 2900.0, k=0.050, iva="Sí"),
    ])
    e_generico = espesor_limite_por_capacidad_mm(recinto_uniforme(), material, refrig, ECONOMIA)
    assert e_generico is not None and not math.isinf(e_generico) and e_generico > 50.7

    df, mejor = comparar_alternativas(
        recinto_uniforme(), {material.nombre: material}, refrig, ECONOMIA, catalogo, AISLANTE
    )
    assert mejor is not None
    assert set(df["producto"]) == {"k mejor"}
    assert df.iloc[0]["iva"] == "Sí"
    assert "condicion" in df.columns
