#!/usr/bin/env python3
"""Genera dashboard_interactivo.html (autocontenido) a partir de resultados.json, narrativa.json y kpis_detalle.xlsx.
Uso: python3 generar_dashboard.py <carpeta_corrida> [plantilla.html]
La plantilla (plantilla_dashboard.html) vive junto al script y se reutiliza en cada corrida.
"""
import json, os, sys, datetime
import pandas as pd

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(os.path.abspath(__file__))
TPL = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "plantilla_dashboard.html")
R = json.load(open(os.path.join(OUT, "resultados.json"), encoding="utf-8"))
N = json.load(open(os.path.join(OUT, "narrativa.json"), encoding="utf-8"))
XL = os.path.join(OUT, "kpis_detalle.xlsx")

def clean(v):
    if v is None: return None
    if isinstance(v, (pd.Timestamp, datetime.date, datetime.datetime)): return str(v)[:10]
    if isinstance(v, float) and v != v: return None
    if hasattr(v, "item"): v = v.item()
    return v

def records(sheet):
    df = pd.read_excel(XL, sheet_name=sheet, index_col=0)
    df.index.name = "k"
    df = df.reset_index()
    return [{c: clean(v) for c, v in row.items()} for row in df.to_dict("records")]

def matrix(sheet):
    df = pd.read_excel(XL, sheet_name=sheet, index_col=0)
    return {"rows": [str(x) for x in df.index], "cols": [str(x) for x in df.columns],
            "values": [[clean(v) for v in r] for r in df.values.tolist()]}

tables = {k: records(k) for k in ["semana","dia_semana","hora","cola","tipo_llamada","motivo","escalamiento_destino","valor_por_motivo","agente","x_csat_escalado","x_csat_fcr","x_csat_espera"]}
mats = {k: matrix(k) for k in ["x_cola_x_motivo_pct","x_cola_x_motivo_n","x_motivo_x_destino_pct","x_motivo_x_destino_n","x_esc_cola_motivo","x_csat_cola_motivo","x_abandono_hora_cola"]}
dq = {k: v for k, v in R["dq"].items()}
data = {"kpis": R["kpis"], "extra": R["extra"], "dx": R["dx"], "dq": dq, "agente_info": R["agente"],
        "tables": tables, "mats": mats, "narrativa": N, "periodo": R["periodo"], "fecha": R["fecha_corrida"]}
html = open(TPL, encoding="utf-8").read()
assert "/*__DATA__*/null" in html, "La plantilla no tiene el marcador de datos"
html = html.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/"))
open(os.path.join(OUT, "dashboard_interactivo.html"), "w", encoding="utf-8").write(html)
print("OK", os.path.getsize(os.path.join(OUT, "dashboard_interactivo.html")))
