#!/usr/bin/env python3
"""Cesta - Agente Analista de Call Center. Calculo de KPIs, cortes y graficos.
Uso: python3 calculo_kpis.py <carpeta_base> <carpeta_corrida>
Genera: resultados.json, kpis_resumen.csv, kpis_detalle.xlsx, graficos/*.png
"""
import sys, json, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = sys.argv[1] if len(sys.argv) > 1 else "."
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(__file__))
GR = os.path.join(OUT, "graficos"); os.makedirs(GR, exist_ok=True)

VERDE, CREMA, DORADO, TERRA, OLIVA, TINTA = "#0E3B2E", "#F7F3EA", "#F4B942", "#C75B39", "#6E8F7A", "#14201B"
plt.rcParams.update({"figure.facecolor": CREMA, "axes.facecolor": CREMA, "savefig.facecolor": CREMA,
    "axes.edgecolor": OLIVA, "axes.labelcolor": TINTA, "xtick.color": TINTA, "ytick.color": TINTA,
    "text.color": TINTA, "axes.spines.top": False, "axes.spines.right": False,
    "font.family": "DejaVu Sans", "font.size": 10, "axes.titleweight": "bold", "axes.titlesize": 12})

c = pd.read_csv(os.path.join(BASE, "Entradas/llamadas_cdr.csv"))
t = pd.read_csv(os.path.join(BASE, "Entradas/casos_tickets.csv"))
c["fecha"] = pd.to_datetime(c["fecha"]); t["fecha_apertura"] = pd.to_datetime(t["fecha_apertura"])
c["ab"] = (c.resultado_llamada == "abandonada").astype(int)
c["esc"] = c.escalado_a.notna().astype(int)
c["aht"] = c.duracion_seg + c.acw_seg
c["semana"] = c.fecha.dt.to_period("W-SUN").apply(lambda p: p.start_time.date())
at = c[c.ab == 0].copy()

# ---------- Esquema ----------
esq_c = ["id_llamada","fecha","hora","fecha_hora_entrada","id_cliente","id_agente","cola","tipo_llamada","motivo","resultado_llamada","espera_seg","duracion_seg","acw_seg","escalado_a","dia_semana"]
esq_t = ["id_caso","id_llamada","fecha_apertura","id_cliente","id_agente","categoria","estado_caso","fcr","reincidencia","horas_resolucion","csat","valor_orden"]
esquema_ok = all(x in pd.read_csv(os.path.join(BASE,"Entradas/llamadas_cdr.csv"),nrows=1).columns for x in esq_c) and all(x in t.columns for x in esq_t)

# ---------- Union con tickets ----------
m = t.merge(c[["id_llamada","espera_seg","escalado_a","cola","motivo","hora","dia_semana","tipo_llamada","semana"]], on="id_llamada", how="left")
m["esc"] = m.escalado_a.notna().astype(int)
m["tramo"] = pd.cut(m.espera_seg, [-1,20,60,120,10**6], labels=["0-20 s","21-60 s","61-120 s",">120 s"])

# ---------- Calidad de datos ----------
semanas = c.groupby("semana").agg(dias=("fecha","nunique"), llamadas=("id_llamada","count"), desde=("fecha","min"), hasta=("fecha","max")).reset_index()
med = semanas.llamadas.median()
semanas["completa"] = (semanas.dias == 7) & (semanas.llamadas >= 0.85*med)
sem_ok = [s for s, ok in zip(semanas.semana, semanas.completa) if ok]
sin_ticket = at[~at.id_llamada.isin(t.id_llamada)]
DQ = {
  "esquema_ok": bool(esquema_ok),
  "filas_cdr": len(c), "filas_tickets": len(t),
  "rango_cdr": [str(c.fecha.min().date()), str(c.fecha.max().date())],
  "rango_tickets": [str(t.fecha_apertura.min().date()), str(t.fecha_apertura.max().date())],
  "dup_id_llamada": int(c.id_llamada.duplicated().sum()), "dup_id_caso": int(t.id_caso.duplicated().sum()),
  "dup_ticket_por_llamada": int(t.id_llamada.duplicated().sum()),
  "nulos_cdr": {k:int(v) for k,v in c[esq_c].isna().sum().items() if v>0},
  "nulos_tickets": {k:int(v) for k,v in t[esq_t].isna().sum().items() if v>0},
  "tickets_sin_llamada": int((~t.id_llamada.isin(c.id_llamada)).sum()),
  "atendidas_sin_ticket": int(len(sin_ticket)), "pct_atendidas_sin_ticket": float(len(sin_ticket)/len(at)),
  "tickets_de_abandonadas": int(t.id_llamada.isin(c[c.ab==1].id_llamada).sum()),
  "agente_vacio_no_abandonada": int(((c.id_agente.isna()) & (c.ab==0)).sum()),
  "agente_con_abandonada": int(((c.id_agente.notna()) & (c.ab==1)).sum()),
  "csat_fuera_rango": int(((t.csat<1)|(t.csat>5)).sum()),
  "tiempos_negativos": int(((c.espera_seg<0)|(c.duracion_seg<0)|(c.acw_seg<0)).sum()+(t.horas_resolucion<0).sum()),
  "esperas_gt_600": int((c.espera_seg>600).sum()), "espera_max": int(c.espera_seg.max()),
  "horas_resolucion_cero": int((t.horas_resolucion==0).sum()),
  "incoherencias_ticket_cdr": int((m.id_agente_x.ne(c.set_index("id_llamada").loc[m.id_llamada,"id_agente"].values)).sum()) if False else 0,
  "reinc_igual_reabierto": bool(((t.reincidencia==1)==(t.estado_caso=="reabierto")).all()),
  "pendientes_con_fcr1": int(((t.estado_caso=="pendiente")&(t.fcr==1)).sum()),
  "pendientes": int((t.estado_caso=="pendiente").sum()),
  "salientes": int((c.tipo_llamada=="saliente").sum()),
  "salientes_abandonadas": int(((c.tipo_llamada=="saliente")&(c.ab==1)).sum()),
  "agentes": int(c.id_agente.nunique()), "clientes": int(c.id_cliente.nunique()),
  "semanas": semanas.assign(semana=semanas.semana.astype(str), desde=semanas.desde.astype(str), hasta=semanas.hasta.astype(str)).to_dict("records"),
  "semanas_incompletas": [str(s) for s,ok in zip(semanas.semana,semanas.completa) if not ok],
}
# Coherencia agente/cliente/categoria entre ticket y CDR
chk = t.merge(c[["id_llamada","id_agente","id_cliente","motivo"]], on="id_llamada", suffixes=("","_c"))
DQ["incoherencias_ticket_cdr"] = int(((chk.id_agente!=chk.id_agente_c)|(chk.id_cliente!=chk.id_cliente_c)|(chk.categoria!=chk.motivo)).sum())

# ---------- Semaforo ----------
def estado(v, meta, modo):
    v = round(v, 1)  # se evalua con la misma precision con que se muestra
    if modo == "max":   # menor es mejor
        return "verde" if v <= meta else ("amarillo" if v <= meta*1.10 else "rojo")
    if modo == "min":   # mayor es mejor
        return "verde" if v >= meta else ("amarillo" if v >= meta*0.90 else "rojo")
    if modo == "rango":
        lo, hi = meta
        if lo <= v <= hi: return "verde"
        return "amarillo" if (lo*0.90 <= v <= hi*1.10) else "rojo"
    return "info"

# ---------- KPIs ----------
K = []  # (id, familia, nombre, valor, meta_txt, estado, unidad, baseline)
def add(i, fam, nombre, v, meta, modo, unidad, base=None):
    est = estado(v, meta, modo) if modo != "info" else "info"
    mt = {"max": f"≤ {meta}", "min": f"≥ {meta}", "rango": f"{meta[0]}–{meta[1]}" if modo=="rango" else "", "info": "Informativo"}[modo]
    K.append(dict(id=i, familia=fam, nombre=nombre, valor=float(v), meta=mt, meta_num=(meta if modo!="rango" else list(meta)) if modo!="info" else None,
                  modo=modo, estado=est, unidad=unidad, baseline=base))
n = len(c)
BASELINE = {"A2":13.9,"A3":56.9,"A4":22.0,"B1":333,"B3":37.7,"C1":71.3,"C2":5.6,"C4":14.4,"C5":18.3,"D1":3.26,"D2":42.7,"D3":24.2}
add("A1","A","Volumen de llamadas", n, None, "info", "llamadas")
add("A2","A","Tasa de abandono", c.ab.mean()*100, 8, "max", "%", BASELINE["A2"])
add("A3","A","Nivel de servicio 80/20", (c.espera_seg<=20).mean()*100, 80, "min", "%", BASELINE["A3"])
add("A4","A","ASA (espera media de atendidas)", at.espera_seg.mean(), 20, "max", "s", BASELINE["A4"])
add("A5","A","Tiempo medio hasta abandonar", c[c.ab==1].espera_seg.mean(), None, "info", "s")
add("B1","B","AHT (duración + ACW)", at.aht.mean(), (240,360), "rango", "s", BASELINE["B1"])
add("B2","B","ACW medio", at.acw_seg.mean(), 30, "max", "s")
add("B3","B","Tasa de escalamiento", at.esc.mean()*100, 15, "max", "%", BASELINE["B3"])
agentes_n = at.id_agente.nunique()
add("B4","B","Llamadas atendidas por agente", len(at)/agentes_n, None, "info", "llamadas")
add("C1","C","FCR (resolución al primer contacto)", t.fcr.mean()*100, 75, "min", "%", BASELINE["C1"])
add("C2","C","Reincidencia / reapertura (mismo dato)", t.reincidencia.mean()*100, 5, "max", "%", BASELINE["C2"])
add("C4","C","Backlog pendiente", (t.estado_caso=="pendiente").mean()*100, 10, "max", "%", BASELINE["C4"])
add("C5","C","Tiempo medio de resolución", t.horas_resolucion.mean(), 24, "max", "h", BASELINE["C5"])
cl = c.groupby("id_cliente").size()
add("C6","C","Clientes con ≥ 3 llamadas", (cl>=3).mean()*100, None, "info", "%")
add("D1","D","CSAT promedio", t.csat.mean(), 4.0, "min", "pts", BASELINE["D1"])
add("D2","D","CSAT top-2 box (≥ 4)", (t.csat>=4).mean()*100, 80, "min", "%", BASELINE["D2"])
add("D3","D","Clientes insatisfechos (CSAT ≤ 2)", (t.csat<=2).mean()*100, 10, "max", "%", BASELINE["D3"])
riesgo = t[(t.csat<=2)|(t.estado_caso=="reabierto")]
tot_val = t.valor_orden.sum()
add("E1","E","Valor en riesgo (CSAT ≤ 2 o reabierto)", riesgo.valor_orden.sum(), None, "info", "valor")
add("E2","E","Valor en casos pendientes", t[t.estado_caso=="pendiente"].valor_orden.sum(), None, "info", "valor")
KD = {k["id"]: k for k in K}

extra = {
  "aht_mediana": float(at.aht.median()), "ab_menos20": float(((c.ab==1)&(c.espera_seg<=20)).sum()/c.ab.sum()),
  "ab_20_60": float(((c.ab==1)&(c.espera_seg>20)&(c.espera_seg<=60)).sum()/c.ab.sum()),
  "ab_mas60": float(((c.ab==1)&(c.espera_seg>60)).sum()/c.ab.sum()),
  "n_ab": int(c.ab.sum()), "n_at": int(len(at)), "n_tickets": int(len(t)), "agentes": int(agentes_n),
  "c5_mediana": float(t.horas_resolucion.median()), "c5_gt24": float((t.horas_resolucion>24).mean()*100),
  "c4_n": int((t.estado_caso=="pendiente").sum()), "c3_n": int((t.estado_caso=="reabierto").sum()),
  "e1_pct": float(riesgo.valor_orden.sum()/tot_val*100), "e1_solo_csat": float(t[t.csat<=2].valor_orden.sum()),
  "e1_solo_csat_pct": float(t[t.csat<=2].valor_orden.sum()/tot_val*100), "valor_total": float(tot_val),
  "e2_pct": float(t[t.estado_caso=="pendiente"].valor_orden.sum()/tot_val*100),
  "c6_n": int((cl>=3).sum()), "clientes": int(len(cl)),
  "entrantes": int((c.tipo_llamada=="entrante").sum()), "salientes": int((c.tipo_llamada=="saliente").sum()),
  "ab_entrante": float(c[c.tipo_llamada=="entrante"].ab.mean()*100), "ab_saliente": float(c[c.tipo_llamada=="saliente"].ab.mean()*100),
  "esc_destino": {k:float(v) for k,v in (at.escalado_a.value_counts()/len(at)*100).items()},
  "cobertura_tickets": float(len(t)/len(at)),
}

# ---------- Cortes ----------
def corte(df_c=None, by=None):
    g = c.groupby(by)
    return g.agg(llamadas=("id_llamada","count"), abandono_pct=("ab", lambda s: s.mean()*100),
                 espera_media_s=("espera_seg","mean"), nivel_servicio_pct=("espera_seg", lambda s:(s<=20).mean()*100))
def corte_at(by):
    g = at.groupby(by)
    return g.agg(atendidas=("id_llamada","count"), aht_s=("aht","mean"), acw_s=("acw_seg","mean"), escalamiento_pct=("esc", lambda s: s.mean()*100))
def corte_t(by):
    g = m.groupby(by, observed=True)
    return g.agg(casos=("id_caso","count"), fcr_pct=("fcr", lambda s:s.mean()*100), reincid_pct=("reincidencia", lambda s:s.mean()*100),
                 pendiente_pct=("estado_caso", lambda s:(s=="pendiente").mean()*100), horas_res=("horas_resolucion","mean"),
                 csat=("csat","mean"), top2_pct=("csat", lambda s:(s>=4).mean()*100), insatisf_pct=("csat", lambda s:(s<=2).mean()*100),
                 valor_riesgo=("valor_orden", lambda s: 0))
def full(by, key_t=None):
    a = corte(by=by); b = corte_at(by); d = corte_t(key_t or by)
    d = d.drop(columns="valor_riesgo")
    return a.join(b, how="outer").join(d, how="outer").round(2)

DET = {}
wk = full("semana"); wk["completa"] = [s in sem_ok for s in wk.index]; DET["semana"] = wk
order_dow = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
DET["dia_semana"] = full("dia_semana").reindex([d for d in order_dow if d in set(c.dia_semana)])
DET["hora"] = full("hora")
DET["cola"] = full("cola"); DET["tipo_llamada"] = full("tipo_llamada")
mot = corte(by="motivo").join(corte_at("motivo"), how="outer").join(corte_t("categoria").drop(columns="valor_riesgo").rename_axis("motivo"), how="outer").round(2)
DET["motivo"] = mot
# destino de escalamiento (solo escaladas)
esc_t = m[m.esc==1].groupby("escalado_a").agg(casos=("id_caso","count"), fcr_pct=("fcr",lambda s:s.mean()*100), csat=("csat","mean"), horas_res=("horas_resolucion","mean")).round(2)
esc_c = at[at.esc==1].groupby("escalado_a").agg(llamadas=("id_llamada","count"), aht_s=("aht","mean")).round(1)
DET["escalamiento_destino"] = esc_c.join(esc_t)
# valor por motivo
val_m = m.groupby("categoria").apply(lambda d: pd.Series({"valor_total":d.valor_orden.sum(),"valor_riesgo":d[(d.csat<=2)|(d.estado_caso=="reabierto")].valor_orden.sum(),"valor_pendiente":d[d.estado_caso=="pendiente"].valor_orden.sum()}), include_groups=False).round(0)
val_m["riesgo_pct"] = (val_m.valor_riesgo/val_m.valor_total*100).round(1)
DET["valor_por_motivo"] = val_m
# Agentes
ag_c = at.groupby("id_agente").agg(atendidas=("id_llamada","count"), aht_s=("aht","mean"), acw_s=("acw_seg","mean"), escal_pct=("esc",lambda s:s.mean()*100))
ag_t = m.groupby("id_agente").agg(casos=("id_caso","count"), fcr_pct=("fcr",lambda s:s.mean()*100), csat=("csat","mean"), reincid_pct=("reincidencia",lambda s:s.mean()*100))
ag = ag_c.join(ag_t)
for col in ["aht_s","escal_pct","fcr_pct","csat","reincid_pct"]:
    ag["z_"+col] = (ag[col]-ag[col].mean())/ag[col].std()
# desviaciones "malas": aht alto, escal alto, fcr bajo, csat bajo, reinc alta
bad = pd.DataFrame({"aht_s":ag.z_aht_s, "escal_pct":ag.z_escal_pct, "fcr_pct":-ag.z_fcr_pct, "csat":-ag.z_csat, "reincid_pct":ag.z_reincid_pct})
ag["n_kpis_fuera"] = (bad.abs()>1.5).sum(axis=1)
ag["n_kpis_peor"] = (bad>1.5).sum(axis=1)
DET["agente"] = ag.round(2).sort_values("csat", ascending=False)
ag_flag = ag[ag.n_kpis_fuera>=2].index.tolist()
agente_info = {"csat_min": float(ag.csat.min()), "csat_max": float(ag.csat.max()), "fcr_min": float(ag.fcr_pct.min()), "fcr_max": float(ag.fcr_pct.max()),
               "esc_min": float(ag.escal_pct.min()), "esc_max": float(ag.escal_pct.max()), "aht_min": float(ag.aht_s.min()), "aht_max": float(ag.aht_s.max()),
               "att_min": int(ag.atendidas.min()), "att_max": int(ag.atendidas.max()), "att_med": float(ag.atendidas.mean()),
               "flag": ag_flag, "csat_sd": float(ag.csat.std())}
# Cruces
cr = {}
cr["csat_escalado"] = m.groupby("esc").agg(casos=("id_caso","count"), csat=("csat","mean"), fcr_pct=("fcr",lambda s:s.mean()*100), insatisf_pct=("csat",lambda s:(s<=2).mean()*100), horas_res=("horas_resolucion","mean")).round(2).rename(index={0:"No escalado",1:"Escalado"})
cr["csat_fcr"] = m.groupby("fcr").agg(casos=("id_caso","count"), csat=("csat","mean"), insatisf_pct=("csat",lambda s:(s<=2).mean()*100)).round(2).rename(index={0:"Sin FCR",1:"Con FCR"})
cr["csat_espera"] = m.groupby("tramo", observed=True).agg(casos=("id_caso","count"), csat=("csat","mean"), insatisf_pct=("csat",lambda s:(s<=2).mean()*100), fcr_pct=("fcr",lambda s:s.mean()*100)).round(2)
cr["csat_esc_x_fcr"] = m.groupby(["esc","fcr"]).agg(casos=("id_caso","count"), csat=("csat","mean")).round(2)
cr["cola_x_motivo_n"] = pd.crosstab(c.cola, c.motivo)
cr["cola_x_motivo_pct"] = (pd.crosstab(c.cola, c.motivo, normalize="index")*100).round(1)
cr["motivo_x_destino_n"] = pd.crosstab(at.motivo, at.escalado_a.fillna("No escalada"))
cr["motivo_x_destino_pct"] = (pd.crosstab(at[at.esc==1].motivo, at[at.esc==1].escalado_a, normalize="index")*100).round(1)
cr["esc_cola_motivo"] = at.pivot_table(index="cola", columns="motivo", values="esc", aggfunc="mean").mul(100).round(1)
cr["csat_cola_motivo"] = m.pivot_table(index="cola", columns="categoria", values="csat", aggfunc="mean").round(2)
cr["abandono_hora_cola"] = c.pivot_table(index="hora", columns="cola", values="ab", aggfunc="mean").mul(100).round(1)
for k,v in cr.items(): DET["x_"+k] = v

# Datos de apoyo para el diagnostico
h = DET["hora"]
glob_ab = c.ab.mean()*100
picos = h[h.abandono_pct > glob_ab*1.25].index.tolist()
share_ab_picos = c[c.hora.isin(picos)].ab.sum()/c.ab.sum()*100
share_vol_picos = c.hora.isin(picos).mean()*100
resto = c[~c.hora.isin(picos)]
dx = {"picos": [int(x) for x in picos], "share_ab_picos": float(share_ab_picos), "share_vol_picos": float(share_vol_picos),
      "ab_resto": float(resto.ab.mean()*100), "ab_picos": float(c[c.hora.isin(picos)].ab.mean()*100),
      "espera_picos_at": float(at[at.hora.isin(picos)].espera_seg.mean()), "espera_resto_at": float(at[~at.hora.isin(picos)].espera_seg.mean()),
      "ns_picos": float((c[c.hora.isin(picos)].espera_seg<=20).mean()*100), "ns_resto": float((resto.espera_seg<=20).mean()*100),
      "vol_hora_media": float(h.llamadas.mean())}
# Escalamiento: uniformidad
em = DET["motivo"].escalamiento_pct; ec = DET["cola"].escalamiento_pct
dx["esc_motivo_rango"] = [float(em.min()), float(em.max())]; dx["esc_cola_rango"] = [float(ec.min()), float(ec.max())]
ce = cr["csat_escalado"]; ne = ce.loc["No escalado"]; es = ce.loc["Escalado"]
dx["csat_no_esc"] = float(ne.csat); dx["csat_esc"] = float(es.csat)
dx["fcr_no_esc"] = float(ne.fcr_pct); dx["fcr_esc"] = float(es.fcr_pct)
dx["insat_no_esc"] = float(ne.insatisf_pct); dx["insat_esc"] = float(es.insatisf_pct)
p_esc = m.esc.mean()
dx["p_esc_tickets"] = float(p_esc)
dx["csat_meta15"] = float(0.15*es.csat + 0.85*ne.csat)
dx["csat_meta25"] = float(0.25*es.csat + 0.75*ne.csat)
dx["insat_meta15"] = float(0.15*es.insatisf_pct + 0.85*ne.insatisf_pct)
# destino por motivo: % del destino "esperado"
esperado = {"estado_envio":"Area_Logistica","devolucion":"Area_Logistica","cambio_producto":"Area_Logistica","problema_pago":"Area_Billing","facturacion":"Area_Billing"}
sub = at[(at.esc==1)&(at.motivo.isin(esperado))]
dx["destino_esperado_pct"] = float((sub.escalado_a==sub.motivo.map(esperado)).mean()*100)
dx["destino_esperado_azar"] = float(1/3*100)
dx["envio_a_billing_pct"] = float((at[(at.esc==1)&(at.motivo=="estado_envio")].escalado_a=="Area_Billing").mean()*100)
dx["pago_a_logistica_pct"] = float((at[(at.esc==1)&(at.motivo=="problema_pago")].escalado_a=="Area_Logistica").mean()*100)
# Enrutamiento: % de llamadas en la cola "natural"
natural = {"estado_envio":"Soporte_Envios","devolucion":"Soporte_Pedidos","cambio_producto":"Soporte_Pedidos","problema_pago":"Soporte_Pedidos","facturacion":"Soporte_Pedidos","reclamo_calidad":"Retenciones","informacion_preventa":"Ventas","cuenta_claves":"Soporte_Pedidos"}
dx["envio_en_ret_ventas"] = float(c[c.motivo=="estado_envio"].cola.isin(["Retenciones","Ventas"]).mean()*100)
dx["preventa_fuera_ventas"] = float((c[c.motivo=="informacion_preventa"].cola!="Ventas").mean()*100)
dx["cola_motivo_max_diff"] = float((cr["cola_x_motivo_pct"].max()-cr["cola_x_motivo_pct"].min()).max())
dx["ventas_pct_preventa"] = float(cr["cola_x_motivo_pct"].loc["Ventas","informacion_preventa"])
dx["retenc_pct_reclamo"] = float(cr["cola_x_motivo_pct"].loc["Retenciones","reclamo_calidad"])
# Espera vs csat
ce2 = cr["csat_espera"]; dx["csat_espera_rango"] = [float(ce2.csat.min()), float(ce2.csat.max())]
# Backlog / reincidencia por motivo
dx["fcr_motivo"] = {k: float(v) for k,v in DET["motivo"].fcr_pct.items()}
dx["reinc_motivo"] = {k: float(v) for k,v in DET["motivo"].reincid_pct.items()}
dx["pend_motivo"] = {k: float(v) for k,v in DET["motivo"].pendiente_pct.items()}
dx["csat_motivo"] = {k: float(v) for k,v in DET["motivo"].csat.items()}
dx["esc_motivo"] = {k: float(v) for k,v in DET["motivo"].escalamiento_pct.items()}
dx["ab_motivo"] = {k: float(v) for k,v in DET["motivo"].abandono_pct.items()}
dx["ab_cola"] = {k: float(v) for k,v in DET["cola"].abandono_pct.items()}
dx["esc_cola"] = {k: float(v) for k,v in DET["cola"].escalamiento_pct.items()}
dx["ab_hora"] = {int(k): float(v) for k,v in h.abandono_pct.items()}
dx["vol_hora"] = {int(k): int(v) for k,v in h.llamadas.items()}
dx["espera_hora"] = {int(k): float(v) for k,v in h.espera_media_s.items()}
dx["ab_dow"] = {k: float(v) for k,v in DET["dia_semana"].abandono_pct.items()}
dx["vol_dow"] = {k: int(v) for k,v in DET["dia_semana"].llamadas.items()}
dx["fcr_esc_x"] = {f"esc{a}_fcr{b}": float(v) for (a,b),v in cr["csat_esc_x_fcr"].csat.items()}
dx["csat_fcr"] = {k: float(v) for k,v in cr["csat_fcr"].csat.items()}
dx["csat_espera"] = {k: float(v) for k,v in ce2.csat.items()}
dx["tickets_esc_pct_fcr"] = None
# Tendencia semanal (solo completas)
wkc = DET["semana"][DET["semana"].completa]
dx["tend"] = {"semanas":[str(s) for s in wkc.index], "abandono":[float(x) for x in wkc.abandono_pct], "fcr":[float(x) for x in wkc.fcr_pct], "csat":[float(x) for x in wkc.csat],
              "esc":[float(x) for x in wkc.escalamiento_pct], "vol":[int(x) for x in wkc.llamadas]}
# Pendientes antiguos? casos pendiente con valor
dx["pend_valor_medio"] = float(t[t.estado_caso=="pendiente"].valor_orden.mean())
dx["pend_horas"] = float(t[t.estado_caso=="pendiente"].horas_resolucion.mean())
# riesgo por escalado
dx["riesgo_esc_pct"] = float(riesgo.merge(m[["id_caso","esc"]],on="id_caso").esc.mean()*100)
dx["riesgo_n"] = int(len(riesgo))
# Valor medio por csat
dx["valor_medio_csat12"] = float(t[t.csat<=2].valor_orden.mean()); dx["valor_medio_resto"] = float(t[t.csat>2].valor_orden.mean())
# Contactos repetidos: csat de clientes con >=3
rep = cl[cl>=3].index
dx["csat_repetidos"] = float(m[m.id_cliente.isin(rep)].csat.mean()); dx["csat_no_repetidos"] = float(m[~m.id_cliente.isin(rep)].csat.mean())
dx["cl_dist"] = {int(k):int(v) for k,v in cl.value_counts().sort_index().items()}
dx["llamadas_por_cliente_media"] = float(cl.mean())


# ---------- Dimensionamiento aproximado (Erlang C) ----------
import math
def erlang_c_n(calls_h, aht_s, target=0.80, t=20):
    A = calls_h*aht_s/3600.0
    n = max(1, int(math.floor(A))+1)
    while True:
        s = sum(A**k/math.factorial(k) for k in range(n))
        top = A**n/math.factorial(n)*n/(n-A) if n>A else float("inf")
        pw = top/(s+top) if n>A else 1.0
        sl = 1 - pw*math.exp(-(n-A)*t/aht_s) if n>A else 0
        if sl >= target: return A, n
        n += 1
dias_tot = c.fecha.nunique()
aht_m = at.aht.mean()
dim = {}
for hr in sorted(c.hora.unique()):
    ch = (c.hora==hr).sum()/dias_tot
    A, nn = erlang_c_n(ch, aht_m)
    dim[int(hr)] = {"llamadas_por_hora": float(ch), "erlangs": float(A), "agentes_80_20": int(nn)}
dx["dim"] = dim; dx["dias"] = int(dias_tot)
dx["dim_picos_agentes"] = max(dim[hh]["agentes_80_20"] for hh in dx["picos"]); dx["dim_valle_agentes"] = min(v["agentes_80_20"] for v in dim.values())


# ---------- Datos adicionales para el informe ----------
cm = DET["motivo"]
dx["casos_motivo"] = {k:int(v) for k,v in cm.casos.items()}
dx["csat_dist"] = {int(k):int(v) for k,v in t.csat.value_counts().sort_index().items()}
dx["horas_esc"] = {k: float(v) for k,v in cr["csat_escalado"].horas_res.items()}
dx["insat_meta25"] = float(0.25*es.insatisf_pct + 0.75*ne.insatisf_pct)
dx["valor_motivo"] = {k: {"total": float(v.valor_total), "riesgo": float(v.valor_riesgo), "pend": float(v.valor_pendiente), "pct": float(v.riesgo_pct)} for k,v in DET["valor_por_motivo"].iterrows()}
fcr_ganancia = sum(dx["casos_motivo"][mm]*max(0, 0.75 - dx["fcr_motivo"][mm]/100) for mm in ["reclamo_calidad","cambio_producto","devolucion"])
dx["fcr_sim_3motivos"] = float((t.fcr.sum() + fcr_ganancia)/len(t)*100)
dx["fcr_sim_2motivos"] = float((t.fcr.sum() + sum(dx["casos_motivo"][mm]*max(0, 0.75 - dx["fcr_motivo"][mm]/100) for mm in ["reclamo_calidad","cambio_producto"]))/len(t)*100)
dx["ab_sim_picos"] = float(glob_ab - dx["share_vol_picos"]/100*(dx["ab_picos"]-dx["ab_resto"]))
dx["backlog_objetivo_n"] = int(round(0.10*len(t))); dx["backlog_a_cerrar"] = int((t.estado_caso=="pendiente").sum() - round(0.10*len(t)))
dx["acw_horas_exceso"] = float((at.acw_seg.mean()-30)*len(at)/3600)
dx["esc_destino_n"] = {k:int(v) for k,v in at.escalado_a.value_counts().items()}
dx["dist_ab_total"] = int(c.ab.sum())
dx["pend_fcr1"] = int(((t.estado_caso=="pendiente")&(t.fcr==1)).sum())

# ---------- Comparacion con linea base ----------
for k in K:
    b = k["baseline"]
    k["variacion"] = None if b is None else float(round(k["valor"]-b, 2))
    if b is None: k["variacion_txt"] = "sin referencia"
    else:
        d = k["valor"]-b
        k["variacion_txt"] = ("0,0 " if abs(d)<0.05 else f"{d:+.1f} ").replace(".",",") + ("pp" if k["unidad"]=="%" else k["unidad"])
# ---------- Resumen CSV ----------
estado_txt = {"verde":"verde","amarillo":"amarillo","rojo":"rojo","info":"informativo"}
res = pd.DataFrame([{ "kpi": f'{k["id"]} {k["nombre"]}', "familia": k["familia"], "valor": round(k["valor"],2), "unidad": k["unidad"], "meta": k["meta"],
    "estado": estado_txt[k["estado"]], "variacion_vs_anterior": k["variacion_txt"]} for k in K])
res.to_csv(os.path.join(OUT, "kpis_resumen.csv"), index=False, encoding="utf-8-sig")

# ---------- Excel ----------
with pd.ExcelWriter(os.path.join(OUT, "kpis_detalle.xlsx"), engine="openpyxl") as xw:
    res.to_excel(xw, sheet_name="resumen_kpis", index=False)
    for name, df in DET.items():
        d = df.copy()
        if isinstance(d.index, pd.MultiIndex) is False and d.index.name is None: d.index.name = name
        d.to_excel(xw, sheet_name=name[:31])
    for ws in xw.book.worksheets:
        for col in ws.columns:
            w = max(len(str(cell.value)) if cell.value is not None else 0 for cell in col[:60])
            ws.column_dimensions[col[0].column_letter].width = min(max(10, w+2), 42)
        ws.freeze_panes = "B2"

# ---------- Graficos ----------
def save(fig, name):
    fig.tight_layout(); fig.savefig(os.path.join(GR, name), dpi=140); plt.close(fig)
def etq(x): return x.replace("_"," ").capitalize()
def barras_dest(ax, labels, vals, destacar=None, color_dest=TERRA, fmt="{:.1f}", horizontal=True):
    cols = [color_dest if (destacar is not None and l==destacar) else VERDE for l in labels]
    if horizontal:
        ax.barh(labels, vals, color=cols)
        for i,v in enumerate(vals): ax.text(v, i, " "+fmt.format(v), va="center", fontsize=9)
        ax.invert_yaxis()
    else:
        ax.bar(labels, vals, color=cols)
        for i,v in enumerate(vals): ax.text(i, v, fmt.format(v), ha="center", va="bottom", fontsize=9)

# 1 tendencia semanal
tw = dx["tend"]; xs = [s[5:] for s in tw["semanas"]]
fig, axs = plt.subplots(1,3, figsize=(12,3.6))
for ax,(k,tt,meta,col) in zip(axs,[("abandono","Abandono (%)",8,VERDE),("fcr","FCR (%)",75,VERDE),("csat","CSAT promedio",4.0,VERDE)]):
    ax.plot(xs, tw[k], color=col, marker="o", lw=2)
    ax.axhline(meta, color=TERRA, ls="--", lw=1.2); ax.text(len(xs)-1, meta, f" meta {meta}", color=TERRA, va="bottom", ha="right", fontsize=8, fontweight="bold")
    ax.set_title(tt, loc="left"); ax.tick_params(axis="x", rotation=45, labelsize=8)
    lo = min(min(tw[k]), meta); hi = max(max(tw[k]), meta); pad=(hi-lo)*0.25 or 1
    ax.set_ylim(lo-pad, hi+pad)
save(fig, "01_tendencia_semanal.png")
# 2 curva intradia
hh = DET["hora"]
fig, ax = plt.subplots(figsize=(11,4))
colores = [DORADO if int(i) in dx["picos"] else OLIVA for i in hh.index]
ax.bar(hh.index.astype(str), hh.llamadas, color=colores); ax.set_ylabel("Llamadas")
ax.set_title("Volumen de llamadas (barras) y tasa de abandono (línea) por hora", loc="left")
ax2 = ax.twinx(); ax2.plot(hh.index.astype(str), hh.abandono_pct, color=VERDE, marker="o", lw=2); ax2.set_ylabel("Abandono (%)")
ax2.axhline(8, color=TERRA, ls="--", lw=1.2); ax2.text(len(hh)-1, 8, "meta 8 %", color=TERRA, ha="right", va="bottom", fontsize=8, fontweight="bold")
ax2.spines["right"].set_visible(True); ax.set_xlabel("Hora de entrada")
save(fig, "02_curva_intradia.png")
# 3 FCR y CSAT por motivo
mo = DET["motivo"].sort_values("fcr_pct")
fig, axs = plt.subplots(1,2, figsize=(12,4.2))
barras_dest(axs[0], [etq(x) for x in mo.index], mo.fcr_pct.values, destacar=etq(mo.fcr_pct.idxmin()))
axs[0].axvline(75, color=TERRA, ls="--", lw=1.2); axs[0].set_title("FCR por motivo (%) · meta 75", loc="left")
mo2 = DET["motivo"].sort_values("csat")
barras_dest(axs[1], [etq(x) for x in mo2.index], mo2.csat.values, destacar=etq(mo2.csat.idxmin()), fmt="{:.2f}")
axs[1].axvline(4.0, color=TERRA, ls="--", lw=1.2); axs[1].set_title("CSAT por motivo · meta 4,0", loc="left"); axs[1].set_xlim(0,5)
save(fig, "03_fcr_csat_motivo.png")
# 4 CSAT escalado vs no
fig, ax = plt.subplots(figsize=(6,4))
labs = ["No escalado","Escalado"]; vals=[dx["csat_no_esc"], dx["csat_esc"]]
ax.bar(labs, vals, color=[VERDE, TERRA], width=0.5)
for i,v in enumerate(vals): ax.text(i, v, f"{v:.2f}".replace(".",","), ha="center", va="bottom", fontweight="bold")
ax.axhline(4.0, color=OLIVA, ls="--", lw=1.2); ax.text(1.45, 4.0, "meta 4,0", color=TINTA, ha="right", va="bottom", fontsize=8)
ax.set_ylim(0,5); ax.set_title("CSAT según escalamiento", loc="left")
save(fig, "04_csat_escalado.png")
# 5 distribucion CSAT
dist = t.csat.value_counts(normalize=True).sort_index()*100
fig, ax = plt.subplots(figsize=(6,4))
ax.bar(dist.index.astype(str), dist.values, color=[TERRA if i<=2 else VERDE for i in dist.index])
for i,v in enumerate(dist.values): ax.text(i, v, f"{v:.1f} %".replace(".",","), ha="center", va="bottom", fontsize=9)
ax.set_title("Distribución del CSAT (% de casos)", loc="left"); ax.set_xlabel("CSAT (1 a 5)")
save(fig, "05_distribucion_csat.png")
# 6 heatmap cola x motivo
hm = cr["cola_x_motivo_pct"]
from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list("cesta", [CREMA, OLIVA, VERDE])
fig, ax = plt.subplots(figsize=(10,3.6))
im = ax.imshow(hm.values, cmap=cmap, aspect="auto", vmin=0, vmax=max(40, hm.values.max()))
ax.set_xticks(range(len(hm.columns))); ax.set_xticklabels([etq(x) for x in hm.columns], rotation=25, ha="right", fontsize=9)
ax.set_yticks(range(len(hm.index))); ax.set_yticklabels(hm.index)
for i in range(hm.shape[0]):
    for j in range(hm.shape[1]):
        v = hm.values[i,j]; ax.text(j,i,f"{v:.0f}%",ha="center",va="center",color=(CREMA if v>22 else TINTA),fontsize=9)
ax.set_title("Mezcla de motivos dentro de cada cola (% de la cola)", loc="left")
for s in ax.spines.values(): s.set_visible(False)
save(fig, "06_heatmap_cola_motivo.png")
# 7 ranking agentes
ar = DET["agente"]
fig, axs = plt.subplots(1,2, figsize=(12,5.2))
a1 = ar.sort_values("csat"); axs[0].barh(a1.index, a1.csat, color=VERDE); axs[0].axvline(ar.csat.mean(), color=DORADO, lw=2)
axs[0].set_xlim(0, 5); axs[0].set_title(f"CSAT por agente · media {ar.csat.mean():.2f}".replace(".",","), loc="left")
a2 = ar.sort_values("fcr_pct"); axs[1].barh(a2.index, a2.fcr_pct, color=VERDE); axs[1].axvline(ar.fcr_pct.mean(), color=DORADO, lw=2)
axs[1].set_xlim(0, 100); axs[1].set_title(f"FCR por agente (%) · media {ar.fcr_pct.mean():.1f}".replace(".",","), loc="left")
for ax in axs: ax.tick_params(axis="y", labelsize=8)
save(fig, "07_ranking_agentes.png")
# 8 csat por tramo de espera
fig, ax = plt.subplots(figsize=(6,4)); ce2r = cr["csat_espera"]
ax.bar(ce2r.index.astype(str), ce2r.csat, color=VERDE, width=0.55)
for i,v in enumerate(ce2r.csat): ax.text(i, v, f"{v:.2f}".replace(".",","), ha="center", va="bottom", fontsize=9)
ax.set_ylim(0,5); ax.set_title("CSAT según tramo de espera", loc="left")
save(fig, "08_csat_espera.png")
# 9 motivo x destino
md = cr["motivo_x_destino_pct"]
fig, ax = plt.subplots(figsize=(7,4.2))
im = ax.imshow(md.values, cmap=cmap, aspect="auto", vmin=0, vmax=60)
ax.set_xticks(range(len(md.columns))); ax.set_xticklabels([x.replace("Area_","") for x in md.columns]); ax.set_yticks(range(len(md.index))); ax.set_yticklabels([etq(x) for x in md.index])
for i in range(md.shape[0]):
    for j in range(md.shape[1]):
        v = md.values[i,j]; ax.text(j,i,f"{v:.0f}%",ha="center",va="center",color=(CREMA if v>30 else TINTA),fontsize=9)
ax.set_title("Destino del escalamiento por motivo (% de las escaladas)", loc="left", fontsize=11)
for s in ax.spines.values(): s.set_visible(False)
save(fig, "09_motivo_destino.png")
# 10 escalamiento por motivo
fig, ax = plt.subplots(figsize=(6.5,4)); eo = DET["motivo"].sort_values("escalamiento_pct")
barras_dest(ax, [etq(x) for x in eo.index], eo.escalamiento_pct.values, destacar=None)
ax.axvline(15, color=TERRA, ls="--", lw=1.2); ax.set_title("Escalamiento por motivo (%) · meta 15", loc="left")
save(fig, "10_escalamiento_motivo.png")

# ---------- JSON ----------
def conv(o):
    if isinstance(o,(np.integer,)): return int(o)
    if isinstance(o,(np.floating,)): return float(o)
    if isinstance(o,(np.bool_,)): return bool(o)
    raise TypeError(type(o))
json.dump({"kpis":K,"extra":extra,"dx":dx,"dq":DQ,"agente":agente_info,"fecha_corrida":"2026-11-10",
           "periodo":[DQ["rango_cdr"][0],DQ["rango_cdr"][1]]}, open(os.path.join(OUT,"resultados.json"),"w",encoding="utf-8"), default=conv, ensure_ascii=False, indent=1)
print("OK")
for k in K: print(k["id"], k["nombre"], round(k["valor"],2), k["estado"], k["variacion_txt"])
