"""Build the interactive dashboard (docs/index.html) for GitHub Pages.

The page is a single self-contained HTML file: Plotly.js from a CDN, all data
inlined as JSON so it works from file://, GitHub Pages or any static host with
no backend. Data are packed as column-oriented arrays to keep the file small.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .config import DB_PATH, DOCS_DIR, DOCS_DATA_DIR, FIGURES_DIR, MODELS_DIR, REPORTS_DIR

AGG = {5000: "World", 5100: "Africa", 5200: "Americas", 5300: "Asia", 5400: "Europe", 5500: "Oceania"}

INDICATORS = {
    # key: (label, unit, group, better, decimals)
    "cereal_production_mt": ("Cereal production", "Mt", "Production", "high", 1),
    "cereal_yield_t_ha": ("Cereal yield", "t/ha", "Production", "high", 2),
    "cereal_area_mha": ("Cereal area harvested", "Mha", "Production", None, 2),
    "cereal_kg_per_cap": ("Cereal production per person", "kg", "Production", "high", 0),
    "meat_production_mt": ("Meat production", "Mt", "Production", None, 2),
    "milk_production_mt": ("Milk production", "Mt", "Production", None, 2),
    "population_m": ("Population", "million", "People", None, 1),
    "urban_share_pct": ("Urban population share", "%", "People", None, 1),
    "gdp_cap_ppp": ("GDP per capita (PPP)", "Int$", "People", "high", 0),
    "pou_pct": ("Undernourishment (PoU, 3-yr avg)", "%", "Food security", "low", 1),
    "undernourished_m": ("People undernourished", "million", "Food security", "low", 1),
    "fies_mod_sev_pct": ("Moderate or severe food insecurity", "%", "Food security", "low", 1),
    "fies_severe_pct": ("Severe food insecurity", "%", "Food security", "low", 1),
    "des_adequacy_pct": ("Dietary energy supply adequacy", "%", "Food security", "high", 0),
    "stunting_pct": ("Child stunting (under 5)", "%", "Food security", "low", 1),
    "obesity_pct": ("Adult obesity", "%", "Food security", "low", 1),
    "anemia_pct": ("Anaemia, women 15-49", "%", "Food security", "low", 1),
    "cereal_import_dep_pct": ("Cereal import dependency", "%", "Food security", "low", 1),
    "water_basic_pct": ("Basic drinking water access", "%", "Food security", "high", 1),
    "sanitation_basic_pct": ("Basic sanitation access", "%", "Food security", "high", 1),
    "cohd_ppp_per_day": ("Cost of a healthy diet", "PPP$/day", "Food security", "low", 2),
    "unaffordable_pct": ("Cannot afford a healthy diet", "%", "Food security", "low", 1),
    "n_kg_per_ha": ("Nitrogen use per ha cropland", "kg N/ha", "Inputs & land", None, 1),
    "cropland_share_pct": ("Cropland share of land", "%", "Inputs & land", None, 1),
    "forest_share_pct": ("Forest share of land", "%", "Inputs & land", "high", 1),
    "pasture_share_pct": ("Pasture share of land", "%", "Inputs & land", None, 1),
    "irrigation_share_pct": ("Arable land equipped for irrigation", "%", "Inputs & land", None, 1),
    "organic_share_pct": ("Organic share of agricultural land", "%", "Inputs & land", "high", 2),
    "agri_ha_per_cap": ("Agricultural land per person", "ha", "Inputs & land", None, 2),
    "temp_change_c": ("Temperature change vs 1951-80", "°C", "Climate", "low", 2),
    "agrifood_mt_co2eq": ("Agrifood-system emissions", "Mt CO2eq", "Climate", "low", 1),
    "agrifood_t_per_cap": ("Agrifood emissions per person", "t CO2eq", "Climate", "low", 2),
    "farm_gate_mt_co2eq": ("Farm-gate emissions", "Mt CO2eq", "Climate", "low", 1),
    "agrifood_share_pct": ("Agrifood share of all emissions", "%", "Climate", None, 1),
}

CROPS = {"15": "Wheat", "27": "Rice", "56": "Maize (corn)", "44": "Barley", "83": "Sorghum", "79": "Millet", "116": "Potatoes", "125": "Cassava",
         "236": "Soya beans", "156": "Sugar cane", "1717": "Cereals (total)", "1726": "Pulses (total)", "1735": "Vegetables (total)", "1738": "Fruit (total)",
         "1720": "Roots & tubers (total)", "1780": "Milk (total)", "1765": "Meat (total)", "1783": "Eggs (total)", "486": "Bananas", "254": "Oil palm fruit"}


def build_panel(con: sqlite3.Connection) -> pd.DataFrame:
    sql = """
    SELECT a.area_code, a.area, a.iso3, a.region, a.is_aggregate, pop.year,
           p.production_t / 1e6 AS cereal_production_mt, p.yield_kg_ha / 1000.0 AS cereal_yield_t_ha, p.area_harvested_ha / 1e6 AS cereal_area_mha,
           pop.population / 1e6 AS population_m, 100.0 * pop.urban_population / pop.population AS urban_share_pct,
           f.n_kg_per_ha,
           100.0 * l.cropland_kha / l.land_area_kha AS cropland_share_pct, 100.0 * l.forest_kha / l.land_area_kha AS forest_share_pct,
           100.0 * l.pastures_kha / l.land_area_kha AS pasture_share_pct,
           100.0 * l.irrigated_equipped_kha / (l.arable_kha + COALESCE(l.perm_crops_kha, 0)) AS irrigation_share_pct,
           100.0 * l.organic_agri_kha / l.agri_land_kha AS organic_share_pct,
           l.agri_land_kha * 1000.0 / pop.population AS agri_ha_per_cap,
           t.temp_change_c,
           e.agrifood_kt_co2eq / 1000.0 AS agrifood_mt_co2eq, e.farm_gate_kt_co2eq / 1000.0 AS farm_gate_mt_co2eq,
           e.agrifood_kt_co2eq * 1000.0 / pop.population AS agrifood_t_per_cap,
           100.0 * e.agrifood_kt_co2eq / e.all_sectors_kt_co2eq AS agrifood_share_pct,
           fs.pou_pct, fs.undernourished_m, fs.fies_mod_sev_pct, fs.fies_severe_pct, fs.des_adequacy_pct, fs.stunting_pct, fs.obesity_pct, fs.anemia_pct,
           fs.cereal_import_dep_pct, fs.water_basic_pct, fs.sanitation_basic_pct, fs.gdp_cap_ppp,
           h.cohd_ppp_per_day, h.unaffordable_pct,
           meat.value / 1e6 AS meat_production_mt, milk.value / 1e6 AS milk_production_mt
    FROM dim_area a
    JOIN v_population pop ON pop.area_code = a.area_code           -- population covers every area-year 1961-2025
    LEFT JOIN v_production p ON p.area_code = a.area_code AND p.year = pop.year AND p.item_code = '1717'
    LEFT JOIN v_fertilizer f ON f.area_code = a.area_code AND f.year = pop.year
    LEFT JOIN v_land l ON l.area_code = a.area_code AND l.year = pop.year
    LEFT JOIN v_temperature t ON t.area_code = a.area_code AND t.year = pop.year
    LEFT JOIN v_emissions e ON e.area_code = a.area_code AND e.year = pop.year
    LEFT JOIN v_food_security fs ON fs.area_code = a.area_code AND fs.year = pop.year
    LEFT JOIN v_healthy_diet h ON h.area_code = a.area_code AND h.year = pop.year
    LEFT JOIN observation meat ON meat.domain = 'QCL' AND meat.area_code = a.area_code AND meat.year = pop.year AND meat.item_code = '1765' AND meat.element_code = 5510
    LEFT JOIN observation milk ON milk.domain = 'QCL' AND milk.area_code = a.area_code AND milk.year = pop.year AND milk.item_code = '1780' AND milk.element_code = 5510
    WHERE ((a.is_aggregate = 0 AND a.region IS NOT NULL) OR a.area_code IN (5000, 5100, 5200, 5300, 5400, 5500))
      AND pop.year BETWEEN 1961 AND 2025
    ORDER BY a.area_code, pop.year
    """
    df = pd.read_sql_query(sql, con)
    df["cereal_kg_per_cap"] = df.cereal_production_mt * 1e9 / (df.population_m * 1e6)
    df.loc[df.irrigation_share_pct > 100, "irrigation_share_pct"] = 100
    return df


def pack(df: pd.DataFrame, cols: list[str], decimals: int = 3) -> dict:
    """Column-oriented JSON with NaN -> null and rounded floats."""
    out = {}
    for c in cols:
        s = df[c]
        if s.dtype.kind == "f":
            out[c] = [None if (v is None or (isinstance(v, float) and np.isnan(v))) else round(float(v), decimals) for v in s.tolist()]
        else:
            out[c] = [None if (isinstance(v, float) and np.isnan(v)) else v for v in s.tolist()]
    return out


def records(df: pd.DataFrame) -> list[dict]:
    """to_dict(orient='records') with NaN -> None so the JSON is strict."""
    return [{k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in r.items()} for r in df.to_dict(orient="records")]


def build_data(con: sqlite3.Connection) -> dict:
    panel = build_panel(con)
    areas = pd.read_sql_query("""SELECT area_code, area, iso3, region, subregion, is_aggregate, is_ldc, is_lldc, is_sids FROM dim_area
                                 WHERE (is_aggregate = 0 AND region IS NOT NULL) OR area_code IN (5000,5100,5200,5300,5400,5500) ORDER BY area""", con)
    areas.loc[areas.is_aggregate == 1, "region"] = areas.loc[areas.is_aggregate == 1, "area"]
    crops = pd.read_sql_query(f"""SELECT area_code, item_code, year, production_t / 1e6 AS production_mt, area_harvested_ha / 1e6 AS area_mha, yield_kg_ha / 1000.0 AS yield_t_ha
                                  FROM v_production WHERE item_code IN ({','.join(repr(k) for k in CROPS)}) AND year >= 1961
                                  AND ((is_aggregate = 0 AND region IS NOT NULL) OR area_code IN (5000,5100,5200,5300,5400,5500))""", con)
    manifest = pd.read_sql_query("SELECT * FROM dim_domain", con)
    dq = pd.read_sql_query("SELECT domain, check_name, status, observed, threshold, detail FROM dq_check WHERE run_at = (SELECT MAX(run_at) FROM dq_check)", con)
    flags = pd.read_sql_query("""SELECT o.domain, o.flag, COALESCE(f.description, 'unspecified') AS description, COUNT(*) AS n
                                 FROM observation o LEFT JOIN dim_flag f ON f.domain = o.domain AND f.flag = o.flag GROUP BY 1, 2""", con)
    answers = json.loads((REPORTS_DIR / "answers.json").read_text())
    metrics = json.loads((MODELS_DIR / "metrics.json").read_text())
    forecasts = pd.read_csv(MODELS_DIR / "yield_forecast_next_year.csv")
    risk = pd.read_csv(MODELS_DIR / "risk_scores_latest.csv")
    typology = pd.read_csv(MODELS_DIR / "typology_clusters.csv")
    projections = pd.read_csv(MODELS_DIR / "cereal_projections.csv")
    test_pred = pd.read_csv(MODELS_DIR / "yield_forecast_test_predictions.csv")
    ind_cols = list(INDICATORS)
    latest_years = {k: int(panel.loc[panel[k].notna() & (panel.is_aggregate == 0), "year"].max()) for k in ind_cols if panel[k].notna().any()}
    return {
        "meta": {"built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "latest_years": latest_years,
                 "year_min": int(panel.year.min()), "year_max": int(panel.year.max()), "n_countries": int((areas.is_aggregate == 0).sum()),
                 "n_observations": int(con.execute("SELECT COUNT(*) FROM observation").fetchone()[0])},
        "indicators": {k: {"label": v[0], "unit": v[1], "group": v[2], "better": v[3], "dp": v[4]} for k, v in INDICATORS.items()},
        "areas": records(areas),
        "panel": pack(panel, ["area_code", "year"] + ind_cols),
        "crops": {"items": CROPS, "data": pack(crops, ["area_code", "item_code", "year", "production_mt", "area_mha", "yield_t_ha"], 4)},
        "manifest": records(manifest),
        "dq": records(dq),
        "flags": records(flags),
        "answers": answers,
        "metrics": metrics,
        "forecasts": records(forecasts.round(3)),
        "risk": records(risk.round(4)),
        "typology": records(typology.round(3)),
        "projections": records(projections.round(2)),
        "yield_test": pack(test_pred, list(test_pred.columns), 3),
    }


def build(db_path=DB_PATH) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    data = build_data(con)
    con.close()
    payload = json.dumps(data, separators=(",", ":"), allow_nan=False)
    (DOCS_DATA_DIR / "dashboard_data.json").write_text(payload)
    # copy figures so the Pages site can link to them
    fig_dir = DOCS_DIR / "figures"
    fig_dir.mkdir(exist_ok=True)
    for f in FIGURES_DIR.glob("*.html"):
        shutil.copy(f, fig_dir / f.name)
    template = (DOCS_DIR / "template.html").read_text()
    html = template.replace("/*__DATA__*/", "window.DATA = " + payload + ";")
    (DOCS_DIR / "index.html").write_text(html)
    print(f"  dashboard written: {len(html) / 1e6:.1f} MB, {len(list(fig_dir.glob('*.html')))} figures copied")


if __name__ == "__main__":
    build()
