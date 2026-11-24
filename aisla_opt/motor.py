"""Motor térmico y económico de AISLA-OPT.

Modelo estacionario de transmisión a través de la envolvente de un cuarto
refrigerado rectangular. Cada superficie (paredes, techo, piso) se resuelve
como una red de resistencias en serie por unidad de área:

    R'' = 1/h_i + R''_adicional + e/k + 1/h_o        U = 1/R''        Q = U·A·ΔT

Convención de nombres: los sufijos indican la unidad SI con su capitalización
habitual (``_W``, ``_kWh``, ``_mm``, ``_m2``, ``_W_mK``, ``_C``, ``_CRC``).
"""
from __future__ import annotations

import math
from dataclasses import dataclass


# --------------------------------------------------------------------------- #
# Datos de entrada
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GeometriaCuarto:
    """Recinto rectangular. Las dimensiones son exteriores de referencia."""

    largo_m: float
    ancho_m: float
    alto_m: float

    def validar(self) -> None:
        if min(self.largo_m, self.ancho_m, self.alto_m) <= 0:
            raise ValueError("Las dimensiones del recinto deben ser mayores que cero.")

    @property
    def area_paredes_m2(self) -> float:
        self.validar()
        return 2 * self.alto_m * (self.largo_m + self.ancho_m)

    @property
    def area_techo_m2(self) -> float:
        self.validar()
        return self.largo_m * self.ancho_m

    @property
    def area_piso_m2(self) -> float:
        return self.area_techo_m2

    @property
    def area_total_m2(self) -> float:
        return self.area_paredes_m2 + self.area_techo_m2 + self.area_piso_m2


@dataclass(frozen=True)
class Superficie:
    """Condiciones de película, resistencia adicional y temperaturas de una superficie."""

    nombre: str
    h_interior_W_m2K: float
    h_exterior_W_m2K: float
    resistencia_adicional_m2K_W: float
    temperatura_exterior_critica_C: float
    temperatura_exterior_operacion_C: float

    def validar(self) -> None:
        if self.h_interior_W_m2K <= 0 or self.h_exterior_W_m2K <= 0:
            raise ValueError(f"{self.nombre}: los coeficientes h deben ser mayores que cero.")
        if self.resistencia_adicional_m2K_W < 0:
            raise ValueError(f"{self.nombre}: la resistencia adicional no puede ser negativa.")


@dataclass(frozen=True)
class Recinto:
    """Geometría, temperatura interior y las tres superficies de la envolvente."""

    geometria: GeometriaCuarto
    temperatura_interior_C: float
    paredes: Superficie
    techo: Superficie
    piso: Superficie

    def superficies_con_area(self) -> list[tuple[Superficie, float]]:
        g = self.geometria
        return [
            (self.paredes, g.area_paredes_m2),
            (self.techo, g.area_techo_m2),
            (self.piso, g.area_piso_m2),
        ]

    def validar(self) -> None:
        self.geometria.validar()
        for superficie, _ in self.superficies_con_area():
            superficie.validar()


@dataclass(frozen=True)
class MaterialAislante:
    nombre: str
    conductividad_W_mK: float

    def validar(self) -> None:
        if self.conductividad_W_mK <= 0:
            raise ValueError(f"{self.nombre}: la conductividad k debe ser mayor que cero.")


@dataclass(frozen=True)
class SistemaRefrigeracion:
    COP: float
    margen_diseno: float = 1.10
    capacidad_disponible_W: float | None = None

    def validar(self) -> None:
        if self.COP <= 0:
            raise ValueError("El COP debe ser mayor que cero.")
        if self.margen_diseno < 1:
            raise ValueError("El margen de diseño no puede ser menor que 1.")
        if self.capacidad_disponible_W is not None and self.capacidad_disponible_W <= 0:
            raise ValueError("La capacidad disponible debe ser mayor que cero.")


@dataclass(frozen=True)
class Economia:
    costo_electricidad_CRC_kWh: float
    horas_operacion_anuales: float
    vida_util_anios: int
    tasa_descuento_real: float = 0.0

    def validar(self) -> None:
        if self.costo_electricidad_CRC_kWh < 0:
            raise ValueError("El costo de la electricidad no puede ser negativo.")
        if not 0 <= self.horas_operacion_anuales <= 8760:
            raise ValueError("Las horas de operación deben estar entre 0 y 8760.")
        if self.vida_util_anios <= 0:
            raise ValueError("La vida útil debe ser mayor que cero.")
        if self.tasa_descuento_real <= -1:
            raise ValueError("La tasa de descuento debe ser mayor que -100 %.")


# --------------------------------------------------------------------------- #
# Resultado
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ResultadoAlternativa:
    material: str
    espesor_mm: float
    conductividad_W_mK: float
    U_paredes_W_m2K: float
    U_techo_W_m2K: float
    U_piso_W_m2K: float
    carga_critica_paredes_W: float
    carga_critica_techo_W: float
    carga_critica_piso_W: float
    carga_critica_total_W: float
    capacidad_recomendada_W: float
    carga_operacion_paredes_W: float
    carga_operacion_techo_W: float
    carga_operacion_piso_W: float
    carga_operacion_total_W: float
    potencia_electrica_operacion_W: float
    energia_anual_kWh: float
    volumen_aislamiento_m3: float
    costo_aislamiento_CRC: float
    costo_energia_anual_CRC: float
    costo_energia_valor_presente_CRC: float
    costo_total_valor_presente_CRC: float
    cumple_capacidad: bool


# --------------------------------------------------------------------------- #
# Ecuaciones
# --------------------------------------------------------------------------- #
def resistencia_total_por_area(
    superficie: Superficie, material: MaterialAislante, espesor_m: float
) -> float:
    """R'' total [m²·K/W] de una superficie con el aislamiento indicado."""
    superficie.validar()
    material.validar()
    if espesor_m <= 0:
        raise ValueError("El espesor debe ser mayor que cero.")
    return (
        1 / superficie.h_interior_W_m2K
        + superficie.resistencia_adicional_m2K_W
        + espesor_m / material.conductividad_W_mK
        + 1 / superficie.h_exterior_W_m2K
    )


def coeficiente_U(superficie: Superficie, material: MaterialAislante, espesor_m: float) -> float:
    return 1 / resistencia_total_por_area(superficie, material, espesor_m)


def carga_superficie_W(
    area_m2: float, U_W_m2K: float, temperatura_exterior_C: float, temperatura_interior_C: float
) -> float:
    return U_W_m2K * area_m2 * (temperatura_exterior_C - temperatura_interior_C)


def factor_valor_presente_anualidad(tasa: float, anios: int) -> float:
    """FVP = [1 − (1+i)^−N] / i, con FVP = N cuando i = 0."""
    if anios <= 0 or tasa <= -1:
        raise ValueError("Parámetros financieros inválidos.")
    if math.isclose(tasa, 0.0, abs_tol=1e-12):
        return float(anios)
    return (1 - (1 + tasa) ** (-anios)) / tasa


def evaluar_alternativa(
    recinto: Recinto,
    material: MaterialAislante,
    espesor_mm: float,
    refrigeracion: SistemaRefrigeracion,
    economia: Economia,
    precio_CRC_m2: float = 0.0,
) -> ResultadoAlternativa:
    """Evalúa un material y espesor uniforme en toda la envolvente.

    ``precio_CRC_m2`` se aplica sobre el área total exterior de referencia.
    Con precio cero el resultado sirve solo para el análisis térmico.
    """
    recinto.validar()
    material.validar()
    refrigeracion.validar()
    economia.validar()

    espesor_m = espesor_mm / 1000
    t_int = recinto.temperatura_interior_C
    g = recinto.geometria

    U_p, U_t, U_i = (
        coeficiente_U(s, material, espesor_m) for s in (recinto.paredes, recinto.techo, recinto.piso)
    )

    def cargas(atributo_temperatura: str) -> tuple[float, float, float]:
        return (
            carga_superficie_W(g.area_paredes_m2, U_p, getattr(recinto.paredes, atributo_temperatura), t_int),
            carga_superficie_W(g.area_techo_m2, U_t, getattr(recinto.techo, atributo_temperatura), t_int),
            carga_superficie_W(g.area_piso_m2, U_i, getattr(recinto.piso, atributo_temperatura), t_int),
        )

    q_crit_p, q_crit_t, q_crit_i = cargas("temperatura_exterior_critica_C")
    q_crit = max(0.0, q_crit_p + q_crit_t + q_crit_i)
    q_recomendada = refrigeracion.margen_diseno * q_crit
    cumple = (
        refrigeracion.capacidad_disponible_W is None
        or q_recomendada <= refrigeracion.capacidad_disponible_W
    )

    q_op_p, q_op_t, q_op_i = cargas("temperatura_exterior_operacion_C")
    q_op = max(0.0, q_op_p + q_op_t + q_op_i)
    potencia_W = q_op / refrigeracion.COP
    energia_kWh = potencia_W / 1000 * economia.horas_operacion_anuales

    costo_energia_anual = energia_kWh * economia.costo_electricidad_CRC_kWh
    costo_energia_vp = costo_energia_anual * factor_valor_presente_anualidad(
        economia.tasa_descuento_real, economia.vida_util_anios
    )
    costo_aislamiento = g.area_total_m2 * max(0.0, precio_CRC_m2)

    return ResultadoAlternativa(
        material=material.nombre,
        espesor_mm=espesor_mm,
        conductividad_W_mK=material.conductividad_W_mK,
        U_paredes_W_m2K=U_p,
        U_techo_W_m2K=U_t,
        U_piso_W_m2K=U_i,
        carga_critica_paredes_W=q_crit_p,
        carga_critica_techo_W=q_crit_t,
        carga_critica_piso_W=q_crit_i,
        carga_critica_total_W=q_crit,
        capacidad_recomendada_W=q_recomendada,
        carga_operacion_paredes_W=q_op_p,
        carga_operacion_techo_W=q_op_t,
        carga_operacion_piso_W=q_op_i,
        carga_operacion_total_W=q_op,
        potencia_electrica_operacion_W=potencia_W,
        energia_anual_kWh=energia_kWh,
        volumen_aislamiento_m3=g.area_total_m2 * espesor_m,
        costo_aislamiento_CRC=costo_aislamiento,
        costo_energia_anual_CRC=costo_energia_anual,
        costo_energia_valor_presente_CRC=costo_energia_vp,
        costo_total_valor_presente_CRC=costo_aislamiento + costo_energia_vp,
        cumple_capacidad=cumple,
    )


def perfil_temperatura_C(
    superficie: Superficie,
    material: MaterialAislante,
    espesor_mm: float,
    temperatura_interior_C: float,
    temperatura_exterior_C: float,
) -> dict[str, float]:
    """Temperaturas en cada interfaz de la red de resistencias (exterior → interior).

    El flujo por unidad de área es el mismo en todas las capas, por lo que
    cada salto de temperatura es proporcional a su resistencia.
    """
    espesor_m = espesor_mm / 1000
    r_total = resistencia_total_por_area(superficie, material, espesor_m)
    flujo_W_m2 = (temperatura_exterior_C - temperatura_interior_C) / r_total

    t_superficie_ext = temperatura_exterior_C - flujo_W_m2 / superficie.h_exterior_W_m2K
    t_cara_ext_aislante = t_superficie_ext - flujo_W_m2 * superficie.resistencia_adicional_m2K_W
    t_cara_int_aislante = t_cara_ext_aislante - flujo_W_m2 * espesor_m / material.conductividad_W_mK
    return {
        "aire_exterior": temperatura_exterior_C,
        "superficie_exterior": t_superficie_ext,
        "cara_exterior_aislante": t_cara_ext_aislante,
        "cara_interior_aislante": t_cara_int_aislante,
        "aire_interior": temperatura_interior_C,
        "flujo_W_m2": flujo_W_m2,
    }
