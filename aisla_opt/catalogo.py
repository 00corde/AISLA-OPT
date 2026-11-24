"""Catálogo comercial: lectura, normalización, guardado y altas de cotizaciones.

El esquema de columnas del CSV se mantiene estable para que los catálogos
existentes sigan funcionando.
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from .materiales import K_MAXIMA_W_mK, K_MINIMA_W_mK

RUTA_CATALOGO = Path(__file__).resolve().parent.parent / "data" / "catalogo_comercial_cr.csv"

COLUMNAS = [
    "Activo", "Sistema", "Material", "Proveedor", "Producto", "Espesor_mm",
    "Precio_CRC_m2", "k_W_mK", "Densidad_kg_m3", "IVA_incluido", "Condicion_precio",
    "Estado_precio", "Fecha", "Fuente",
]
COLUMNAS_NUMERICAS = ["Espesor_mm", "Precio_CRC_m2", "k_W_mK", "Densidad_kg_m3"]
COLUMNAS_IDENTIDAD = ["Sistema", "Material", "Proveedor", "Producto"]
COLUMNAS_PRECIO_WEB = ["Precio_CRC_m2", "Estado_precio", "Fecha", "Fuente"]
OPCIONES_IVA = ("No indicado", "Sí", "No")


def completar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega columnas faltantes y devuelve el catálogo en el orden del esquema."""
    x = df.copy()
    for columna in COLUMNAS:
        if columna not in x.columns:
            x[columna] = None
    return x[COLUMNAS]


def cargar(ruta: Path | str = RUTA_CATALOGO) -> pd.DataFrame:
    return completar_columnas(pd.read_csv(ruta))


def leer_csv_subido(archivo) -> pd.DataFrame:
    """Lee un CSV subido por el usuario y valida que tenga las columnas clave."""
    df = pd.read_csv(archivo)
    faltantes = [c for c in ["Sistema", "Material", "Espesor_mm"] if c not in df.columns]
    if faltantes:
        raise ValueError("Faltan columnas obligatorias: " + ", ".join(faltantes))
    return completar_columnas(df)


def _fecha_iso(valor) -> str:
    if pd.isna(valor) or not str(valor).strip():
        return ""
    fecha = pd.to_datetime(str(valor).strip(), errors="coerce")
    return fecha.date().isoformat() if not pd.isna(fecha) else str(valor).strip()


def a_csv(df: pd.DataFrame) -> str:
    """Serializa el catálogo con fechas ISO y saltos de línea normalizados."""
    x = completar_columnas(df)
    x["Fecha"] = x["Fecha"].map(_fecha_iso)
    return x.to_csv(index=False, lineterminator="\n")


def guardar(df: pd.DataFrame, ruta: Path | str = RUTA_CATALOGO) -> None:
    Path(ruta).write_text(a_csv(df), encoding="utf-8-sig")


def normalizar(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte tipos (booleanos y numéricos) sin modificar el original."""
    x = completar_columnas(df)
    x["Activo"] = x["Activo"].fillna(False).astype(bool)
    for columna in COLUMNAS_NUMERICAS:
        x[columna] = pd.to_numeric(x[columna], errors="coerce")
    return x


def k_fuera_de_rango(df: pd.DataFrame) -> pd.Series:
    k = pd.to_numeric(df["k_W_mK"], errors="coerce")
    return k.notna() & ~k.between(K_MINIMA_W_mK, K_MAXIMA_W_mK, inclusive="both")


def upsert(base: pd.DataFrame, filas: Iterable[dict], solo_precio: bool = False) -> pd.DataFrame:
    """Inserta o actualiza filas identificadas por sistema+material+proveedor+producto+espesor.

    Con ``solo_precio=True`` (actualización web) solo cambian precio, estado,
    fecha y fuente; se conservan k, densidad, IVA y condición registrados.
    """
    df = completar_columnas(base)
    for fila in filas:
        espesor_nuevo = pd.to_numeric(pd.Series([fila.get("Espesor_mm")]), errors="coerce").iloc[0]
        espesores = pd.to_numeric(df["Espesor_mm"], errors="coerce")
        mismo_espesor = (
            (espesores - float(espesor_nuevo)).abs() < 1e-9 if pd.notna(espesor_nuevo) else espesores.isna()
        )
        coincide = mismo_espesor.copy()
        for columna in COLUMNAS_IDENTIDAD:
            coincide &= df[columna].astype(str) == str(fila.get(columna, ""))

        if coincide.any():
            indice = df[coincide].index[0]
            columnas = COLUMNAS_PRECIO_WEB if solo_precio else COLUMNAS
            for columna in columnas:
                if columna in fila:
                    df.at[indice, columna] = fila[columna]
        else:
            nueva = pd.DataFrame([{c: fila.get(c) for c in COLUMNAS}])
            df = nueva if df.empty else pd.concat([df, nueva], ignore_index=True)
    return df


def inventario_material(catalogo: pd.DataFrame, material: str, sistema: str) -> pd.DataFrame:
    """Productos activos de un material y sistema con espesor válido."""
    x = normalizar(catalogo)
    return x[
        x["Activo"]
        & (x["Material"].astype(str) == str(material))
        & (x["Sistema"].astype(str) == str(sistema))
        & x["Espesor_mm"].notna()
        & (x["Espesor_mm"] > 0)
    ].copy()


def precio_por_m2(
    precio_CRC: float,
    unidad: str,
    ancho_m: float | None = None,
    largo_m: float | None = None,
    unidades_por_paquete: int = 1,
) -> float:
    """Normaliza un precio cotizado a CRC/m².

    ``unidad`` puede ser ``"m2"``, ``"lamina"`` (precio de una lámina o panel)
    o ``"paquete"`` (precio de varias láminas iguales). Solo convierte con
    dimensiones documentadas; nunca inventa un factor.
    """
    if precio_CRC <= 0:
        raise ValueError("El precio debe ser mayor que cero.")
    if unidad == "m2":
        return float(precio_CRC)
    if not ancho_m or not largo_m or ancho_m <= 0 or largo_m <= 0:
        raise ValueError("Indique el ancho y el largo de la lámina o panel en metros.")
    if unidad == "lamina":
        return float(precio_CRC) / (ancho_m * largo_m)
    if unidad == "paquete":
        if unidades_por_paquete < 1:
            raise ValueError("El paquete debe tener al menos una unidad.")
        return float(precio_CRC) / (ancho_m * largo_m * unidades_por_paquete)
    raise ValueError(f"Unidad de precio desconocida: {unidad}")


def resumen_por_material(catalogo: pd.DataFrame, sistema: str, materiales: Iterable[str]) -> pd.DataFrame:
    """Cuántos productos y cuántos con precio tiene cada material del sistema."""
    filas = []
    for material in materiales:
        inventario = inventario_material(catalogo, material, sistema)
        con_precio = int((inventario["Precio_CRC_m2"] > 0).sum())
        filas.append({
            "Material": material,
            "Productos": len(inventario),
            "Con precio": con_precio,
            "Espesores con precio": int(inventario.loc[inventario["Precio_CRC_m2"] > 0, "Espesor_mm"].nunique()),
        })
    return pd.DataFrame(filas, columns=["Material", "Productos", "Con precio", "Espesores con precio"])
