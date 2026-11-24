"""AISLA-OPT V2 - motor termo-economico para cuartos refrigerados.

Incluye paredes, techo y piso por separado, temperaturas critica y de operacion,
capas base, multiples aislantes, espesores comerciales, COP, margen de diseno,
capacidad opcional de equipo, valor presente, optimizacion discreta, CSV y graficas.

Los datos del caso main() son DEMOSTRATIVOS y deben reemplazarse por fuentes reales.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional
import csv, math
import matplotlib.pyplot as plt

@dataclass(frozen=True)
class GeometriaCuarto:
    """Geometría rectangular. En AISLA-OPT la interfaz interpreta estas dimensiones como exteriores de referencia."""
    largo_m: float; ancho_m: float; alto_m: float
    def validar(self):
        if min(self.largo_m,self.ancho_m,self.alto_m)<=0: raise ValueError("Dimensiones > 0.")
    @property
    def area_paredes_m2(self): self.validar(); return 2*self.alto_m*(self.largo_m+self.ancho_m)
    @property
    def area_techo_m2(self): self.validar(); return self.largo_m*self.ancho_m
    @property
    def area_piso_m2(self): return self.area_techo_m2
    @property
    def area_total_m2(self): return self.area_paredes_m2+self.area_techo_m2+self.area_piso_m2

@dataclass(frozen=True)
class Superficie:
    nombre: str
    h_interior_W_m2K: float
    h_exterior_W_m2K: float
    resistencia_base_m2K_W: float
    temperatura_exterior_critica_C: float
    temperatura_exterior_operacion_C: float
    def validar(self):
        if self.h_interior_W_m2K<=0 or self.h_exterior_W_m2K<=0: raise ValueError(f"{self.nombre}: h > 0")
        if self.resistencia_base_m2K_W<0: raise ValueError(f"{self.nombre}: R_base >= 0")

@dataclass(frozen=True)
class CondicionesInterior:
    temperatura_interior_C: float

@dataclass(frozen=True)
class MaterialAislante:
    nombre: str
    conductividad_W_mK: float
    costo_CRC_m3: float
    espesores_comerciales_mm: tuple[float,...]
    def validar(self):
        if self.conductividad_W_mK<=0: raise ValueError(f"{self.nombre}: k > 0")
        if self.costo_CRC_m3<0: raise ValueError(f"{self.nombre}: costo >= 0")
        if not self.espesores_comerciales_mm or any(e<=0 for e in self.espesores_comerciales_mm): raise ValueError(f"{self.nombre}: espesores invalidos")

@dataclass(frozen=True)
class SistemaRefrigeracion:
    COP: float
    margen_diseno: float=1.10
    capacidad_equipo_existente_W: Optional[float]=None
    def validar(self):
        if self.COP<=0: raise ValueError("COP > 0")
        if self.margen_diseno<1: raise ValueError("Margen >= 1")
        if self.capacidad_equipo_existente_W is not None and self.capacidad_equipo_existente_W<=0: raise ValueError("Capacidad > 0")

@dataclass(frozen=True)
class Economia:
    costo_electricidad_CRC_kWh: float
    horas_operacion_anuales: float
    vida_util_anios: int
    tasa_descuento_real: float=0.0
    def validar(self):
        if self.costo_electricidad_CRC_kWh<0: raise ValueError("Costo electricidad >= 0")
        if not 0<=self.horas_operacion_anuales<=8760: raise ValueError("Horas entre 0 y 8760")
        if self.vida_util_anios<=0: raise ValueError("Vida util > 0")
        if self.tasa_descuento_real<=-1: raise ValueError("Tasa > -100%")

@dataclass(frozen=True)
class ResultadoAlternativa:
    material: str; espesor_mm: float
    U_paredes_W_m2K: float; U_techo_W_m2K: float; U_piso_W_m2K: float
    carga_critica_paredes_W: float; carga_critica_techo_W: float; carga_critica_piso_W: float
    carga_critica_total_W: float; capacidad_recomendada_W: float
    carga_operacion_total_W: float; potencia_electrica_operacion_W: float; energia_anual_kWh: float
    volumen_aislamiento_m3: float; costo_aislamiento_CRC: float; costo_energia_anual_CRC: float
    costo_energia_valor_presente_CRC: float; costo_total_valor_presente_CRC: float
    cumple_capacidad_equipo: bool

def resistencia_total_por_area(s,m,e_m):
    s.validar(); m.validar()
    if e_m<=0: raise ValueError("Espesor > 0")
    return 1/s.h_interior_W_m2K+s.resistencia_base_m2K_W+e_m/m.conductividad_W_mK+1/s.h_exterior_W_m2K

def coeficiente_U(s,m,e_m): return 1/resistencia_total_por_area(s,m,e_m)
def carga_superficie_W(A,U,Text,Tint): return U*A*(Text-Tint)

def factor_valor_presente_anualidad(i,N):
    if N<=0 or i<=-1: raise ValueError("Parametros financieros invalidos")
    return float(N) if math.isclose(i,0.0,abs_tol=1e-12) else (1-(1+i)**(-N))/i

def evaluar_alternativa(g,interior,paredes,techo,piso,m,e_mm,refrig,econ):
    g.validar(); paredes.validar(); techo.validar(); piso.validar(); m.validar(); refrig.validar(); econ.validar()
    e=e_mm/1000
    Up,Ut,Ui=(coeficiente_U(x,m,e) for x in (paredes,techo,piso))
    Qcp=carga_superficie_W(g.area_paredes_m2,Up,paredes.temperatura_exterior_critica_C,interior.temperatura_interior_C)
    Qct=carga_superficie_W(g.area_techo_m2,Ut,techo.temperatura_exterior_critica_C,interior.temperatura_interior_C)
    Qci=carga_superficie_W(g.area_piso_m2,Ui,piso.temperatura_exterior_critica_C,interior.temperatura_interior_C)
    Qc=max(0,Qcp+Qct+Qci); Qreq=refrig.margen_diseno*Qc
    ok=refrig.capacidad_equipo_existente_W is None or Qreq<=refrig.capacidad_equipo_existente_W
    Qop=carga_superficie_W(g.area_paredes_m2,Up,paredes.temperatura_exterior_operacion_C,interior.temperatura_interior_C)
    Qot=carga_superficie_W(g.area_techo_m2,Ut,techo.temperatura_exterior_operacion_C,interior.temperatura_interior_C)
    Qoi=carga_superficie_W(g.area_piso_m2,Ui,piso.temperatura_exterior_operacion_C,interior.temperatura_interior_C)
    Qo=max(0,Qop+Qot+Qoi); Pel=Qo/refrig.COP; E=Pel/1000*econ.horas_operacion_anuales
    Canual=E*econ.costo_electricidad_CRC_kWh
    Cevp=Canual*factor_valor_presente_anualidad(econ.tasa_descuento_real,econ.vida_util_anios)
    V=g.area_total_m2*e; Caisl=V*m.costo_CRC_m3; Ctot=Caisl+Cevp
    return ResultadoAlternativa(m.nombre,e_mm,Up,Ut,Ui,Qcp,Qct,Qci,Qc,Qreq,Qo,Pel,E,V,Caisl,Canual,Cevp,Ctot,ok)

def optimizar(g,interior,paredes,techo,piso,materiales,refrig,econ):
    resultados=[]
    for m in list(materiales):
        m.validar()
        for e in sorted(set(m.espesores_comerciales_mm)):
            resultados.append(evaluar_alternativa(g,interior,paredes,techo,piso,m,e,refrig,econ))
    factibles=[r for r in resultados if r.cumple_capacidad_equipo]
    if not factibles: raise RuntimeError("Ninguna alternativa cumple la capacidad del equipo.")
    return resultados,min(factibles,key=lambda r:r.costo_total_valor_presente_CRC)

def crc(v): return f"CRC {v:,.0f}"

def imprimir_resumen(g,interior,refrig,econ,resultados,opt):
    print("\nAISLA-OPT V2")
    print(f"Cuarto: {g.largo_m} x {g.ancho_m} x {g.alto_m} m | Area total: {g.area_total_m2:.2f} m2")
    print(f"Tint: {interior.temperatura_interior_C:.1f} C | COP: {refrig.COP:.2f} | Vida: {econ.vida_util_anios} anos")
    print("\nMaterial                  e(mm)  Qcrit(kW)  Qreq(kW)  E(kWh/a)   Ctotal VP")
    print("-"*82)
    for r in resultados:
        print(f"{r.material[:24]:<25}{r.espesor_mm:6.0f}{r.carga_critica_total_W/1000:11.3f}{r.capacidad_recomendada_W/1000:10.3f}{r.energia_anual_kWh:11.1f}{crc(r.costo_total_valor_presente_CRC):>18}")
    print("\nOPTIMO")
    print(f"Material: {opt.material}")
    print(f"Espesor: {opt.espesor_mm:.0f} mm")
    print(f"Carga pico de transmision: {opt.carga_critica_total_W/1000:.3f} kW")
    print(f"Transmision + margen: {opt.capacidad_recomendada_W/1000:.3f} kW")
    print(f"Energia anual atribuible a transmision: {opt.energia_anual_kWh:.1f} kWh/a")
    print(f"Costo aislamiento: {crc(opt.costo_aislamiento_CRC)}")
    print(f"Costo energia VP: {crc(opt.costo_energia_valor_presente_CRC)}")
    print(f"Costo total VP: {crc(opt.costo_total_valor_presente_CRC)}")

def exportar_csv(resultados,ruta):
    ruta=Path(ruta); campos=list(ResultadoAlternativa.__dataclass_fields__.keys())
    with ruta.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=campos); w.writeheader()
        for r in resultados: w.writerow({c:getattr(r,c) for c in campos})
    return ruta

def graficar_costos(resultados,opt,ruta):
    ruta=Path(ruta); fig,ax=plt.subplots(figsize=(9,6))
    for mat in sorted(set(r.material for r in resultados)):
        d=sorted([r for r in resultados if r.material==mat],key=lambda r:r.espesor_mm)
        ax.plot([r.espesor_mm for r in d],[r.costo_total_valor_presente_CRC for r in d],marker="o",label=mat)
    ax.scatter([opt.espesor_mm],[opt.costo_total_valor_presente_CRC],s=100,zorder=5,label=f"Optimo: {opt.material}, {opt.espesor_mm:.0f} mm")
    ax.set_title("Costo total de ciclo de vida vs. espesor"); ax.set_xlabel("Espesor [mm]"); ax.set_ylabel("Costo total VP [CRC]"); ax.grid(True,alpha=.25); ax.legend(); fig.tight_layout(); fig.savefig(ruta,dpi=180); plt.close(fig); return ruta

def graficar_carga(resultados,ruta):
    ruta=Path(ruta); fig,ax=plt.subplots(figsize=(9,6))
    for mat in sorted(set(r.material for r in resultados)):
        d=sorted([r for r in resultados if r.material==mat],key=lambda r:r.espesor_mm)
        ax.plot([r.espesor_mm for r in d],[r.carga_critica_total_W/1000 for r in d],marker="o",label=mat)
    ax.set_title("Carga termica critica vs. espesor"); ax.set_xlabel("Espesor [mm]"); ax.set_ylabel("Carga termica critica [kW]"); ax.grid(True,alpha=.25); ax.legend(); fig.tight_layout(); fig.savefig(ruta,dpi=180); plt.close(fig); return ruta

def pruebas_coherencia(resultados):
    assert resultados
    assert all(r.carga_critica_total_W>=0 and r.energia_anual_kWh>=0 and r.costo_total_valor_presente_CRC>=0 for r in resultados)
    for mat in set(r.material for r in resultados):
        d=sorted([r for r in resultados if r.material==mat],key=lambda r:r.espesor_mm)
        assert all(b.carga_critica_total_W<=a.carga_critica_total_W+1e-9 for a,b in zip(d,d[1:])), f"Carga no monotona: {mat}"

def main():
    g=GeometriaCuarto(4,3,2.5); interior=CondicionesInterior(5)
    paredes=Superficie("Paredes",9.1,9.1,0.0,35,28)
    techo=Superficie("Techo",9.1,9.1,0.0,38,30)
    piso=Superficie("Piso",9.1,9.1,0.0,25,24)
    materiales=[
        MaterialAislante("Material A (DEMO)",.025,250000,(25,50,75,100,125,150)),
        MaterialAislante("Material B (DEMO)",.035,190000,(25,50,75,100,125,150)),
        MaterialAislante("Material C (DEMO)",.045,150000,(25,50,75,100,125,150)),
    ]
    refrig=SistemaRefrigeracion(3.0,1.10,2500)
    econ=Economia(120,8760,10,.05)
    resultados,opt=optimizar(g,interior,paredes,techo,piso,materiales,refrig,econ)
    pruebas_coherencia(resultados); imprimir_resumen(g,interior,refrig,econ,resultados,opt)
    out=Path(__file__).resolve().parent
    print("\nArchivos:")
    print(exportar_csv(resultados,out/"resultados_aisla_opt_v2.csv"))
    print(graficar_costos(resultados,opt,out/"costos_aisla_opt_v2.png"))
    print(graficar_carga(resultados,out/"carga_termica_aisla_opt_v2.png"))
    print("Pruebas de coherencia: APROBADAS")

if __name__=="__main__": main()
