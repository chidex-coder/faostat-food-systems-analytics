"""Shared loaders for the Dash and Streamlit apps.

Both apps are thin views over artefacts the pipeline already committed
(reports/, models/, docs/), so they run without the 600 MB warehouse; when
data/faostat.db is present the Data tab also shows the live provenance table.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
MODELS = ROOT / "models"
DOCS = ROOT / "docs"
DB = ROOT / "data" / "faostat.db"

REPO_URL = "https://github.com/chidex-coder/faostat-food-systems-analytics"
PAGES_URL = "https://chidex-coder.github.io/faostat-food-systems-analytics/"
NOTEBOOK_LINKS = {
    "View on GitHub": f"{REPO_URL}/blob/main/notebooks/food_systems_analysis.ipynb",
    "Interactive figures on nbviewer": "https://nbviewer.org/github/chidex-coder/faostat-food-systems-analytics/blob/main/notebooks/food_systems_analysis.ipynb",
    "Download .ipynb": f"{REPO_URL}/raw/main/notebooks/food_systems_analysis.ipynb",
    "Static HTML copy": f"{PAGES_URL}notebook.html",
}


def answers() -> list[dict]:
    return json.loads((REPORTS / "answers.json").read_text())


def metrics() -> dict:
    return json.loads((MODELS / "metrics.json").read_text())


def figure_html(name: str) -> str:
    """Standalone figure page (pinned Plotly.js + SRI) for embedding in an iframe."""
    path = FIGURES / (name if name.endswith(".html") else f"{name}.html")
    return path.read_text() if path.exists() else "<p>figure not built - run the pipeline</p>"


def notebook_html() -> str:
    path = DOCS / "notebook.html"
    return path.read_text() if path.exists() else "<p>notebook not built - run <code>python -m src.notebook</code></p>"


def table(name: str, n: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(MODELS / f"{name}.csv")
    return df.head(n) if n else df


def kpis() -> dict:
    """World headline numbers from the answers' recorded numbers (no database needed)."""
    out = {}
    for a in answers():
        out.update(a.get("numbers", {}))
    return out


def provenance() -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    if not DB.exists():
        return None, None
    con = sqlite3.connect(DB)
    try:
        dom = pd.read_sql_query("""SELECT domain, name, rows_raw, rows_loaded, rows_dropped_filter, rows_dropped_missing, rows_dropped_dupe,
                                          substr(sha256,1,12) AS sha256, server_last_modified FROM dim_domain ORDER BY rows_loaded DESC""", con)
        dq = pd.read_sql_query("""SELECT check_name, domain, status, observed, threshold, detail FROM dq_check
                                  WHERE run_at = (SELECT MAX(run_at) FROM dq_check)""", con)
    finally:
        con.close()
    return dom, dq


def pins() -> pd.DataFrame:
    p = json.loads((ROOT / "data" / "reference" / "archive_pins.json").read_text())
    return pd.DataFrame([{"domain": k, **v} for k, v in p.items()])
