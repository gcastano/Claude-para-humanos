"""Genera informe_kpis.html, plan_de_accion.md, calidad_datos.md y amplía kpis_resumen.csv con indicadores de apoyo.
Requiere haber corrido calculo_kpis.py (lee resultados.json). Uso: python3 generar_informe.py"""
import json, os, datetime
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ENT = os.path.join(HERE, '..', '..', 'Entradas')
J = json.load(open(os.path.join(HERE, 'resultados.json'), encoding='utf-8'))
cdr = pd.read_csv(os.path.join(ENT, 'llamadas_cdr.csv')); tk = pd.read_csv(os.path.join(ENT, 'casos_tickets.csv'))
HOY = '2026-11-11'

# ---------------- utilidades ----------------
def T(name):
    c = J['cortes'][name]; idx = c['index']
    if idx and isinstance(idx[0], list): idx = pd.MultiIndex.from_tuples([tuple(i) for i in idx])
    return pd.DataFrame(c['data'], index=idx, columns=c['columns'])
K = {k['id']: k for k in J['kpis']}
def v(i): return K[i]['valor']
def es(x, d=1):
    s = f"{x:,.{d}f}"
    return s.replace(',', '§').replace('.', ',').replace('§', '.')
def pc(x, d=1): return es(x, d) + ' %'
def n0(x): return es(x, 0)
ST = {'cumple': 'Cumple meta', 'riesgo': 'En riesgo', 'fuera': 'Fuera de meta', 'contexto': 'Contexto'}
COL = {'cumple': '#0E3B2E', 'riesgo': '#F4B942', 'fuera': '#C75B39', 'contexto': '#6E8F7A'}
VERDE, CREMA, TINTA, DORADO, TERRA, OLIVA = '#0E3B2E', '#F7F3EA', '#14201B', '#F4B942', '#C75B39', '#6E8F7A'

# ---------------- cifras derivadas (desde datos crudos) ----------------
cdr['fecha'] = pd.to_datetime(cdr.fecha)
ent = cdr[cdr.tipo_llamada == 'entrante'].copy(); ent['ab'] = (ent.resultado_llamada == 'abandonada').astype(int)
att = cdr[cdr.resultado_llamada == 'atendida'].copy(); att['esc'] = att.escalado_a.notna().astype(int)
PICOS = [10, 11, 12, 13, 19, 20, 21]
pk = ent.hora.isin(PICOS)
X = {}
X['pico_share_ent'] = pk.mean() * 100
X['pico_share_ab'] = ent[pk].ab.sum() / ent.ab.sum() * 100
X['pico_ab_n'] = int(ent[pk].ab.sum()); X['ab_n'] = int(ent.ab.sum())
X['pico_ab'] = ent[pk].ab.mean() * 100; X['fuera_ab'] = ent[~pk].ab.mean() * 100
X['pico_sl'] = (ent[pk].espera_seg <= 20).mean() * 100; X['fuera_sl'] = (ent[~pk].espera_seg <= 20).mean() * 100
X['pico_asa'] = ent[pk & (ent.ab == 0)].espera_seg.mean(); X['fuera_asa'] = ent[~pk & (ent.ab == 0)].espera_seg.mean()
X['pico_tab'] = ent[pk & (ent.ab == 1)].espera_seg.mean(); X['fuera_tab'] = ent[~pk & (ent.ab == 1)].espera_seg.mean()
esp = {'estado_envio': 'Area_Logistica', 'devolucion': 'Area_Logistica', 'cambio_producto': 'Area_Logistica', 'reclamo_calidad': 'Area_Logistica',
       'problema_pago': 'Area_Billing', 'facturacion': 'Area_Billing'}
xx = att[att.escalado_a.isin(['Area_Logistica', 'Area_Billing']) & att.motivo.isin(esp)].copy()
xx['ok'] = xx.motivo.map(esp) == xx.escalado_a
X['mis_n'] = int((~xx.ok).sum()); X['mis_base'] = len(xx); X['mis_pct'] = (~xx.ok).mean() * 100
t2 = tk.merge(cdr[['id_llamada', 'escalado_a', 'motivo']], on='id_llamada'); t2['esc'] = t2.escalado_a.notna()
t2m = t2[t2.escalado_a.isin(['Area_Logistica', 'Area_Billing']) & t2.motivo.isin(esp)].copy(); t2m['ok'] = t2m.motivo.map(esp) == t2m.escalado_a
X['csat_mis'] = t2m[~t2m.ok].csat.mean(); X['csat_okr'] = t2m[t2m.ok].csat.mean()
X['p_esc_t'] = t2.esc.mean() * 100
X['csat_esc'] = t2[t2.esc].csat.mean(); X['csat_no'] = t2[~t2.esc].csat.mean()
def escen(p): return p * X['csat_esc'] + (1 - p) * X['csat_no']
X['csat_25'] = escen(.25); X['csat_15'] = escen(.15)
X['insat_15'] = (.15 * (t2[t2.esc].csat <= 2).mean() + .85 * (t2[~t2.esc].csat <= 2).mean()) * 100
X['share_insat_esc'] = ((t2.csat <= 2) & t2.esc).sum() / (t2.csat <= 2).sum() * 100
X['riesgo_esc'] = T('escalado').loc['Escalado', 'valor_en_riesgo']; X['riesgo_tot'] = v('D4')
X['riesgo_esc_pct'] = X['riesgo_esc'] / X['riesgo_tot'] * 100
X['acw_gt30'] = (att.acw_seg > 30).mean() * 100
X['acw_horas'] = (att.acw_seg.mean() - 30) * len(att) / 3600
X['sal_ab'] = J['n_ab_sal']; X['sal_ab_pct'] = J['n_ab_sal'] / J['n_sal'] * 100
X['att_sin_ticket'] = int((~att.id_llamada.isin(tk.id_llamada)).sum()); X['att_sin_ticket_pct'] = X['att_sin_ticket'] / len(att) * 100
X['tk_sal'] = int(tk.id_llamada.isin(cdr[cdr.tipo_llamada == 'saliente'].id_llamada).sum())
X['n_reab'] = int((tk.estado_caso == 'reabierto').sum()); X['n_pend'] = int((tk.estado_caso == 'pendiente').sum())
X['meta_pend_n'] = int(np.ceil(.10 * len(tk)))
BA = T('backlog_antiguedad'); X['bk_30'] = int(BA.loc['TOTAL', '>30 d']); X['bk_15_30'] = int(BA.loc['TOTAL', '15–30 d'])
X['bk_30_pct'] = X['bk_30'] / X['n_pend'] * 100; X['bk_15_pct'] = (X['bk_30'] + X['bk_15_30']) / X['n_pend'] * 100
AG = T('agentes')
X['ag_fcr_min'], X['ag_fcr_max'] = AG.fcr_pct.min(), AG.fcr_pct.max()
X['ag_csat_min'], X['ag_csat_max'] = AG.csat.min(), AG.csat.max()
X['ag_esc_min'], X['ag_esc_max'] = AG.escalamiento_pct.min(), AG.escalamiento_pct.max()
X['ag_acw_min'], X['ag_acw_max'] = AG.acw_s.min(), AG.acw_s.max()
X['ag_aht_dev_max'] = AG.desvio_aht_pct.abs().max(); X['ag_carga_dev_max'] = AG.desvio_carga_pct.abs().max()
X['ag_n'] = len(AG); X['ag_casos_med'] = AG.casos.mean()
p = v('C1') / 100; X['ag_ci'] = 1.96 * np.sqrt(p * (1 - p) / X['ag_casos_med']) * 100
X['corr'] = J['corr_espera_csat']
top3 = list(AG.index[:3]); bot3 = list(AG.index[-3:][::-1])
HR, DI, CO, MO = T('hora'), T('dia'), T('cola'), T('motivo_acceso')
CAT, ESC, AREA, CAV = T('categoria'), T('escalado'), T('area_destino'), T('cobertura_hora')
SEM = T('semana'); sem_ok = [s for s in SEM.index if s not in J['sem_inc']]
X['ab_sem_ok_min'] = SEM.loc[sem_ok, 'A2'].min(); X['ab_sem_ok_max'] = SEM.loc[sem_ok, 'A2'].max()

# ---------------- indicadores de apoyo (se añaden a kpis_resumen.csv) ----------------
periodo = f"{J['periodo'][0]} a {J['periodo'][1]}"
APOYO = [
    ('X1 Peso de franjas pico (10–13 h y 19–21 h) en entrantes', X['pico_share_ent'], '%'),
    ('X2 Peso de franjas pico en abandonos', X['pico_share_ab'], '%'),
    ('X3 Abandono en franjas pico', X['pico_ab'], '%'), ('X4 Abandono fuera de pico', X['fuera_ab'], '%'),
    ('X5 Nivel de servicio en franjas pico', X['pico_sl'], '%'), ('X6 Nivel de servicio fuera de pico', X['fuera_sl'], '%'),
    ('X7 ASA en franjas pico', X['pico_asa'], 's'), ('X8 ASA fuera de pico', X['fuera_asa'], 's'),
    ('X9 Tiempo hasta abandono en pico', X['pico_tab'], 's'), ('X10 Tiempo hasta abandono fuera de pico', X['fuera_tab'], 's'),
    ('X11 CSAT en casos escalados', X['csat_esc'], 'de 5'), ('X12 CSAT en casos no escalados', X['csat_no'], 'de 5'),
    ('X13 % de casos escalados', X['p_esc_t'], '%'), ('X14 Insatisfechos que vienen de casos escalados', X['share_insat_esc'], '%'),
    ('X15 Valor en riesgo en casos escalados', X['riesgo_esc'], 'moneda local'), ('X16 Valor en riesgo en casos escalados, % del total', X['riesgo_esc_pct'], '%'),
    ('X17 Escalamientos a Logística/Billing que no coinciden con el área esperada', X['mis_pct'], '%'),
    ('X18 CSAT escenario con 25 % de escalamiento', X['csat_25'], 'de 5'), ('X19 CSAT escenario con 15 % de escalamiento', X['csat_15'], 'de 5'),
    ('X20 Correlación espera–CSAT', X['corr'], 'r'), ('X21 Llamadas con ACW sobre 30 s', X['acw_gt30'], '%'),
    ('X22 Horas-agente por exceso de ACW en el periodo', X['acw_horas'], 'h'),
    ('X23 Pendientes con más de 30 días', X['bk_30_pct'], '%'), ('X24 Pendientes con más de 14 días', X['bk_15_pct'], '%'),
    ('X25 Margen de error del FCR por agente (95 %)', X['ag_ci'], 'pp'),
]
base = pd.read_csv(os.path.join(HERE, 'kpis_resumen.csv'))
base = base[~base.kpi.str.startswith('X')]
extra = pd.DataFrame([dict(kpi=a, valor=round(float(b), 2), unidad=c, meta='', estado='apoyo', variacion_vs_anterior='sin ejecución previa', periodo=periodo) for a, b, c in APOYO])
pd.concat([base, extra]).to_csv(os.path.join(HERE, 'kpis_resumen.csv'), index=False, encoding='utf-8-sig')

# ---------------- gráficos SVG ----------------
FONT = "font-family:Inter,system-ui,sans-serif"
def svg_wrap(w, h, body, title): return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{title}" style="width:100%;height:auto;max-width:{w}px">{body}</svg>'
def txt(x, y, s, size=11, anchor='start', fill=TINTA, weight=400): return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}" style="{FONT}">{s}</text>'

def lines(weeks, series, ymin, ymax, unit, title, meta=None, meta_lbl='', w=560, h=240, dec=1):
    L, R, Tp, B = 52, 16, 30, 34
    iw, ih = w - L - R, h - Tp - B
    xs = {wk: L + (i + .5) * iw / len(weeks) for i, wk in enumerate(weeks)}
    yv = lambda val: Tp + ih - (val - ymin) / (ymax - ymin) * ih
    o = [txt(L, 14, unit, 11, fill=TINTA, weight=500)]
    for i in range(5):
        val = ymin + (ymax - ymin) * i / 4
        o.append(f'<line x1="{L}" x2="{w-R}" y1="{yv(val):.1f}" y2="{yv(val):.1f}" stroke="#E4DFD2" stroke-width="1"/>')
        o.append(txt(L - 6, yv(val) + 4, es(val, dec if (ymax - ymin) < 6 else 0), 11, 'end'))
    if meta is not None:
        o.append(f'<line x1="{L}" x2="{w-R}" y1="{yv(meta):.1f}" y2="{yv(meta):.1f}" stroke="{VERDE}" stroke-width="1.5" stroke-dasharray="5 4"/>')
        o.append(txt(w - R, yv(meta) - 5, meta_lbl, 11, 'end', VERDE, 600))
    for wk in weeks:
        inc = wk in J['sem_inc']
        o.append(txt(xs[wk], h - 12, f"S{wk}{'*' if inc else ''}", 11, 'middle'))
    for name, vals, color in series:
        pts = [(xs[wk], yv(vals[str(wk)] if str(wk) in vals else vals[wk])) for wk in weeks]
        o.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}"/>')
        for wk, (a, b) in zip(weeks, pts):
            inc = wk in J['sem_inc']; val = vals[str(wk)] if str(wk) in vals else vals[wk]
            o.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="4" fill="{CREMA if inc else color}" stroke="{color}" stroke-width="2"/>')
            o.append(txt(a, b - 9, es(val, dec), 10.5, 'middle', TINTA, 500))
    return svg_wrap(w, h, ''.join(o), title)

def hbar(items, title, unit, vmax=None, meta=None, meta_lbl='', color_fn=None, w=560, dec=1, label_w=150):
    rh = 26; h = len(items) * rh + 34
    vmax = vmax or max(v_ for _, v_ in items) * 1.15
    bw = w - label_w - 70
    o = [txt(label_w, 12, unit, 11, weight=500)]
    for i, (lab, val) in enumerate(items):
        y = 24 + i * rh
        c = color_fn(lab, val) if color_fn else VERDE
        o.append(txt(label_w - 8, y + 14, lab, 12, 'end'))
        o.append(f'<rect x="{label_w}" y="{y+3}" width="{max(val,0)/vmax*bw:.1f}" height="16" fill="{c}" rx="2"/>')
        o.append(txt(label_w + max(val, 0) / vmax * bw + 6, y + 15, es(val, dec), 12, weight=600))
    if meta is not None:
        mx = label_w + meta / vmax * bw
        o.append(f'<line x1="{mx:.1f}" x2="{mx:.1f}" y1="18" y2="{h-6}" stroke="{TINTA}" stroke-width="1.5" stroke-dasharray="4 3"/>')
        o.append(txt(mx + 4, h - 8, meta_lbl, 11, weight=600))
    return svg_wrap(w, h, ''.join(o), title)

def vbar_hora(title, vals, picos, meta, alerta, unit, w=620, h=250, dec=0):
    L, R, Tp, B = 40, 10, 28, 30
    hrs = list(vals.index); iw, ih = w - L - R, h - Tp - B; bw = iw / len(hrs)
    ymax = max(vals.max() * 1.15, (alerta or 0) * 1.3, (meta or 0) * 1.1)
    yv = lambda val: Tp + ih - val / ymax * ih
    o = [txt(L, 14, unit, 11, weight=500)]
    for i in range(5):
        val = ymax * i / 4
        o.append(f'<line x1="{L}" x2="{w-R}" y1="{yv(val):.1f}" y2="{yv(val):.1f}" stroke="#E4DFD2"/>')
        o.append(txt(L - 6, yv(val) + 4, es(val, 0), 11, 'end'))
    for i, hr in enumerate(hrs):
        val = vals[hr]; x = L + i * bw
        o.append(f'<rect x="{x+3:.1f}" y="{yv(val):.1f}" width="{bw-6:.1f}" height="{Tp+ih-yv(val):.1f}" fill="{TERRA if hr in picos else VERDE}" rx="2"/>')
        o.append(txt(x + bw / 2, yv(val) - 4, es(val, dec), 10, 'middle', TINTA, 500))
        o.append(txt(x + bw / 2, h - 12, f"{hr}", 11, 'middle'))
    lv = []
    if meta is not None: lv.append((meta, f'Meta {es(meta,0)} %', '5 4'))
    if alerta is not None: lv.append((alerta, f'Alerta {es(alerta,0)} %', '2 3'))
    for val, lab, dash in lv:
        o.append(f'<line x1="{L}" x2="{w-R}" y1="{yv(val):.1f}" y2="{yv(val):.1f}" stroke="{TINTA}" stroke-width="1.2" stroke-dasharray="{dash}"/>')
        o.append(txt(w - R, yv(val) - 4, lab, 10.5, 'end', TINTA, 600))
    o.append(txt(w / 2, h - 0, 'Hora de entrada (h)', 11, 'middle'))
    return svg_wrap(w, h, ''.join(o), title)

def mix(c1, c2, t):
    a = [int(c1[i:i+2], 16) for i in (1, 3, 5)]; b = [int(c2[i:i+2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f"{int(a[i]+(b[i]-a[i])*t):02X}" for i in range(3))

def heat(df, title, vmax, dec=0, unit=''):
    cw, rh, L, Tp = 58, 22, 36, 40
    w = L + cw * len(df.columns) + 10; h = Tp + rh * len(df.index) + 8
    o = [txt(L, 14, unit, 11, weight=500)]
    for j, c in enumerate(df.columns): o.append(txt(L + j * cw + cw / 2, 34, c, 11, 'middle', weight=500))
    for i, hr in enumerate(df.index):
        y = Tp + i * rh; o.append(txt(L - 6, y + 15, f"{hr} h", 11, 'end'))
        for j, c in enumerate(df.columns):
            val = df.loc[hr, c]; t = min(val / vmax, 1) * .85
            o.append(f'<rect x="{L+j*cw}" y="{y}" width="{cw-2}" height="{rh-2}" fill="{mix(CREMA, TERRA, t)}" rx="2"/>')
            o.append(txt(L + j * cw + cw / 2 - 1, y + 14, es(val, dec), 10.5, 'middle', TINTA, 500))
    return svg_wrap(w, h, ''.join(o), title)

CSAT_COL = {1: TERRA, 2: '#E3A18C', 3: '#DCD6C6', 4: OLIVA, 5: VERDE}
def stack(rows, title, w=620, label_w=170):
    rh = 34; h = len(rows) * rh + 58; bw = w - label_w - 16
    o = []
    for i, (lab, vals) in enumerate(rows):
        y = 12 + i * rh; x = label_w
        o.append(txt(label_w - 8, y + 18, lab, 12, 'end'))
        for k, val in zip([1, 2, 3, 4, 5], vals):
            ww = val / 100 * bw
            o.append(f'<rect x="{x:.1f}" y="{y}" width="{ww:.1f}" height="24" fill="{CSAT_COL[k]}"/>')
            if val >= 6: o.append(txt(x + ww / 2, y + 16, es(val, 0), 11, 'middle', CREMA if k in (1, 5) else TINTA, 600))
            x += ww
    ly = h - 28
    for k in range(1, 6):
        lx = label_w + (k - 1) * 90
        o.append(f'<rect x="{lx}" y="{ly}" width="12" height="12" fill="{CSAT_COL[k]}"/>')
        o.append(txt(lx + 17, ly + 11, f"CSAT {k}", 11))
    o.append(txt(label_w, h - 4, '% de casos (cada barra suma 100 %)', 10.5))
    return svg_wrap(w, h, ''.join(o), title)

def scatter(pts, title, xl, yl, xm, ym, w=560, h=330):
    L, R, Tp, B = 52, 20, 20, 44
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, x1 = min(xs) - .8, max(xs) + .8; y0, y1 = min(ys) - .03, max(ys) + .03
    px = lambda a: L + (a - x0) / (x1 - x0) * (w - L - R); py = lambda b: Tp + (y1 - b) / (y1 - y0) * (h - Tp - B)
    o = []
    for i in range(5):
        a = x0 + (x1 - x0) * i / 4; b = y0 + (y1 - y0) * i / 4
        o.append(txt(px(a), h - 26, es(a, 0), 11, 'middle')); o.append(txt(L - 6, py(b) + 4, es(b, 2), 11, 'end'))
        o.append(f'<line x1="{L}" x2="{w-R}" y1="{py(b):.1f}" y2="{py(b):.1f}" stroke="#E4DFD2"/>')
    o.append(f'<line x1="{px(xm):.1f}" x2="{px(xm):.1f}" y1="{Tp}" y2="{h-B}" stroke="{OLIVA}" stroke-dasharray="4 3"/>')
    o.append(f'<line x1="{L}" x2="{w-R}" y1="{py(ym):.1f}" y2="{py(ym):.1f}" stroke="{OLIVA}" stroke-dasharray="4 3"/>')
    for a, b, lab, hi in pts:
        o.append(f'<circle cx="{px(a):.1f}" cy="{py(b):.1f}" r="{6 if hi else 4}" fill="{TERRA if hi=="bot" else VERDE if hi=="top" else OLIVA}"/>')
        if hi: o.append(txt(px(a) + 8, py(b) + 4, lab, 11, weight=600))
    o.append(txt((L + w - R) / 2, h - 6, xl, 11, 'middle', weight=500)); o.append(txt(L, 12, yl, 11, weight=500))
    return svg_wrap(w, h, ''.join(o), title)

# ---------------- gráficos concretos ----------------
wk = J['semanas']
g_ab_sl = lines(wk, [('Abandono', SEM.A2.to_dict(), TERRA)], 0, 20, 'Abandono de entrantes (%)', 'Abandono semanal', meta=5, meta_lbl='Meta 5 %')
g_sl = lines(wk, [('SL', SEM.A3.to_dict(), VERDE)], 40, 90, 'Nivel de servicio 80/20 (%)', 'Nivel de servicio semanal', meta=80, meta_lbl='Meta 80 %', dec=0)
g_asa = lines(wk, [('ASA', SEM.A4.to_dict(), VERDE)], 10, 30, 'ASA (segundos)', 'ASA semanal', meta=20, meta_lbl='Meta 20 s', dec=1)
g_vol = lines(wk, [('Total', SEM.A1.to_dict(), VERDE)], 0, 2200, 'Llamadas por semana', 'Volumen semanal', dec=0)
g_hora_ab = vbar_hora('Abandono por hora', HR.abandono_pct, PICOS, 5, 8, 'Abandono de entrantes por hora (%)')
g_hora_sl = vbar_hora('Nivel de servicio por hora', HR.sl_pct, PICOS, 80, None, 'Nivel de servicio 80/20 por hora (%)')
g_heat_ab = heat(T('heat_abandono'), 'Mapa de calor del abandono', 30, 0, 'Abandono de entrantes (%) · hora × día')
g_heat_es = heat(T('heat_espera'), 'Mapa de calor de la espera', 45, 0, 'Espera media (s) · hora × día')
g_tab = vbar_hora('Tiempo hasta abandono por hora', HR.tiempo_hasta_abandono_s, PICOS, None, None, 'Segundos de espera antes de colgar', dec=0)
g_aht = hbar([(m, r.aht_s) for m, r in T('aht_motivo').sort_values('aht_s', ascending=False).iterrows()], 'AHT por motivo', 'Segundos (duración + ACW)', dec=0)
g_acw = hbar([(a, r.acw_s) for a, r in AG.sort_values('acw_s', ascending=False).iterrows()][:12], 'ACW por agente (12 más altos)', 'Segundos de ACW · meta 30 s', meta=30, meta_lbl='Meta 30 s', vmax=45, color_fn=lambda l, x: TERRA, dec=1, label_w=80)
g_carga = hbar([(a, r.desvio_carga_pct) for a, r in AG.sort_values('desvio_carga_pct', ascending=False).iterrows()][:8], 'Carga por agente', 'Desvío de carga vs promedio (%) · 8 agentes con más carga', dec=1, label_w=80, vmax=20)
EA = T('esc_motivo_area_pct')
g_esc_mot = hbar([(m, 100 - EA.loc[m, 'Sin escalar']) for m in EA.index], 'Escalamiento por motivo', '% de llamadas atendidas escaladas · meta 15 %', meta=15, meta_lbl='Meta 15 %', vmax=50, color_fn=lambda l, x: TERRA, dec=1)
g_esc_ag = hbar([(a, r.escalamiento_pct) for a, r in AG.sort_values('escalamiento_pct', ascending=False).iterrows()][:10], 'Escalamiento por agente', '% escalado · 10 agentes con valor más alto', meta=15, meta_lbl='Meta 15 %', vmax=50, color_fn=lambda l, x: TERRA, dec=1, label_w=80)
g_fcr_cat = hbar([(c, r.fcr_pct) for c, r in CAT.sort_values('fcr_pct').iterrows()], 'FCR por categoría', 'FCR (%) · meta 75 %', meta=75, meta_lbl='Meta 75 %', vmax=100, color_fn=lambda l, x: VERDE if x >= 75 else TERRA)
g_reinc = hbar([(c, r.reincidencia_pct) for c, r in CAT.sort_values('reincidencia_pct', ascending=False).iterrows()], 'Reincidencia por categoría', 'Reincidencia (%) · meta 5 %', meta=5, meta_lbl='Meta 5 %', vmax=12, color_fn=lambda l, x: VERDE if x <= 5 else TERRA)
g_reab = lines(wk, [('Reapertura', SEM.C3.to_dict(), TERRA)], 0, 8, 'Reapertura semanal (%)', 'Reapertura semanal', meta=3, meta_lbl='Meta 3 %')
g_bk = None
def bk_chart():
    cols = ['0–7 d', '8–14 d', '15–30 d', '>30 d']; cc = ['#DCD6C6', OLIVA, '#E3A18C', TERRA]
    rows = [r for r in BA.index if r != 'TOTAL']; rows = sorted(rows, key=lambda r: -BA.loc[r].sum())
    w = 620; label_w = 150; rh = 28; h = len(rows) * rh + 60; mx = max(BA.loc[r].sum() for r in rows); bw = w - label_w - 70
    o = [txt(label_w, 12, 'Casos pendientes por antigüedad (días desde apertura al 23-oct)', 11, weight=500)]
    for i, r in enumerate(rows):
        y = 22 + i * rh; x = label_w; o.append(txt(label_w - 8, y + 16, r, 12, 'end'))
        for c, col in zip(cols, cc):
            ww = BA.loc[r, c] / mx * bw; o.append(f'<rect x="{x:.1f}" y="{y}" width="{ww:.1f}" height="20" fill="{col}"/>'); x += ww
        o.append(txt(x + 6, y + 15, n0(BA.loc[r].sum()), 12, weight=600))
    for k, (c, col) in enumerate(zip(cols, cc)):
        o.append(f'<rect x="{label_w+k*95}" y="{h-26}" width="12" height="12" fill="{col}"/>'); o.append(txt(label_w + k * 95 + 17, h - 15, c, 11))
    return svg_wrap(w, h, ''.join(o), 'Backlog por antigüedad')
g_bk = bk_chart()
g_res = hbar([(c, r.res_p90_h) for c, r in CAT.sort_values('res_p90_h', ascending=False).iterrows()], 'P90 de resolución por categoría', 'Horas (P90, casos resueltos) · meta 24 h', meta=24, meta_lbl='Meta 24 h', vmax=40, color_fn=lambda l, x: TERRA, dec=1)
D = T('csat_dist_categoria'); DE = T('csat_dist_escalado'); DT = T('csat_dist_total')
g_csat_dist = stack([('Todos los casos', [DT.loc[k, 'pct'] for k in (1, 2, 3, 4, 5)])] + [(i, [DE.loc[i, str(k)] if str(k) in DE.columns else DE.loc[i, k] for k in (1, 2, 3, 4, 5)]) for i in ['Escalado', 'No escalado']], 'Distribución de CSAT')
g_csat_cat = hbar([(c, r.csat) for c, r in CAT.sort_values('csat').iterrows()], 'CSAT por categoría', 'CSAT medio (1–5) · meta 4,0', meta=4, meta_lbl='Meta 4,0', vmax=5, color_fn=lambda l, x: TERRA, dec=2)
CE = T('csat_espera')
g_csat_esp = hbar([(i, r.csat) for i, r in CE.iterrows()], 'CSAT según espera', 'CSAT medio por rango de espera · meta 4,0', meta=4, meta_lbl='Meta 4,0', vmax=5, color_fn=lambda l, x: OLIVA, dec=2, label_w=90)
g_csat_esc = hbar([('No escalado', X['csat_no']), ('Escalado', X['csat_esc'])], 'CSAT escalado vs no escalado', 'CSAT medio (1–5) · meta 4,0', meta=4, meta_lbl='Meta 4,0', vmax=5, color_fn=lambda l, x: TERRA if l == 'Escalado' else VERDE, dec=2, label_w=110)
g_riesgo = hbar([(c, r.valor_en_riesgo / 1000) for c, r in CAT.sort_values('valor_en_riesgo', ascending=False).iterrows()], 'Valor en riesgo por categoría', 'Valor en riesgo (miles, moneda local)', dec=0, color_fn=lambda l, x: VERDE)
agp = [(r.fcr_pct, r.csat, a, 'top' if a in top3 else 'bot' if a in bot3 else None) for a, r in AG.iterrows()]
g_scatter = scatter(agp, 'FCR vs CSAT por agente', 'FCR (%)', 'CSAT medio', AG.fcr_pct.mean(), AG.csat.mean())

# ---------------- HTML ----------------
def card(i):
    k = K[i]; val = k['valor']
    u = k['unidad']
    disp = {'%': pc(val), 's': es(val, 1) + ' s', 'h': es(val, 1) + ' h', 'de 5': es(val, 2) + ' / 5', 'llamadas': n0(val), 'moneda local': n0(val)}[u]
    if i == 'B3': disp = n0(val) + ' llamadas'
    meta = '' if k['meta'] is None else f"Meta {'≤' if k['tipo']=='max' else '≥'} {es(k['meta'], 1 if k['meta'] % 1 else 0)}{' %' if u=='%' else ' '+u if u in ('s','h') else ''}"
    if i == 'D1': meta = 'Meta ≥ 4,0'
    vc = {'cumple': VERDE, 'fuera': TERRA}.get(k['estado'], TINTA)
    return (f'<div class="kc" style="border-left:5px solid {COL[k["estado"]]}"><div class="kid">{i}</div><div class="kn">{k["kpi"]}</div>'
            f'<div class="kv" style="color:{vc}">{disp}</div><div class="km">{meta or "Sin meta · contexto"}</div>'
            f'<div class="ks"><span class="dot" style="background:{COL[k["estado"]]}"></span>{ST[k["estado"]]}</div></div>')

def diag(que, donde, por, hacer):
    return (f'<div class="dg"><div><h5>Qué pasa</h5><p>{que}</p></div><div><h5>Dónde</h5><p>{donde}</p></div>'
            f'<div><h5>Por qué (evidencia e hipótesis)</h5><p>{por}</p></div><div><h5>Qué hacer</h5><p>{hacer}</p></div></div>')

def kblock(i, defin, chart='', lectura='', dg=''):
    k = K[i]
    return (f'<article class="kb" id="{i}"><header><span class="tag"><span class="dot" style="background:{COL[k["estado"]]}"></span>{ST[k["estado"]]}</span>'
            f'<h3>{i} · {k["kpi"]}</h3></header><p class="def">{defin}</p>{f"<figure>{chart}</figure>" if chart else ""}'
            f'{f"<p>{lectura}</p>" if lectura else ""}{dg}</article>')

semafs = {e: sum(1 for k in J['kpis'] if k['estado'] == e and k['id'] not in ('A1e', 'A1s', 'C5p90')) for e in ST}

# Hallazgos priorizados
top5 = [
    (f"El escalamiento explica la insatisfacción: {pc(v('B4'))} de las llamadas se escalan y esos casos tienen CSAT {es(X['csat_esc'],2)} frente a {es(X['csat_no'],2)}.",
     f"Los escalados concentran el {pc(X['share_insat_esc'])} de los clientes insatisfechos y {pc(X['riesgo_esc_pct'],0)} del valor en riesgo ({n0(X['riesgo_esc'])} de {n0(X['riesgo_tot'])})."),
    (f"El cliente no logra hablarnos en dos franjas: abandono {pc(v('A2'))} y nivel de servicio {pc(v('A3'),0)} frente a metas de 5 % y 80 %.",
     f"Las franjas 10–13 h y 19–21 h reúnen el {pc(X['pico_share_ent'],0)} de las llamadas y el {pc(X['pico_share_ab'],0)} de los abandonos ({n0(X['pico_ab_n'])} de {n0(X['ab_n'])})."),
    (f"La primera línea no resuelve reclamos de calidad ni cambios de producto: FCR de {pc(CAT.loc['reclamo_calidad','fcr_pct'])} y {pc(CAT.loc['cambio_producto','fcr_pct'])}.",
     f"Ambas categorías tienen reincidencia cercana al {pc(CAT.loc['reclamo_calidad','reincidencia_pct'],0)}, el doble de la meta. El FCR global es {pc(v('C1'))}."),
    (f"El backlog de {n0(X['n_pend'])} casos pendientes ({pc(v('C4'))}) está envejecido: {n0(X['bk_30'])} llevan más de 30 días.",
     f"Los casos que se resuelven tardan {es(v('C5'),1)} h en promedio. Los pendientes no son lentos: están detenidos."),
    (f"El ACW promedio es {es(v('B2'),1)} s frente a una meta de 30 s, y ningún agente lo cumple.",
     f"Va de {es(X['ag_acw_min'],1)} a {es(X['ag_acw_max'],1)} s entre agentes. Es un problema de proceso o de sistema, no de personas."),
]
descartes = [
    f"La espera no explica la satisfacción. El CSAT es {es(CE.csat.min(),2)}–{es(CE.csat.max(),2)} en todos los rangos de espera, con correlación r ≈ {es(abs(X['corr']),2)}.",
    f"Los agentes no explican los problemas. El FCR por agente va de {pc(X['ag_fcr_min'])} a {pc(X['ag_fcr_max'])}, dentro de un margen de error de ±{es(X['ag_ci'],1)} pp.",
    f"El escalamiento no depende del motivo, la cola ni el agente: va de {pc(100-EA['Sin escalar'].max())} a {pc(100-EA['Sin escalar'].min())} entre motivos. Parece una regla general, no un nicho.",
]

cards = lambda ids: '<div class="kgrid">' + ''.join(card(i) for i in ids) + '</div>'

# --- Bloque A
A = ''
A += kblock('A1', 'Cuántas llamadas entran y salen. Es contexto para dimensionar.', g_vol,
            f"Hubo {n0(J['n_llamadas'])} llamadas: {n0(J['n_ent'])} entrantes y {n0(J['n_sal'])} salientes. Las semanas completas rondan las 1.800 llamadas. S35 y S43 (*) están incompletas: no las uses para comparar volumen.")
A += kblock('A2', 'Abandonadas entrantes ÷ entrantes. Meta ≤ 5 %, alerta > 8 %.', g_hora_ab,
            f"Las barras en terracota son las franjas pico. Solo las 7 h quedan bajo el umbral de alerta de 8 %; todas las horas superan la meta de 5 %. Por semana (completas) oscila entre {pc(X['ab_sem_ok_min'])} y {pc(X['ab_sem_ok_max'])}, sin una tendencia concluyente.<figure>{g_heat_ab}</figure>",
            diag(
                f"El abandono es {pc(v('A2'))}, {es(v('A2')/5,1)} veces la meta de 5 %. Se perdieron {n0(X['ab_n'])} llamadas entrantes.",
                f"Hora × día: 11 h ({pc(HR.loc[11,'abandono_pct'])}), 20 h ({pc(HR.loc[20,'abandono_pct'])}), 12 h ({pc(HR.loc[12,'abandono_pct'])}) y 13 h ({pc(HR.loc[13,'abandono_pct'])}). Los picos tienen {pc(X['pico_ab'])} de abandono; fuera de pico, {pc(X['fuera_ab'])}. Por cola y motivo la diferencia es pequeña ({pc(CO.abandono_pct.min())}–{pc(CO.abandono_pct.max())} por cola). Por día de la semana tampoco hay diferencia relevante, salvo el martes ({pc(DI.loc['Mar','abandono_pct'])}).",
                f"Evidencia: la espera sube de {es(X['fuera_asa'],0)} s fuera de pico a {es(X['pico_asa'],0)} s en pico y el cliente aguanta más antes de colgar ({es(X['pico_tab'],0)} s frente a {es(X['fuera_tab'],0)} s). Hipótesis (capacidad): hay menos agentes disponibles que demanda en esas franjas. El CDR no trae turnos, así que no se puede confirmar. Aun igualando el pico al nivel fuera de pico, el abandono quedaría en {pc(X['fuera_ab'])}: también falta cobertura fuera de pico.",
                "1) WFM: reforzar 10–13 h y 19–21 h (turnos, descansos y formaciones fuera de esas franjas). 2) WFM: pronosticar por intervalos de 30 minutos y revisar la cobertura fuera de pico. 3) WFM: evaluar devolución de llamada en picos. Meta: abandono ≤ 8 % en 30 días y ≤ 5 % en 90 días."))
A += kblock('A3', 'Entrantes con espera ≤ 20 s ÷ entrantes. Meta ≥ 80 %.', g_sl + f'<figure>{g_hora_sl}</figure>',
            f"Ninguna hora llega al 80 %. La mejor es la {HR.sl_pct.idxmax()} h con {pc(HR.sl_pct.max())}. Las barras en terracota son las franjas pico.",
            diag(f"El nivel de servicio es {pc(v('A3'),1)}, {es(80-v('A3'),1)} puntos bajo la meta.",
                 f"En pico baja a {pc(X['pico_sl'])}; fuera de pico es {pc(X['fuera_sl'])}. El mínimo es 11 h con {pc(HR.loc[11,'sl_pct'])}.",
                 "Mismo origen que el abandono: demanda concentrada con cobertura insuficiente (hipótesis de capacidad). Un SL de 68,7 % fuera de pico indica que la meta de 80/20 exige más agentes de forma general, no solo en picos.",
                 "WFM: recalcular dotación para 80/20 con Erlang C usando el AHT de 333 s y el volumen por intervalo. Meta: SL ≥ 70 % en 30 días y ≥ 80 % en 90 días."))
A += kblock('A4', 'Promedio de espera de las llamadas atendidas. Meta ≤ 20 s.', g_asa,
            f"El ASA está {es(v('A4')-20,1)} s sobre la meta. Cumple en las horas de menor demanda (por ejemplo, {es(HR.loc[9,'asa_s'],1)} s a las 9 h).",
            diag(f"El ASA es {es(v('A4'),1)} s, {pc((v('A4')/20-1)*100,0)} sobre la meta. Pasa apenas el límite de riesgo (22 s).",
                 f"11 h ({es(HR.loc[11,'asa_s'],1)} s), 12 h ({es(HR.loc[12,'asa_s'],1)} s) y 20 h ({es(HR.loc[20,'asa_s'],1)} s).",
                 "El promedio oculta el problema: fuera de pico cumple y en pico no. Es consecuencia de la misma brecha de capacidad.",
                 "Se resuelve con las acciones de A2 y A3. No requiere un plan aparte."))
A += kblock('A5', 'Segundos de espera antes de colgar. Indica cuánta paciencia tiene el cliente.', g_tab,
            f"En promedio el cliente cuelga a los {es(v('A5'),0)} s. En 11–12 h y 20 h espera 70–75 s antes de rendirse: ahí una devolución de llamada o un aviso de espera tendría más efecto.")
# --- Bloque B
Bq = ''
Bq += kblock('B1', 'Duración de conversación + ACW de llamadas atendidas.', g_aht,
             f"El AHT global es {es(v('B1'),0)} s y no varía entre colas ({es(T('aht_cola').aht_s.min(),0)}–{es(T('aht_cola').aht_s.max(),0)} s). Sí varía por motivo: de {es(T('aht_motivo').aht_s.min(),0)} s en cuenta_claves a {es(T('aht_motivo').aht_s.max(),0)} s en reclamo_calidad. Entre agentes, el desvío máximo es {pc(X['ag_aht_dev_max'])}, por debajo del 15 % de vigilancia.")
Bq += kblock('B2', 'Promedio del trabajo posterior a la llamada. Meta ≤ 30 s.', g_acw,
             f"{pc(X['acw_gt30'],0)} de las llamadas superan 30 s de ACW.",
             diag(f"El ACW medio es {es(v('B2'),1)} s, {es(v('B2')-30,1)} s sobre la meta.",
                  f"En todos los agentes: de {es(X['ag_acw_min'],1)} a {es(X['ag_acw_max'],1)} s. También es igual en todas las colas y motivos (36,8–38,1 s).",
                  f"Evidencia: nadie cumple y la dispersión es mínima, por lo que no es un tema de personas. Hipótesis: pasos manuales de registro o un cierre de caso poco ágil en el sistema. El exceso suma unas {es(X['acw_horas'],0)} horas-agente en el periodo.",
                  "Calidad y Formación: mapear los pasos del ACW, simplificar la plantilla de cierre y automatizar la disposición. Meta: ACW ≤ 30 s en 30 días; recupera unas 28 horas-agente por periodo."))
Bq += kblock('B3', 'Llamadas atendidas por agente. Se busca balance (± 15 % del promedio).', g_carga,
             f"El promedio es {n0(v('B3'))} llamadas por agente. El desvío máximo es {pc(X['ag_carga_dev_max'])}: la carga está balanceada.")
Bq += kblock('B4', 'Atendidas con escalamiento ÷ atendidas. Meta ≤ 15 %.', g_esc_mot,
             f"La tasa es pareja entre motivos ({pc(100-EA['Sin escalar'].max())}–{pc(100-EA['Sin escalar'].min())}) y entre áreas: Logística {pc(T('escalamiento_area').loc['Area_Logistica','pct_de_atendidas'])}, Billing {pc(T('escalamiento_area').loc['Area_Billing','pct_de_atendidas'])} y Supervisor {pc(T('escalamiento_area').loc['Supervisor','pct_de_atendidas'])}.<figure>{g_esc_ag}</figure>",
             diag(f"El {pc(v('B4'))} de las llamadas atendidas se escala, {es(v('B4')/15,1)} veces la meta de 15 %.",
                  f"En todas partes: cuatro colas entre {pc(T('aht_cola').escalamiento_pct.min())} y {pc(T('aht_cola').escalamiento_pct.max())}; agentes entre {pc(X['ag_esc_min'])} y {pc(X['ag_esc_max'])}.",
                  f"Evidencia: el destino no sigue al motivo. De {n0(X['mis_base'])} escalamientos a Logística o Billing con motivo claro, {n0(X['mis_n'])} ({pc(X['mis_pct'],0)}) fueron al área contraria. Un estado_envio va a Billing tanto como a Logística. Aun así, los mal dirigidos tienen el mismo CSAT ({es(X['csat_mis'],2)} frente a {es(X['csat_okr'],2)}): lo que daña es escalar, no el destino. Hipótesis: criterios de escalamiento poco claros o falta de facultades en primera línea. Se valida escuchando una muestra de llamadas.",
                  "1) Calidad: escuchar 100 escalamientos y clasificar la causa real. 2) Líder de cola: acordar criterios y dar facultades para casos frecuentes. 3) Logística y Billing: publicar una tabla de enrutamiento por motivo. Meta: ≤ 25 % en 90 días."))
# --- Bloque C
Cb = ''
Cb += kblock('C1', 'Casos resueltos en el primer contacto. Meta ≥ 75 %.', g_fcr_cat,
             f"Cumplen estado_envio ({pc(CAT.loc['estado_envio','fcr_pct'])}), informacion_preventa ({pc(CAT.loc['informacion_preventa','fcr_pct'])}), cuenta_claves ({pc(CAT.loc['cuenta_claves','fcr_pct'])}) y facturacion ({pc(CAT.loc['facturacion','fcr_pct'])}). Escalar no cambia el FCR: {pc(ESC.loc['Escalado','fcr_pct'])} escalados frente a {pc(ESC.loc['No escalado','fcr_pct'])} no escalados.",
             diag(f"El FCR es {pc(v('C1'))}, {es(75-v('C1'),1)} puntos bajo la meta.",
                  f"reclamo_calidad ({pc(CAT.loc['reclamo_calidad','fcr_pct'])}), cambio_producto ({pc(CAT.loc['cambio_producto','fcr_pct'])}), devolucion ({pc(CAT.loc['devolucion','fcr_pct'])}) y problema_pago ({pc(CAT.loc['problema_pago','fcr_pct'])}). Entre agentes el rango es corto ({pc(X['ag_fcr_min'])}–{pc(X['ag_fcr_max'])}).",
                  "Evidencia: la brecha depende de la categoría, no de la persona ni de escalar. Hipótesis: esos trámites requieren acciones que primera línea no puede ejecutar (aprobar cambios, coordinar recogida, revisar producto) y quedan para un segundo contacto.",
                  "1) Formación y Logística: guía paso a paso y facultades para cambios y reclamos. 2) Billing: definir qué puede resolver primera línea en pagos. 3) Calidad: revisar 30 casos de reclamo_calidad. Meta: FCR ≥ 65 % en esas categorías en 90 días."))
Cb += kblock('C2', 'Clientes que volvieron por lo mismo. Meta ≤ 5 %.', g_reinc,
             "En los datos, la reincidencia coincide caso a caso con la reapertura (639 casos): ambos indicadores miden el mismo grupo.",
             diag(f"La reincidencia es {pc(v('C2'),2)}, {es(v('C2')-5,1)} puntos sobre la meta.",
                  f"reclamo_calidad ({pc(CAT.loc['reclamo_calidad','reincidencia_pct'])}) y cambio_producto ({pc(CAT.loc['cambio_producto','reincidencia_pct'])}); devolucion ({pc(CAT.loc['devolucion','reincidencia_pct'])}) y problema_pago ({pc(CAT.loc['problema_pago','reincidencia_pct'])}) también superan 5 %.",
                  "Las mismas categorías con FCR bajo reinciden más: el cliente vuelve porque el primer contacto no cerró el problema.",
                  "Se mueve con las acciones de C1. Agrega un seguimiento a 48 horas en esas categorías (Calidad)."))
Cb += kblock('C3', 'Casos reabiertos ÷ casos. Meta ≤ 3 %.', g_reab,
             f"Hay {n0(X['n_reab'])} casos reabiertos. La tasa semanal se mantiene entre {pc(SEM.loc[sem_ok,'C3'].min())} y {pc(SEM.loc[sem_ok,'C3'].max())} en semanas completas.",
             diag(f"La reapertura es {pc(v('C3'),2)}, casi el doble de la meta de 3 %.",
                  f"Misma distribución que la reincidencia: reclamo_calidad {pc(CAT.loc['reclamo_calidad','reapertura_pct'])} y cambio_producto {pc(CAT.loc['cambio_producto','reapertura_pct'])}.",
                  "Hipótesis: casos cerrados sin confirmar con el cliente. Los datos no traen el motivo de reapertura; sería un dato adicional útil.",
                  "Calidad: checklist de cierre y confirmación con el cliente en categorías con reapertura > 9 %. Registrar el motivo de reapertura. Meta: ≤ 4 % en 90 días."))
Cb += kblock('C4', 'Casos en estado pendiente. Meta ≤ 10 %.', g_bk,
             f"La categoría con más pendientes en número es estado_envio ({n0(CAT.loc['estado_envio','pendiente_n'])}); la de mayor proporción es facturacion ({pc(CAT.loc['facturacion','pendiente_pct'])}).",
             diag(f"Hay {n0(X['n_pend'])} casos pendientes ({pc(v('C4'))}). Para llegar al 10 % habría que cerrar unos {n0(X['n_pend']-X['meta_pend_n'])}.",
                  f"{n0(X['bk_30'])} ({pc(X['bk_30_pct'],0)}) llevan más de 30 días y {pc(X['bk_15_pct'],0)} más de 14. La proporción es pareja entre categorías ({pc(CAT.pendiente_pct.min())}–{pc(CAT.pendiente_pct.max())}).",
                  "Evidencia: el backlog es parejo y antiguo, no un pico reciente. Hipótesis: casos que esperan a un área externa sin responsable ni fecha.",
                  "Líder de cola con Logística y Billing: depuración de los casos de más de 30 días, un dueño por caso y revisión semanal. Meta: ≤ 10 % en 60 días."))
Cb += kblock('C5', 'Horas hasta el cierre de casos resueltos. Meta ≤ 24 h (promedio y P90).', g_res,
             f"El promedio es {es(v('C5'),1)} h y cumple. El P90 es {es(v('C5p90'),1)} h: uno de cada diez casos resueltos tarda más de lo deseado.",
             diag(f"El promedio ({es(v('C5'),1)} h) cumple; el P90 ({es(v('C5p90'),1)} h) queda {es(v('C5p90')-24,1)} h sobre 24 h.",
                  f"Parejo por categoría: P90 entre {es(CAT.res_p90_h.min(),1)} y {es(CAT.res_p90_h.max(),1)} h.",
                  "Es una cola larga de casos complejos. Se trata junto con el backlog.",
                  "Líder de cola: alerta automática a las 24 h de abierto un caso. Meta: P90 ≤ 24 h en 90 días."))
# --- Bloque D
Dd = ''
Dd += kblock('D1', 'Satisfacción media de 1 a 5. Meta ≥ 4,0.', g_csat_esc + f'<figure>{g_csat_cat}</figure>',
             f"Por categoría el CSAT va de {es(CAT.csat.min(),2)} a {es(CAT.csat.max(),2)}: casi no cambia. La diferencia grande está entre escalados y no escalados.",
             diag(f"El CSAT es {es(v('D1'),2)}, {es(4-v('D1'),2)} puntos bajo la meta.",
                  f"Casos escalados: {es(X['csat_esc'],2)}. No escalados: {es(X['csat_no'],2)}. Los escalados son el {pc(X['p_esc_t'],0)} de los casos.",
                  f"Evidencia: la espera no influye ({es(CE.csat.min(),2)}–{es(CE.csat.max(),2)} en todos los rangos) y el agente tampoco ({es(X['ag_csat_min'],2)}–{es(X['ag_csat_max'],2)}). Escenario: con 25 % de escalamiento el CSAT sería {es(X['csat_25'],2)}; con 15 %, {es(X['csat_15'],2)}. Aun así quedaría bajo 4,0: los no escalados ({es(X['csat_no'],2)}) tampoco llegan.",
                  "Atacar el escalamiento (B4) y el FCR (C1). Después, revisar qué frena a los no escalados con una encuesta abierta de dos preguntas (Calidad)."))
Dd += kblock('D2', 'Casos con CSAT 4 o 5. Meta ≥ 80 %.', g_csat_dist,
             f"Solo {pc(v('D2'))} de los casos califica 4 o 5. Entre los escalados es {pc(ESC.loc['Escalado','top2_pct'])}; entre los no escalados, {pc(ESC.loc['No escalado','top2_pct'])}.")
Dd += kblock('D3', 'Casos con CSAT 1 o 2. Meta ≤ 10 %.', '',
             f"El {pc(v('D3'))} de los casos queda insatisfecho. Entre escalados es {pc(ESC.loc['Escalado','insatisfechos_pct'])}; entre no escalados, {pc(ESC.loc['No escalado','insatisfechos_pct'])} (cumple). reclamo_calidad es la categoría más afectada con {pc(CAT.loc['reclamo_calidad','insatisfechos_pct'])}. Con 15 % de escalamiento, el indicador bajaría a {pc(X['insat_15'])}.")
Dd += kblock('D4', 'Suma de valor_orden de casos con CSAT ≤ 2 o reincidencia. Sirve para priorizar.', g_riesgo,
             f"Hay {n0(v('D4'))} en riesgo (moneda local). Los casos escalados aportan {n0(X['riesgo_esc'])} ({pc(X['riesgo_esc_pct'],0)}). Por categoría, estado_envio ({n0(CAT.loc['estado_envio','valor_en_riesgo'])}) y devolucion ({n0(CAT.loc['devolucion','valor_en_riesgo'])}) son las categorías con más valor en riesgo.")

# --- Agentes
rank_rows = ''
for a, r in AG.iterrows():
    rank_rows += (f"<tr><td>{int(r.ranking)}</td><td>{a}</td><td>{es(r.indice,2)}</td><td>{pc(r.fcr_pct)}</td><td>{es(r.csat,2)}</td><td>{es(r.aht_s,0)} s</td><td>{pc(r.escalamiento_pct)}</td><td>{es(r.acw_s,1)} s</td><td>{n0(r.atendidas)}</td></tr>")
agentes_html = f"""
<p>El índice promedia los puntajes z de FCR, CSAT, AHT (invertido) y escalamiento (invertido). Cero es el promedio del equipo.</p>
<p><strong>Lectura:</strong> las diferencias entre agentes son pequeñas. El FCR va de {pc(X['ag_fcr_min'])} a {pc(X['ag_fcr_max'])} con un margen de error de ±{es(X['ag_ci'],1)} pp por agente. El CSAT va de {es(X['ag_csat_min'],2)} a {es(X['ag_csat_max'],2)}. Los problemas son de proceso: todo el equipo falla igual en ACW, escalamiento y FCR.</p>
<p>El ranking sirve para orientar el acompañamiento, no para evaluar a nadie. Quienes lideran ({', '.join(top3)}) pueden compartir prácticas en escalamiento y AHT. Quienes hoy necesitan más apoyo son {', '.join(bot3)}: en ellos FCR, CSAT, AHT y escalamiento quedan algo por debajo del equipo, cada uno por motivos distintos (ver tabla).</p>
<div class="two"><figure>{g_scatter}<figcaption>Verde: tres primeros del índice. Terracota: tres con más margen de apoyo. Líneas punteadas: promedio del equipo.</figcaption></figure>
<div class="tw"><table><thead><tr><th>#</th><th>Agente</th><th>Índice</th><th>FCR</th><th>CSAT</th><th>AHT</th><th>Escal.</th><th>ACW</th><th>Atendidas</th></tr></thead><tbody>{rank_rows}</tbody></table></div></div>
"""

# --- Plan de acción
ACC = [
    ('P1', 'Escuchar 100 escalamientos (50 con CSAT ≤ 2) y clasificar la causa real', 'B4, D1', 'Calidad', 'Valida la hipótesis principal; define el resto del plan', 'Bajo', 'Inmediato'),
    ('P2', 'Definir criterios de escalamiento y dar facultades de resolución a primera línea', 'B4, D1, D3', 'Líder de cola', f'Escalamiento de {pc(v("B4"))} a ≤ 25 %; CSAT hasta {es(X["csat_25"],2)}', 'Medio', '90 días'),
    ('P3', 'Publicar una tabla de enrutamiento de escalamientos por motivo', 'B4, C5', 'Logística y Billing', f'Hoy {pc(X["mis_pct"],0)} va al área contraria; menos reasignaciones', 'Bajo', '30 días'),
    ('P4', 'Reforzar cobertura en 10–13 h y 19–21 h (turnos, descansos, formaciones fuera de esas franjas)', 'A2, A3, A4', 'WFM', f'Abandono en pico de {pc(X["pico_ab"])} a ≤ 10 %; SL ≥ 70 %', 'Medio', '30 días'),
    ('P5', 'Recalcular dotación 80/20 por intervalos de 30 minutos, incluida la cobertura fuera de pico', 'A2, A3', 'WFM', f'Abandono global de {pc(v("A2"))} a ≤ 5 %; SL ≥ 80 %', 'Medio', '90 días'),
    ('P6', 'Probar devolución de llamada en picos (el cliente espera 70–75 s antes de colgar)', 'A2, A5', 'WFM', 'Reduce abandonos en 11–12 h y 20 h', 'Medio', '90 días'),
    ('P7', 'Guía paso a paso y facultades para reclamo_calidad y cambio_producto', 'C1, C2, C3', 'Formación y Logística', f'FCR de {pc(CAT.loc["reclamo_calidad","fcr_pct"],0)} y {pc(CAT.loc["cambio_producto","fcr_pct"],0)} a ≥ 65 %', 'Medio', '90 días'),
    ('P8', 'Definir qué resuelve primera línea en devoluciones y pagos', 'C1, C2', 'Billing', f'FCR de devolucion ({pc(CAT.loc["devolucion","fcr_pct"],0)}) y problema_pago ({pc(CAT.loc["problema_pago","fcr_pct"],0)}) a ≥ 75 %', 'Medio', '90 días'),
    ('P9', f'Depurar los {n0(X["bk_30"])} casos pendientes de más de 30 días con dueño y fecha por caso', 'C4, C5', 'Líder de cola', f'Pendientes de {pc(v("C4"))} a ≤ 10 % (cerrar unos {n0(X["n_pend"]-X["meta_pend_n"])} casos)', 'Medio', 'Inmediato'),
    ('P10', 'Checklist de cierre y seguimiento a 48 h en categorías con reapertura > 9 %', 'C2, C3', 'Calidad', f'Reapertura de {pc(v("C3"))} a ≤ 4 %', 'Bajo', '30 días'),
    ('P11', 'Simplificar la plantilla de cierre y automatizar la disposición (ACW)', 'B2', 'Calidad y Formación', f'ACW de {es(v("B2"),1)} s a ≤ 30 s; unas {es(X["acw_horas"],0)} horas-agente recuperadas', 'Bajo', '30 días'),
    ('P12', 'Registrar turnos, causa de escalamiento y motivo de reapertura; revisar casos faltantes', 'Todos', 'WFM y Líder de cola', f'Cierra los vacíos del análisis ({pc(X["att_sin_ticket_pct"])} de atendidas sin caso)', 'Bajo', '30 días'),
    ('P13', 'Acompañamiento a los agentes con índice más bajo y sesión de buenas prácticas con los primeros', 'D5, B4', 'Formación', 'Acerca el escalamiento y el AHT al promedio del equipo', 'Bajo', '30 días'),
]
plan_rows = ''.join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td><td>{e}</td><td>{f}</td><td>{g}</td></tr>" for a, b, c, d, e, f, g in ACC)

# --- Calidad (HTML anexo)
calidad_items = [
    f"CDR: {n0(J['n_llamadas'])} filas; casos: {n0(J['n_casos'])} filas. Periodo {J['periodo'][0]} a {J['periodo'][1]} (60 días con datos).",
    "IDs duplicados: 0 en id_llamada, 0 en id_caso, 0 llamadas con más de un caso.",
    f"id_agente vacío: 2.155 filas, todas abandonadas. Ninguna llamada atendida sin agente. escalado_a vacío: 10.503 (no escaladas, esperado).",
    "Valores imposibles: 0 esperas, duraciones o ACW negativos; 0 abandonadas con duración > 0; CSAT siempre entre 1 y 5.",
    "Casos con id_llamada ausente en el CDR: 0. Casos de llamadas abandonadas: 0. Agente, cliente y fecha coinciden con el CDR en todos los casos.",
    f"Semanas incompletas: S35 (6 días, falta el lunes 24-ago) y S43 (5 días, hasta el viernes 23-oct). Se marcan con * y no se usan para concluir tendencias.",
    f"{n0(X['sal_ab'])} llamadas salientes ({pc(X['sal_ab_pct'])}) figuran como abandonadas y con espera. Es raro en salientes; revisa la definición. No entran en A2–A5.",
    f"{n0(X['att_sin_ticket'])} llamadas atendidas ({pc(X['att_sin_ticket_pct'])}) no tienen caso. FCR, CSAT y resolución cubren el {pc(100-X['att_sin_ticket_pct'])} de las atendidas. {n0(X['tk_sal'])} casos vienen de llamadas salientes.",
    f"Reincidencia = 1 coincide exactamente con estado reabierto ({n0(X['n_reab'])} casos): C2 y C3 miden el mismo grupo.",
    "horas_resolucion y csat vienen informados también en casos pendientes y reabiertos. C5 usa solo casos resueltos; el CSAT usa todos los casos.",
]
supuestos = [
    "Semana ISO (lunes a domingo). A2–A5 sobre llamadas entrantes. B1–B4 sobre llamadas atendidas (entrantes y salientes). C y D sobre casos.",
    "Semáforo: cumple si alcanza la meta; en riesgo si está a menos de 10 % relativo de la meta; fuera de meta si pasa de ahí. Se aplica sobre el valor sin redondear.",
    "Diferencia con la línea base: ASA (22,06 s, 10,3 % sobre la meta) y reincidencia (5,59 %, 11,8 % sobre la meta) caen en «fuera de meta» con esta regla estricta. La línea base los marcó «en riesgo». Los valores coinciden con la línea base.",
    "No hay metas propias de Cesta en Recursos/: se usan las metas estándar del CLAUDE.md. Recursos/ solo contiene la hoja de marca v1.0.",
    "Franjas pico: 10–13 h y 19–21 h (nivel de servicio por hora bajo 55 %). Área esperada de escalamiento: Logística para estado_envio, devolucion, cambio_producto y reclamo_calidad; Billing para problema_pago y facturacion. Es un supuesto a validar con la operación.",
    "Cobertura: el CDR no trae turnos. Los agentes con llamadas por hora son una aproximación, no la dotación real.",
    f"Antigüedad del backlog: días entre fecha_apertura y 2026-10-23. Valor en riesgo: suma de valor_orden sin doble conteo, en moneda local.",
    "No hay ejecución previa en Salidas/: no se calculan variaciones. El recálculo coincide con la línea base del CLAUDE.md.",
]

GLOS = [
    ('A1', 'Volumen de llamadas', 'Cuántas llamadas entran y salen. Sirve para dimensionar el equipo.', 'Conteo de llamadas; entrantes y salientes por separado', 'Contexto'),
    ('A2', 'Tasa de abandono', 'Porcentaje de llamadas entrantes en las que el cliente cuelga antes de ser atendido.', 'Abandonadas entrantes ÷ entrantes × 100', '≤ 5 % (alerta > 8 %)'),
    ('A3', 'Nivel de servicio 80/20 (SL)', 'Porcentaje de entrantes atendidas o abandonadas dentro de 20 segundos de espera.', 'Entrantes con espera ≤ 20 s ÷ entrantes × 100', '≥ 80 %'),
    ('A4', 'ASA (Average Speed of Answer)', 'Velocidad media de respuesta: cuánto espera el cliente hasta que lo atienden.', 'Promedio de espera_seg de las llamadas atendidas', '≤ 20 s'),
    ('A5', 'Tiempo medio hasta abandono', 'Cuánto espera el cliente antes de colgar. Indica su paciencia.', 'Promedio de espera_seg de las llamadas abandonadas', 'Contexto'),
    ('B1', 'AHT (Average Handling Time)', 'Tiempo medio de gestión de una llamada, incluido el trabajo posterior.', 'Promedio de (duracion_seg + acw_seg) de atendidas', 'Contexto; vigilar variación > 15 % entre agentes'),
    ('B2', 'ACW (After Call Work)', 'Tiempo que el agente dedica a registrar y cerrar tras la llamada.', 'Promedio de acw_seg de atendidas', '≤ 30 s'),
    ('B3', 'Carga por agente', 'Cuántas llamadas atiende cada agente. Muestra si el reparto es parejo.', 'Llamadas atendidas por agente; desvío = atendidas ÷ promedio − 1', 'Balanceada (± 15 % del promedio)'),
    ('B4', 'Tasa de escalamiento', 'Porcentaje de llamadas que la primera línea pasa a Logística, Billing o un supervisor.', 'Atendidas con escalado_a informado ÷ atendidas × 100', '≤ 15 %'),
    ('C1', 'FCR (First Contact Resolution)', 'Porcentaje de casos resueltos en el primer contacto, sin que el cliente vuelva.', 'Promedio de fcr (1 = resuelto) × 100', '≥ 75 %'),
    ('C2', 'Tasa de reincidencia', 'Porcentaje de casos en que el cliente volvió a contactar por lo mismo.', 'Promedio de reincidencia (1 = volvió) × 100', '≤ 5 %'),
    ('C3', 'Tasa de reapertura', 'Porcentaje de casos que se cerraron y debieron reabrirse.', 'Casos en estado reabierto ÷ casos × 100', '≤ 3 %'),
    ('C4', 'Backlog pendiente', 'Casos abiertos que aún no se resuelven, en número y como porcentaje.', 'Casos en estado pendiente ÷ casos × 100; antigüedad = fecha final − fecha_apertura', '≤ 10 %'),
    ('C5', 'Tiempo de resolución (media y P90)', 'Horas hasta cerrar un caso. P90 es el valor bajo el cual queda el 90 % de los casos.', 'Promedio y percentil 90 de horas_resolucion en casos resueltos', '≤ 24 h'),
    ('D1', 'CSAT (Customer Satisfaction)', 'Satisfacción del cliente, calificada de 1 a 5.', 'Promedio de csat', '≥ 4,0'),
    ('D2', 'CSAT Top-2-Box', 'Porcentaje de clientes que califican con las dos notas más altas (4 o 5).', 'Casos con csat ≥ 4 ÷ casos × 100', '≥ 80 %'),
    ('D3', '% de insatisfechos', 'Porcentaje de clientes que califican con las dos notas más bajas (1 o 2).', 'Casos con csat ≤ 2 ÷ casos × 100', '≤ 10 %'),
    ('D4', 'Valor en riesgo', 'Valor de los pedidos asociados a clientes insatisfechos o que reincidieron. Sirve para priorizar.', 'Suma de valor_orden de casos con csat ≤ 2 o reincidencia = 1 (sin doble conteo)', 'Contexto'),
    ('D5', 'Ranking de agentes (índice)', 'Índice que resume el desempeño de cada agente frente al equipo. Orienta el acompañamiento.', 'Promedio de los puntajes z de FCR, CSAT, AHT (invertido) y escalamiento (invertido); z = (valor − media) ÷ desviación estándar', 'Detectar tres primeros y tres últimos'),
]
SIGLAS = [
    ('CDR', 'Call Detail Record: registro de cada llamada (hora, cola, espera, duración, agente).'),
    ('WFM', 'Workforce Management: planificación de turnos y dotación de agentes.'),
    ('Cola', 'Fila de espera por tipo de atención: Soporte_Envios, Soporte_Pedidos, Retenciones o Ventas.'),
    ('Escalamiento', 'Traspaso de la llamada de primera línea a Logística, Billing o Supervisor.'),
    ('Franjas pico', 'Horas con nivel de servicio bajo 55 %: 10–13 h y 19–21 h.'),
    ('Erlang C', 'Método estándar para calcular cuántos agentes se necesitan según llamadas, AHT y nivel de servicio.'),
    ('Puntaje z', 'Distancia de un valor al promedio del equipo, medida en desviaciones estándar.'),
    ('pp', 'Puntos porcentuales: diferencia entre dos porcentajes.'),
]
glos_rows = ''.join(f"<tr><td>{a}</td><td><strong>{b}</strong><br>{c}</td><td>{d}</td><td>{e}</td></tr>" for a, b, c, d, e in GLOS)
siglas_rows = ''.join(f"<tr><td><strong>{a}</strong></td><td>{b}</td></tr>" for a, b in SIGLAS)

CSS = f"""
:root{{--v:{VERDE};--c:{CREMA};--d:{DORADO};--t:{TERRA};--o:{OLIVA};--i:{TINTA};--fd:"Fraunces",Georgia,serif;--ft:"Inter",system-ui,sans-serif}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--c);color:var(--i);font:400 16px/1.6 var(--ft)}}
h1,h2,h3,.kv,.cover .brand{{font-family:var(--fd)}}h1{{font-size:48px;line-height:1.1;font-weight:700;margin:0 0 16px}}
h2{{font-size:32px;line-height:1.2;font-weight:600;margin:0 0 20px;color:var(--v)}}h3{{font-size:22px;line-height:1.3;font-weight:600;margin:0}}
h5{{font:600 12px/1.4 var(--ft);letter-spacing:.04em;text-transform:uppercase;margin:0 0 4px;color:var(--v)}}
.cover{{background:var(--v);color:var(--c);padding:72px 8vw 64px}}.cover .brand{{font-size:28px;font-weight:600;letter-spacing:-.02em;margin-bottom:56px}}
.cover .tg{{color:var(--d);font-weight:600;font-size:14px;margin-bottom:12px}}.cover p{{margin:6px 0;font-size:16px;max-width:60ch}}
.cover .meta{{display:flex;gap:48px;margin-top:40px;flex-wrap:wrap}}.cover .meta div b{{display:block;font:700 32px var(--fd);color:var(--c)}}.cover .meta div span{{font-size:14px;color:var(--c)}}
main{{max-width:1040px;margin:0 auto;padding:0 24px 80px}}section{{padding:56px 0 8px;border-bottom:1px solid #E1DBCB}}section:last-child{{border:none}}
nav{{position:sticky;top:0;background:var(--c);border-bottom:1px solid #E1DBCB;z-index:5;padding:10px 8vw;font-size:14px;display:flex;gap:20px;flex-wrap:wrap}}nav a{{color:var(--v);text-decoration:none;font-weight:600}}
.kgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px;margin:12px 0 24px}}
.kc{{background:#fff8;border:1px solid #E1DBCB;padding:14px 16px;border-radius:4px}}.kid{{font:600 12px var(--ft);color:var(--o)}}
.kn{{font-size:14px;font-weight:500;min-height:42px}}.kv{{font-size:30px;font-weight:700;line-height:1.2;margin:4px 0}}.km{{font-size:13px}}.ks{{font-size:13px;font-weight:600;margin-top:6px}}
.dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:baseline}}
.tag{{font-size:12px;font-weight:600;display:block;margin-bottom:4px}}
.kb{{margin:0 0 44px}}.kb header{{border-top:2px solid var(--v);padding-top:12px;margin-bottom:6px}}.def{{color:var(--i);font-size:15px;margin:4px 0 14px}}
figure{{margin:12px 0 16px}}figcaption{{font-size:13px;margin-top:4px}}
.dg{{display:grid;grid-template-columns:1fr 1fr;gap:18px 28px;background:#fff8;border:1px solid #E1DBCB;border-left:4px solid var(--t);padding:18px 22px;margin-top:14px;border-radius:4px}}
.dg p{{margin:0;font-size:14.5px}}
ol.top{{padding-left:0;list-style:none;counter-reset:n}}ol.top li{{counter-increment:n;margin:0 0 22px;padding-left:52px;position:relative}}
ol.top li::before{{content:counter(n);position:absolute;left:0;top:-4px;font:700 32px var(--fd);color:var(--v)}}ol.top b{{display:block;font-weight:600}}ol.top span{{font-size:15px}}
table{{border-collapse:collapse;width:100%;font-size:13.5px}}th{{background:var(--v);color:var(--c);text-align:left;padding:8px 10px;font-weight:600}}td{{padding:7px 10px;border-bottom:1px solid #E1DBCB;vertical-align:top}}
.tw{{overflow-x:auto}}.two td,.two th{{white-space:nowrap}}.two{{display:grid;grid-template-columns:1fr 1.25fr;gap:24px;align-items:start}}
.note{{background:#fff8;border:1px solid #E1DBCB;padding:12px 16px;font-size:14px;margin:16px 0}}ul.q{{padding-left:20px}}ul.q li{{margin-bottom:6px;font-size:14.5px}}
footer{{padding:24px 8vw;font-size:13px;border-top:1px solid #E1DBCB}}
@media(max-width:760px){{h1{{font-size:32px}}h2{{font-size:24px}}.dg,.two{{grid-template-columns:1fr}}}}
@media print{{nav{{display:none}}.kb{{break-inside:avoid}}}}
"""

html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cesta · Informe de KPIs del call center · {J['periodo'][0]} a {J['periodo'][1]}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<div class="cover"><div class="brand">Cesta</div><div class="tg">Operaciones · Call center</div>
<h1>Informe de KPIs del call center</h1><p>Qué mide cada indicador, cómo está, por qué está así y qué hacer.</p>
<div class="meta"><div><b>{J['periodo'][0]} → {J['periodo'][1]}</b><span>Periodo analizado</span></div><div><b>{n0(J['n_llamadas'])}</b><span>Llamadas ({n0(J['n_ent'])} entrantes)</span></div><div><b>{n0(J['n_casos'])}</b><span>Casos abiertos</span></div><div><b>{HOY}</b><span>Fecha de generación</span></div></div></div>
<nav><a href="#resumen">Resumen</a><a href="#tablero">Tablero</a><a href="#A">Accesibilidad</a><a href="#B">Eficiencia</a><a href="#C">Efectividad</a><a href="#D">Experiencia</a><a href="#agentes">Agentes</a><a href="#plan">Plan de acción</a><a href="#anexo">Anexo</a><a href="#glosario">Glosario</a></nav>
<main>
<section id="resumen"><h2>Resumen ejecutivo</h2>
<p>De {semafs['cumple']+semafs['riesgo']+semafs['fuera']} indicadores con meta, {semafs['cumple']} cumple, {semafs['riesgo']} está en riesgo y {semafs['fuera']} están fuera de meta. Solo el tiempo medio de resolución cumple. Estos son los cinco hallazgos, ordenados por volumen afectado, gravedad y valor en riesgo.</p>
<ol class="top">{''.join(f'<li><b>{a}</b><span>{b}</span></li>' for a, b in top5)}</ol>
<h3 style="margin:28px 0 8px">Lo que los datos descartan</h3><ul class="q">{''.join(f'<li>{d}</li>' for d in descartes)}</ul>
<p class="note">Primera ejecución archivada en Salidas/: no hay variaciones contra una ejecución anterior. El recálculo coincide con la línea base del CLAUDE.md. Las semanas S35 y S43 (*) están incompletas.</p></section>

<section id="tablero"><h2>Tablero de KPIs</h2>
<p>Verde Cesta: cumple. Dorado: en riesgo (a menos de 10 % de la meta). Terracota: fuera de meta. Gris verdoso: contexto, sin meta.</p>
<h3>A · Accesibilidad</h3>{cards(['A2','A3','A4','A5','A1'])}
<h3>B · Eficiencia</h3>{cards(['B1','B2','B3','B4'])}
<h3>C · Efectividad</h3>{cards(['C1','C2','C3','C4','C5','C5p90'])}
<h3>D · Experiencia y negocio</h3>{cards(['D1','D2','D3','D4'])}</section>

<section id="A"><h2>A · Accesibilidad: ¿el cliente logra hablar con nosotros?</h2>{A}</section>
<section id="B"><h2>B · Eficiencia: ¿cuánto cuesta cada contacto?</h2>{Bq}</section>
<section id="C"><h2>C · Efectividad: ¿resolvemos?</h2>{Cb}</section>
<section id="D"><h2>D · Experiencia y negocio: ¿qué siente el cliente y cuánto vale?</h2>{Dd}</section>
<section id="agentes"><h2>D5 · Agentes: dónde acompañar</h2>{agentes_html}</section>
<section id="plan"><h2>Plan de acción</h2><p>Ordenado por prioridad. Las metas de impacto son objetivos de trabajo, no pronósticos.</p>
<div class="tw"><table><thead><tr><th>#</th><th>Acción</th><th>KPI objetivo</th><th>Responsable</th><th>Impacto esperado</th><th>Esfuerzo</th><th>Plazo</th></tr></thead><tbody>{plan_rows}</tbody></table></div></section>
<section id="anexo"><h2>Anexo</h2><h3>Calidad de datos</h3><ul class="q">{''.join(f'<li>{c}</li>' for c in calidad_items)}</ul>
<h3 style="margin-top:24px">Definiciones y supuestos</h3><ul class="q">{''.join(f'<li>{c}</li>' for c in supuestos)}</ul>
<p class="note">Evidencia es lo que muestran los datos. Hipótesis es lo que hay que validar con la operación (escucha de llamadas, reglas de enrutamiento, entrevista a líderes).</p></section>
<section id="glosario"><h2>Glosario</h2><p>Qué significa cada KPI, cómo se calcula y cuál es su meta.</p>
<div class="tw"><table><thead><tr><th>#</th><th>KPI y descripción</th><th>Fórmula</th><th>Meta</th></tr></thead><tbody>{glos_rows}</tbody></table></div>
<h3 style="margin-top:28px">Siglas y términos</h3>
<div class="tw"><table><thead><tr><th>Término</th><th>Significado</th></tr></thead><tbody>{siglas_rows}</tbody></table></div></section>
</main><footer>Cesta · Informe de KPIs del call center · Generado el {HOY} · calculo_kpis.py y generar_informe.py en esta carpeta.</footer></body></html>"""
open(os.path.join(HERE, 'informe_kpis.html'), 'w', encoding='utf-8').write(html)

# ---------------- plan_de_accion.md ----------------
md = ['# Plan de acción · Call center Cesta', '', f'Periodo analizado: {J["periodo"][0]} a {J["periodo"][1]} · Generado el {HOY}', '',
      'Ordenado por prioridad. Las metas son objetivos de trabajo, no pronósticos.', '',
      '| # | Acción | KPI objetivo | Responsable | Impacto esperado | Esfuerzo | Plazo |', '|---|---|---|---|---|---|---|']
md += [f'| {a} | {b} | {c} | {d} | {e} | {f} | {g} |' for a, b, c, d, e, f, g in ACC]
md += ['', '## Hipótesis que hay que validar', '',
       '- Los escalamientos se originan en criterios poco claros o en falta de facultades de primera línea (P1).',
       '- Hay menos agentes disponibles que demanda en 10–13 h y 19–21 h; el CDR no trae turnos para confirmarlo (P4, P12).',
       '- Reclamos de calidad y cambios de producto necesitan acciones que primera línea no puede ejecutar (P7).',
       '- Los pendientes de más de 30 días esperan a un área externa sin responsable (P9).']
open(os.path.join(HERE, 'plan_de_accion.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')

# ---------------- calidad_datos.md ----------------
q = ['# Calidad de datos', '', f'Periodo {J["periodo"][0]} a {J["periodo"][1]} · Generado el {HOY}', '', '## Hallazgos', ''] + [f'- {c}' for c in calidad_items]
q += ['', '## Supuestos aplicados', ''] + [f'- {c}' for c in supuestos]
open(os.path.join(HERE, 'calidad_datos.md'), 'w', encoding='utf-8').write('\n'.join(q) + '\n')
print('OK', len(html))
