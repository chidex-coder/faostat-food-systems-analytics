"""Build and execute the analysis notebook.

notebooks/food_systems_analysis.ipynb walks through the warehouse, every one of
the 35 questions (SQL, figure, findings), the four models, and the dashboard.
Cells call the same functions the pipeline runs (src.analysis, src.ml), so the
notebook cannot drift from the reports.

Figures are displayed with the ``plotly_mimetype+png`` renderer: the PNG shows
on GitHub and in the static HTML export, the Plotly JSON gives the interactive
figure in Jupyter, JupyterLab, VS Code and nbviewer.

Outputs
-------
notebooks/food_systems_analysis.ipynb   executed notebook
docs/notebook.html                      static HTML export (PNG outputs only, no external scripts)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

from .analysis import HANDLERS, _sql
from .config import DOCS_DIR, ROOT

NOTEBOOKS_DIR = ROOT / "notebooks"
NOTEBOOK_PATH = NOTEBOOKS_DIR / "food_systems_analysis.ipynb"
NOTEBOOK_HTML = DOCS_DIR / "notebook.html"
DASHBOARD_URL = "https://chidex-coder.github.io/faostat-food-systems-analytics/"
REPO_URL = "https://github.com/chidex-coder/faostat-food-systems-analytics"

SETUP = '''import json, sqlite3, sys
from pathlib import Path

import pandas as pd
import plotly.io as pio
from IPython.display import HTML, IFrame, Markdown, display

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT))
from src import viz                       # registers the shared Plotly theme
from src.analysis import HANDLERS, _sql
from src.config import DB_PATH

pio.renderers.default = "plotly_mimetype+png"   # interactive in Jupyter, PNG on GitHub
pio.defaults.default_width = 1000
pio.defaults.default_height = 520
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 30)

con = sqlite3.connect(DB_PATH)


def answer(slug, show_table=True):
    """Run one question: SQL from sql/questions, the analysis handler, then figure + findings."""
    sql, question = _sql(slug)
    theme, handler = HANDLERS[slug]
    df = pd.read_sql_query(sql, con)
    fig, findings, numbers, *rest = handler(df)
    table = rest[0] if rest else df
    display(fig)
    display(Markdown("\\n".join(f"- {f}" for f in findings)))
    if show_table:
        display(table.head(12))
    return table

print(f"warehouse: {DB_PATH.relative_to(ROOT)} · {con.execute('SELECT COUNT(*) FROM observation').fetchone()[0]:,} observations")
'''

WAREHOUSE = '''domains = pd.read_sql_query("""SELECT domain, name, rows_raw, rows_loaded, rows_dropped_filter, rows_dropped_missing,
                                       rows_dropped_dupe, substr(sha256, 1, 12) AS sha256, catalogue_date_update
                                FROM dim_domain ORDER BY rows_loaded DESC""", con)
display(domains)

dq = pd.read_sql_query("""SELECT check_name, domain, status, observed, threshold, detail
                          FROM dq_check WHERE run_at = (SELECT MAX(run_at) FROM dq_check)""", con)
print(dq.status.value_counts().to_dict())
display(dq[dq.status != "pass"] if (dq.status != "pass").any() else Markdown("All checks pass."))
'''

SCHEMA = '''for name in ["observation", "dim_area", "dim_item", "dim_element", "dim_flag", "dim_domain", "dq_check"]:
    n = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({name})")]
    print(f"{name:12} {n:>10,} rows   {', '.join(cols)}")
print()
print("views:", ", ".join(r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")))
'''

ML_SETUP = '''from src import ml
panel = ml.build_panel(con)
print(f"feature panel: {len(panel):,} country-years · {panel.area_code.nunique()} countries · {panel.year.min()}–{panel.year.max()}")
panel[["area", "year", "cereal_yield_t_ha", "n_kg_per_ha", "temp_change_c", "pou_pct", "gdp_cap_ppp", "cereal_kg_per_cap"]].dropna().tail(6)
'''

ML_YIELD = '''yield_metrics, fig = ml.yield_forecast(panel)
display(fig)
pd.DataFrame(yield_metrics["models"]).T.round(3)
'''
ML_YIELD_2 = '''print("best model:", yield_metrics["best"], "· split:", yield_metrics["split"])
display(pd.DataFrame(yield_metrics["top_features"]).round(3))
forecast = pd.read_csv(ROOT / "models" / "yield_forecast_next_year.csv")
forecast[forecast.cereal_area_ha >= 1e6].sort_values("change_pct", ascending=False).head(12).round(2)
'''
ML_RISK = '''risk_metrics, fig = ml.risk_classifier(panel)
display(fig)
pd.DataFrame({k: {m: v[m] for m in ("roc_auc", "pr_auc", "f1", "balanced_accuracy")} for k, v in risk_metrics["models"].items()}).T.round(3)
'''
ML_RISK_2 = '''scores = pd.read_csv(ROOT / "models" / "risk_scores_latest.csv")
print("positive rate in test years:", round(risk_metrics["positive_rate_test"], 3))
scores.head(15).round(3)
'''
ML_TYPO = '''typology_metrics, fig = ml.typology(panel)
display(fig)
for c in typology_metrics["clusters"]:
    print(f"cluster {c['cluster']} (n = {c['n']}): {c['name']}")
    print("   ", ", ".join(c["members"][:14]), "…" if c["n"] > 14 else "")
'''
ML_PROJ = '''projection_metrics, fig = ml.projections(con)
display(fig)
pd.DataFrame(projection_metrics["regions"]).T.round(1)
'''

DASHBOARD = f'''metrics = json.loads((ROOT / "models" / "metrics.json").read_text())
print("intended use:", metrics["intended_use"])
print()
for lim in metrics["limitations"]:
    print("-", lim)
display(Markdown("**Live dashboard:** {DASHBOARD_URL}  \\n**Repository:** {REPO_URL}"))
IFrame("{DASHBOARD_URL}", width="100%", height=820)
'''

KPIS = '''kpis = pd.read_sql_query("""
WITH w AS (SELECT * FROM v_production WHERE area_code = 5000 AND item_code = '1717' AND year = 2024),
     f AS (SELECT * FROM v_food_security WHERE area_code = 5000 AND year = 2024),
     e AS (SELECT * FROM v_emissions WHERE area_code = 5000 AND year = 2023),
     t AS (SELECT * FROM v_temperature WHERE area_code = 5000 AND year = 2024),
     h AS (SELECT * FROM v_healthy_diet WHERE area_code = 5000 AND year = 2025)
SELECT w.production_t / 1e6 AS cereal_production_mt_2024, w.yield_kg_ha / 1000.0 AS cereal_yield_t_ha_2024,
       f.pou_pct AS undernourishment_pct_2024, f.undernourished_m AS undernourished_million_2024,
       e.agrifood_kt_co2eq / 1e6 AS agrifood_gt_co2eq_2023, t.temp_change_c AS temp_change_c_2024,
       h.unaffordable_pct AS cannot_afford_healthy_diet_pct_2025
FROM w, f, e, t, h""", con)
kpis.T.rename(columns={0: "World"}).round(2)
'''


def build_notebook() -> nbformat.NotebookNode:
    nb = new_notebook(metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                                "language_info": {"name": "python"}})
    cells = [
        new_markdown_cell(f"""# FAOSTAT food-systems analytics

This notebook walks through the whole project on the FAO statistical database: the SQLite warehouse
built from nine FAOSTAT bulk domains, the 35 analytical questions with their SQL, figures and findings,
the four predictive models, and the interactive dashboard.

* Repository: {REPO_URL}
* Live dashboard: {DASHBOARD_URL}
* Written findings: `reports/analysis_report.md` · Model card: `models/MODEL_CARD.md`

Run `python run_pipeline.py` first so `data/faostat.db` exists; every cell below reads from that warehouse
and calls the same functions the pipeline runs, so the notebook and the reports cannot disagree.
"""),
        new_markdown_cell("## 1. Setup"),
        new_code_cell(SETUP),
        new_markdown_cell("## 2. The warehouse\n\nNine domains, one long fact table, conformed dimensions, and a quality gate that runs on every build."),
        new_code_cell(SCHEMA),
        new_code_cell(WAREHOUSE),
        new_markdown_cell("### Headline numbers (World)"),
        new_code_cell(KPIS),
        new_markdown_cell("## 3. The questions\n\nEach question is a SQL file in `sql/questions/` and a handler in `src/analysis.py`. "
                          "The SQL is shown before each cell; the cell runs it, renders the figure and prints the generated findings."),
    ]
    n = 0
    for theme in dict.fromkeys(t for t, _ in HANDLERS.values()):
        cells.append(new_markdown_cell(f"### {theme}"))
        for slug, (t, _) in HANDLERS.items():
            if t != theme:
                continue
            n += 1
            sql, question = _sql(slug)
            qid = slug.split("_")[0].upper()
            cells.append(new_markdown_cell(f"#### {qid}. {question}\n\n```sql\n{sql.strip()}\n```"))
            cells.append(new_code_cell(f'{slug.split("_", 1)[1]} = answer("{slug}")'))
    cells += [
        new_markdown_cell("## 4. Predictive models\n\nFour models, each validated with a strictly time-based split "
                          "(train on earlier years, test on later ones). They are descriptive screening aids trained on FAO's "
                          "published - partly modelled - series; see `models/MODEL_CARD.md` for intended use and limitations."),
        new_code_cell(ML_SETUP),
        new_markdown_cell("### 4.1 Next-year cereal-yield forecast\n\nOne step ahead, from lagged yields, last year's inputs and "
                          "temperature, and region. Persistence (last year's yield) is the baseline every model must beat; "
                          "the target year's own weather is excluded because a planner does not have it."),
        new_code_cell(ML_YIELD),
        new_code_cell(ML_YIELD_2),
        new_markdown_cell("### 4.2 Undernourishment-risk classifier\n\nProbability that prevalence of undernourishment is ≥ 15 %, "
                          "from structural features only. Dietary-energy inputs are excluded: PoU is computed from them, so "
                          "including them would be leakage rather than prediction."),
        new_code_cell(ML_RISK),
        new_code_cell(ML_RISK_2),
        new_markdown_cell("### 4.3 Food-system typology\n\nk-means on 12 standardised latest-year indicators; k chosen by silhouette; PCA only for display."),
        new_code_cell(ML_TYPO),
        new_markdown_cell("### 4.4 Regional cereal projections to 2030\n\nLog-linear trend on 2005–2024 with a 95 % prediction interval from the residual variance."),
        new_code_cell(ML_PROJ),
        new_markdown_cell("## 5. The dashboard\n\nEverything above is packed into a single static page with filters "
                          "(regions, country, year range), maps, a free X/Y explorer, the model outputs and a governance tab. "
                          "It is embedded below; open it full-size at the link."),
        new_code_cell(DASHBOARD),
        new_markdown_cell("---\nData © FAO, FAOSTAT bulk downloads, used under the FAO statistical database terms of use. "
                          "Geography: UN Statistics Division M49."),
    ]
    nb.cells = cells
    print(f"  notebook: {len(cells)} cells, {n} questions")
    return nb


def execute(nb: nbformat.NotebookNode) -> nbformat.NotebookNode:
    client = NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(NOTEBOOKS_DIR)}})
    client.execute()
    return nb


def export_html(nb: nbformat.NotebookNode) -> None:
    """Static export: keep PNG/text outputs only so the page needs no external scripts."""
    static = nbformat.from_dict(json.loads(json.dumps(nb)))
    for cell in static.cells:
        for out in cell.get("outputs", []):
            data = out.get("data")
            if data and "image/png" in data:
                for k in list(data):
                    if k not in ("image/png", "text/plain"):
                        del data[k]
    exporter = HTMLExporter(template_name="lab")
    exporter.exclude_input_prompt = True
    exporter.exclude_output_prompt = True
    exporter.mathjax_url = ""
    body, _ = exporter.from_notebook_node(static)
    # drop any remaining external script/link tags; the export must be self-contained
    body = re.sub(r'<script[^>]+src="https?://[^"]+"[^>]*>\s*</script>', "", body)
    body = re.sub(r'<link[^>]+href="https?://[^"]+"[^>]*>', "", body)
    body = body.replace("<head>", "<head><meta name=\"referrer\" content=\"no-referrer\">", 1)
    NOTEBOOK_HTML.write_text(body)


def build() -> None:
    NOTEBOOKS_DIR.mkdir(exist_ok=True)
    nb = build_notebook()
    nb = execute(nb)
    nbformat.write(nb, NOTEBOOK_PATH)
    export_html(nb)
    size = NOTEBOOK_PATH.stat().st_size / 1e6
    print(f"  written {NOTEBOOK_PATH.relative_to(ROOT)} ({size:.1f} MB) and {NOTEBOOK_HTML.relative_to(ROOT)} ({NOTEBOOK_HTML.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    build()
