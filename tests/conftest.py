from __future__ import annotations

import pandas as pd
import pytest

from aisla_opt.caso import ParametrosCaso


def fila_catalogo(
    material: str,
    producto: str,
    espesor_mm: float,
    precio: float | None,
    k: float | None = None,
    iva: str = "No indicado",
    proveedor: str = "Prueba",
    sistema: str = "Aislante independiente",
) -> dict:
    return {
        "Activo": True, "Sistema": sistema, "Material": material, "Proveedor": proveedor,
        "Producto": producto, "Espesor_mm": espesor_mm, "Precio_CRC_m2": precio, "k_W_mK": k,
        "Densidad_kg_m3": None, "IVA_incluido": iva, "Condicion_precio": "prueba",
        "Estado_precio": "prueba", "Fecha": "2026-11-22", "Fuente": "",
    }


@pytest.fixture
def catalogo_eps() -> pd.DataFrame:
    eps = "Poliestireno expandido (EPS)"
    return pd.DataFrame([
        fila_catalogo(eps, "EPS 25", 25.0, 2000.0),
        fila_catalogo(eps, "EPS 50", 50.0, 3000.0),
        fila_catalogo(eps, "EPS 75", 75.0, 4200.0),
        fila_catalogo(eps, "EPS 100", 100.0, 5300.0),
    ])


@pytest.fixture
def caso_eps() -> ParametrosCaso:
    return ParametrosCaso(materiales=["Poliestireno expandido (EPS)"])
