"""Caso de estudio: todas las entradas en una estructura, su evaluación y advertencias.

``ParametrosCaso`` contiene solo valores simples, de modo que un caso se puede
guardar como JSON, reproducir y variar para análisis de sensibilidad.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field, fields, replace

import pandas as pd

from . import __version__
from .catalogo import k_fuera_de_rango, resumen_por_material
from .materiales import (
    MATERIALES_ASHRAE,
    MATERIALES_INICIALES,
    MATERIALES_POR_SISTEMA,
    SISTEMA_AISLANTE,
    SISTEMAS,
    k_es_plausible,
    k_generica,
)
from .motor import (
    Economia,
    GeometriaCuarto,
    MaterialAislante,
    Recinto,
    SistemaRefrigeracion,
    Superficie,
)
from .seleccion import comparar_alternativas, limites_por_capacidad


@dataclass
class ParametrosCaso:
    # Solución comercial
    sistema: str = SISTEMA_AISLANTE
    materiales: list[str] = field(default_factory=lambda: list(MATERIALES_INICIALES[SISTEMA_AISLANTE]))
    k_ficha_W_mK: dict[str, float] = field(default_factory=dict)
    # Geometría exterior de referencia
    largo_m: float = 4.0
    ancho_m: float = 3.0
    alto_m: float = 2.5
    # Temperaturas
    t_interior_C: float = 5.0
    t_paredes_critica_C: float = 35.0
    t_paredes_operacion_C: float = 28.0
    t_techo_critica_C: float = 38.0
    t_techo_operacion_C: float = 30.0
    t_piso_critica_C: float = 25.0
    t_piso_operacion_C: float = 24.0
    # Refrigeración
    cop: float = 3.0
    margen_pct: float = 10.0
    usar_capacidad: bool = False
    capacidad_kW: float = 2.5
    # Economía
    tarifa_CRC_kWh: float = 120.0
    horas_anio: float = 8760.0
    vida_util_anios: int = 10
    tasa_descuento_pct: float = 5.0
    # Parámetros térmicos avanzados
    h_interior_W_m2K: float = 9.1
    h_exterior_paredes_W_m2K: float = 9.1
    h_exterior_techo_W_m2K: float = 9.1
    h_piso_W_m2K: float = 9.1
    r_adicional_paredes_m2K_W: float = 0.0
    r_adicional_techo_m2K_W: float = 0.0
    r_adicional_piso_m2K_W: float = 0.0

    # ------------------------------------------------------------------ #
    def validar(self) -> None:
        if self.sistema not in SISTEMAS:
            raise ValueError(f"Sistema desconocido: {self.sistema}")
        desconocidos = [m for m in self.materiales if m not in MATERIALES_ASHRAE]
        if desconocidos:
            raise ValueError("Materiales desconocidos: " + ", ".join(desconocidos))
        for material, k in self.k_ficha_W_mK.items():
            if not k_es_plausible(k):
                raise ValueError(f"k de {material} fuera del rango 0.01–0.20 W/m·K; revise unidades.")

    def recinto(self) -> Recinto:
        def superficie(nombre: str, h_ext: float, r: float, t_crit: float, t_op: float) -> Superficie:
            return Superficie(nombre, self.h_interior_W_m2K, h_ext, r, t_crit, t_op)

        return Recinto(
            geometria=GeometriaCuarto(self.largo_m, self.ancho_m, self.alto_m),
            temperatura_interior_C=self.t_interior_C,
            paredes=superficie("Paredes", self.h_exterior_paredes_W_m2K, self.r_adicional_paredes_m2K_W,
                               self.t_paredes_critica_C, self.t_paredes_operacion_C),
            techo=superficie("Techo", self.h_exterior_techo_W_m2K, self.r_adicional_techo_m2K_W,
                             self.t_techo_critica_C, self.t_techo_operacion_C),
            piso=superficie("Piso", self.h_piso_W_m2K, self.r_adicional_piso_m2K_W,
                            self.t_piso_critica_C, self.t_piso_operacion_C),
        )

    def refrigeracion(self) -> SistemaRefrigeracion:
        return SistemaRefrigeracion(
            COP=self.cop,
            margen_diseno=1 + self.margen_pct / 100,
            capacidad_disponible_W=self.capacidad_kW * 1000 if self.usar_capacidad else None,
        )

    def economia(self) -> Economia:
        return Economia(self.tarifa_CRC_kWh, self.horas_anio, int(self.vida_util_anios),
                        self.tasa_descuento_pct / 100)

    def materiales_modelo(self) -> dict[str, MaterialAislante]:
        """Materiales con la k genérica o, si se indicó, la k de una ficha técnica."""
        return {
            nombre: MaterialAislante(nombre, float(self.k_ficha_W_mK.get(nombre, k_generica(nombre))))
            for nombre in self.materiales
        }

    # ------------------------------------------------------------------ #
    def a_dict(self) -> dict:
        return asdict(self)

    def a_json(self) -> str:
        return json.dumps(
            {"aplicacion": "AISLA-OPT", "version": __version__, "parametros": self.a_dict()},
            ensure_ascii=False, indent=2,
        )

    @classmethod
    def desde_dict(cls, datos: dict) -> ParametrosCaso:
        """Crea un caso ignorando claves desconocidas, para tolerar versiones futuras."""
        conocidos = {f.name for f in fields(cls)}
        caso = cls(**{k: v for k, v in datos.items() if k in conocidos})
        caso.materiales = [m for m in caso.materiales if m in MATERIALES_POR_SISTEMA.get(caso.sistema, ())]
        caso.validar()
        return caso

    @classmethod
    def desde_json(cls, texto: str) -> ParametrosCaso:
        datos = json.loads(texto)
        if not isinstance(datos, dict):
            raise ValueError("El archivo no contiene un escenario de AISLA-OPT.")
        return cls.desde_dict(datos.get("parametros", datos))


# Puntos de partida editables. No sustituyen datos de diseño del proyecto.
PLANTILLAS: dict[str, dict] = {
    "Conservación a 5 °C": {},
    "Congelación a −18 °C": {"t_interior_C": -18.0, "cop": 1.8},
}


def caso_desde_plantilla(nombre: str, base: ParametrosCaso | None = None) -> ParametrosCaso:
    """Aplica una plantilla sobre los valores iniciales, conservando la solución comercial elegida."""
    caso = replace(ParametrosCaso(), **PLANTILLAS[nombre])
    if base is not None:
        caso.sistema, caso.materiales = base.sistema, list(base.materiales)
        caso.k_ficha_W_mK = dict(base.k_ficha_W_mK)
    return caso


# --------------------------------------------------------------------------- #
# Evaluación completa
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Aviso:
    nivel: str  # "error" | "advertencia" | "info" | "exito"
    texto: str


@dataclass
class ResultadoCaso:
    parametros: ParametrosCaso
    alternativas: pd.DataFrame
    mejor: dict | None
    limites: pd.DataFrame | None
    disponibilidad: pd.DataFrame
    posicion_mejor: str | None
    avisos: list[Aviso]

    @property
    def hay_comparacion(self) -> bool:
        return self.mejor is not None


def posicion_en_catalogo(alternativas: pd.DataFrame, mejor: dict) -> str:
    """Ubica la mejor alternativa dentro del rango de espesores con precio de su material."""
    mismo = alternativas[alternativas["material"] == mejor["material"]]["espesor_mm"]
    if mismo.nunique() < 2:
        return "unico"
    if math.isclose(mejor["espesor_mm"], mismo.max()):
        return "borde_superior"
    if math.isclose(mejor["espesor_mm"], mismo.min()):
        return "borde_inferior"
    return "interior"


MENSAJES_POSICION = {
    "unico": Aviso("advertencia",
                   "Solo hay un espesor con precio para este material, así que no se puede afirmar "
                   "que sea un mínimo económico robusto."),
    "borde_superior": Aviso("advertencia",
                            "La mejor alternativa es el espesor más grueso con precio de este material. "
                            "El costo podría seguir bajando con espesores mayores: el catálogo limita la conclusión."),
    "borde_inferior": Aviso("info",
                            "La mejor alternativa es el espesor más delgado con precio de este material: con estas "
                            "condiciones, el ahorro de energía de espesores mayores no compensa su costo inicial."),
    "interior": Aviso("exito",
                      "La mejor alternativa queda dentro del rango de espesores con precio, no en un extremo. "
                      "La conclusión es más sólida dentro de ese rango."),
}


def _avisos_temperatura(p: ParametrosCaso) -> list[Aviso]:
    pares = [
        ("paredes crítica", p.t_paredes_critica_C), ("paredes operación", p.t_paredes_operacion_C),
        ("techo crítica", p.t_techo_critica_C), ("techo operación", p.t_techo_operacion_C),
        ("piso crítica", p.t_piso_critica_C), ("piso operación", p.t_piso_operacion_C),
    ]
    sin_carga = [nombre for nombre, t in pares if t <= p.t_interior_C]
    if not sin_carga:
        return []
    return [Aviso("advertencia",
                  "Revise las temperaturas de " + ", ".join(sin_carga) + ": no superan la interior, así que "
                  "esa superficie representa pérdida de calor y no carga de refrigeración.")]


def evaluar_caso(p: ParametrosCaso, catalogo: pd.DataFrame) -> ResultadoCaso:
    """Evalúa el caso completo: límites por capacidad, comparación económica y avisos."""
    p.validar()
    if not p.materiales:
        raise ValueError("Seleccione al menos un material.")
    if k_fuera_de_rango(catalogo).any():
        raise ValueError("El catálogo tiene valores de k fuera de 0.01–0.20 W/m·K. Revise las unidades.")

    recinto, refrigeracion, economia = p.recinto(), p.refrigeracion(), p.economia()
    materiales = p.materiales_modelo()
    avisos = _avisos_temperatura(p)

    limites = (
        limites_por_capacidad(recinto, materiales, refrigeracion, economia, catalogo, p.sistema)
        if p.usar_capacidad else None
    )
    alternativas, mejor = comparar_alternativas(recinto, materiales, refrigeracion, economia, catalogo, p.sistema)
    disponibilidad = resumen_por_material(catalogo, p.sistema, p.materiales)

    sin_precio = disponibilidad.loc[disponibilidad["Con precio"] == 0, "Material"].tolist()
    if sin_precio and len(sin_precio) < len(p.materiales):
        avisos.append(Aviso("info",
                            "Sin productos con precio en el catálogo, no entran en la comparación económica: "
                            + ", ".join(sin_precio) + ". Registre una cotización para incluirlos."))

    posicion = None
    if mejor is None:
        if disponibilidad["Con precio"].sum() == 0:
            avisos.append(Aviso("advertencia",
                                f"No hay productos con precio en CRC/m² para «{p.sistema}» y los materiales "
                                "seleccionados. El análisis térmico está disponible; registre cotizaciones "
                                "en la pestaña Catálogo para comparar costos."))
        else:
            avisos.append(Aviso("advertencia",
                                "Ningún producto con precio cumple la capacidad disponible para transmisión. "
                                "Aumente la capacidad o agregue productos de mayor espesor o menor k."))
    else:
        posicion = posicion_en_catalogo(alternativas, mejor)
        avisos.append(MENSAJES_POSICION[posicion])
        iva = alternativas["iva"].fillna("No indicado").astype(str).str.strip().replace("", "No indicado")
        if (iva == "No indicado").any() or iva.nunique() > 1:
            avisos.append(Aviso("advertencia",
                                "Los precios no están en la misma base de IVA (incluido, excluido o no indicado). "
                                "La comparación económica es preliminar hasta normalizarla."))

    if limites is not None:
        cerca = limites.loc[limites["sensibilidad"] == "Cerca del salto", "material"].tolist()
        if cerca:
            avisos.append(Aviso("advertencia",
                                ", ".join(cerca) + " queda muy cerca del límite de su espesor comercial: una pequeña "
                                "variación de carga obligaría al siguiente espesor disponible."))

    return ResultadoCaso(p, alternativas, mejor, limites, disponibilidad, posicion, avisos)
