"""Dash front-end over the committed pipeline artefacts.

    python apps/dash_app.py            # http://127.0.0.1:8767
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from dash import Dash, Input, Output, dash_table, dcc, html

import common as c

ANSWERS = c.answers()
METRICS = c.metrics()
THEMES = list(dict.fromkeys(a["theme"] for a in ANSWERS))

app = Dash(__name__, title="Food Systems Explorer · Dash")
FRAME = {"width": "100%", "height": "620px", "border": "0", "background": "#fcfcfb"}


def kpi_tiles():
    k = c.kpis()
    tiles = [
        ("World cereal production", f"{k.get('production_mt_latest', 0):,.0f} Mt", str(k.get("latest_year", ""))),
        ("Undernourishment (PoU)", f"{k.get('world_pou_latest', 0):.1f} %", f"{k.get('world_undernourished_m', 0):,.0f} million people"),
        ("Cannot afford a healthy diet", f"{k.get('world_unaffordable_pct', 0):.1f} %", f"{k.get('world_unaffordable_m', 0):,.0f} million people"),
        ("Agrifood-system emissions", f"{k.get('world_agrifood_gt', 0):.1f} Gt CO2eq", f"{k.get('world_agrifood_share', 0):.0f} % of all emissions"),
        ("Land temperature change", f"{k.get('world_temp_change_5yr', 0):+.2f} °C", "5-year mean vs 1951-80"),
        ("World nitrogen intensity", f"{k.get('world_n_kg_ha', 0):.0f} kg N/ha", "of cropland"),
    ]
    return html.Div([html.Div([html.Div(t, className="label"), html.Div(v, className="value"), html.Div(s, className="sub")], className="tile")
                     for t, v, s in tiles], className="tiles")


def tab_overview():
    return html.Div([
        kpi_tiles(),
        html.Div([html.Iframe(srcDoc=c.figure_html("q01_global_cereal_production"), style=FRAME),
                  html.Iframe(srcDoc=c.figure_html("q08_pou_by_region"), style=FRAME)], className="two"),
        html.P(["Full interactive dashboard with filters, maps and the explorer: ", html.A(c.PAGES_URL, href=c.PAGES_URL, target="_blank")]),
    ])


def tab_questions():
    return html.Div([
        html.Div([
            html.Label("Theme"), dcc.Dropdown(id="theme", options=THEMES, value=THEMES[0], clearable=False, style={"minWidth": "260px"}),
            html.Label("Question"), dcc.Dropdown(id="question", clearable=False, style={"minWidth": "520px", "flex": "1"}),
        ], className="controls"),
        html.Div(id="question-body"),
    ])


def tab_predictions():
    yf, rc, ty, pj = METRICS["yield_forecast"], METRICS["risk_classifier"], METRICS["typology"], METRICS["projections"]
    scorecard = pd.DataFrame([
        {"model": yf["best"], "task": yf["task"], "test size": yf["n_test"], "metrics": f"MAE {yf['models'][yf['best']]['mae']:.3f} t/ha · R² {yf['models'][yf['best']]['r2']:.3f} · persistence MAE {yf['models']['Persistence (last year)']['mae']:.3f}"},
        {"model": rc["best"], "task": rc["task"], "test size": rc["n_test"], "metrics": f"ROC-AUC {rc['models'][rc['best']]['roc_auc']:.3f} · PR-AUC {rc['models'][rc['best']]['pr_auc']:.3f} · F1 {rc['models'][rc['best']]['f1']:.3f}"},
        {"model": f"k-means (k = {ty['k']})", "task": ty["task"], "test size": ty["n_countries"], "metrics": "silhouette " + ", ".join(f"k{k}: {v:.2f}" for k, v in ty["silhouette_by_k"].items())},
        {"model": "log-linear trend", "task": pj["task"], "test size": "-", "metrics": " · ".join(f"{r} {v['trend_pct_per_year']:+.1f} %/yr" for r, v in pj["regions"].items())},
    ])
    fc = c.table("yield_forecast_next_year"); fc = fc[fc.cereal_area_ha >= 5e5].sort_values("change_pct", ascending=False).round(2)
    risk = c.table("risk_scores_latest").round(3)
    return html.Div([
        html.Div(METRICS["intended_use"], className="note"),
        dash_table.DataTable(scorecard.to_dict("records"), [{"name": i, "id": i} for i in scorecard.columns], style_cell={"textAlign": "left", "whiteSpace": "normal", "fontSize": 13}, style_as_list_view=True),
        html.Div([html.Iframe(srcDoc=c.figure_html("ml_yield_forecast"), style=FRAME), html.Iframe(srcDoc=c.figure_html("ml_risk_classifier"), style=FRAME)], className="two"),
        html.Div([html.Iframe(srcDoc=c.figure_html("ml_typology"), style=FRAME), html.Iframe(srcDoc=c.figure_html("ml_projections"), style=FRAME)], className="two"),
        html.Div([
            html.Div([html.H4(f"Next-year yield forecast ({yf['forecast_year']}, producers ≥ 500 kha)"),
                      dash_table.DataTable(fc.to_dict("records"), [{"name": i, "id": i} for i in fc.columns], page_size=15, sort_action="native", filter_action="native", style_cell={"textAlign": "left", "fontSize": 13})]),
            html.Div([html.H4("Undernourishment risk score (latest)"),
                      dash_table.DataTable(risk.to_dict("records"), [{"name": i, "id": i} for i in risk.columns], page_size=15, sort_action="native", filter_action="native", style_cell={"textAlign": "left", "fontSize": 13})]),
        ], className="two"),
        html.P(["Model card: ", html.A("models/MODEL_CARD.md", href=f"{c.REPO_URL}/blob/main/models/MODEL_CARD.md", target="_blank")]),
    ])


def tab_notebook():
    return html.Div([
        html.P("The executed analysis notebook: warehouse, all 35 questions with SQL, figures and findings, the four models and the dashboard. "
               "It calls the same functions the pipeline runs."),
        html.Div([html.A(label, href=url, target="_blank", className="btn") for label, url in c.NOTEBOOK_LINKS.items()], className="controls"),
        html.Iframe(srcDoc=c.notebook_html(), style={**FRAME, "height": "1400px", "background": "#fff"}),
    ])


def tab_data():
    dom, dq = c.provenance()
    pins = c.pins()
    children = [html.H4("Reviewed FAO release hashes (data/reference/archive_pins.json)"),
                dash_table.DataTable(pins.to_dict("records"), [{"name": i, "id": i} for i in pins.columns], style_cell={"textAlign": "left", "fontSize": 12})]
    if dom is not None:
        children += [html.H4("Loaded domains (dim_domain)"),
                     dash_table.DataTable(dom.to_dict("records"), [{"name": i, "id": i} for i in dom.columns], style_cell={"textAlign": "left", "fontSize": 12}),
                     html.H4("Quality gate (latest run)"),
                     dash_table.DataTable(dq.to_dict("records"), [{"name": i, "id": i} for i in dq.columns], style_cell={"textAlign": "left", "fontSize": 12, "whiteSpace": "normal"},
                                          style_data_conditional=[{"if": {"filter_query": "{status} = fail"}, "color": "#d03b3b"}, {"if": {"filter_query": "{status} = warn"}, "color": "#b7791f"}])]
    else:
        children.append(html.P("Warehouse not present locally (data/faostat.db); run the pipeline to see load statistics and the quality gate."))
    children.append(html.Iframe(srcDoc=c.figure_html("q32_data_provenance"), style=FRAME))
    return html.Div(children)


app.layout = html.Div([
    html.H1("Food Systems Explorer"),
    html.P(["FAOSTAT production, food security, inputs, land, climate, prices and predictive models · ",
            html.A("repository", href=c.REPO_URL, target="_blank"), " · ", html.A("static dashboard", href=c.PAGES_URL, target="_blank")], className="lede"),
    dcc.Tabs(id="tabs", value="overview", children=[
        dcc.Tab(label="Overview", value="overview"), dcc.Tab(label="Questions", value="questions"),
        dcc.Tab(label="Predictions", value="predictions"), dcc.Tab(label="Notebook", value="notebook"),
        dcc.Tab(label="Data & governance", value="data"),
    ]),
    html.Div(id="tab-body"),
], className="page")


@app.callback(Output("tab-body", "children"), Input("tabs", "value"))
def render_tab(tab):
    return {"overview": tab_overview, "questions": tab_questions, "predictions": tab_predictions, "notebook": tab_notebook, "data": tab_data}[tab]()


@app.callback(Output("question", "options"), Output("question", "value"), Input("theme", "value"))
def questions_for_theme(theme):
    opts = [{"label": f"{a['qid']}. {a['question']}", "value": a["slug"]} for a in ANSWERS if a["theme"] == theme]
    return opts, opts[0]["value"]


@app.callback(Output("question-body", "children"), Input("question", "value"))
def show_question(slug):
    a = next(x for x in ANSWERS if x["slug"] == slug)
    return html.Div([
        html.Iframe(srcDoc=c.figure_html(slug), style={**FRAME, "height": "680px"}),
        html.Ul([html.Li(f) for f in a["findings"]]),
        html.P([html.A("SQL", href=f"{c.REPO_URL}/blob/main/{a['sql_file']}", target="_blank"), " · ",
                html.A("result table", href=f"{c.REPO_URL}/blob/main/reports/{a['table_file']}", target="_blank")], className="small"),
    ])


app.index_string = """<!DOCTYPE html><html><head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
<style>
body{margin:0;background:#f5f7f2;color:#161d18;font:14px/1.5 Inter,"Helvetica Neue",Arial,sans-serif}
.page{max-width:1400px;margin:0 auto;padding:18px 16px 48px}
h1{margin:0;font-size:22px}.lede{color:#4f5852;margin:4px 0 12px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:14px 0}
.tile{background:#fbfcf9;border:1px solid #d6dbd2;border-radius:8px;padding:12px}
.tile .label{font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:#7d857f;font-weight:600}
.tile .value{font-size:24px;font-weight:650;margin-top:4px}.tile .sub{font-size:12px;color:#4f5852}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(460px,1fr));gap:14px;margin:14px 0}
.controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:12px 0}
.note{background:#e3efe7;border-radius:8px;padding:10px 14px;margin:10px 0;color:#4f5852}
.btn{border:1px solid #d6dbd2;background:#fbfcf9;border-radius:8px;padding:6px 10px;color:#161d18;text-decoration:none}
.small{font-size:12px;color:#7d857f}
</style></head><body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>"""

if __name__ == "__main__":
    app.run(debug=False, port=8767)
