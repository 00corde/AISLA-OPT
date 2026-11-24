"""Gráficas Altair y diagrama de la sección de pared.

Reglas aplicadas (skill de visualización de datos): un solo eje Y por
gráfica, color fijo por material, leyenda con dos o más series y etiquetas
directas selectivas, líneas de 2 px y marcadores de al menos 8 px.
"""
from __future__ import annotations

import altair as alt
import pandas as pd

from aisla_opt import formato
from aisla_opt.analisis import abreviatura

from .tema import Paleta, escala_materiales

# Formato numérico con coma decimal en los ejes (Vega usa punto por defecto).
EJE_MILLONES = "replace(format(datum.value, '.2f'), '.', ',')"
EJE_UN_DECIMAL = "replace(format(datum.value, '.1f'), '.', ',')"
EJE_ENTERO = "replace(format(datum.value, ',.0f'), /,/g, ' ')"


def _base(grafica: alt.Chart, alto: int = 320) -> alt.Chart:
    return grafica.properties(height=alto).configure_axis(
        grid=True, gridOpacity=0.35, domain=False, tickColor="transparent", labelPadding=6, titlePadding=10,
    ).configure_view(stroke=None).configure_legend(
        orient="bottom", title=None, symbolStrokeWidth=2, labelLimit=0, columns=0
    ).configure_axisY(labelLimit=240)


# --------------------------------------------------------------------------- #
def costo_vs_espesor(alternativas: pd.DataFrame, mejor: dict, paleta: Paleta) -> alt.Chart:
    """Costo total VP de cada producto; línea por material uniendo el más barato de cada espesor."""
    df = alternativas.copy()
    df["costo_M"] = df["costo_total_vp_CRC"] / 1e6
    df["costo_txt"] = df["costo_total_vp_CRC"].map(formato.colones)
    df["espesor_txt"] = df["espesor_mm"].map(formato.espesor)
    dominio, rango = escala_materiales(df["material"].tolist(), paleta)
    color = alt.Color("material:N", scale=alt.Scale(domain=dominio, range=rango), title=None)
    x = alt.X("espesor_mm:Q", title="Espesor [mm]", scale=alt.Scale(zero=False, nice=True))
    y = alt.Y("costo_M:Q", title="Costo total VP [millones de ₡]",
              axis=alt.Axis(labelExpr=EJE_MILLONES), scale=alt.Scale(zero=False))

    tendencia = (
        df.sort_values("costo_total_vp_CRC").drop_duplicates(["material", "espesor_mm"]).sort_values("espesor_mm")
    )
    lineas = alt.Chart(tendencia).mark_line(strokeWidth=2, opacity=0.55).encode(x=x, y=y, color=color)
    puntos = alt.Chart(df).mark_circle(size=90, opacity=1, stroke=paleta.superficie, strokeWidth=2).encode(
        x=x, y=y, color=color,
        tooltip=[
            alt.Tooltip("producto:N", title="Producto"),
            alt.Tooltip("proveedor:N", title="Proveedor"),
            alt.Tooltip("espesor_txt:N", title="Espesor"),
            alt.Tooltip("costo_txt:N", title="Costo total VP"),
        ],
    )
    marca = pd.DataFrame([{
        "espesor_mm": mejor["espesor_mm"], "costo_M": mejor["costo_total_vp_CRC"] / 1e6,
        "texto": f"Mejor evaluada: {abreviatura(mejor['material'])} {formato.espesor(mejor['espesor_mm'])}",
    }])
    anillo = alt.Chart(marca).mark_point(size=420, shape="circle", filled=False, strokeWidth=2.5,
                                         color=paleta.texto).encode(x="espesor_mm:Q", y="costo_M:Q")
    rotulo = alt.Chart(marca).mark_text(align="right", dx=-16, dy=-14, fontWeight=600, color=paleta.texto).encode(
        x="espesor_mm:Q", y="costo_M:Q", text="texto:N"
    )
    return _base(lineas + puntos + anillo + rotulo)


def curva_termica(curva: pd.DataFrame, paleta: Paleta) -> alt.Chart:
    """Carga pico vs espesor por material, con cursor que muestra los valores."""
    df = curva.copy()
    df["carga_txt"] = df["carga_pico_kW"].map(lambda v: formato.unidad(v, "kW", 2))
    dominio, rango = escala_materiales(df["material"].tolist(), paleta)
    color = alt.Color("material:N", scale=alt.Scale(domain=dominio, range=rango), title=None)
    x = alt.X("espesor_mm:Q", title="Espesor de aislamiento [mm]")
    y = alt.Y("carga_pico_kW:Q", title="Carga pico de transmisión [kW]", axis=alt.Axis(labelExpr=EJE_UN_DECIMAL))

    cursor = alt.selection_point(nearest=True, on="pointerover", fields=["espesor_mm"], empty=False)
    lineas = alt.Chart(df).mark_line(strokeWidth=2).encode(x=x, y=y, color=color)
    selector = alt.Chart(df).mark_rule(opacity=0).encode(x=x).add_params(cursor)
    regla = (
        alt.Chart(df).mark_rule(color=paleta.texto_secundario, strokeDash=[3, 3]).encode(x=x).transform_filter(cursor)
    )
    puntos = alt.Chart(df).mark_circle(size=70).encode(
        x=x, y=y, color=color,
        tooltip=[alt.Tooltip("material:N", title="Material"), alt.Tooltip("espesor_mm:Q", title="Espesor [mm]"),
                 alt.Tooltip("carga_txt:N", title="Carga pico")],
    ).transform_filter(cursor)
    finales = df.sort_values("espesor_mm").groupby("material").tail(1).copy()
    finales["etiqueta"] = finales["material"].map(abreviatura)
    etiquetas = alt.Chart(finales).mark_text(align="left", dx=6, fontWeight=600).encode(
        x=x, y=y, text="etiqueta:N", color=color
    ) if len(dominio) <= 4 else None
    capas = lineas + selector + regla + puntos
    return _base(capas + etiquetas if etiquetas is not None else capas)


def limite_vs_comercial(limites: pd.DataFrame, paleta: Paleta) -> alt.Chart:
    df = limites.dropna(subset=["limite_mm", "espesor_comercial_mm"])
    largo = df.melt(id_vars="material", value_vars=["limite_mm", "espesor_comercial_mm"],
                    var_name="medida", value_name="espesor_mm")
    largo["medida"] = largo["medida"].map({"limite_mm": "Límite continuo", "espesor_comercial_mm": "Primer comercial"})
    largo["material"] = largo["material"].map(abreviatura)
    return _base(
        alt.Chart(largo).mark_bar(cornerRadiusEnd=4, height=14).encode(
            y=alt.Y("material:N", title=None),
            yOffset=alt.YOffset("medida:N", sort=["Límite continuo", "Primer comercial"]),
            x=alt.X("espesor_mm:Q", title="Espesor [mm]"),
            color=alt.Color("medida:N", scale=alt.Scale(domain=["Límite continuo", "Primer comercial"],
                                                        range=[paleta.series[0], paleta.series[1]])),
            tooltip=[alt.Tooltip("material:N"), alt.Tooltip("medida:N"),
                     alt.Tooltip("espesor_mm:Q", title="Espesor [mm]", format=".1f")],
        ),
        alto=max(140, 70 * df["material"].nunique()),
    )


def tornado(sensibilidad: pd.DataFrame, paleta: Paleta) -> alt.Chart:
    """Variación del costo de la mejor alternativa al mover cada parámetro."""
    base_M = float(sensibilidad["costo_base_CRC"].iloc[0]) / 1e6
    filas = []
    for fila in sensibilidad.itertuples():
        for extremo, costo, valor in (("Parámetro bajo", fila.costo_bajo_CRC, fila.valor_bajo),
                                      ("Parámetro alto", fila.costo_alto_CRC, fila.valor_alto)):
            filas.append({
                "parametro": fila.parametro, "extremo": extremo, "inicio": base_M, "fin": costo / 1e6,
                "valor": f"{formato.numero(valor, 2 if valor < 10 else 0)} {fila.unidad}".strip(),
                "costo": formato.colones(costo),
            })
    df = pd.DataFrame(filas)
    orden = sensibilidad["parametro"].tolist()
    barras = alt.Chart(df).mark_bar(height=18, cornerRadiusEnd=4).encode(
        y=alt.Y("parametro:N", sort=orden, title=None),
        x=alt.X("inicio:Q", title="Costo total de la mejor alternativa [millones de ₡]",
                axis=alt.Axis(labelExpr=EJE_MILLONES), scale=alt.Scale(zero=False)),
        x2="fin:Q",
        color=alt.Color("extremo:N", scale=alt.Scale(domain=["Parámetro bajo", "Parámetro alto"],
                                                     range=[paleta.series[0], paleta.series[1]])),
        tooltip=[alt.Tooltip("parametro:N", title="Parámetro"), alt.Tooltip("valor:N", title="Valor"),
                 alt.Tooltip("costo:N", title="Costo total VP")],
    )
    eje_base = alt.Chart(pd.DataFrame({"x": [base_M]})).mark_rule(color=paleta.texto, strokeWidth=1.5).encode(x="x:Q")
    return _base(barras + eje_base, alto=max(180, 48 * len(orden)))


def barrido(df: pd.DataFrame, valor_base: float, titulo_x: str, paleta: Paleta) -> alt.Chart:
    datos = df.copy()
    datos["costo_M"] = datos["costo_total_vp_CRC"] / 1e6
    datos["costo_txt"] = datos["costo_total_vp_CRC"].map(formato.colones)
    alternativas = list(dict.fromkeys(datos["alternativa"]))
    color = alt.Color("alternativa:N", scale=alt.Scale(domain=alternativas, range=list(paleta.series[:5])),
                      title=None)
    x = alt.X("valor:Q", title=titulo_x)
    y = alt.Y("costo_M:Q", title="Costo total VP [millones de ₡]", axis=alt.Axis(labelExpr=EJE_MILLONES),
              scale=alt.Scale(zero=False))
    lineas = alt.Chart(datos).mark_line(strokeWidth=2).encode(x=x, y=y, color=color)
    mejores = alt.Chart(datos[datos["es_mejor"]]).mark_circle(size=80, stroke=paleta.superficie, strokeWidth=2).encode(
        x=x, y=y, color=color,
        tooltip=[alt.Tooltip("valor:Q", title=titulo_x, format=".2f"),
                 alt.Tooltip("alternativa:N", title="Mejor alternativa"), alt.Tooltip("costo_txt:N", title="Costo")],
    )
    regla = alt.Chart(pd.DataFrame({"x": [valor_base]})).mark_rule(
        color=paleta.texto_secundario, strokeDash=[4, 4]).encode(x="x:Q")
    return _base(lineas + mejores + regla)


def vpn_incremental(incremental: pd.DataFrame, paleta: Paleta) -> alt.Chart:
    df = incremental.copy()
    df["paso"] = df["espesor_desde_mm"].map(formato.espesor) + " → " + df["espesor_hasta_mm"].map(formato.espesor)
    df["paso"] = df["paso"].str.replace("\u00a0", " ")
    df["vpn_M"] = df["vpn_incremental_CRC"] / 1e6
    df["resultado"] = df["conviene"].map({True: "Conviene engrosar", False: "No conviene"})
    df["vpn_txt"] = df["vpn_incremental_CRC"].map(formato.colones)
    return _base(
        alt.Chart(df).mark_bar(cornerRadiusEnd=4, height=20).encode(
            y=alt.Y("paso:N", sort=df["paso"].tolist(), title=None),
            x=alt.X("vpn_M:Q", title="VPN incremental del paso [millones de ₡]",
                    axis=alt.Axis(labelExpr=EJE_MILLONES)),
            color=alt.Color("resultado:N", scale=alt.Scale(domain=["Conviene engrosar", "No conviene"],
                                                           range=[paleta.positivo, paleta.negativo])),
            tooltip=[alt.Tooltip("paso:N", title="Paso"), alt.Tooltip("vpn_txt:N", title="VPN incremental"),
                     alt.Tooltip("resultado:N", title="Resultado")],
        ),
        alto=max(140, 46 * len(df)),
    )


def desglose(df: pd.DataFrame, paleta: Paleta) -> alt.Chart:
    datos = df.copy()
    datos["etiqueta"] = datos.apply(
        lambda f: f"{formato.unidad(f['carga_pico_W'], 'W', 0)} · {formato.numero(f['participacion_pct'])} %", axis=1
    )
    barras = alt.Chart(datos).mark_bar(cornerRadiusEnd=4, height=22, color=paleta.series[0]).encode(
        y=alt.Y("superficie:N", sort=["Paredes", "Techo", "Piso"], title=None),
        x=alt.X("carga_pico_W:Q", title="Carga pico de transmisión [W]", axis=alt.Axis(labelExpr=EJE_ENTERO)),
        tooltip=[alt.Tooltip("superficie:N", title="Superficie"), alt.Tooltip("etiqueta:N", title="Carga")],
    )
    textos = barras.mark_text(align="left", dx=6, color=paleta.texto).encode(text="etiqueta:N")
    return _base(barras + textos, alto=170)


# --------------------------------------------------------------------------- #
# Diagrama de la sección de pared
# --------------------------------------------------------------------------- #
def seccion_pared_svg(perfil: dict[str, float], espesor_mm: float, nombre_material: str, paleta: Paleta) -> str:
    """Corte de la pared con el perfil de temperatura real (exterior a la izquierda)."""
    ancho, alto = 470, 262
    fondo_zonas = alto - 50  # franja inferior reservada para la flecha de flujo
    x_aire_ext, x_pared_ext = 14, 120
    grosor = max(56, min(200, 1.2 * espesor_mm))
    x_pared_int = x_pared_ext + grosor
    x_aire_int = ancho - 18
    capa = 16  # capa límite (película) dibujada a cada lado de la pared
    arriba, abajo = 46, fondo_zonas - 24

    temps = [perfil["aire_exterior"], perfil["superficie_exterior"], perfil["cara_interior_aislante"],
             perfil["aire_interior"]]
    t_max, t_min = max(temps), min(temps)
    rango = (t_max - t_min) or 1.0

    def y(t: float) -> float:
        return arriba + (t_max - t) / rango * (abajo - arriba)

    puntos = [
        (x_aire_ext, y(perfil["aire_exterior"])),
        (x_pared_ext - capa, y(perfil["aire_exterior"])),
        (x_pared_ext, y(perfil["superficie_exterior"])),
        (x_pared_int, y(perfil["cara_interior_aislante"])),
        (x_pared_int + capa, y(perfil["aire_interior"])),
        (x_aire_int, y(perfil["aire_interior"])),
    ]
    trazo = " ".join(f"{px:.1f},{py:.1f}" for px, py in puntos)

    def grados(t: float) -> str:
        return f"{formato.numero(t, 1)} °C"

    centro = (x_pared_ext + x_pared_int) / 2
    flujo = formato.numero(perfil["flujo_W_m2"], 1)
    descripcion = (
        f"Sección de pared con {nombre_material} de {formato.espesor(espesor_mm)}: "
        f"{grados(perfil['aire_exterior'])} afuera, {grados(perfil['aire_interior'])} adentro, "
        f"flujo de {flujo} W/m²."
    )
    return f"""
<figure class="diagrama" role="img" aria-label="{descripcion}">
<svg viewBox="0 0 {ancho} {alto}" xmlns="http://www.w3.org/2000/svg" font-family="inherit">
  <defs>
    <pattern id="espuma" width="10" height="10" patternUnits="userSpaceOnUse">
      <rect width="10" height="10" fill="{paleta.aislante}"/>
      <circle cx="3" cy="3" r="1.3" fill="{paleta.borde}"/><circle cx="8" cy="7" r="1" fill="{paleta.borde}"/>
    </pattern>
    <marker id="punta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="{paleta.calor}"/>
    </marker>
  </defs>
  <rect x="0" y="22" width="{x_pared_ext}" height="{fondo_zonas - 22}" fill="{paleta.calor}" opacity=".08"/>
  <rect x="{x_pared_int}" y="22" width="{ancho - x_pared_int}" height="{fondo_zonas - 22}"
        fill="{paleta.frio}" opacity=".85"/>
  <rect x="{x_pared_ext}" y="22" width="{grosor}" height="{fondo_zonas - 22}" fill="url(#espuma)"
        stroke="{paleta.texto_secundario}" stroke-width="1.5"/>
  <text x="10" y="15" font-size="13" fill="{paleta.calor}" font-weight="600">Exterior</text>
  <text x="{ancho - 10}" y="15" font-size="13" fill="{paleta.texto}" font-weight="600" text-anchor="end">Interior</text>
  <text x="{centro}" y="15" font-size="13" fill="{paleta.texto}" text-anchor="middle">\
{formato.espesor(espesor_mm)} de {abreviatura(nombre_material)}</text>
  <polyline points="{trazo}" fill="none" stroke="{paleta.texto}" stroke-width="2.5" stroke-linejoin="round"/>
  {''.join(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{paleta.texto}"/>' for px, py in puntos[1:5])}
  <text x="{x_aire_ext}" y="{y(perfil['aire_exterior']) - 9:.1f}" font-size="13" fill="{paleta.texto}">\
{grados(perfil['aire_exterior'])}</text>
  <text x="{x_pared_ext - 6}" y="{y(perfil['superficie_exterior']) + 20:.1f}" font-size="12" text-anchor="end" \
fill="{paleta.texto_secundario}">{grados(perfil['superficie_exterior'])}</text>
  <text x="{x_pared_int + 6}" y="{y(perfil['cara_interior_aislante']) - 9:.1f}" font-size="12" \
fill="{paleta.texto_secundario}">{grados(perfil['cara_interior_aislante'])}</text>
  <text x="{x_aire_int}" y="{y(perfil['aire_interior']) + 20:.1f}" font-size="13" text-anchor="end" \
fill="{paleta.texto}">{grados(perfil['aire_interior'])}</text>
  <line x1="{x_pared_ext - 50}" y1="{alto - 12}" x2="{x_pared_int + 50}" y2="{alto - 12}" stroke="{paleta.calor}"
        stroke-width="2" marker-end="url(#punta)"/>
  <text x="{centro}" y="{alto - 22}" font-size="12.5" fill="{paleta.calor}" text-anchor="middle" font-weight="600">\
Flujo de calor {flujo} W/m²</text>
</svg>
<figcaption>Perfil de temperatura en las paredes en condición crítica. La mayor caída ocurre dentro del \
aislamiento; las películas de aire explican el resto.</figcaption>
</figure>"""
