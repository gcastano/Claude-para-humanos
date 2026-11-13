"""Cálculo de KPIs del call center de Cesta.
Uso: python3 calculo_kpis.py (el script vive en Salidas/AAAA-MM-DD/ y lee ../../Entradas/*.csv).
Escribe kpis_resumen.csv, kpis_detalle.xlsx y resultados.json en su misma carpeta."""
import json, os
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ENT = os.path.join(HERE, '..', '..', 'Entradas')
cdr = pd.read_csv(os.path.join(ENT, 'llamadas_cdr.csv'))
tk = pd.read_csv(os.path.join(ENT, 'casos_tickets.csv'))

cdr['fecha'] = pd.to_datetime(cdr['fecha'])
tk['fecha_apertura'] = pd.to_datetime(tk['fecha_apertura'])
cdr['semana'] = cdr['fecha'].dt.isocalendar().week.astype(int)
tk['semana'] = tk['fecha_apertura'].dt.isocalendar().week.astype(int)
cdr['aht'] = cdr['duracion_seg'] + cdr['acw_seg']
cdr['esc'] = cdr['escalado_a'].notna().astype(int)
DIAS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
DIAS_ES = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
semanas = sorted(cdr['semana'].unique())
SEM_INC = [int(semanas[0]), int(semanas[-1])]  # primera y última semana parciales

ent = cdr[cdr.tipo_llamada == 'entrante'].copy()
ent['ab'] = (ent.resultado_llamada == 'abandonada').astype(int)
ent['sl'] = (ent.espera_seg <= 20).astype(int)
att = cdr[cdr.resultado_llamada == 'atendida'].copy()
tkm = tk.merge(cdr[['id_llamada', 'cola', 'hora', 'dia_semana', 'espera_seg', 'escalado_a', 'duracion_seg', 'acw_seg', 'tipo_llamada']],
               on='id_llamada', how='left')
tkm['esc'] = tkm['escalado_a'].notna().astype(int)
tkm['esc_lbl'] = np.where(tkm.esc == 1, 'Escalado', 'No escalado')
tkm['area'] = tkm.escalado_a.fillna('Sin escalar')
FECHA_FIN = tk['fecha_apertura'].max()


def r(x, n=1):
    return None if pd.isna(x) else round(float(x), n)


def k_abandono(d): return d.ab.mean() * 100
def k_sl(d): return d.sl.mean() * 100
def k_asa(d): return d.loc[d.resultado_llamada == 'atendida', 'espera_seg'].mean()
def k_tab(d): return d.loc[d.ab == 1, 'espera_seg'].mean()


def estado(v, meta, tipo):
    if meta is None or pd.isna(v): return 'contexto'
    if tipo == 'max':
        if v <= meta: return 'cumple'
        return 'riesgo' if v <= meta * 1.10 else 'fuera'
    if v >= meta: return 'cumple'
    return 'riesgo' if v >= meta * 0.90 else 'fuera'


def semanal(fn, df, col='semana'):
    return {int(s): r(fn(g), 2) for s, g in df.groupby(col)}


K = []


def add(id_, nombre, valor, meta, tipo, unidad, sem=None):
    K.append(dict(id=id_, kpi=nombre, valor=r(valor, 2), meta=meta, tipo=tipo, unidad=unidad,
                  estado=estado(valor, meta, tipo), semanal=sem or {}))


n_ent, n_sal = len(ent), int((cdr.tipo_llamada == 'saliente').sum())
sal = cdr[cdr.tipo_llamada == 'saliente']
add('A1', 'Volumen total de llamadas', len(cdr), None, None, 'llamadas', semanal(len, cdr))
add('A1e', 'Llamadas entrantes', n_ent, None, None, 'llamadas', semanal(len, ent))
add('A1s', 'Llamadas salientes', n_sal, None, None, 'llamadas', semanal(len, sal))
add('A2', 'Tasa de abandono (entrantes)', k_abandono(ent), 5, 'max', '%', semanal(k_abandono, ent))
add('A3', 'Nivel de servicio 80/20 (entrantes)', k_sl(ent), 80, 'min', '%', semanal(k_sl, ent))
add('A4', 'ASA (velocidad media de respuesta)', k_asa(ent), 20, 'max', 's', semanal(k_asa, ent))
add('A5', 'Tiempo medio hasta abandono', k_tab(ent), None, None, 's', semanal(k_tab, ent))
add('B1', 'AHT (duración + ACW)', att.aht.mean(), None, None, 's', semanal(lambda d: d.aht.mean(), att))
add('B2', 'ACW medio', att.acw_seg.mean(), 30, 'max', 's', semanal(lambda d: d.acw_seg.mean(), att))
carga = att.groupby('id_agente').size()
add('B3', 'Carga por agente (atendidas, promedio)', carga.mean(), None, None, 'llamadas', {})
add('B4', 'Tasa de escalamiento', att.esc.mean() * 100, 15, 'max', '%', semanal(lambda d: d.esc.mean() * 100, att))
add('C1', 'FCR (resolución en primer contacto)', tk.fcr.mean() * 100, 75, 'min', '%', semanal(lambda d: d.fcr.mean() * 100, tk))
add('C2', 'Tasa de reincidencia', tk.reincidencia.mean() * 100, 5, 'max', '%', semanal(lambda d: d.reincidencia.mean() * 100, tk))
add('C3', 'Tasa de reapertura', (tk.estado_caso == 'reabierto').mean() * 100, 3, 'max', '%', semanal(lambda d: (d.estado_caso == 'reabierto').mean() * 100, tk))
add('C4', 'Backlog pendiente (% de casos)', (tk.estado_caso == 'pendiente').mean() * 100, 10, 'max', '%', semanal(lambda d: (d.estado_caso == 'pendiente').mean() * 100, tk))
res_ = tk[tk.estado_caso == 'resuelto']
add('C5', 'Tiempo medio de resolución (resueltos)', res_.horas_resolucion.mean(), 24, 'max', 'h', semanal(lambda d: d[d.estado_caso == 'resuelto'].horas_resolucion.mean(), tk))
add('C5p90', 'Tiempo de resolución P90 (resueltos)', res_.horas_resolucion.quantile(.9), 24, 'max', 'h', semanal(lambda d: d[d.estado_caso == 'resuelto'].horas_resolucion.quantile(.9), tk))
add('D1', 'CSAT medio', tk.csat.mean(), 4.0, 'min', 'de 5', semanal(lambda d: d.csat.mean(), tk))
add('D2', 'CSAT Top-2-Box', (tk.csat >= 4).mean() * 100, 80, 'min', '%', semanal(lambda d: (d.csat >= 4).mean() * 100, tk))
add('D3', '% insatisfechos (CSAT 1–2)', (tk.csat <= 2).mean() * 100, 10, 'max', '%', semanal(lambda d: (d.csat <= 2).mean() * 100, tk))
riesgo_mask = (tk.csat <= 2) | (tk.reincidencia == 1)
add('D4', 'Valor en riesgo', tk.loc[riesgo_mask, 'valor_orden'].sum(), None, None, 'moneda local',
    semanal(lambda d: d.loc[(d.csat <= 2) | (d.reincidencia == 1), 'valor_orden'].sum(), tk))

cortes = {}


def acc(df, by):
    g = df.groupby(by, observed=True)
    return pd.DataFrame({
        'entrantes': g.size(), 'abandono_pct': g.ab.mean() * 100, 'sl_pct': g.sl.mean() * 100,
        'asa_s': g.apply(k_asa, include_groups=False), 'tiempo_hasta_abandono_s': g.apply(k_tab, include_groups=False)})


ent['dia'] = pd.Categorical(ent.dia_semana, DIAS, ordered=True)
cortes['hora'] = acc(ent, 'hora')
cortes['dia'] = acc(ent, 'dia'); cortes['dia'].index = DIAS_ES
cortes['cola'] = acc(ent, 'cola')
cortes['motivo_acceso'] = acc(ent, 'motivo')
sem = pd.DataFrame({k['id']: pd.Series(k['semanal']) for k in K if k['semanal']})
sem['incompleta'] = [s in SEM_INC for s in sem.index]
cortes['semana'] = sem

heat_ab = ent.pivot_table(index='hora', columns='dia', values='ab', aggfunc='mean', observed=False) * 100
heat_es = ent.pivot_table(index='hora', columns='dia', values='espera_seg', aggfunc='mean', observed=False)
heat_n = ent.pivot_table(index='hora', columns='dia', values='ab', aggfunc='size', observed=False)
for h in (heat_ab, heat_es, heat_n): h.columns = DIAS_ES
cortes['heat_abandono'] = heat_ab; cortes['heat_espera'] = heat_es; cortes['heat_volumen'] = heat_n

cortes['volumen_hora'] = cdr.groupby(['hora', 'tipo_llamada']).size().unstack(fill_value=0)
cortes['volumen_motivo'] = cdr.groupby(['motivo', 'tipo_llamada']).size().unstack(fill_value=0)
cortes['volumen_cola'] = cdr.groupby(['cola', 'tipo_llamada']).size().unstack(fill_value=0)


def efi(by):
    g = att.groupby(by)
    return pd.DataFrame({'atendidas': g.size(), 'aht_s': g.aht.mean(), 'duracion_s': g.duracion_seg.mean(),
                         'acw_s': g.acw_seg.mean(), 'escalamiento_pct': g.esc.mean() * 100})


cortes['aht_cola'] = efi('cola'); cortes['aht_motivo'] = efi('motivo')
esc_area = att[att.esc == 1].groupby('escalado_a').size()
cortes['escalamiento_area'] = pd.DataFrame({'escaladas': esc_area, 'pct_de_atendidas': esc_area / len(att) * 100})
cortes['esc_motivo_area'] = pd.crosstab(att.motivo, att.escalado_a.fillna('Sin escalar'))
cortes['esc_motivo_area_pct'] = pd.crosstab(att.motivo, att.escalado_a.fillna('Sin escalar'), normalize='index') * 100
cortes['esc_cola_area'] = pd.crosstab(att.cola, att.escalado_a.fillna('Sin escalar'), normalize='index') * 100
cortes['esc_cola_motivo'] = att.pivot_table(index='cola', columns='motivo', values='esc', aggfunc='mean') * 100


def efe(by, d=tkm):
    g = d.groupby(by)
    res_g = d[d.estado_caso == 'resuelto'].groupby(by).horas_resolucion
    return pd.DataFrame({
        'casos': g.size(), 'fcr_pct': g.fcr.mean() * 100, 'reincidencia_pct': g.reincidencia.mean() * 100,
        'reapertura_pct': g.apply(lambda x: (x.estado_caso == 'reabierto').mean() * 100, include_groups=False),
        'pendiente_pct': g.apply(lambda x: (x.estado_caso == 'pendiente').mean() * 100, include_groups=False),
        'pendiente_n': g.apply(lambda x: (x.estado_caso == 'pendiente').sum(), include_groups=False),
        'res_media_h': res_g.mean(), 'res_p90_h': res_g.quantile(.9),
        'csat': g.csat.mean(), 'top2_pct': g.csat.apply(lambda s: (s >= 4).mean() * 100),
        'insatisfechos_pct': g.csat.apply(lambda s: (s <= 2).mean() * 100),
        'valor_en_riesgo': g.apply(lambda x: x.loc[(x.csat <= 2) | (x.reincidencia == 1), 'valor_orden'].sum(), include_groups=False)})


cortes['categoria'] = efe('categoria')
cortes['escalado'] = efe('esc_lbl')
cortes['area_destino'] = efe('area')
cortes['cola_casos'] = efe('cola')
cortes['fcr_escalado_categoria'] = efe(['esc_lbl', 'categoria'])[['casos', 'fcr_pct', 'csat']]
cortes['area_x_categoria'] = tkm.pivot_table(index='categoria', columns='area', values='csat', aggfunc='mean')

bins = [0, 10, 20, 40, 60, 10000]; labs = ['≤10 s', '11–20 s', '21–40 s', '41–60 s', '>60 s']
tkm['espera_bin'] = pd.cut(tkm.espera_seg, bins, labels=labs)
cortes['csat_espera'] = tkm.groupby('espera_bin', observed=True).agg(
    casos=('csat', 'size'), csat=('csat', 'mean'), fcr_pct=('fcr', lambda s: s.mean() * 100), insatisfechos_pct=('csat', lambda s: (s <= 2).mean() * 100))
cortes['csat_espera_x_esc'] = tkm.groupby(['esc_lbl', 'espera_bin'], observed=True).agg(casos=('csat', 'size'), csat=('csat', 'mean'))
corr_esp = float(tkm[['espera_seg', 'csat']].corr().iloc[0, 1])
cortes['csat_dist_categoria'] = pd.crosstab(tkm.categoria, tkm.csat, normalize='index') * 100
cortes['csat_dist_escalado'] = pd.crosstab(tkm.esc_lbl, tkm.csat, normalize='index') * 100
cortes['csat_dist_total'] = (tkm.csat.value_counts(normalize=True).sort_index() * 100).to_frame('pct')

pend = tk[tk.estado_caso == 'pendiente'].copy()
pend['dias'] = (FECHA_FIN - pend.fecha_apertura).dt.days
pend['antiguedad'] = pd.cut(pend.dias, [-1, 7, 14, 30, 1000], labels=['0–7 d', '8–14 d', '15–30 d', '>30 d'])
ba = pd.crosstab(pend.categoria, pend.antiguedad)
ba.loc['TOTAL'] = ba.sum()
cortes['backlog_antiguedad'] = ba

# Agentes
ag_att = att.groupby('id_agente').agg(atendidas=('id_llamada', 'size'), aht_s=('aht', 'mean'), acw_s=('acw_seg', 'mean'),
                                      escalamiento_pct=('esc', lambda s: s.mean() * 100))
ag_tk = tk.groupby('id_agente').agg(casos=('id_caso', 'size'), fcr_pct=('fcr', lambda s: s.mean() * 100),
                                    reincidencia_pct=('reincidencia', lambda s: s.mean() * 100), csat=('csat', 'mean'),
                                    insatisfechos_pct=('csat', lambda s: (s <= 2).mean() * 100))
ag = ag_att.join(ag_tk)
z = lambda s: (s - s.mean()) / s.std(ddof=0)
ag['z_fcr'] = z(ag.fcr_pct); ag['z_csat'] = z(ag.csat); ag['z_aht'] = -z(ag.aht_s); ag['z_esc'] = -z(ag.escalamiento_pct)
ag['indice'] = ag[['z_fcr', 'z_csat', 'z_aht', 'z_esc']].mean(axis=1)
ag = ag.sort_values('indice', ascending=False); ag['ranking'] = range(1, len(ag) + 1)
ag['desvio_carga_pct'] = (ag.atendidas / ag.atendidas.mean() - 1) * 100
ag['desvio_aht_pct'] = (ag.aht_s / ag.aht_s.mean() - 1) * 100
cortes['agentes'] = ag
cortes['carga_agente_hora'] = att.pivot_table(index='id_agente', columns='hora', values='id_llamada', aggfunc='size', fill_value=0)
act = att.groupby(['fecha', 'hora']).id_agente.nunique().groupby('hora').mean()
cortes['cobertura_hora'] = pd.DataFrame({'agentes_activos_prom': act, 'entrantes_prom_por_dia': ent.groupby('hora').size() / cdr.fecha.nunique()})

rows = []
for k in K:
    rows.append(dict(kpi=f"{k['id']} {k['kpi']}", valor=k['valor'], unidad=k['unidad'], meta=k['meta'] if k['meta'] is not None else '',
                     estado=k['estado'], variacion_vs_anterior='sin ejecución previa',
                     periodo=f"{cdr.fecha.min().date()} a {cdr.fecha.max().date()}"))
pd.DataFrame(rows).to_csv(os.path.join(HERE, 'kpis_resumen.csv'), index=False, encoding='utf-8-sig')

SHEETS = {'semana': 'semana', 'hora': 'hora', 'dia': 'dia', 'cola': 'cola', 'motivo_acceso': 'motivo_acceso',
          'heat_abandono': 'heat_abandono', 'heat_espera': 'heat_espera', 'volumen_hora': 'volumen_hora',
          'volumen_motivo': 'volumen_motivo', 'volumen_cola': 'volumen_cola', 'aht_cola': 'eficiencia_cola',
          'aht_motivo': 'eficiencia_motivo', 'escalamiento_area': 'esc_area', 'esc_motivo_area': 'esc_motivo_area_n',
          'esc_motivo_area_pct': 'esc_motivo_area_pct', 'esc_cola_motivo': 'esc_cola_motivo', 'categoria': 'categoria',
          'escalado': 'escalado_si_no', 'area_destino': 'area_destino', 'cola_casos': 'efectividad_cola',
          'fcr_escalado_categoria': 'fcr_esc_categoria', 'csat_espera': 'csat_vs_espera', 'csat_espera_x_esc': 'csat_espera_x_esc',
          'csat_dist_categoria': 'csat_dist_categoria', 'backlog_antiguedad': 'backlog_antiguedad', 'agentes': 'agentes',
          'cobertura_hora': 'cobertura_hora'}
with pd.ExcelWriter(os.path.join(HERE, 'kpis_detalle.xlsx')) as xw:
    pd.DataFrame(rows).to_excel(xw, sheet_name='resumen', index=False)
    for key, sh in SHEETS.items():
        cortes[key].round(2).to_excel(xw, sheet_name=sh)


def tojson(df):
    return json.loads(df.round(3).to_json(orient='split'))


J = dict(kpis=K, sem_inc=SEM_INC, semanas=[int(s) for s in semanas],
         periodo=[str(cdr.fecha.min().date()), str(cdr.fecha.max().date())],
         n_llamadas=len(cdr), n_ent=n_ent, n_sal=n_sal, n_att=len(att), n_casos=len(tk), n_ab=int(ent.ab.sum()),
         n_ab_sal=int((sal.resultado_llamada == 'abandonada').sum()),
         corr_espera_csat=corr_esp, cortes={k: tojson(v) for k, v in cortes.items()})
with open(os.path.join(HERE, 'resultados.json'), 'w', encoding='utf-8') as f:
    json.dump(J, f, ensure_ascii=False)
print('OK', len(K), 'KPIs;', len(cortes), 'cortes')
