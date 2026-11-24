from __future__ import annotations

import io
from dataclasses import replace

import pandas as pd
import pytest
from openpyxl import load_workbook

from aisla_opt import analisis, formato
from aisla_opt.caso import PLANTILLAS, ParametrosCaso, caso_desde_plantilla, evaluar_caso
from aisla_opt.catalogo import cargar
from aisla_opt.motor import MaterialAislante, Superficie, perfil_temperatura_C
from aisla_opt.reporte import generar_excel

EPS = "Poliestireno expandido (EPS)"


def test_escenario_json_ida_y_vuelta():
    caso = ParametrosCaso(largo_m=6.5, k_ficha_W_mK={EPS: 0.034}, usar_capacidad=True)
    assert ParametrosCaso.desde_json(caso.a_json()) == caso


def test_escenario_json_ignora_claves_desconocidas():
    caso = ParametrosCaso.desde_dict({"largo_m": 7.0, "clave_futura": 1})
    assert caso.largo_m == 7.0


def test_k_de_ficha_implausible_se_rechaza():
    with pytest.raises(ValueError, match="fuera del rango"):
        ParametrosCaso(k_ficha_W_mK={EPS: 37.0}).validar()


@pytest.mark.parametrize("nombre", list(PLANTILLAS))
def test_plantillas_son_casos_validos(nombre):
    caso = caso_desde_plantilla(nombre, ParametrosCaso(materiales=[EPS]))
    caso.validar()
    assert caso.materiales == [EPS]


def test_evaluacion_con_catalogo_incluido_encuentra_mejor():
    resultado = evaluar_caso(ParametrosCaso(), cargar())
    assert resultado.hay_comparacion
    assert resultado.alternativas["costo_total_vp_CRC"].is_monotonic_increasing
    assert resultado.alternativas.iloc[0]["diferencia_vs_mejor_CRC"] == 0
    # XPS no tiene productos con precio en el catálogo incluido: debe avisarse.
    assert any("Poliestireno extruido" in a.texto for a in resultado.avisos)


def test_panel_sin_precios_avisa_y_no_compara():
    resultado = evaluar_caso(
        ParametrosCaso(sistema="Panel frigorífico completo", materiales=["Poliuretano (PU)"]), cargar()
    )
    assert not resultado.hay_comparacion
    assert any("No hay productos con precio" in a.texto for a in resultado.avisos)


def test_posicion_borde_superior(catalogo_eps, caso_eps):
    resultado = evaluar_caso(replace(caso_eps, tarifa_CRC_kWh=500), catalogo_eps)
    assert resultado.posicion_mejor == "borde_superior"


def test_sensibilidad_ordena_por_rango(catalogo_eps, caso_eps):
    df = analisis.sensibilidad(caso_eps, catalogo_eps, 0.2)
    assert len(df) == len(analisis.PARAMETROS_SENSIBLES)
    assert df["rango_CRC"].is_monotonic_decreasing
    tarifa = df.set_index("parametro").loc["Tarifa eléctrica"]
    assert tarifa["costo_bajo_CRC"] < tarifa["costo_base_CRC"] < tarifa["costo_alto_CRC"]


def test_barrido_marca_una_mejor_por_valor(catalogo_eps, caso_eps):
    df = analisis.barrido(caso_eps, catalogo_eps, "tarifa_CRC_kWh", [1, 120, 600])
    assert (df.groupby("valor")["es_mejor"].sum() == 1).all()
    # Con energía casi gratis conviene el espesor más delgado; con energía cara, el más grueso.
    mejores = df[df["es_mejor"]].set_index("valor")["alternativa"]
    assert mejores[1].startswith("EPS 25") and mejores[600].startswith("EPS 100")


def test_incremental_coherente_con_costo_total(catalogo_eps, caso_eps):
    resultado = evaluar_caso(caso_eps, catalogo_eps)
    inc = analisis.analisis_incremental(resultado.alternativas, EPS, caso_eps.economia())
    assert len(inc) == 3
    por_espesor = resultado.alternativas.set_index("espesor_mm")["costo_total_vp_CRC"]
    for fila in inc.itertuples():
        diferencia = por_espesor[fila.espesor_desde_mm] - por_espesor[fila.espesor_hasta_mm]
        assert fila.vpn_incremental_CRC == pytest.approx(diferencia, rel=1e-9)


def test_desglose_suma_la_carga_total(caso_eps):
    material = MaterialAislante(EPS, 0.037)
    df = analisis.desglose_superficies(caso_eps.recinto(), material, 50.0, caso_eps.refrigeracion(),
                                       caso_eps.economia())
    assert df["participacion_pct"].sum() == pytest.approx(100.0)


def test_perfil_temperatura_conserva_flujo():
    s = Superficie("pared", 9.1, 20.0, 0.05, 35.0, 28.0)
    m = MaterialAislante("PU", 0.026)
    p = perfil_temperatura_C(s, m, 80.0, 5.0, 35.0)
    assert p["aire_exterior"] > p["superficie_exterior"] > p["cara_interior_aislante"] > p["aire_interior"]
    # El último salto (película interior) debe ser flujo / h_i.
    assert p["cara_interior_aislante"] - p["aire_interior"] == pytest.approx(p["flujo_W_m2"] / 9.1)


def test_excel_contiene_hojas_principales(catalogo_eps, caso_eps):
    resultado = evaluar_caso(caso_eps, catalogo_eps)
    contenido = generar_excel(resultado, catalogo_eps, analisis.sensibilidad(caso_eps, catalogo_eps))
    libro = load_workbook(io.BytesIO(contenido))
    assert {"Resumen", "Entradas", "Alternativas", "Sensibilidad", "Advertencias"} <= set(libro.sheetnames)


@pytest.mark.parametrize("valor, esperado", [
    (1529577.4, "1\u202f529\u202f577"),
    (0.5712, "0,57"),
    (None, "—"),
    (float("nan"), "—"),
])
def test_formato_numero(valor, esperado):
    decimales = 2 if valor is not None and valor == valor and valor < 1 else 0
    assert formato.numero(valor, decimales) == esperado


def test_formato_espesor_sin_ceros_sobrantes():
    assert formato.espesor(50.0) == "50\u00a0mm"
    assert formato.espesor(101.6) == "101,6\u00a0mm"


def test_catalogo_incluido_no_tiene_valores_vacios_en_identidad():
    df = cargar()
    assert not df[["Sistema", "Material", "Proveedor", "Producto"]].isna().any().any()
    assert isinstance(df, pd.DataFrame)
