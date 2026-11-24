from __future__ import annotations

import io

import pandas as pd
import pytest

from aisla_opt import catalogo as cat

from .conftest import fila_catalogo

EPS = "Poliestireno expandido (EPS)"


def test_catalogo_incluido_tiene_esquema_completo():
    df = cat.cargar()
    assert list(df.columns) == cat.COLUMNAS
    assert not cat.k_fuera_de_rango(df).any()


def test_actualizacion_web_conserva_datos_tecnicos():
    base = pd.DataFrame([fila_catalogo(EPS, "EPS 50", 50.0, 3000.0, k=0.036, iva="Sí")])
    web = {**fila_catalogo(EPS, "EPS 50", 50.0, 3500.0), "Estado_precio": "web", "Fecha": "2026-12-01"}
    nuevo = cat.upsert(base, [web], solo_precio=True)
    assert len(nuevo) == 1
    fila = nuevo.iloc[0]
    assert fila["Precio_CRC_m2"] == 3500.0 and fila["Fecha"] == "2026-12-01"
    assert fila["k_W_mK"] == 0.036 and fila["IVA_incluido"] == "Sí"


def test_espesores_distintos_no_se_sobrescriben():
    base = pd.DataFrame([fila_catalogo(EPS, "EPS", 50.0, 3000.0)])
    nuevo = cat.upsert(base, [fila_catalogo(EPS, "EPS", 75.0, 4000.0)])
    assert sorted(nuevo["Espesor_mm"]) == [50.0, 75.0]


def test_csv_normaliza_fechas_a_iso():
    df = pd.DataFrame([{**fila_catalogo(EPS, "EPS", 50.0, 3000.0), "Fecha": "2026/11/05"}])
    leido = pd.read_csv(io.StringIO(cat.a_csv(df)))
    assert leido.loc[0, "Fecha"] == "2026-11-05"


def test_csv_subido_sin_columnas_clave_se_rechaza():
    with pytest.raises(ValueError, match="Faltan columnas"):
        cat.leer_csv_subido(io.StringIO("Producto,Precio\nA,1\n"))


@pytest.mark.parametrize("unidad, kwargs, esperado", [
    ("m2", {}, 5000.0),
    ("lamina", {"ancho_m": 1.22, "largo_m": 2.44}, 5000.0 / (1.22 * 2.44)),
    ("paquete", {"ancho_m": 1.0, "largo_m": 2.0, "unidades_por_paquete": 5}, 500.0),
])
def test_precio_por_m2(unidad, kwargs, esperado):
    assert cat.precio_por_m2(5000.0, unidad, **kwargs) == pytest.approx(esperado)


def test_precio_por_lamina_exige_dimensiones():
    with pytest.raises(ValueError, match="ancho"):
        cat.precio_por_m2(5000.0, "lamina")


def test_resumen_por_material_cuenta_precios():
    df = pd.DataFrame([
        fila_catalogo(EPS, "A", 50.0, 3000.0),
        fila_catalogo(EPS, "B", 75.0, None),
    ])
    resumen = cat.resumen_por_material(df, "Aislante independiente", [EPS, "Corcho"]).set_index("Material")
    assert resumen.loc[EPS, "Productos"] == 2 and resumen.loc[EPS, "Con precio"] == 1
    assert resumen.loc["Corcho", "Productos"] == 0
