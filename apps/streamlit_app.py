"""Streamlit front-end over the committed pipeline artefacts.

    streamlit run apps/streamlit_app.py --server.port 8768
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import common as c

st.set_page_config(page_title="Food Systems Explorer · Streamlit", page_icon="🌾", layout="wide")
ANSWERS = c.answers()
METRICS = c.metrics()

st.title("Food Systems Explorer")
st.caption(f"FAOSTAT production, food security, inputs, land, climate, prices and predictive models · [repository]({c.REPO_URL}) · [static dashboard]({c.PAGES_URL})")

tab_overview, tab_questions, tab_predictions, tab_notebook, tab_data = st.tabs(["Overview", "Questions", "Predictions", "Notebook", "Data & governance"])

with tab_overview:
    k = c.kpis()
    cols = st.columns(6)
    cols[0].metric("World cereal production", f"{k.get('production_mt_latest', 0):,.0f} Mt", str(k.get("latest_year", "")))
    cols[1].metric("Undernourishment (PoU)", f"{k.get('world_pou_latest', 0):.1f} %", f"{k.get('world_undernourished_m', 0):,.0f} M people", delta_color="off")
    cols[2].metric("Cannot afford a healthy diet", f"{k.get('world_unaffordable_pct', 0):.1f} %", f"{k.get('world_unaffordable_m', 0):,.0f} M people", delta_color="off")
    cols[3].metric("Agrifood emissions", f"{k.get('world_agrifood_gt', 0):.1f} Gt CO2eq", f"{k.get('world_agrifood_share', 0):.0f} % of total", delta_color="off")
    cols[4].metric("Land temperature change", f"{k.get('world_temp_change_5yr', 0):+.2f} °C", "5-yr mean vs 1951-80", delta_color="off")
    cols[5].metric("Nitrogen intensity", f"{k.get('world_n_kg_ha', 0):.0f} kg N/ha", "of cropland", delta_color="off")
    a, b = st.columns(2)
    with a:
        components.html(c.figure_html("q01_global_cereal_production"), height=560)
    with b:
        components.html(c.figure_html("q08_pou_by_region"), height=560)

with tab_questions:
    themes = list(dict.fromkeys(a["theme"] for a in ANSWERS))
    theme = st.selectbox("Theme", themes, key="theme")
    options = [a for a in ANSWERS if a["theme"] == theme]
    chosen = st.selectbox("Question", options, format_func=lambda a: f"{a['qid']}. {a['question']}", key="question")
    components.html(c.figure_html(chosen["slug"]), height=700, scrolling=True)
    for f in chosen["findings"]:
        st.markdown(f"- {f}")
    st.caption(f"[SQL]({c.REPO_URL}/blob/main/{chosen['sql_file']}) · [result table]({c.REPO_URL}/blob/main/reports/{chosen['table_file']})")

with tab_predictions:
    st.info(METRICS["intended_use"])
    yf, rc, ty, pj = METRICS["yield_forecast"], METRICS["risk_classifier"], METRICS["typology"], METRICS["projections"]
    st.dataframe(pd.DataFrame([
        {"model": yf["best"], "task": yf["task"], "test size": yf["n_test"], "metrics": f"MAE {yf['models'][yf['best']]['mae']:.3f} t/ha · R² {yf['models'][yf['best']]['r2']:.3f} · persistence MAE {yf['models']['Persistence (last year)']['mae']:.3f}"},
        {"model": rc["best"], "task": rc["task"], "test size": rc["n_test"], "metrics": f"ROC-AUC {rc['models'][rc['best']]['roc_auc']:.3f} · PR-AUC {rc['models'][rc['best']]['pr_auc']:.3f} · F1 {rc['models'][rc['best']]['f1']:.3f}"},
        {"model": f"k-means (k = {ty['k']})", "task": ty["task"], "test size": ty["n_countries"], "metrics": "silhouette " + ", ".join(f"k{k}: {v:.2f}" for k, v in ty["silhouette_by_k"].items())},
        {"model": "log-linear trend", "task": pj["task"], "test size": "-", "metrics": " · ".join(f"{r} {v['trend_pct_per_year']:+.1f} %/yr" for r, v in pj["regions"].items())},
    ]), hide_index=True, use_container_width=True)
    a, b = st.columns(2)
    with a:
        components.html(c.figure_html("ml_yield_forecast"), height=600)
        components.html(c.figure_html("ml_typology"), height=660)
    with b:
        components.html(c.figure_html("ml_risk_classifier"), height=600)
        components.html(c.figure_html("ml_projections"), height=660)
    a, b = st.columns(2)
    fc = c.table("yield_forecast_next_year")
    with a:
        st.subheader(f"Next-year yield forecast ({yf['forecast_year']})")
        min_area = st.slider("Minimum cereal area (kha)", 20, 5000, 500, step=20)
        st.dataframe(fc[fc.cereal_area_ha >= min_area * 1000].sort_values("change_pct", ascending=False).round(2), hide_index=True, use_container_width=True)
    with b:
        st.subheader("Undernourishment risk score (latest)")
        thr = st.slider("Show scores ≥", 0.0, 1.0, 0.5, 0.05)
        risk = c.table("risk_scores_latest")
        st.dataframe(risk[risk.risk_score >= thr].round(3), hide_index=True, use_container_width=True)
    st.caption(f"Model card: [models/MODEL_CARD.md]({c.REPO_URL}/blob/main/models/MODEL_CARD.md)")

with tab_notebook:
    st.markdown("The executed analysis notebook: warehouse, all 35 questions with SQL, figures and findings, the four models and the dashboard. It calls the same functions the pipeline runs.")
    st.markdown(" · ".join(f"[{label}]({url})" for label, url in c.NOTEBOOK_LINKS.items()))
    components.html(c.notebook_html(), height=1400, scrolling=True)

with tab_data:
    st.subheader("Reviewed FAO release hashes")
    st.dataframe(c.pins(), hide_index=True, use_container_width=True)
    dom, dq = c.provenance()
    if dom is not None:
        st.subheader("Loaded domains")
        st.dataframe(dom, hide_index=True, use_container_width=True)
        st.subheader("Quality gate (latest run)")
        st.dataframe(dq, hide_index=True, use_container_width=True)
    else:
        st.caption("Warehouse not present locally (data/faostat.db); run the pipeline to see load statistics and the quality gate.")
    components.html(c.figure_html("q32_data_provenance"), height=560)
