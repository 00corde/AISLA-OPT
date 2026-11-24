"""Formato de números en convención costarricense: espacio para miles y coma decimal."""
from __future__ import annotations

import math

SEPARADOR_MILES = "\u202f"  # espacio fino que no se corta al final de línea


def _vacio(valor) -> bool:
    if valor is None:
        return True
    try:
        return math.isnan(float(valor)) or math.isinf(float(valor))
    except (TypeError, ValueError):
        return True


def numero(valor: float | None, decimales: int = 0, vacio: str = "—") -> str:
    if _vacio(valor):
        return vacio
    texto = f"{float(valor):,.{decimales}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", SEPARADOR_MILES)


def colones(valor: float | None, decimales: int = 0) -> str:
    if _vacio(valor):
        return "—"
    signo = "−" if float(valor) < 0 else ""
    return f"{signo}₡{numero(abs(float(valor)), decimales)}"


def unidad(valor: float | None, simbolo: str, decimales: int = 1) -> str:
    return "—" if _vacio(valor) else f"{numero(valor, decimales)}\u00a0{simbolo}"


def espesor(valor_mm: float | None) -> str:
    """Espesores sin ceros sobrantes: 50 mm, 101,6 mm."""
    if _vacio(valor_mm):
        return "—"
    decimales = 0 if float(valor_mm).is_integer() else 1
    return unidad(valor_mm, "mm", decimales)
