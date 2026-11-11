#!/usr/bin/env python3
"""Genera informe_kpis.html (autocontenido) a partir de resultados.json y graficos/."""
import json, base64, os, sys, html
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(OUT, "resultados.json"), encoding="utf-8"))
K = {k["id"]: k for k in R["kpis"]}; X = R["extra"]; D = R["dx"]; Q = R["dq"]; AG = R["agente"]

def n(x, d=1):
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")
def pc(x, d=1): return n(x, d) + " %"
def img(name, alt):
    b = base64.b64encode(open(os.path.join(OUT, "graficos", name), "rb").read()).decode()
    return f'<figure><img src="data:image/png;base64,{b}" alt="{html.escape(alt)}"><figcaption>{html.escape(alt)}</figcaption></figure>'
def fmt(k):
    u, v = k["unidad"], k["valor"]
    if u == "%": return pc(v)
    if u == "s": return n(v) + " s"
    if u == "h": return n(v) + " h"
    if u == "pts": return n(v, 2)
    if u in ("valor", "llamadas"): return n(v, 0)
    return n(v)
ETQ = {"estado_envio":"Estado de envío","devolucion":"Devolución","problema_pago":"Problema de pago","cambio_producto":"Cambio de producto",
       "facturacion":"Facturación","cuenta_claves":"Cuenta y claves","reclamo_calidad":"Reclamo de calidad","informacion_preventa":"Información preventa"}
def E(t): return f'<span class="tag ev">Evidencia</span> {t}'
def H(t): return f'<span class="tag hi">Hipótesis</span> {t}'
def dot(est): return f'<span class="dot {est}" title="{est}"></span>'
ESTTXT = {"verde":"Cumple","amarillo":"En riesgo","rojo":"Incumple","info":"Informativo"}

def card(i):
    k = K[i]; var = k["variacion_txt"]
    v2 = "igual a la línea base" if var.startswith("0,0") else var
    if k["variacion"] is None: v2 = "sin referencia previa"
    return f'''<div class="card {k["estado"]}"><div class="cid">{i} · {html.escape(k["nombre"])}</div>
<div class="cval">{fmt(k)}</div><div class="cmeta">Meta: {html.escape(k["meta"])}</div>
<div class="cest">{dot(k["estado"])} {ESTTXT[k["estado"]]}</div><div class="cvar">vs línea base: {v2}</div></div>'''
def fam_cards(f): return '<div class="cards">' + "".join(card(i) for i in K if K[i]["familia"] == f) + "</div>"

# ---------- Cifras clave ----------
t = D["tend"]
picos = ", ".join(str(h) for h in D["picos"][:-1]) + " y " + str(D["picos"][-1]) + " h"
fcr_m = D["fcr_motivo"]; reinc_m = D["reinc_motivo"]
sin_ticket = Q["atendidas_sin_ticket"]; pct_sin = Q["pct_atendidas_sin_ticket"]*100
valor_t = X["valor_total"]
dim = D["dim"]
def agentes_h(h): return dim[str(h)]["agentes_80_20"]

hall = [
 f"El escalamiento es el mayor freno del CSAT. Escalan {pc(K['B3']['valor'])} de las llamadas atendidas, contra una meta de 15 %. El CSAT es {n(D['csat_esc'],2)} en casos escalados y {n(D['csat_no_esc'],2)} en los demás.",
 f"El escalamiento es parejo: entre {pc(D['esc_motivo_rango'][0],0)} y {pc(D['esc_motivo_rango'][1],0)} en todos los motivos. Además, el destino no sigue al motivo: solo {pc(D['destino_esperado_pct'],0)} llega al área esperada, casi lo mismo que el azar ({pc(D['destino_esperado_azar'],0)}).",
 f"El abandono es {pc(K['A2']['valor'])} y el nivel de servicio {pc(K['A3']['valor'])}. Las franjas de {picos} concentran {pc(D['share_ab_picos'],0)} de los abandonos con {pc(D['share_vol_picos'],0)} del volumen. Fuera de ellas el abandono sigue en {pc(D['ab_resto'])}.",
 f"El enrutamiento no separa motivos. Todas las colas reciben una mezcla casi idéntica (diferencia máxima {n(D['cola_motivo_max_diff'])} pp). Solo {pc(100-D['preventa_fuera_ventas'],0)} de las consultas de preventa llega a Ventas.",
 f"El FCR es {pc(K['C1']['valor'])}. Reclamo de calidad ({pc(fcr_m['reclamo_calidad'],0)}), cambio de producto ({pc(fcr_m['cambio_producto'],0)}) y devolución ({pc(fcr_m['devolucion'],0)}) son los motivos más débiles. Los dos primeros reinciden cerca de 10 %.",
 f"La espera no mueve el CSAT: queda entre {n(D['csat_espera_rango'][0],2)} y {n(D['csat_espera_rango'][1],2)} en todos los tramos. Resolver bien pesa más que contestar rápido.",
 f"El valor en riesgo es {n(K['E1']['valor'],0)} ({pc(X['e1_pct'])} del total) y hay {n(X['c4_n'],0)} casos pendientes. Los 25 agentes rinden de forma parecida (CSAT {n(AG['csat_min'],2)} a {n(AG['csat_max'],2)}): el problema es de proceso.",
]
top3 = [
 ("Reducir el escalamiento y corregir su destino.", f"Dar autonomía al agente en los motivos frecuentes y fijar reglas de derivación por motivo. Bajar a 25 % llevaría el CSAT a ≈ {n(D['csat_meta25'],2)}."),
 ("Reforzar las franjas de 11–12 h y 20 h.", f"Hacen falta cerca de {agentes_h(11)} agentes simultáneos a las 11 h y {agentes_h(20)} a las 20 h. Contrasta con la malla de turnos actual."),
 ("Corregir el enrutamiento del IVR.", "Cada motivo debe llegar a su cola. Es un cambio de bajo esfuerzo que ordena la carga y el escalamiento."),
]

CSS = """
:root{--cesta-verde:#0E3B2E;--cesta-crema:#F7F3EA;--cesta-dorado:#F4B942;--cesta-terracota:#C75B39;--cesta-oliva:#6E8F7A;--cesta-tinta:#14201B;
--font-display:"Fraunces",Georgia,serif;--font-text:"Inter",system-ui,sans-serif}
*{box-sizing:border-box}
body{margin:0;background:var(--cesta-crema);color:var(--cesta-tinta);font-family:var(--font-text);font-size:16px;line-height:1.6}
h1,h2,h3{font-family:var(--font-display);color:var(--cesta-verde);margin:0}
h1{font-size:48px;line-height:1.1;font-weight:700;color:var(--cesta-crema)}
h2{font-size:32px;line-height:1.2;font-weight:600;padding-bottom:8px;border-bottom:2px solid var(--cesta-dorado);margin-bottom:20px}
h3{font-size:22px;line-height:1.3;font-weight:600;margin:28px 0 8px}
h4{font-family:var(--font-text);font-size:14px;letter-spacing:.06em;text-transform:uppercase;color:var(--cesta-verde);margin:20px 0 6px;font-weight:600}
.wrap{max-width:1040px;margin:0 auto;padding:0 24px}
header.portada{background:var(--cesta-verde);color:var(--cesta-crema);padding:72px 0 56px}
.portada .marca{display:flex;align-items:center;gap:12px;margin-bottom:48px}
.portada .marca span{font-family:var(--font-display);font-weight:600;font-size:26px;color:var(--cesta-crema)}
.portada .sub{color:var(--cesta-dorado);font-weight:500;font-size:18px;margin:16px 0 28px}
.portada .meta{display:flex;gap:32px;flex-wrap:wrap;font-size:14px;color:var(--cesta-crema);border-top:1px solid var(--cesta-oliva);padding-top:16px}
nav.idx{position:sticky;top:0;background:var(--cesta-crema);border-bottom:1px solid var(--cesta-oliva);z-index:5}
nav.idx .wrap{display:flex;gap:20px;flex-wrap:wrap;padding-top:10px;padding-bottom:10px;font-size:14px}
nav.idx a{color:var(--cesta-verde);text-decoration:none;font-weight:500}
section{padding:48px 0 8px}
p{margin:0 0 12px;max-width:760px}
.lead{font-size:18px}
.hall{counter-reset:h;list-style:none;padding:0;margin:0 0 24px}
.hall li{counter-increment:h;padding:12px 0 12px 44px;position:relative;border-bottom:1px solid #e3dccb;max-width:820px}
.hall li:before{content:counter(h);position:absolute;left:0;top:10px;width:28px;height:28px;border-radius:50%;background:var(--cesta-verde);color:var(--cesta-crema);font-weight:600;font-size:14px;text-align:center;line-height:28px}
.top3{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-top:12px}
.top3 div{background:var(--cesta-verde);color:var(--cesta-crema);border-radius:12px;padding:20px}
.top3 b{display:block;font-family:var(--font-display);font-size:19px;margin-bottom:6px}
.top3 .num{color:var(--cesta-dorado);font-family:var(--font-display);font-size:30px;font-weight:700}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px;margin:12px 0 20px}
.card{background:#fff;border:1px solid #e3dccb;border-left:6px solid var(--cesta-oliva);border-radius:10px;padding:14px 16px}
.card.rojo{border-left-color:var(--cesta-terracota)}.card.amarillo{border-left-color:var(--cesta-dorado)}.card.verde{border-left-color:var(--cesta-oliva)}.card.info{border-left-color:#cfc8b6}
.cid{font-size:13px;font-weight:600;color:var(--cesta-verde);min-height:38px}
.cval{font-family:var(--font-display);font-weight:700;font-size:32px;line-height:1.2;color:var(--cesta-tinta);margin:4px 0}
.cmeta,.cvar{font-size:13px}.cest{font-size:14px;font-weight:600;margin:6px 0 2px}
.dot{display:inline-block;width:12px;height:12px;border-radius:50%;vertical-align:-1px;margin-right:4px;background:#cfc8b6}
.dot.verde{background:var(--cesta-oliva)}.dot.amarillo{background:var(--cesta-dorado)}.dot.rojo{background:var(--cesta-terracota)}
.nota{background:#fff;border-left:4px solid var(--cesta-dorado);border-radius:0 10px 10px 0;padding:12px 16px;margin:16px 0;max-width:820px;font-size:15px}
.tag{display:inline-block;font-size:12px;font-weight:600;padding:1px 8px;border-radius:10px;margin-right:6px;letter-spacing:.02em}
.tag.ev{background:var(--cesta-verde);color:var(--cesta-crema)}.tag.hi{background:#fff;color:var(--cesta-verde);border:1px solid var(--cesta-oliva)}
ul.causas{padding:0;list-style:none;margin:0 0 12px;max-width:820px}ul.causas li{padding:6px 0;border-bottom:1px solid #ece6d6}
figure{margin:16px 0;background:#fff;border:1px solid #e3dccb;border-radius:10px;padding:12px}
figure img{width:100%;height:auto;display:block}figcaption{font-size:13px;color:var(--cesta-tinta);margin-top:6px}
.dos{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}
table{border-collapse:collapse;width:100%;font-size:14px;background:#fff;margin:12px 0 20px}
th{background:var(--cesta-verde);color:var(--cesta-crema);text-align:left;padding:10px 12px;font-weight:600;font-size:13px}
td{padding:10px 12px;border-bottom:1px solid #ece6d6;vertical-align:top}tr:nth-child(even) td{background:#faf7ef}
.tw{overflow-x:auto}
footer{background:var(--cesta-verde);color:var(--cesta-crema);margin-top:56px;padding:28px 0;font-size:14px}
code{background:#ece6d6;padding:1px 6px;border-radius:4px;font-size:13px}
@media(max-width:700px){h1{font-size:32px}h2{font-size:24px}}
@media print{nav.idx{display:none}section{page-break-inside:avoid}}
"""
LOGO = '''<svg width="44" height="44" viewBox="0 0 100 100" aria-hidden="true"><rect width="100" height="100" rx="24" fill="#F7F3EA"/><path d="M34 44V34a16 16 0 0 1 32 0v10" fill="none" stroke="#F4B942" stroke-width="8"/><path d="M26 44h48l-6 36a8 8 0 0 1-8 7H40a8 8 0 0 1-8-7z" fill="#0E3B2E"/><rect x="29" y="55" width="42" height="4" rx="2" fill="#F7F3EA"/><rect x="32" y="68" width="36" height="4" rx="2" fill="#F7F3EA"/></svg>'''

P = []
P.append(f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Informe de indicadores del call center · Cesta</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header class="portada"><div class="wrap"><div class="marca">{LOGO}<span>Cesta</span></div>
<h1>Indicadores del call center</h1><div class="sub">Lo esencial, bien elegido.</div>
<div class="meta"><div>Periodo analizado<br><b>25 ago al 23 oct 2026</b></div><div>Fecha de la corrida<br><b>10 nov 2026</b></div>
<div>Base<br><b>{n(Q["filas_cdr"],0)} llamadas · {n(Q["filas_tickets"],0)} casos · {Q["agentes"]} agentes</b></div></div></div></header>
<nav class="idx"><div class="wrap"><a href="#resumen">Resumen</a><a href="#tablero">Tablero</a><a href="#A">A · Accesibilidad</a><a href="#B">B · Eficiencia</a><a href="#C">C · Efectividad</a><a href="#D">D · Experiencia</a><a href="#E">E · Negocio</a><a href="#plan">Plan de acción</a><a href="#calidad">Calidad de datos</a></div></nav>
<main class="wrap">''')

# Resumen
P.append('<section id="resumen"><h2>Resumen ejecutivo</h2><p class="lead">Siete hallazgos que explican por qué el servicio no alcanza sus metas y dónde actuar primero.</p><ol class="hall">')
P += [f"<li>{h}</li>" for h in hall]
P.append('</ol><h3>Top 3 de prioridades para el próximo periodo</h3><div class="top3">')
for i,(a,b) in enumerate(top3,1): P.append(f'<div><span class="num">{i}</span><b>{a}</b>{b}</div>')
P.append('</div></section>')

# Tablero
P.append('<section id="tablero"><h2>Tablero de KPIs</h2><p>Semáforo: cumple la meta, en riesgo (hasta 10 % peor que la meta) o incumple. No hay una corrida anterior. La variación se mide contra la línea base registrada para este mismo periodo, por eso aparece sin cambios.</p>')
for f,nm in [("A","A · Accesibilidad"),("B","B · Eficiencia"),("C","C · Efectividad"),("D","D · Experiencia del cliente"),("E","E · Impacto en negocio")]:
    P.append(f'<h3>{nm}</h3>{fam_cards(f)}')
P.append('<div class="nota">Dos lecturas difieren de la línea base. La reincidencia (5,6 %) queda en rojo, no en amarillo, porque supera en 12 % la meta de 5 %. El ACW medio (37,6 s) no figuraba en la línea base y incumple la meta de 30 s.</div></section>')

# A
P.append(f'''<section id="A"><h2>A · Accesibilidad: ¿nos pueden contactar?</h2>
<p><b>Qué mide.</b> Cuántas llamadas se pierden y cuánto espera quien sí es atendido. Abandono y nivel de servicio miran a todas las llamadas. ASA mira solo a las atendidas.</p>
{fam_cards("A")}
<h3>Qué pasa</h3>
<p>El abandono es {pc(K["A2"]["valor"])} (meta 8 %) y el nivel de servicio {pc(K["A3"]["valor"])} (meta 80 %). El ASA es {n(K["A4"]["valor"])} s, apenas sobre la meta de 20 s.</p>
<p>La tendencia semanal mejora despacio: el abandono pasó de {pc(t["abandono"][0])} a {pc(t["abandono"][-1])} en siete semanas completas. La semana del 7 de septiembre marcó el máximo ({pc(max(t["abandono"]))}). No hay ninguna semana en meta.</p>
{img("01_tendencia_semanal.png","Tendencia semanal de abandono, FCR y CSAT (7 semanas completas)")}
<h3>Dónde se concentra</h3>
<p>Las franjas de {picos} concentran {pc(D["share_ab_picos"],0)} de los abandonos con {pc(D["share_vol_picos"],0)} del volumen. En esas horas el abandono es {pc(D["ab_picos"])} y fuera de ellas {pc(D["ab_resto"])}.</p>
<p>La espera media de las llamadas atendidas sube de {n(D["espera_resto_at"])} s a {n(D["espera_picos_at"])} s en esas franjas. El nivel de servicio cae de {pc(D["ns_resto"])} a {pc(D["ns_picos"])}.</p>
{img("02_curva_intradia.png","Volumen de llamadas y abandono por hora. En dorado, las tres franjas pico.")}
<p>El problema no depende de la cola ({pc(min(D["ab_cola"].values()))} a {pc(max(D["ab_cola"].values()))}) ni del motivo ({pc(min(D["ab_motivo"].values()))} a {pc(max(D["ab_motivo"].values()))}). Los días de la semana tampoco difieren mucho. El martes es el más alto ({pc(D["ab_dow"]["Tuesday"])}); el resto va de {pc(min(v for k,v in D["ab_dow"].items() if k!="Tuesday"))} a {pc(max(v for k,v in D["ab_dow"].items() if k!="Tuesday"))}.</p>
<p>Quien abandona lo hace pronto: {pc(X["ab_menos20"]*100,0)} cuelga antes de 20 s, {pc(X["ab_20_60"]*100,0)} entre 21 y 60 s y {pc(X["ab_mas60"]*100,0)} después de 60 s. El tiempo medio hasta colgar es {n(K["A5"]["valor"])} s.</p>
<h3>Posibles causas</h3><ul class="causas">
<li>{E(f"Desajuste de capacidad en las franjas pico: volumen, espera y abandono suben a la vez.")}</li>
<li>{E(f"Hay también una brecha fuera de los picos: el abandono base de {pc(D['ab_resto'])} sigue sobre la meta. El problema es de capacidad general, no solo de picos.")}</li>
<li>{H(f"Los turnos no siguen la curva de demanda. Con la carga observada, un cálculo Erlang C para 80/20 pide unos {agentes_h(11)} agentes simultáneos a las 11 h, {agentes_h(12)} a las 12 h y las 20 h, y {agentes_h(14)} entre las 14 y las 18 h. Lo confirma la malla de turnos real, que no está en los archivos.")}</li>
<li>{H(f"El {pc(X['ab_menos20']*100,0)} de abandonos antes de 20 s sugiere un mensaje de bienvenida largo o un IVR confuso. Lo confirmaría la duración del mensaje inicial y el punto del menú donde cuelgan.")}</li></ul>
<h3>Impacto</h3>
<p>{n(X["n_ab"],0)} contactos no fueron atendidos. Entre quienes sí fueron atendidos, la espera no cambia el CSAT (ver sección D). El costo del abandono es contacto perdido, no insatisfacción de quien espera. Si los picos bajaran al nivel del resto del día, el abandono total sería ≈ {pc(D["ab_sim_picos"])}. Supuesto: el resto del día no cambia.</p>
</section>''')

# B
P.append(f'''<section id="B"><h2>B · Eficiencia: ¿cuánto cuesta atender?</h2>
<p><b>Qué mide.</b> Cuánto dura cada gestión, cuánto trabajo queda después de colgar y cuántas llamadas el agente no puede cerrar solo.</p>
{fam_cards("B")}
<h3>Qué pasa</h3>
<p>El AHT es {n(K["B1"]["valor"],0)} s, dentro del rango de 240 a 360 s (mediana {n(X["aht_mediana"],0)} s). El ACW es {n(K["B2"]["valor"])} s y supera la meta de 30 s. El escalamiento es {pc(K["B3"]["valor"])}, más del doble de la meta de 15 %.</p>
<p>El escalamiento no tiene tendencia: se mueve entre {pc(min(t["esc"]))} y {pc(max(t["esc"]))} semana a semana. Se reparte casi por igual entre Logística ({n(X["esc_destino_n"]["Area_Logistica"] if "esc_destino_n" in X else D["esc_destino_n"]["Area_Logistica"],0)}), Billing ({n(D["esc_destino_n"]["Area_Billing"],0)}) y Supervisor ({n(D["esc_destino_n"]["Supervisor"],0)}).</p>
<h3>Dónde se concentra</h3>
<p>En ninguna parte. Es uniforme por motivo ({pc(D["esc_motivo_rango"][0])} a {pc(D["esc_motivo_rango"][1])}), por cola ({pc(D["esc_cola_rango"][0])} a {pc(D["esc_cola_rango"][1])}) y por agente ({pc(AG["esc_min"])} a {pc(AG["esc_max"])}).</p>
<div class="dos">{img("10_escalamiento_motivo.png","Escalamiento por motivo (%)")}{img("09_motivo_destino.png","Destino del escalamiento por motivo")}</div>
<p>La carga por agente está equilibrada: entre {n(AG["att_min"],0)} y {n(AG["att_max"],0)} llamadas atendidas cada uno (media {n(K["B4"]["valor"],0)}).</p>
<h3>Enrutamiento: ¿cada motivo llega a su cola?</h3>
{img("06_heatmap_cola_motivo.png","Mezcla de motivos dentro de cada cola (% de la cola)")}
<p>Las cuatro colas reciben casi la misma mezcla de motivos: la diferencia máxima entre colas para un mismo motivo es {n(D["cola_motivo_max_diff"])} pp. Información preventa es {pc(D["ventas_pct_preventa"])} de lo que atiende Ventas y reclamo de calidad es {pc(D["retenc_pct_reclamo"])} de lo que atiende Retenciones. El {pc(D["envio_en_ret_ventas"],0)} de las llamadas de estado de envío cae en Retenciones o Ventas.</p>
<h3>Posibles causas</h3><ul class="causas">
<li>{E("Las colas no están especializadas: el motivo no predice la cola. Es consistente con un IVR o reglas de enrutamiento que no usan el motivo.")}</li>
<li>{H("El menú del IVR no separa los motivos o el cliente elige la opción al azar. Lo confirmaría el diseño actual del menú y el porcentaje de transferencias entre colas, que no está en los archivos.")}</li>
<li>{E(f"Un escalamiento tan parejo indica que no depende del tipo de caso. Si fueran casos complejos, variaría por motivo.")}</li>
<li>{H("Los agentes tienen facultades limitadas o una política que obliga a derivar. Lo confirmaría la matriz de autonomía vigente y una muestra de casos escalados que el agente podía resolver.")}</li>
<li>{E(f"El destino no sigue al motivo. Solo {pc(D['destino_esperado_pct'],0)} de los escalamientos de envío, devolución, cambio, pago y facturación llega al área esperada; al azar serían {pc(D['destino_esperado_azar'],0)}. El {pc(D['envio_a_billing_pct'],0)} de los de estado de envío va a Billing y el {pc(D['pago_a_logistica_pct'],0)} de los de pago va a Logística.")}</li>
<li>{H("La tipificación del motivo o las reglas de derivación están mal definidas. Lo confirmaría revisar cómo el agente elige el destino en el sistema.")}</li>
<li>{H(f"El ACW alto puede venir de notas manuales o de cerrar el caso en varios sistemas. El exceso sobre 30 s equivale a unas {n(D['acw_horas_exceso'],0)} horas de agente en el periodo.")}</li></ul>
<h3>Impacto</h3>
<p>El escalamiento es la palanca más fuerte sobre el CSAT (sección D). El AHT no es un problema: bajarlo no es prioridad.</p>
</section>''')

# C
fcr_tab = "".join(f"<tr><td>{ETQ[m]}</td><td>{n(D['casos_motivo'][m],0)}</td><td>{pc(fcr_m[m])}</td><td>{pc(reinc_m[m])}</td><td>{pc(D['pend_motivo'][m])}</td></tr>" for m in sorted(fcr_m, key=lambda x: fcr_m[x]))
P.append(f'''<section id="C"><h2>C · Efectividad: ¿resolvemos?</h2>
<p><b>Qué mide.</b> Si el cliente queda resuelto en el primer contacto, si vuelve por lo mismo y cuántos casos siguen abiertos. En los datos, reincidencia y reapertura son idénticas ({n(X["c3_n"],0)} casos), así que se reportan como un solo indicador.</p>
{fam_cards("C")}
<h3>Qué pasa</h3>
<p>El FCR es {pc(K["C1"]["valor"])} (meta 75 %) y ninguna semana completa llega a la meta (entre {pc(min(t["fcr"]))} y {pc(max(t["fcr"]))}). La reincidencia es {pc(K["C2"]["valor"])}. El backlog es {pc(K["C4"]["valor"])}: {n(X["c4_n"],0)} casos pendientes.</p>
<p>El tiempo medio de resolución es {n(K["C5"]["valor"])} h y cumple, pero {pc(X["c5_gt24"])} de los casos pasa de 24 h. En promedio cada cliente llamó {n(D["llamadas_por_cliente_media"])} veces; {pc(K["C6"]["valor"],0)} llamó tres veces o más.</p>
<h3>Dónde se concentra</h3>
{img("03_fcr_csat_motivo.png","FCR y CSAT por motivo")}
<div class="tw"><table><tr><th>Motivo</th><th>Casos</th><th>FCR</th><th>Reincidencia</th><th>Pendiente</th></tr>{fcr_tab}</table></div>
<p>Tres motivos quedan bajo la meta con holgura: reclamo de calidad, cambio de producto y devolución. Reclamo y cambio también reinciden cerca de 10 %. El backlog, en cambio, es parejo ({pc(min(D["pend_motivo"].values()))} a {pc(max(D["pend_motivo"].values()))}).</p>
<h3>Posibles causas</h3><ul class="causas">
<li>{E("El FCR bajo se concentra en los motivos que suelen requerir autorización, logística o cambio de política: reclamo, cambio y devolución.")}</li>
<li>{H("Los agentes no tienen guía de resolución ni facultad para aprobar estos casos en la llamada. Lo confirmaría revisar el guion y la política de cada motivo.")}</li>
<li>{E(f"El FCR no distingue escalados: {pc(D['fcr_esc'])} de los casos escalados figura como resuelto al primer contacto, igual que {pc(D['fcr_no_esc'])} de los no escalados. Su CSAT no mejora con FCR ({n(D['fcr_esc_x']['esc1_fcr0'],2)} sin FCR contra {n(D['fcr_esc_x']['esc1_fcr1'],2)} con FCR).")}</li>
<li>{H("El FCR está sobreestimado porque el agente lo marca antes de saber si el caso se derivó. Lo confirmaría una definición escrita del campo y cómo se llena.")}</li>
<li>{E(f"{n(D['pend_fcr1'],0)} de los {n(X['c4_n'],0)} casos pendientes figuran con FCR = 1, lo cual es contradictorio.")}</li>
<li>{H("El backlog parejo en todos los motivos apunta a falta de seguimiento o de SLA en el cierre, no a un tipo de caso. Lo confirmaría la antigüedad real de cada pendiente, que no está en los datos.")}</li></ul>
<h3>Impacto</h3>
<p>Si reclamo de calidad y cambio de producto llegaran a 75 % de FCR, el FCR global sería ≈ {pc(D["fcr_sim_2motivos"])}. Con devolución también, ≈ {pc(D["fcr_sim_3motivos"])}. Supuesto: el resto de motivos se mantiene.</p>
<p>Contactos repetidos no cambia el CSAT: {n(D["csat_repetidos"],2)} en clientes con tres llamadas o más y {n(D["csat_no_repetidos"],2)} en el resto. Por eso es un dato informativo.</p>
</section>''')

# D
dist = D["csat_dist"]; tot = sum(dist.values())
P.append(f'''<section id="D"><h2>D · Experiencia del cliente</h2>
<p><b>Qué mide.</b> Qué tan satisfecho queda el cliente tras el caso, en escala de 1 a 5. El top-2 box cuenta notas 4 y 5. Insatisfecho es una nota de 1 o 2.</p>
{fam_cards("D")}
<h3>Qué pasa</h3>
<p>El CSAT promedio es {n(K["D1"]["valor"],2)} (meta 4,0). Solo {pc(K["D2"]["valor"])} da 4 o 5 y {pc(K["D3"]["valor"])} da 1 o 2. La tendencia es estable: entre {n(min(t["csat"]),2)} y {n(max(t["csat"]),2)} por semana, con una mejora leve desde la primera.</p>
<div class="dos">{img("05_distribucion_csat.png","Distribución del CSAT (% de casos)")}{img("04_csat_escalado.png","CSAT según escalamiento")}</div>
<h3>Dónde se concentra</h3>
<p>En los casos escalados. {pc(D["insat_esc"])} de ellos queda insatisfecho, contra {pc(D["insat_no_esc"])} de los no escalados. Aunque escalan {pc(D["p_esc_tickets"]*100,0)} de los casos, concentran {pc(D["riesgo_esc_pct"],0)} de los casos en riesgo.</p>
<p>Entre los no escalados, el FCR sube el CSAT de {n(D["fcr_esc_x"]["esc0_fcr0"],2)} a {n(D["fcr_esc_x"]["esc0_fcr1"],2)}. En los escalados no cambia ({n(D["fcr_esc_x"]["esc1_fcr0"],2)} y {n(D["fcr_esc_x"]["esc1_fcr1"],2)}).</p>
<div class="dos">{img("08_csat_espera.png","CSAT según tramo de espera")}{img("07_ranking_agentes.png","CSAT y FCR por agente. Línea dorada: media del equipo.")}</div>
<p>Por motivo, el más bajo es reclamo de calidad ({n(D["csat_motivo"]["reclamo_calidad"],2)}) y el más alto información preventa ({n(D["csat_motivo"]["informacion_preventa"],2)}). Entre agentes el CSAT va de {n(AG["csat_min"],2)} a {n(AG["csat_max"],2)}.</p>
<h3>Posibles causas</h3><ul class="causas">
<li>{E(f"El escalamiento explica la mayor brecha: {n(D['csat_no_esc'],2)} contra {n(D['csat_esc'],2)}.")}</li>
<li>{E(f"El escalamiento no alarga la resolución: {n(D['horas_esc']['Escalado'])} h en escalados y {n(D['horas_esc']['No escalado'])} h en los demás. La caída de CSAT no viene del tiempo total.")}</li>
<li>{H("El cliente califica mal la experiencia de ser derivado: repetir su caso, esperar respuesta de otra área o no tener seguimiento. Lo confirmarían el número de transferencias por caso y el tiempo de respuesta del área destino.")}</li>
<li>{E(f"La espera no mueve el CSAT: {n(D['csat_espera']['0-20 s'],2)} con espera de hasta 20 s y {n(D['csat_espera']['>120 s'],2)} con más de 120 s. La prioridad es resolver, no solo contestar rápido.")}</li>
<li>{E(f"Los agentes son homogéneos (desviación estándar del CSAT {n(AG['csat_sd'],2)}). No hay agentes que justifiquen una intervención individual.")}</li></ul>
<h3>Impacto</h3>
<p>Si el escalamiento bajara a 25 %, el CSAT subiría a ≈ {n(D["csat_meta25"],2)} y los insatisfechos bajarían a ≈ {pc(D["insat_meta25"])}. Con 15 %: CSAT ≈ {n(D["csat_meta15"],2)} e insatisfechos ≈ {pc(D["insat_meta15"])}. Supuesto: los casos que dejan de escalarse logran el CSAT de los no escalados actuales ({n(D["csat_no_esc"],2)}).</p>
<p>Ni así se llega a 4,0, porque los no escalados promedian {n(D["csat_no_esc"],2)}. La meta pide mejorar también la resolución de los casos que no escalan.</p>
</section>''')

# E
vm = D["valor_motivo"]
vt = "".join(f"<tr><td>{ETQ[m]}</td><td>{n(vm[m]['total'],0)}</td><td>{n(vm[m]['riesgo'],0)}</td><td>{pc(vm[m]['pct'])}</td><td>{n(vm[m]['pend'],0)}</td></tr>" for m in sorted(vm, key=lambda x: -vm[x]["riesgo"]))
P.append(f'''<section id="E"><h2>E · Impacto en negocio</h2>
<p><b>Qué mide.</b> Cuánto valor de órdenes está asociado a casos con mala experiencia o sin cerrar. El valor está en la moneda del negocio.</p>
{fam_cards("E")}
<h3>Qué pasa</h3>
<p>El valor en riesgo (CSAT ≤ 2 o caso reabierto) es {n(K["E1"]["valor"],0)}: {pc(X["e1_pct"])} del valor total de {n(valor_t,0)}. Son {n(D["riesgo_n"],0)} casos y {pc(D["riesgo_esc_pct"],0)} de ellos fue escalado. Si solo se cuenta CSAT ≤ 2, el valor es {n(X["e1_solo_csat"],0)} ({pc(X["e1_solo_csat_pct"])}), la cifra de la línea base.</p>
<p>Los casos pendientes suman {n(K["E2"]["valor"],0)} ({pc(X["e2_pct"])} del total), con un valor medio de {n(D["pend_valor_medio"],0)} por caso.</p>
<h3>Dónde se concentra</h3>
<div class="tw"><table><tr><th>Motivo</th><th>Valor total</th><th>Valor en riesgo</th><th>% en riesgo</th><th>Valor pendiente</th></tr>{vt}</table></div>
<p>En valor absoluto pesan más estado de envío y devolución, por volumen. En proporción, reclamo de calidad ({pc(vm["reclamo_calidad"]["pct"])}) y cambio de producto ({pc(vm["cambio_producto"]["pct"])}) tienen el mayor riesgo.</p>
<h3>Causas e impacto</h3><ul class="causas">
<li>{E("El valor en riesgo sigue al escalamiento y a los motivos de bajo FCR, tal como muestran las secciones C y D.")}</li>
<li>{E(f"Los casos en riesgo no son más caros que el resto: valor medio {n(D['valor_medio_csat12'],0)} contra {n(D['valor_medio_resto'],0)}. El riesgo es por cantidad de casos, no por órdenes grandes.")}</li>
<li>{H("Parte de este valor puede ser recuperable con seguimiento proactivo. Lo confirmaría el porcentaje de clientes que compra de nuevo tras un CSAT bajo, dato que no está en los archivos.")}</li></ul>
</section>''')

# Plan
plan = [
 ("Fijar reglas de destino del escalamiento por motivo (envío, devolución y cambio a Logística; pago y facturación a Billing; Supervisor solo por excepción).","Escalamiento al área equivocada: solo 35 % llega al destino esperado.","Jefe de operaciones y Calidad","Bajo","Menos rebotes entre áreas y menor tiempo de respuesta en escalados.","% de escalamientos al destino esperado de 35 % a 90 % o más. CSAT de escalados cada semana."),
 ("Corregir el enrutamiento del IVR: preventa a Ventas, reclamo de calidad a Retenciones, envíos a Soporte_Envios.","Mezcla idéntica de motivos en todas las colas.","Operaciones y TI telefonía","Bajo a medio","Colas especializadas, menos transferencias y mejor uso de la capacidad.","Mezcla de motivos por cola. Preventa en Ventas de 16 % a más de 80 %."),
 ("Registrar el ticket en todas las llamadas atendidas y fijar una definición de FCR que excluya casos escalados.","14,7 % de atendidas sin ticket. FCR no distingue escalados y 1.278 pendientes figuran con FCR = 1.","BI y Operaciones","Bajo","Indicadores más fiables en la próxima corrida.","Atendidas sin ticket igual a 0 %. Pendientes con FCR = 1 igual a 0."),
 ("Activar devolución de llamada o mensaje de espera con tiempo estimado a partir de 20 s, en las franjas de 11–12 h y 20 h.","46 % de los abandonos ocurre entre 21 y 60 s.","Operaciones y TI telefonía","Medio","Recuperar parte de los contactos perdidos. Efecto por estimar tras un piloto.","Abandono en franjas pico. Llamadas recuperadas por devolución."),
 ("Entregar una matriz de autonomía: qué puede resolver el agente sin escalar en devolución, cambio, pago y facturación.","Escalamiento de 37,7 % uniforme en todos los motivos.","Jefe de operaciones, Logística y Billing","Medio","Con escalamiento en 25 %, CSAT ≈ " + n(D["csat_meta25"],2) + " e insatisfechos ≈ " + pc(D["insat_meta25"]) + ". Con 15 %, CSAT ≈ " + n(D["csat_meta15"],2) + ".","Escalamiento semanal (B3). CSAT escalado y no escalado. Meta intermedia: 25 % en 60 días."),
 ("Rebalancear turnos: " + str(agentes_h(11)) + " agentes simultáneos a las 11 h y " + str(agentes_h(12)) + " a las 12 h y 20 h, según cálculo Erlang C. Contrastar con la malla actual y mover horas desde 14–18 h.","Abandono de 18,8 % en franjas pico y base de 11,9 % fuera de ellas.","Planificación de turnos","Medio","Abandono total hacia ≈ " + pc(D["ab_sim_picos"]) + " si los picos igualan al resto del día.","Abandono y nivel de servicio por hora (A2, A3). Meta: 8 % y 80 %."),
 ("Crear guías de resolución para reclamo de calidad, cambio de producto y devolución, con criterios de aprobación en la llamada.","FCR de 45 %, 56 % y 63 %. Reincidencia cercana a 10 % en reclamo y cambio.","Capacitación y Calidad","Medio","FCR global ≈ " + pc(D["fcr_sim_2motivos"]) + " con reclamo y cambio en 75 %, y ≈ " + pc(D["fcr_sim_3motivos"]) + " con devolución.","FCR y reincidencia por motivo (C1, C2)."),
 ("Plan de limpieza del backlog: cerrar " + n(D["backlog_a_cerrar"],0) + " casos pendientes, priorizados por valor y antigüedad, y fijar un SLA de cierre.","Backlog de 14,4 % (" + n(X["c4_n"],0) + " casos, " + n(K["E2"]["valor"],0) + " en valor).","Jefe de operaciones","Medio","Backlog en 10 % (" + n(D["backlog_objetivo_n"],0) + " casos). Menos valor expuesto.","Backlog semanal (C4) y valor pendiente (E2)."),
 ("Revisar el cierre post-llamada: plantillas de notas y menos pantallas.","ACW de 37,6 s contra meta de 30 s.","Operaciones y Calidad","Bajo a medio","Unas " + n(D["acw_horas_exceso"],0) + " horas de agente liberadas en un periodo similar.","ACW medio (B2) igual o menor a 30 s."),
]
P.append('<section id="plan"><h2>Plan de acción</h2><p>Las tres primeras acciones son de bajo esfuerzo y se pueden hacer ya. Los efectos son estimaciones con los supuestos indicados en cada sección.</p><div class="tw"><table><tr><th>Acción</th><th>Problema que ataca</th><th>Responsable sugerido</th><th>Esfuerzo</th><th>Impacto esperado</th><th>Cómo medir el éxito</th></tr>')
for a in plan: P.append("<tr>" + "".join(f"<td>{html.escape(x)}</td>" for x in a) + "</tr>")
P.append('</table></div><h3>Top 3 de prioridades</h3><div class="top3">')
for i,(a,b) in enumerate(top3,1): P.append(f'<div><span class="num">{i}</span><b>{a}</b>{b}</div>')
P.append('</div></section>')

# Calidad
sem_rows = "".join(f"<tr><td>{s['semana']}</td><td>{s['desde']} a {s['hasta']}</td><td>{s['dias']}</td><td>{n(s['llamadas'],0)}</td><td>{'Completa' if s['completa'] else 'Incompleta'}</td></tr>" for s in Q["semanas"])
P.append(f'''<section id="calidad"><h2>Calidad de datos y notas metodológicas</h2>
<h3>Calidad de datos</h3>
<div class="tw"><table><tr><th>Control</th><th>Resultado</th></tr>
<tr><td>Esquema</td><td>Coincide con el esperado. No hay columnas nuevas ni faltantes.</td></tr>
<tr><td>Filas y rango</td><td>CDR: {n(Q["filas_cdr"],0)} filas. Tickets: {n(Q["filas_tickets"],0)} filas. Ambos del {Q["rango_cdr"][0]} al {Q["rango_cdr"][1]}.</td></tr>
<tr><td>Duplicados</td><td>Ninguno en id_llamada, id_caso ni en tickets por llamada.</td></tr>
<tr><td>Nulos</td><td>Solo los esperados: id_agente en las {n(Q["nulos_cdr"]["id_agente"],0)} abandonadas y escalado_a en las no escaladas. Tickets sin nulos.</td></tr>
<tr><td>Integridad CDR–tickets</td><td>Ningún ticket sin llamada y ninguno de una abandonada. Agente, cliente y categoría coinciden en todos.</td></tr>
<tr><td><b>Atendidas sin ticket</b></td><td><b>{n(sin_ticket,0)} llamadas ({pc(pct_sin)}).</b> Se reparten parejo por cola, motivo y escalamiento. Los KPI de las familias C, D y E cubren {pc(X["cobertura_tickets"]*100,0)} de las atendidas.</td></tr>
<tr><td>Rangos</td><td>CSAT siempre entre 1 y 5. Sin tiempos negativos. Espera máxima {n(Q["espera_max"],0)} s, sin esperas sobre 600 s. {Q["horas_resolucion_cero"]} casos con 0 h de resolución.</td></tr>
<tr><td><b>Llamadas salientes</b></td><td>Hay {n(Q["salientes"],0)} salientes con espera y {n(Q["salientes_abandonadas"],0)} abandonadas, lo cual es raro en llamadas que inicia el agente. Se incluyen en A2 a A5 como pide el catálogo. El abandono de las entrantes es {pc(X["ab_entrante"])}.</td></tr>
<tr><td><b>Pendientes con FCR = 1</b></td><td>{n(Q["pendientes_con_fcr1"],0)} de {n(Q["pendientes"],0)} pendientes. Reincidencia y reapertura coinciden al 100 %, por lo que se cuentan una vez (C2).</td></tr>
<tr><td>Horas de resolución de pendientes</td><td>Los pendientes tienen horas registradas ({n(D["pend_horas"])} h en promedio) aunque no están cerrados. Esas horas no son una resolución real.</td></tr></table></div>
<h3>Semanas del periodo</h3>
<p>Las tendencias usan solo semanas completas (7 días). Se excluyen la semana del 24 de agosto (empieza el martes 25) y la del 19 de octubre (termina el viernes 23).</p>
<div class="tw"><table><tr><th>Semana (lunes)</th><th>Rango con datos</th><th>Días</th><th>Llamadas</th><th>Estado</th></tr>{sem_rows}</table></div>
<h3>Notas metodológicas</h3>
<ul class="causas">
<li>Nivel de servicio: llamadas con espera de 20 s o menos sobre el total, incluidas las abandonadas.</li>
<li>AHT: duración más ACW de las llamadas atendidas. ASA: espera media de las atendidas.</li>
<li>Semáforo: se evalúa con un decimal. En amarillo, hasta 10 % peor que la meta. Se usan las metas de referencia de industria, porque Recursos no incluye metas propias de Cesta.</li>
<li>Valor en riesgo: suma del valor de orden de casos con CSAT ≤ 2 o reabiertos, sin duplicar casos.</li>
<li>Dimensionamiento: Erlang C con la media de llamadas por hora (todos los días, {D["dias"]} días calendario), AHT medio y objetivo 80/20. Es una referencia aproximada: no considera ausentismo ni pausas.</li>
<li>Agentes: se señala solo a quien se aleja más de 1,5 desviaciones estándar en varios KPI. AG-002 cumple el criterio en dos indicadores (FCR bajo y reincidencia alta) y AG-018 en otros dos (AHT alto y CSAT bajo), pero las diferencias absolutas son pequeñas. No se recomienda acción individual.</li>
<li>Los gráficos de tendencia usan un eje recortado para mostrar variación. Los de agentes parten de cero.</li>
<li>Reproducible: <code>calculo_kpis.py</code> calcula y <code>generar_informe.py</code> arma este archivo.</li></ul>
</section></main>
<footer><div class="wrap">Cesta · Informe de indicadores del call center · Corrida del 10 de noviembre de 2026</div></footer></body></html>''')
open(os.path.join(OUT, "informe_kpis.html"), "w", encoding="utf-8").write("".join(P))
# Narrativa para reutilizar en el dashboard interactivo
json.dump({"hallazgos": hall, "top3": [{"titulo": a, "detalle": b} for a,b in top3],
           "plan": [dict(zip(["accion","problema","responsable","esfuerzo","impacto","medicion"], row)) for row in plan]},
          open(os.path.join(OUT, "narrativa.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("OK", os.path.getsize(os.path.join(OUT, "informe_kpis.html")))
