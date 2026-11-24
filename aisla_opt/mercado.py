"""Consulta opcional de precios web de EPS en Costa Rica.

Solo propone precios que pueden normalizarse a CRC/m² con dimensiones
documentadas (láminas de 1.22 × 2.44 m). Nunca modifica el catálogo por sí
misma: la interfaz muestra una vista previa y el usuario decide.
"""
from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from . import __version__
from .materiales import SISTEMA_AISLANTE

MATERIAL_EPS = "Poliestireno expandido (EPS)"
AREA_LAMINA_m2 = 1.22 * 2.44

URL_ELKY = "https://elkymaria.com/productos/construccion/aislantes.html"
PRODUCTOS_ELKY = [
    # (espesor_mm, texto buscado en la página, nombre en catálogo)
    (25.4, 'LAMINA ESTEREOFON 1.22 X 2.44 X 1"', "EPS 25.4 mm · 1.22×2.44 m"),
    (50.8, 'LAMINA ESTEREOFON 1.22 X 2.44 X 2"', "EPS 50.8 mm · 1.22×2.44 m"),
    (76.2, 'LAMINA ESTEREOFON 122 X 244 X 3"', "EPS 76.2 mm · 1.22×2.44 m"),
    (101.6, 'LAMINA ESTEREOFON 122 X 244 X 4"', "EPS 101.6 mm · 1.22×2.44 m"),
]
PRODUCTOS_EPA = [
    # (nombre en catálogo, espesor_mm, url)
    ("EPS 38 mm · 1.22×2.44 m", 38.0, "https://cr.epaenlinea.com/lamina-de-estereofon-112-122-x-244-cm.html"),
    ("EPS 50 mm · 1.22×2.44 m", 50.0, "https://cr.epaenlinea.com/es-cr/products/lamina-de-estereofon-2-122-x-244-cm"),
    ("EPS 76 mm · 1.22×2.44 m", 76.0, "https://cr.epaenlinea.com/es-cr/products/lamina-de-estereofon-3-122-x-244-cm"),
]

CABECERAS_HTTP = {
    "User-Agent": f"Mozilla/5.0 (compatible; AISLA-OPT/{__version__})",
    "Accept-Language": "es-CR,es;q=0.9,en;q=0.6",
}
TIEMPO_ESPERA_s = (5, 12)
TAMANO_MAXIMO_RESPUESTA_bytes = 5_000_000
CONDICION_PRECIO_WEB = "Precio web de material; verificar IVA, stock y condiciones de venta"

# Captura un monto en colones sin tragarse números posteriores como "2 disponibles".
PATRON_COLONES = re.compile(
    r"(?:₡|¢)\s*((?:\d{1,3}(?:[ .,\u00a0\u202f]\d{3})+|\d+)(?:[.,]\d{2})?)(?!\d)"
)


def _precio_lamina_plausible(precio_CRC: float) -> bool:
    return 100.0 <= float(precio_CRC) <= 10_000_000.0


def _precio_m2_plausible(precio_CRC_m2: float) -> bool:
    return 100.0 <= float(precio_CRC_m2) <= 500_000.0


def _fecha_hoy_cr() -> str:
    return datetime.now(ZoneInfo("America/Costa_Rica")).date().isoformat()


def interpretar_monto(texto: str) -> float:
    """Convierte '₡15 815,00', '6.393', '15,815.00', etc. a número."""
    s = re.sub(r"[^\d,.\-]", "", texto or "")
    if not s:
        raise ValueError("precio ilegible")
    if "," in s and "." in s:
        # El separador que aparece último es el decimal.
        s = s.replace(",", "") if s.rfind(".") > s.rfind(",") else s.replace(".", "").replace(",", ".")
    elif "," in s:
        decimales = s.rsplit(",", 1)[-1]
        s = s.replace(".", "")
        s = s.replace(",", ".") if len(decimales) == 2 else s.replace(",", "")
    elif "." in s:
        decimales = s.rsplit(".", 1)[-1]
        if len(decimales) != 2:
            s = s.replace(".", "")
    return float(s)


def _descargar_html(url: str) -> str:
    respuesta = requests.get(url, timeout=TIEMPO_ESPERA_s, headers=CABECERAS_HTTP)
    if respuesta.status_code == 429:
        raise RuntimeError("el proveedor limitó temporalmente las consultas")
    respuesta.raise_for_status()
    tipo = (respuesta.headers.get("Content-Type") or "").lower()
    if tipo and not any(t in tipo for t in ("text/html", "application/xhtml+xml", "text/plain")):
        raise RuntimeError("la respuesta del proveedor no es una página HTML compatible")
    if len(respuesta.content) > TAMANO_MAXIMO_RESPUESTA_bytes:
        raise RuntimeError("la respuesta del proveedor excede el tamaño permitido")
    return respuesta.text


def _precio_en_pagina_producto(url: str) -> float:
    pagina = BeautifulSoup(_descargar_html(url), "html.parser")
    candidatos = [
        pagina.find("meta", attrs={"property": "product:price:amount"}),
        pagina.find(attrs={"itemprop": "price"}),
        pagina.select_one(".price"),
        pagina.select_one("[class*='price']"),
    ]
    for nodo in candidatos:
        if not nodo:
            continue
        crudo = nodo.get("content") if getattr(nodo, "attrs", None) else None
        crudo = crudo or nodo.get_text(" ", strip=True)
        try:
            precio = interpretar_monto(crudo)
        except ValueError:
            continue
        if precio > 100:
            return precio

    coincidencia = PATRON_COLONES.search(pagina.get_text(" ", strip=True))
    if not coincidencia:
        raise RuntimeError("no se encontró un precio reconocible")
    precio = interpretar_monto(coincidencia.group(1))
    if not _precio_lamina_plausible(precio):
        raise RuntimeError("precio fuera de rango plausible")
    return precio


def _precio_junto_a_producto(pagina: BeautifulSoup, texto_buscado: str) -> float:
    """Busca el precio dentro del bloque DOM más cercano al nombre del producto."""
    objetivo = pagina.find(string=lambda t: isinstance(t, str) and texto_buscado.lower() in t.lower())
    if objetivo is None:
        raise RuntimeError("producto no localizado")

    nodo = objetivo.parent
    for _ in range(5):
        if nodo is None:
            break
        montos = []
        for coincidencia in PATRON_COLONES.finditer(nodo.get_text(" ", strip=True)):
            try:
                monto = interpretar_monto(coincidencia.group(1))
            except ValueError:
                continue
            if _precio_lamina_plausible(monto):
                montos.append(monto)
        if montos:
            return montos[0]
        nodo = nodo.parent
    raise RuntimeError("precio no localizado junto al producto")


def _oferta(proveedor: str, producto: str, espesor_mm: float, precio_m2: float, fecha: str, fuente: str) -> dict:
    return {
        "Activo": True,
        "Sistema": SISTEMA_AISLANTE,
        "Material": MATERIAL_EPS,
        "Proveedor": proveedor,
        "Producto": producto,
        "Espesor_mm": espesor_mm,
        "Precio_CRC_m2": precio_m2,
        "k_W_mK": None,
        "Densidad_kg_m3": None,
        "IVA_incluido": "No indicado",
        "Condicion_precio": CONDICION_PRECIO_WEB,
        "Estado_precio": "Precio web normalizado",
        "Fecha": fecha,
        "Fuente": fuente,
    }


def consultar_eps() -> dict:
    """Propuestas de actualización ya normalizadas a CRC/m².

    Devuelve ``{"ofertas": [...], "mensajes": [...]}``. Si un proveedor falla
    se informa en ``mensajes`` y el catálogo existente se conserva.
    """
    resultado: dict[str, list] = {"ofertas": [], "mensajes": []}
    fecha = _fecha_hoy_cr()

    try:
        pagina = BeautifulSoup(_descargar_html(URL_ELKY), "html.parser")
        encontrados = 0
        for espesor, texto_buscado, producto in PRODUCTOS_ELKY:
            try:
                precio_m2 = _precio_junto_a_producto(pagina, texto_buscado) / AREA_LAMINA_m2
            except RuntimeError:
                continue
            if not _precio_m2_plausible(precio_m2):
                continue
            resultado["ofertas"].append(_oferta("Elky María", producto, espesor, precio_m2, fecha, URL_ELKY))
            encontrados += 1
        resultado["mensajes"].append(
            f"Elky María: {encontrados} precios disponibles."
            if encontrados
            else "Elky María: no se encontraron precios compatibles; se conserva el catálogo actual."
        )
    except (requests.RequestException, RuntimeError):
        resultado["mensajes"].append(
            "Elky María: no respondió; se conserva el último catálogo guardado."
        )

    encontrados_epa = 0
    for producto, espesor, url in PRODUCTOS_EPA:
        try:
            precio_m2 = _precio_en_pagina_producto(url) / AREA_LAMINA_m2
        except (requests.RequestException, RuntimeError, ValueError):
            continue
        if not _precio_m2_plausible(precio_m2):
            continue
        resultado["ofertas"].append(_oferta("EPA Costa Rica", producto, espesor, precio_m2, fecha, url))
        encontrados_epa += 1

    resultado["mensajes"].append(
        f"EPA Costa Rica: {encontrados_epa} precios disponibles."
        if encontrados_epa
        else "EPA Costa Rica: no respondió; se conserva el último catálogo guardado."
    )
    return resultado
