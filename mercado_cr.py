from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

ELKY_URL = "https://elkymaria.com/productos/construccion/aislantes.html"
EPA_URLS = [
    ("EPS 38 mm · 1.22×2.44 m", 38.0, "https://cr.epaenlinea.com/lamina-de-estereofon-112-122-x-244-cm.html"),
    ("EPS 50 mm · 1.22×2.44 m", 50.0, "https://cr.epaenlinea.com/es-cr/products/lamina-de-estereofon-2-122-x-244-cm"),
    ("EPS 76 mm · 1.22×2.44 m", 76.0, "https://cr.epaenlinea.com/es-cr/products/lamina-de-estereofon-3-122-x-244-cm"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AISLA-OPT/4.0",
    "Accept-Language": "es-CR,es;q=0.9,en;q=0.6",
}

# Captura un monto CRC sin tragarse números posteriores como "2 disponibles".
CRC_RE = re.compile(
    r"(?:₡|¢)\s*((?:\d{1,3}(?:[ .,\u00a0\u202f]\d{3})+|\d+)(?:[.,]\d{2})?)(?!\d)"
)


def _precio_plausible_crc(precio: float) -> bool:
    return 100.0 <= float(precio) <= 10_000_000.0


def _precio_normalizado_plausible(precio_m2: float) -> bool:
    return 100.0 <= float(precio_m2) <= 500_000.0


def _hoy() -> str:
    return datetime.now(ZoneInfo("America/Costa_Rica")).date().isoformat()


def _numero(texto: str) -> float:
    s = re.sub(r"[^\d,.\-]", "", texto or "")
    if not s:
        raise ValueError("precio ilegible")
    if "," in s and "." in s:
        if s.rfind(".") > s.rfind(","):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        tail = s.rsplit(",", 1)[-1]
        s = s.replace(".", "")
        s = s.replace(",", ".") if len(tail) == 2 else s.replace(",", "")
    elif "." in s:
        tail = s.rsplit(".", 1)[-1]
        if len(tail) != 2:
            s = s.replace(".", "")
    return float(s)


def _get(url: str) -> str:
    r = requests.get(url, timeout=(5, 12), headers=HEADERS)
    if r.status_code == 429:
        raise RuntimeError("proveedor limitó temporalmente las consultas")
    r.raise_for_status()
    ctype = (r.headers.get("Content-Type") or "").lower()
    if ctype and not any(x in ctype for x in ("text/html", "application/xhtml+xml", "text/plain")):
        raise RuntimeError("respuesta del proveedor no es una página HTML compatible")
    if len(r.content) > 5_000_000:
        raise RuntimeError("respuesta del proveedor excede el tamaño permitido")
    return r.text


def _price_from_page(url: str) -> float:
    soup = BeautifulSoup(_get(url), "html.parser")
    for node in [
        soup.find("meta", attrs={"property": "product:price:amount"}),
        soup.find(attrs={"itemprop": "price"}),
        soup.select_one(".price"),
        soup.select_one("[class*='price']"),
    ]:
        if node:
            raw = node.get("content") if getattr(node, "attrs", None) else None
            raw = raw or node.get_text(" ", strip=True)
            try:
                p = _numero(raw)
                if p > 100:
                    return p
            except Exception:
                pass
    txt = soup.get_text(" ", strip=True)
    m = CRC_RE.search(txt)
    if not m:
        raise RuntimeError("no se encontró un precio reconocible")
    p = _numero(m.group(1))
    if not _precio_plausible_crc(p):
        raise RuntimeError("precio fuera de rango plausible")
    return p


def _price_near_product(soup: BeautifulSoup, needle: str) -> float:
    """Busca el precio dentro del bloque DOM más cercano al nombre del producto."""
    target = soup.find(string=lambda t: isinstance(t, str) and needle.lower() in t.lower())
    if target is None:
        raise RuntimeError("producto no localizado")

    node = target.parent
    for _ in range(5):
        if node is None:
            break
        txt = node.get_text(" ", strip=True)
        montos = []
        for m in CRC_RE.finditer(txt):
            try:
                p = _numero(m.group(1))
                if _precio_plausible_crc(p):
                    montos.append(p)
            except Exception:
                pass
        if montos:
            return montos[0]
        node = node.parent

    raise RuntimeError("precio no localizado junto al producto")


def consultar_eps() -> dict:
    """
    Returns price-update proposals already normalized to SI.
    The app may keep existing catalog values when a provider is unavailable.
    """
    result = {"ofertas": [], "mensajes": []}
    area = 1.22 * 2.44
    fecha = _hoy()

    # Elky
    try:
        soup = BeautifulSoup(_get(ELKY_URL), "html.parser")
        items = [
            (25.4, 'LAMINA ESTEREOFON 1.22 X 2.44 X 1"', "EPS 25.4 mm · 1.22×2.44 m"),
            (50.8, 'LAMINA ESTEREOFON 1.22 X 2.44 X 2"', "EPS 50.8 mm · 1.22×2.44 m"),
            (76.2, 'LAMINA ESTEREOFON 122 X 244 X 3"', "EPS 76.2 mm · 1.22×2.44 m"),
            (101.6, 'LAMINA ESTEREOFON 122 X 244 X 4"', "EPS 101.6 mm · 1.22×2.44 m"),
        ]
        count = 0
        for e, needle, product in items:
            try:
                price = _price_near_product(soup, needle)
            except Exception:
                continue
            price_m2 = price / area
            if not _precio_normalizado_plausible(price_m2):
                continue
            result["ofertas"].append({
                "Activo": True,
                "Sistema": "Aislante independiente",
                "Material": "Poliestireno expandido (EPS)",
                "Proveedor": "Elky María",
                "Producto": product,
                "Espesor_mm": e,
                "Precio_CRC_m2": price_m2,
                "k_W_mK": None,
                "Densidad_kg_m3": None,
                "IVA_incluido": "No indicado",
                "Condicion_precio": "Precio web de material; verificar IVA, stock y condiciones de venta",
                "Estado_precio": "Precio web normalizado",
                "Fecha": fecha,
                "Fuente": ELKY_URL,
            })
            count += 1
        result["mensajes"].append(
            f"Elky María: {count} precios disponibles."
            if count else
            "Elky María: no se encontraron precios compatibles; se conserva el catálogo actual."
        )
    except Exception:
        result["mensajes"].append(
            "Elky María: temporalmente no disponible; se conserva el último catálogo guardado."
        )

    # EPA
    epa_count = 0
    for product, e, url in EPA_URLS:
        try:
            price = _price_from_page(url)
            price_m2 = price / area
            if not _precio_normalizado_plausible(price_m2):
                raise RuntimeError("precio normalizado fuera de rango plausible")
            result["ofertas"].append({
                "Activo": True,
                "Sistema": "Aislante independiente",
                "Material": "Poliestireno expandido (EPS)",
                "Proveedor": "EPA Costa Rica",
                "Producto": product,
                "Espesor_mm": e,
                "Precio_CRC_m2": price_m2,
                "k_W_mK": None,
                "Densidad_kg_m3": None,
                "IVA_incluido": "No indicado",
                "Condicion_precio": "Precio web de material; verificar IVA, stock y condiciones de venta",
                "Estado_precio": "Precio web normalizado",
                "Fecha": fecha,
                "Fuente": url,
            })
            epa_count += 1
        except Exception:
            pass

    if epa_count:
        result["mensajes"].append(f"EPA Costa Rica: {epa_count} precios disponibles.")
    else:
        result["mensajes"].append(
            "EPA Costa Rica: temporalmente no disponible; se conserva el último catálogo guardado."
        )

    return result
