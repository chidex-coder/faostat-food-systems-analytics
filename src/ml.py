"""Predictive analytics on the warehouse.

Four models, each chosen for a decision it supports:

1. Cereal-yield forecast (regression)   - "what yield should we plan for next year?"
   Country-year panel, one-step-ahead target, *time-based* split so the test set
   is strictly in the future of the training set. Persistence (last year's yield)
   is the baseline every model must beat.
2. Undernourishment-risk classifier     - "which countries are at risk of PoU >= 15 %?"
   Structural features only (income, production per head, trade dependence,
   water/sanitation, climate); dietary-energy inputs are excluded because PoU is
   derived from them, which would be leakage rather than prediction.
3. Food-system typology (clustering)    - "which countries face the same problem?"
   K-means on standardised latest-year profiles, k chosen by silhouette, PCA for display.
4. Regional cereal projections to 2030  - log-linear trend with an empirical
   prediction interval from the residuals; deliberately simple and explainable.

Artefacts land in models/ (metrics, predictions, importances) and reports/figures/.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (average_precision_score, balanced_accuracy_score, f1_score, mean_absolute_error,
                             r2_score, roc_auc_score, silhouette_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import viz
from .config import DB_PATH, FIGURES_DIR, MODELS_DIR
from .viz import CATEGORICAL

SEED = 2026
REGIONS = ["Africa", "Americas", "Asia", "Europe", "Oceania"]


# ---------------------------------------------------------------------------
# Feature panel
# ---------------------------------------------------------------------------
def build_panel(con: sqlite3.Connection) -> pd.DataFrame:
    """Country-year panel joining every view; one row per country per year."""
    sql = """
    SELECT c.area_code, c.area, c.region, c.subregion, c.is_ldc, c.is_lldc, c.is_sids, p.year,
           p.yield_kg_ha / 1000.0 AS cereal_yield_t_ha, p.production_t AS cereal_production_t, p.area_harvested_ha AS cereal_area_ha,
           pop.population, pop.urban_population * 1.0 / pop.population AS urban_share,
           f.n_kg_per_ha, f.p2o5_kg_per_ha, f.k2o_kg_per_ha,
           l.cropland_kha, l.arable_kha, l.perm_crops_kha, l.pastures_kha, l.forest_kha, l.land_area_kha, l.irrigated_equipped_kha,
           t.temp_change_c,
           e.agrifood_kt_co2eq, e.farm_gate_kt_co2eq,
           fs.pou_pct, fs.des_adequacy_pct, fs.des_kcal, fs.gdp_cap_ppp, fs.cereal_import_dep_pct, fs.food_import_share_pct,
           fs.stunting_pct, fs.obesity_pct, fs.water_basic_pct, fs.sanitation_basic_pct, fs.protein_g, fs.cereal_share_pct,
           fs.supply_variability_kcal, fs.fies_mod_sev_pct,
           h.cohd_ppp_per_day, h.unaffordable_pct
    FROM v_country c
    JOIN v_production p ON p.area_code = c.area_code AND p.item_code = '1717'
    LEFT JOIN v_population pop ON pop.area_code = c.area_code AND pop.year = p.year
    LEFT JOIN v_fertilizer f ON f.area_code = c.area_code AND f.year = p.year
    LEFT JOIN v_land l ON l.area_code = c.area_code AND l.year = p.year
    LEFT JOIN v_temperature t ON t.area_code = c.area_code AND t.year = p.year
    LEFT JOIN v_emissions e ON e.area_code = c.area_code AND e.year = p.year
    LEFT JOIN v_food_security fs ON fs.area_code = c.area_code AND fs.year = p.year
    LEFT JOIN v_healthy_diet h ON h.area_code = c.area_code AND h.year = p.year
    WHERE p.year >= 1990
    ORDER BY c.area_code, p.year
    """
    df = pd.read_sql_query(sql, con)
    df["cereal_kg_per_cap"] = df.cereal_production_t * 1000 / df.population
    df["agrifood_t_per_cap"] = df.agrifood_kt_co2eq * 1000 / df.population
    df["irrigation_share"] = df.irrigated_equipped_kha / (df.arable_kha + df.perm_crops_kha.fillna(0))
    df["cropland_share"] = df.cropland_kha / df.land_area_kha
    df["forest_share"] = df.forest_kha / df.land_area_kha
    df["log_gdp_cap"] = np.log(df.gdp_cap_ppp)
    df["log_population"] = np.log(df.population)
    for r in REGIONS:
        df[f"region_{r}"] = (df.region == r).astype(int)
    return df


def _permutation_importance(model, X: pd.DataFrame, y: np.ndarray, feats: list[str], repeats: int = 15) -> pd.DataFrame:
    """Model-agnostic permutation importance (MAE increase when a feature is shuffled)."""
    rng = np.random.default_rng(SEED)
    base = mean_absolute_error(y, model.predict(X))
    rows = []
    for f in feats:
        deltas = []
        for _ in range(repeats):
            Xp = X.copy()
            Xp[f] = rng.permutation(Xp[f].values)
            deltas.append(mean_absolute_error(y, model.predict(Xp)) - base)
        rows.append(dict(feature=f, importance=float(np.mean(deltas)), std=float(np.std(deltas))))
    return pd.DataFrame(rows).sort_values("importance", ascending=False)


def _metrics_reg(y, yhat) -> dict:
    y, yhat = np.asarray(y), np.asarray(yhat)
    return {"mae": float(mean_absolute_error(y, yhat)), "rmse": float(np.sqrt(np.mean((y - yhat) ** 2))),
            "r2": float(r2_score(y, yhat)), "mape_pct": float(100 * np.mean(np.abs((y - yhat) / y)))}


# ---------------------------------------------------------------------------
# 1. Yield forecast
# ---------------------------------------------------------------------------
def yield_forecast(panel: pd.DataFrame) -> dict:
    df = panel[(panel.cereal_area_ha >= 20000)].copy()
    df = df.sort_values(["area_code", "year"])
    g = df.groupby("area_code")
    for k in (1, 2, 3):
        df[f"yield_lag{k}"] = g.cereal_yield_t_ha.shift(k)
    df["yield_mean3"] = df[["yield_lag1", "yield_lag2", "yield_lag3"]].mean(axis=1)
    df["yield_trend5"] = g.cereal_yield_t_ha.transform(lambda s: s.rolling(5).apply(lambda w: np.polyfit(range(5), w, 1)[0], raw=True)).shift(1)
    df["temp_lag1"] = g.temp_change_c.shift(1)
    df["n_lag1"] = g.n_kg_per_ha.shift(1)
    df["irrigation_lag1"] = g.irrigation_share.shift(1)
    df["target"] = df.cereal_yield_t_ha
    # Only information available *before* the target year: lags of yield, last
    # year's inputs and temperature, and the region. The target year's own
    # weather is deliberately excluded - a planner does not know it in advance.
    feats = ["yield_lag1", "yield_lag2", "yield_lag3", "yield_mean3", "yield_trend5", "n_lag1", "temp_lag1",
             "irrigation_lag1", "log_population", "year"] + [f"region_{r}" for r in REGIONS]
    data = df.dropna(subset=["yield_lag1", "yield_lag2", "yield_lag3", "target"]).copy()
    data[feats] = data[feats].astype(float)
    split_year = 2019
    train, test = data[data.year < split_year], data[data.year >= split_year]
    med = train[feats].median()

    class _Model:
        def __init__(self, est, fill):
            self.est, self.fill = est, fill

        def fit(self, X, y):
            self.est.fit(X.fillna(med) if self.fill else X, y)
            return self

        def predict(self, X):
            return self.est.predict(X.fillna(med) if self.fill else X)

    fitted = {
        "Ridge regression": _Model(make_pipeline(StandardScaler(), Ridge(alpha=1.0)), True).fit(train[feats], train.target),
        "Gradient boosting": _Model(HistGradientBoostingRegressor(max_iter=600, learning_rate=0.04, max_depth=6, min_samples_leaf=15,
                                                                 l2_regularization=0.5, random_state=SEED), False).fit(train[feats], train.target),
    }
    preds = {"Persistence (last year)": test.yield_lag1.values}
    for name, m in fitted.items():
        preds[name] = m.predict(test[feats])
    results = {name: _metrics_reg(test.target, yhat) for name, yhat in preds.items()}
    best = min(results, key=lambda k: results[k]["mae"])
    best_model = fitted[best]

    importance = _permutation_importance(best_model, test[feats], test.target.values, feats)

    out = test[["area", "region", "year", "target"]].copy()
    for name, yhat in preds.items():
        out[name] = yhat
    out.to_csv(MODELS_DIR / "yield_forecast_test_predictions.csv", index=False)
    importance.to_csv(MODELS_DIR / "yield_forecast_importance.csv", index=False)

    # one-step-ahead forecast for the year after the last observed one, with the best model
    last = df.groupby("area_code").tail(1).dropna(subset=["yield_lag1", "yield_lag2"]).copy()
    last_year = int(last.year.max())
    nxt = last[last.year == last_year].copy()
    nxt["year"] = last_year + 1
    nxt[["yield_lag1", "yield_lag2", "yield_lag3"]] = nxt[["cereal_yield_t_ha", "yield_lag1", "yield_lag2"]].values
    nxt["yield_mean3"] = nxt[["yield_lag1", "yield_lag2", "yield_lag3"]].mean(axis=1)
    nxt["temp_lag1"] = nxt.temp_change_c
    nxt["n_lag1"] = nxt.n_kg_per_ha
    nxt["irrigation_lag1"] = nxt.irrigation_share
    nxt["forecast_t_ha"] = best_model.predict(nxt[feats].astype(float))
    nxt["change_pct"] = 100 * (nxt.forecast_t_ha / nxt.cereal_yield_t_ha - 1)
    fc = nxt[["area", "region", "year", "cereal_yield_t_ha", "forecast_t_ha", "change_pct", "cereal_area_ha"]].rename(columns={"cereal_yield_t_ha": f"yield_{last_year}_t_ha"})
    fc.to_csv(MODELS_DIR / "yield_forecast_next_year.csv", index=False)

    # figures
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=2, subplot_titles=(f"Actual vs predicted cereal yield, {split_year}-{int(test.year.max())} (t/ha)", "Permutation importance (MAE increase, t/ha)"), horizontal_spacing=0.16, column_widths=[0.55, 0.45])
    for i, region in enumerate(REGIONS):
        s = out[out.region == region]
        fig.add_trace(go.Scatter(x=s.target, y=s[best], mode="markers", name=region, marker=dict(color=viz.colour_for_region(region), size=7, opacity=0.7, line=dict(width=1, color=viz.SURFACE)),
                                 customdata=np.stack([s.area, s.year], axis=1), hovertemplate="%{customdata[0]} %{customdata[1]}<br>actual %{x:.2f} · predicted %{y:.2f}<extra></extra>"), row=1, col=1)
    m = out.target.max()
    fig.add_trace(go.Scatter(x=[0, m], y=[0, m], mode="lines", line=dict(color=viz.TEXT_2, dash="dot", width=1.5), name="perfect", hoverinfo="skip"), row=1, col=1)
    imp = importance.head(12).iloc[::-1]
    fig.add_trace(go.Bar(y=imp.feature, x=imp.importance, orientation="h", marker_color=CATEGORICAL[0], showlegend=False, error_x=dict(type="data", array=imp["std"], color=viz.TEXT_2, thickness=1),
                         hovertemplate="%{y}: +%{x:.3f} t/ha MAE<extra></extra>"), row=1, col=2)
    fig.update_layout(title=f"Cereal-yield forecast · best model: {best} (MAE {results[best]['mae']:.3f} t/ha vs persistence {results['Persistence (last year)']['mae']:.3f})", height=560)
    fig.update_xaxes(title_text="Actual (t/ha)", row=1, col=1)
    fig.update_yaxes(title_text="Predicted (t/ha)", row=1, col=1)
    viz.legend_bottom(fig)
    fig.write_html(FIGURES_DIR / "ml_yield_forecast.html", include_plotlyjs="cdn", config={"displaylogo": False, "responsive": True})

    return {"task": "One-step-ahead cereal yield (t/ha), countries with >= 20 kha harvested", "split": f"train < {split_year}, test >= {split_year}",
            "n_train": int(len(train)), "n_test": int(len(test)), "n_countries": int(data.area_code.nunique()), "features": feats,
            "models": results, "best": best, "top_features": importance.head(6).to_dict(orient="records"),
            "forecast_year": last_year + 1, "n_forecast_countries": int(len(fc))}


# ---------------------------------------------------------------------------
# 2. Undernourishment risk
# ---------------------------------------------------------------------------
def risk_classifier(panel: pd.DataFrame) -> dict:
    threshold = 15.0
    feats = ["log_gdp_cap", "cereal_kg_per_cap", "cereal_import_dep_pct", "food_import_share_pct", "water_basic_pct", "sanitation_basic_pct",
             "urban_share", "irrigation_share", "n_kg_per_ha", "temp_change_c", "cereal_yield_t_ha", "agrifood_t_per_cap", "forest_share",
             "is_ldc", "is_lldc", "is_sids"] + [f"region_{r}" for r in REGIONS]
    data = panel.dropna(subset=["pou_pct", "log_gdp_cap"]).copy()
    data["target"] = (data.pou_pct >= threshold).astype(int)
    data[feats] = data[feats].astype(float)
    split_year = 2017
    train, test = data[data.year < split_year], data[data.year >= split_year]
    med = train[feats].median()
    models = {
        "Logistic regression": make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=2000, class_weight="balanced")),
        "Random forest": RandomForestClassifier(n_estimators=500, min_samples_leaf=5, class_weight="balanced_subsample", random_state=SEED, n_jobs=-1),
        "Gradient boosting": HistGradientBoostingClassifier(max_iter=400, learning_rate=0.05, max_depth=5, min_samples_leaf=20, class_weight="balanced", random_state=SEED),
    }
    results, probs = {}, {}
    for name, model in models.items():
        Xtr = train[feats] if "Gradient" in name else train[feats].fillna(med)
        Xte = test[feats] if "Gradient" in name else test[feats].fillna(med)
        model.fit(Xtr, train.target)
        p = model.predict_proba(Xte)[:, 1]
        probs[name] = p
        pred = (p >= 0.5).astype(int)
        results[name] = {"roc_auc": float(roc_auc_score(test.target, p)), "pr_auc": float(average_precision_score(test.target, p)),
                         "f1": float(f1_score(test.target, pred)), "balanced_accuracy": float(balanced_accuracy_score(test.target, pred)),
                         "confusion": {"tn": int(((pred == 0) & (test.target == 0)).sum()), "fp": int(((pred == 1) & (test.target == 0)).sum()),
                                       "fn": int(((pred == 0) & (test.target == 1)).sum()), "tp": int(((pred == 1) & (test.target == 1)).sum())}}
    best = max(results, key=lambda k: results[k]["roc_auc"])
    model = models[best]
    Xte = test[feats] if "Gradient" in best else test[feats].fillna(med)
    perm = permutation_importance(model, Xte, test.target, n_repeats=15, random_state=SEED, scoring="roc_auc")
    importance = pd.DataFrame({"feature": feats, "importance": perm.importances_mean, "std": perm.importances_std}).sort_values("importance", ascending=False)
    importance.to_csv(MODELS_DIR / "risk_classifier_importance.csv", index=False)

    # latest-year risk scores per country (using the latest row with GDP available)
    latest = panel.dropna(subset=["log_gdp_cap"]).sort_values("year").groupby("area_code").tail(1).copy()
    latest[feats] = latest[feats].astype(float)
    Xl = latest[feats] if "Gradient" in best else latest[feats].fillna(med)
    latest["risk_score"] = model.predict_proba(Xl)[:, 1]
    latest["observed_pou_pct"] = latest.pou_pct
    scores = latest[["area", "region", "year", "risk_score", "observed_pou_pct"]].sort_values("risk_score", ascending=False)
    scores.to_csv(MODELS_DIR / "risk_scores_latest.csv", index=False)
    out = test[["area", "region", "year", "pou_pct", "target"]].copy()
    for name, p in probs.items():
        out[name] = p
    out.to_csv(MODELS_DIR / "risk_classifier_test_predictions.csv", index=False)

    from plotly.subplots import make_subplots
    from sklearn.metrics import roc_curve
    fig = make_subplots(rows=1, cols=2, subplot_titles=(f"ROC curves, test years >= {split_year}", "Permutation importance (ROC-AUC drop)"), horizontal_spacing=0.16)
    for i, (name, p) in enumerate(probs.items()):
        fpr, tpr, _ = roc_curve(test.target, p)
        fig.add_trace(go.Scatter(x=fpr, y=tpr, mode="lines", name=f"{name} (AUC {results[name]['roc_auc']:.3f})", line=dict(color=CATEGORICAL[i], width=2), hovertemplate="FPR %{x:.2f} · TPR %{y:.2f}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=viz.TEXT_2, dash="dot", width=1), showlegend=False, hoverinfo="skip"), row=1, col=1)
    imp = importance.head(12).iloc[::-1]
    fig.add_trace(go.Bar(y=imp.feature, x=imp.importance, orientation="h", marker_color=CATEGORICAL[0], showlegend=False, error_x=dict(type="data", array=imp["std"], color=viz.TEXT_2, thickness=1),
                         hovertemplate="%{y}: %{x:.3f}<extra></extra>"), row=1, col=2)
    fig.update_layout(title=f"Undernourishment-risk classifier (PoU >= {threshold:.0f} %) · best: {best}", height=560)
    fig.update_xaxes(title_text="False positive rate", row=1, col=1)
    fig.update_yaxes(title_text="True positive rate", row=1, col=1)
    viz.legend_bottom(fig)
    fig.write_html(FIGURES_DIR / "ml_risk_classifier.html", include_plotlyjs="cdn", config={"displaylogo": False, "responsive": True})

    return {"task": f"Classify country-years with prevalence of undernourishment >= {threshold:.0f} % from structural features only",
            "split": f"train < {split_year}, test >= {split_year}", "n_train": int(len(train)), "n_test": int(len(test)),
            "positive_rate_test": float(test.target.mean()), "features": feats, "models": results, "best": best,
            "top_features": importance.head(6).to_dict(orient="records"), "n_scored_countries": int(len(scores))}


# ---------------------------------------------------------------------------
# 3. Typology
# ---------------------------------------------------------------------------
def typology(panel: pd.DataFrame) -> dict:
    feats = {"cereal_yield_t_ha": "Cereal yield", "n_kg_per_ha": "N per ha", "cereal_kg_per_cap": "Cereal per head", "cereal_import_dep_pct": "Import dependency",
             "pou_pct": "Undernourishment", "obesity_pct": "Obesity", "agrifood_t_per_cap": "Agrifood CO2e per head", "urban_share": "Urban share",
             "log_gdp_cap": "log GDP per head", "forest_share": "Forest share", "cropland_share": "Cropland share", "unaffordable_pct": "Diet unaffordable"}
    latest = panel.sort_values("year").groupby("area_code").apply(lambda g: g[list(feats)].ffill().iloc[-1], include_groups=False)
    latest = latest.join(panel.groupby("area_code")[["area", "region", "is_ldc"]].last())
    latest = latest.dropna(thresh=len(feats) - 2, subset=list(feats))
    X = latest[list(feats)].fillna(latest[list(feats)].median())
    Xs = StandardScaler().fit_transform(X)
    best_k, best_s, best_model = None, -1, None
    sil = {}
    for k in range(3, 8):
        km = KMeans(n_clusters=k, n_init=20, random_state=SEED).fit(Xs)
        s = silhouette_score(Xs, km.labels_)
        sil[k] = float(s)
        if s > best_s:
            best_k, best_s, best_model = k, s, km
    latest["cluster"] = best_model.labels_
    pca = PCA(n_components=2, random_state=SEED)
    coords = pca.fit_transform(Xs)
    latest["pc1"], latest["pc2"] = coords[:, 0], coords[:, 1]
    profile = latest.groupby("cluster")[list(feats)].median()
    # name clusters by their most distinctive traits (z-score of cluster median vs overall median)
    z = (profile - X.median()) / X.std()
    names = {}
    for c in profile.index:
        top = z.loc[c].abs().sort_values(ascending=False).head(2).index
        names[c] = " · ".join(f"{'high' if z.loc[c, t] > 0 else 'low'} {feats[t].lower()}" for t in top)
    latest["cluster_name"] = latest.cluster.map(names)
    latest.reset_index()[["area_code", "area", "region", "cluster", "cluster_name", "pc1", "pc2"] + list(feats)].to_csv(MODELS_DIR / "typology_clusters.csv", index=False)
    profile.assign(name=pd.Series(names)).to_csv(MODELS_DIR / "typology_profiles.csv")

    fig = go.Figure()
    for i, c in enumerate(sorted(latest.cluster.unique())):
        s = latest[latest.cluster == c]
        fig.add_trace(go.Scatter(x=s.pc1, y=s.pc2, mode="markers", name=f"Cluster {c}: {names[c]} (n = {len(s)})",
                                 marker=dict(color=CATEGORICAL[i % 8], size=9, opacity=0.85, line=dict(width=1.5, color=viz.SURFACE)),
                                 customdata=np.stack([s.area, s.region], axis=1), hovertemplate="<b>%{customdata[0]}</b> (%{customdata[1]})<extra></extra>"))
    load = pd.DataFrame(pca.components_.T, index=[feats[f] for f in feats], columns=["pc1", "pc2"])
    scale = 0.9 * max(abs(latest.pc1).max(), abs(latest.pc2).max())
    for f, r in load.iterrows():
        fig.add_annotation(x=r.pc1 * scale, y=r.pc2 * scale, ax=0, ay=0, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=2, arrowcolor=viz.MUTED, arrowwidth=1)
        fig.add_annotation(x=r.pc1 * scale * 1.12, y=r.pc2 * scale * 1.12, text=f, showarrow=False, font=dict(size=10, color=viz.TEXT_2))
    fig.update_layout(title=f"Food-system typology: k-means (k = {best_k}, silhouette {best_s:.2f}) on {len(feats)} standardised indicators, PCA projection",
                      xaxis_title=f"PC1 ({100 * pca.explained_variance_ratio_[0]:.0f} % of variance)", yaxis_title=f"PC2 ({100 * pca.explained_variance_ratio_[1]:.0f} %)", height=620)
    viz.legend_bottom(fig)
    fig.write_html(FIGURES_DIR / "ml_typology.html", include_plotlyjs="cdn", config={"displaylogo": False, "responsive": True})
    return {"task": "Cluster countries by latest food-system profile", "k": best_k, "silhouette_by_k": sil, "n_countries": int(len(latest)),
            "features": list(feats), "explained_variance_pc1_pc2": [float(v) for v in pca.explained_variance_ratio_],
            "clusters": [{"cluster": int(c), "name": names[c], "n": int((latest.cluster == c).sum()),
                          "members": sorted(latest[latest.cluster == c].area.tolist())} for c in profile.index]}


# ---------------------------------------------------------------------------
# 4. Projections
# ---------------------------------------------------------------------------
def projections(con: sqlite3.Connection, horizon: int = 2030) -> dict:
    df = pd.read_sql_query("""SELECT a.area AS region, p.year, p.production_t / 1e6 AS production_mt
                              FROM v_production p JOIN dim_area a USING (area_code)
                              WHERE p.item_code = '1717' AND p.area_code IN (5000, 5100, 5200, 5300, 5400, 5500) AND p.year >= 2005""", con)
    rows, fig = [], go.Figure()
    summary = {}
    for region, g in df.groupby("region"):
        g = g.sort_values("year")
        x, y = g.year.values.astype(float), np.log(g.production_mt.values)
        coef = np.polyfit(x, y, 1)
        resid = y - np.polyval(coef, x)
        se = resid.std(ddof=2)
        future = np.arange(g.year.max() + 1, horizon + 1)
        n, xbar = len(x), x.mean()
        for yr in future:
            pred = np.polyval(coef, yr)
            half = 1.96 * se * np.sqrt(1 + 1 / n + (yr - xbar) ** 2 / ((x - xbar) ** 2).sum())
            rows.append(dict(region=region, year=int(yr), projected_mt=float(np.exp(pred)), lower_mt=float(np.exp(pred - half)), upper_mt=float(np.exp(pred + half))))
        c = viz.colour_for_region(region)
        fig.add_trace(go.Scatter(x=g.year, y=g.production_mt, mode="lines", name=region, line=dict(color=c, width=2), legendgroup=region, hovertemplate=f"<b>{region}</b> %{{x}}: %{{y:,.0f}} Mt<extra></extra>"))
        pr = pd.DataFrame([r for r in rows if r["region"] == region])
        fig.add_trace(go.Scatter(x=list(pr.year) + list(pr.year[::-1]), y=list(pr.upper_mt) + list(pr.lower_mt[::-1]), fill="toself", fillcolor=c, opacity=0.12, line=dict(width=0), hoverinfo="skip", showlegend=False, legendgroup=region))
        fig.add_trace(go.Scatter(x=pr.year, y=pr.projected_mt, mode="lines", line=dict(color=c, width=2, dash="dot"), showlegend=False, legendgroup=region, hovertemplate=f"<b>{region}</b> %{{x}} projection: %{{y:,.0f}} Mt<extra></extra>"))
        summary[region] = {"trend_pct_per_year": float(100 * (np.exp(coef[0]) - 1)), f"projected_{horizon}_mt": float(np.exp(np.polyval(coef, horizon))),
                           "latest_mt": float(g.production_mt.iloc[-1]), "latest_year": int(g.year.max())}
    pd.DataFrame(rows).to_csv(MODELS_DIR / "cereal_projections.csv", index=False)
    fig.update_layout(title=f"Cereal production by region: observed and log-linear projection to {horizon} (95 % prediction band)", yaxis_title="Mt", yaxis_type="log", hovermode="x unified")
    fig.write_html(FIGURES_DIR / "ml_projections.html", include_plotlyjs="cdn", config={"displaylogo": False, "responsive": True})
    return {"task": f"Log-linear trend projection of regional cereal production to {horizon}", "fit_window": "2005 - latest", "regions": summary}


def run_all(db_path: Path = DB_PATH) -> dict:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    panel = build_panel(con)
    panel.to_csv(MODELS_DIR / "feature_panel.csv", index=False)
    metrics = {"panel_rows": int(len(panel)), "panel_countries": int(panel.area_code.nunique()), "seed": SEED}
    print("  yield forecast ...")
    metrics["yield_forecast"] = yield_forecast(panel)
    print("  risk classifier ...")
    metrics["risk_classifier"] = risk_classifier(panel)
    print("  typology ...")
    metrics["typology"] = typology(panel)
    print("  projections ...")
    metrics["projections"] = projections(con)
    (MODELS_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    con.close()
    return metrics


if __name__ == "__main__":
    m = run_all()
    print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk in ("models", "best", "k", "regions")}) for k, v in m.items()}, indent=2))
