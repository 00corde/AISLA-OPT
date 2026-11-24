"""Prueba de humo de la interfaz: la app se ejecuta sin excepciones en los flujos principales."""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

RUTA_APP = str(Path(__file__).resolve().parent.parent / "app.py")
TIEMPO_s = 60


@pytest.fixture
def app() -> AppTest:
    at = AppTest.from_file(RUTA_APP, default_timeout=TIEMPO_s)
    at.run()
    return at


def test_carga_inicial_muestra_mejor_alternativa(app):
    assert not app.exception
    assert any("Mejor alternativa comercial evaluada" in m.value for m in app.markdown)


def test_cambiar_entrada_mantiene_resultados(app):
    app.number_input(key="largo_m").set_value(5.0).run()
    assert not app.exception
    assert any("Mejor alternativa comercial evaluada" in m.value for m in app.markdown)


def test_paneles_sin_precio_avisan(app):
    app.radio(key="sistema").set_value("Panel frigorífico completo").run()
    assert not app.exception
    assert app.session_state["materiales"] == ["Poliuretano (PU)", "Poliisocianurato (PIR)"]
    assert any("No hay productos con precio" in w.value for w in app.warning)


def test_restriccion_de_capacidad(app):
    app.checkbox(key="usar_capacidad").check().run()
    assert not app.exception
    assert any("Del cálculo continuo" in s.value for s in app.subheader)


def test_plantilla_congelacion(app):
    app.selectbox(key="plantilla").set_value("Congelación a −18 °C").run()
    next(b for b in app.sidebar.button if b.label == "Aplicar plantilla").click().run()
    assert not app.exception
    assert app.session_state["t_interior_C"] == -18.0


def test_sin_materiales(app):
    app.multiselect(key="materiales").set_value([]).run()
    assert not app.exception
    assert any("Elija al menos un material" in i.value for i in app.info)
