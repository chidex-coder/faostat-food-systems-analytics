"""Analysis stage: answer each question in sql/questions with SQL + pandas, and
render one Plotly figure per question.

Outputs
-------
reports/figures/qNN_slug.html   interactive figure (pinned Plotly.js from CDN, SRI-checked)
reports/tables/qNN_slug.csv     the tidy result table behind the figure
reports/analysis_report.md      question, findings and figure link for every question
reports/answers.json            machine-readable findings used by the dashboard
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import viz
from .config import DB_PATH, FIGURES_DIR, REPORTS_DIR, SQL_DIR
from .viz import CATEGORICAL, CROP_COLOURS, REGION_COLOURS, SEQUENTIAL, TEXT_2
from .web import write_figure

TABLES_DIR = REPORTS_DIR / "tables"
QUESTIONS_DIR = SQL_DIR / "questions"
REGIONS = ["Africa", "Americas", "Asia", "Europe", "Oceania"]


@dataclass
class Answer:
    qid: str
    slug: str
    question: str
    theme: str
    findings: list[str]
    figure_file: str
    table_file: str
    sql_file: str
    numbers: dict = field(default_factory=dict)


HANDLERS: dict[str, tuple[str, Callable]] = {}


def question(theme: str):
    def deco(fn):
        HANDLERS[fn.__name__] = (theme, fn)
        return fn
    return deco


def _sql(slug: str) -> tuple[str, str]:
    path = QUESTIONS_DIR / f"{slug}.sql"
    text = path.read_text()
    m = re.search(r"^--\s*Q\d+\s+(.*)$", text, re.M)
    return text, (m.group(1).strip() if m else slug)


def cagr(a: float, b: float, years: float) -> float:
    return (b / a) ** (1 / years) - 1 if a and b and years else np.nan


def fit_line(x, y, log_x=False):
    xx = np.log10(x) if log_x else np.asarray(x, dtype=float)
    yy = np.asarray(y, dtype=float)
    ok = np.isfinite(xx) & np.isfinite(yy)
    slope, intercept = np.polyfit(xx[ok], yy[ok], 1)
    r = np.corrcoef(xx[ok], yy[ok])[0, 1]
    grid = np.linspace(xx[ok].min(), xx[ok].max(), 50)
    gx = 10 ** grid if log_x else grid
    return gx, slope * grid + intercept, slope, r


# ---------------------------------------------------------------------------
# Production
# ---------------------------------------------------------------------------
@question("Production")
def q01_global_cereal_production(df):
    first, last = df.iloc[0], df.iloc[-1]
    idx = df.set_index("year")
    base = idx.loc[1961]
    indexed = (idx[["production_mt", "area_mha", "yield_t_ha"]] / base[["production_mt", "area_mha", "yield_t_ha"]] * 100).reset_index()
    long = indexed.melt("year", var_name="series", value_name="index")
    names = {"production_mt": "Production", "area_mha": "Area harvested", "yield_t_ha": "Yield"}
    long["series"] = long["series"].map(names)
    fig = viz.line_chart(long, "year", "index", "series", "World cereals since 1961, indexed to 1961 = 100",
                         "Index (1961 = 100)", colour_map={"Production": CATEGORICAL[0], "Area harvested": CATEGORICAL[1], "Yield": CATEGORICAL[2]},
                         hover_fmt=":.0f")
    fig.add_hline(y=100, line=dict(color=viz.GRID, width=1))
    findings = [
        f"World cereal production rose from {first.production_mt:,.0f} Mt in {int(first.year)} to {last.production_mt:,.0f} Mt in {int(last.year)} "
        f"({last.production_mt / first.production_mt:.1f}x, {100 * cagr(first.production_mt, last.production_mt, last.year - first.year):.1f} % a year).",
        f"Harvested area grew only {100 * (last.area_mha / first.area_mha - 1):.0f} % ({first.area_mha:,.0f} -> {last.area_mha:,.0f} Mha); "
        f"yield rose {100 * (last.yield_t_ha / first.yield_t_ha - 1):.0f} % ({first.yield_t_ha:.2f} -> {last.yield_t_ha:.2f} t/ha), so intensification, not expansion, fed the growth.",
    ]
    return fig, findings, {"production_mt_latest": round(last.production_mt, 1), "latest_year": int(last.year),
                           "yield_t_ha_latest": round(last.yield_t_ha, 2)}


@question("Production")
def q02_top_cereal_producers(df):
    fig = viz.bar_chart(df, "area", "production_mt", f"Top 15 cereal producers, {int(df.year.iloc[0])}", "Production (Mt)",
                        orientation="h", colour_col="region", unit=" Mt", hover_fmt=":,.0f")
    fig.update_layout(height=520)
    top3 = df.head(3)
    findings = [
        f"{', '.join(top3.area)} produce {top3.share_pct.sum():.0f} % of world cereals ({top3.production_mt.sum():,.0f} Mt of the top-15 total {df.production_mt.sum():,.0f} Mt).",
        f"The 15 largest producers account for {df.share_pct.sum():.0f} % of global output; {df.region.value_counts().idxmax()} contributes the most entries in the list.",
    ]
    return fig, findings, {"top_producer": df.area.iloc[0], "top_share_pct": round(df.share_pct.iloc[0], 1)}


@question("Production")
def q03_staple_yields_by_region(df):
    fig = go.Figure()
    crops = ["Wheat", "Maize (corn)", "Rice"]
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=3, subplot_titles=crops, shared_yaxes=True, horizontal_spacing=0.04)
    for c, crop in enumerate(crops, start=1):
        for region in REGIONS:
            g = df[(df.item == crop) & (df.region == region)].sort_values("year")
            fig.add_trace(go.Scatter(x=g.year, y=g.yield_t_ha, name=region, mode="lines",
                                     line=dict(color=REGION_COLOURS[region], width=2), legendgroup=region,
                                     showlegend=(c == 1), hovertemplate=f"<b>{region}</b> %{{x}}: %{{y:.2f}} t/ha<extra></extra>"),
                          row=1, col=c)
    fig.update_layout(title="Staple yields by continent, 1961 - 2024 (t/ha)", height=500, hovermode="x unified")
    viz.legend_bottom(fig)
    fig.update_yaxes(title_text="t/ha", row=1, col=1)
    latest = df[df.year == df.year.max()].pivot(index="region", columns="item", values="yield_t_ha")
    findings = []
    for crop in crops:
        s = latest[crop].dropna().sort_values()
        findings.append(f"{crop}: {s.index[-1]} leads at {s.iloc[-1]:.1f} t/ha while {s.index[0]} trails at {s.iloc[0]:.1f} t/ha - a {s.iloc[-1] / s.iloc[0]:.1f}x gap in {int(df.year.max())}.")
    g = df[(df.item == "Maize (corn)") & (df.year.isin([1961, df.year.max()]))].pivot(index="region", columns="year", values="yield_t_ha")
    growth = (g.iloc[:, 1] / g.iloc[:, 0]).sort_values()
    findings.append(f"Since 1961 maize yields multiplied {growth.iloc[-1]:.1f}x in {growth.index[-1]} but only {growth.iloc[0]:.1f}x in {growth.index[0]}.")
    return fig, findings, {}


@question("Production")
def q04_maize_yield_gap(df):
    p90 = df.yield_t_ha.quantile(0.9)
    df = df.assign(gap_t_ha=p90 - df.yield_t_ha, gap_pct=100 * (1 - df.yield_t_ha / p90))
    df["potential_extra_mt"] = df.gap_t_ha.clip(lower=0) * df.area_ha / 1e6
    top = df.sort_values("potential_extra_mt", ascending=False).head(20)
    fig = viz.bar_chart(top, "area", "potential_extra_mt", f"Maize: extra output if yield reached the top-decile level ({p90:.1f} t/ha), 2022-24 avg",
                        "Potential additional production (Mt)", orientation="h", colour_col="region", unit=" Mt")
    fig.update_layout(height=600)
    findings = [
        f"The top-decile maize yield among countries harvesting >= 100 kha is {p90:.1f} t/ha; the median country reaches {df.yield_t_ha.median():.1f} t/ha.",
        f"Closing the gap in just {', '.join(top.area.head(3))} would add {top.potential_extra_mt.head(3).sum():,.0f} Mt - "
        f"the 20 largest gaps together represent {top.potential_extra_mt.sum():,.0f} Mt of latent production.",
        f"By region the median yield is " + ", ".join(f"{r} {v:.1f} t/ha" for r, v in df.groupby("region").yield_t_ha.median().sort_values().items()) + ".",
    ]
    return fig, findings, {"p90_yield": round(p90, 2)}, top


@question("Production")
def q05_growth_decomposition(df):
    rows = []
    for region, g in df.groupby("region"):
        g = g.sort_values("year")
        if len(g) < 2:
            continue
        a, b = g.iloc[0], g.iloc[1]
        lp = np.log(b.production_t / a.production_t)
        la = np.log(b.area_harvested_ha / a.area_harvested_ha)
        ly = np.log(b.yield_kg_ha / a.yield_kg_ha)
        rows.append(dict(region=region, growth_pct=100 * (b.production_t / a.production_t - 1),
                         area_share=100 * la / lp if lp else 0, yield_share=100 * ly / lp if lp else 0,
                         area_contrib_pct=100 * la, yield_contrib_pct=100 * ly, to_year=int(b.year)))
    out = pd.DataFrame(rows).sort_values("growth_pct")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=out.region, x=out.yield_contrib_pct, name="Yield", orientation="h", marker_color=CATEGORICAL[2],
                         hovertemplate="%{y}: yield +%{x:.1f} log-pts<extra></extra>"))
    fig.add_trace(go.Bar(y=out.region, x=out.area_contrib_pct, name="Area harvested", orientation="h", marker_color=CATEGORICAL[1],
                         hovertemplate="%{y}: area %{x:+.1f} log-pts<extra></extra>"))
    fig.update_layout(barmode="relative", bargap=0.35, title=f"Cereal production growth 2000 - {out.to_year.iloc[0]}, split into yield and area (log-points)",
                      xaxis_title="Contribution (log-points; sum = total growth)", yaxis=dict(gridcolor=viz.SURFACE))
    findings = []
    for _, r in out.iterrows():
        findings.append(f"{r.region}: production +{r.growth_pct:.0f} %, of which yield explains {r.yield_share:.0f} % and area {r.area_share:.0f} %.")
    return fig, findings, {}, out


@question("Production")
def q06_global_meat_production(df):
    names = {"Beef and Buffalo Meat, primary": "Bovine", "Meat, Poultry": "Poultry", "Meat of pig with the bone, fresh or chilled": "Pig", "Sheep and Goat Meat": "Sheep & goat"}
    df = df.assign(kind=df.item.map(names))
    fig = go.Figure()
    for i, kind in enumerate(["Poultry", "Pig", "Bovine", "Sheep & goat"]):
        g = df[df.kind == kind].sort_values("year")
        fig.add_trace(go.Scatter(x=g.year, y=g.production_mt, name=kind, mode="lines", stackgroup="one",
                                 line=dict(width=0.5, color=CATEGORICAL[i]), fillcolor=CATEGORICAL[i],
                                 hovertemplate=f"<b>{kind}</b> %{{x}}: %{{y:,.0f}} Mt<extra></extra>"))
    fig.update_layout(title="World meat production by type (Mt)", yaxis_title="Mt", hovermode="x unified")
    piv = df.pivot(index="year", columns="kind", values="production_mt")
    share = piv.div(piv.sum(axis=1), axis=0) * 100
    y0, y1 = piv.index.min(), piv.index.max()
    findings = [
        f"Total meat output grew from {piv.loc[y0].sum():,.0f} Mt ({y0}) to {piv.loc[y1].sum():,.0f} Mt ({y1}).",
        f"Poultry's share rose from {share.loc[y0, 'Poultry']:.0f} % to {share.loc[y1, 'Poultry']:.0f} %; it overtook pig meat in {int(share[share.Poultry > share.Pig].index.min())}.",
        f"Bovine meat's share fell from {share.loc[y0, 'Bovine']:.0f} % to {share.loc[y1, 'Bovine']:.0f} %.",
    ]
    return fig, findings, {"meat_mt_latest": round(piv.loc[y1].sum(), 1)}


@question("Production")
def q07_production_volatility(df):
    g = df.groupby(["area", "region"]).production_t.agg(["mean", "std", "count"]).reset_index()
    g = g[(g["count"] >= 12) & (g["mean"] >= 1e6)]
    g["cv_pct"] = 100 * g["std"] / g["mean"]
    # de-trended CV: residual std around a linear trend
    res = []
    for (area, region), s in df.groupby(["area", "region"]):
        s = s.sort_values("year")
        if len(s) >= 12 and s.production_t.mean() >= 1e6:
            coef = np.polyfit(s.year, s.production_t, 1)
            resid = s.production_t - np.polyval(coef, s.year)
            res.append(dict(area=area, region=region, detrended_cv_pct=100 * resid.std() / s.production_t.mean(), mean_mt=s.production_t.mean() / 1e6))
    out = pd.DataFrame(res).sort_values("detrended_cv_pct", ascending=False)
    top = out.head(20)
    fig = viz.bar_chart(top, "area", "detrended_cv_pct", "Most volatile cereal producers, 2010-2024 (de-trended coefficient of variation, producers >= 1 Mt)",
                        "Residual variation (% of mean output)", orientation="h", colour_col="region", unit=" %")
    fig.update_layout(height=600)
    findings = [
        f"{top.area.iloc[0]} has the most volatile cereal output ({top.detrended_cv_pct.iloc[0]:.0f} % of its {top.mean_mt.iloc[0]:.1f} Mt mean), followed by {top.area.iloc[1]} and {top.area.iloc[2]}.",
        f"{(top.region == 'Africa').sum()} of the 20 most volatile producers are African; the median de-trended CV across all {len(out)} producers is {out.detrended_cv_pct.median():.1f} %.",
    ]
    return fig, findings, {}, out


# ---------------------------------------------------------------------------
# Food security
# ---------------------------------------------------------------------------
@question("Food security")
def q08_pou_by_region(df):
    fig = viz.line_chart(df, "year", "pou_pct", "region", "Prevalence of undernourishment by region (%)", "% of population", unit=" %", hover_fmt=":.1f")
    w = df[df.region == "World"].set_index("year")
    lo, hi = w.pou_pct.idxmin(), w.index.max()
    findings = [
        f"World undernourishment fell from {w.pou_pct.iloc[0]:.1f} % ({w.index[0]}) to a low of {w.pou_pct.min():.1f} % in {lo}, then rose to {w.pou_pct.loc[hi]:.1f} % in {hi} - "
        f"{w.undernourished_m.loc[hi]:,.0f} million people.",
    ]
    latest = df[df.year == df.year.max()].set_index("region").pou_pct
    findings.append("Latest regional rates: " + ", ".join(f"{r} {v:.1f} %" for r, v in latest.drop("World", errors="ignore").sort_values(ascending=False).items()) + ".")
    af = df[df.region == "Africa"].set_index("year").pou_pct
    findings.append(f"Africa is the only region above 15 %: {af.loc[af.index.max()]:.1f} % in {af.index.max()}, up from its {af.min():.1f} % low in {af.idxmin()}.")
    return fig, findings, {"world_pou_latest": round(w.pou_pct.loc[hi], 1), "world_undernourished_m": round(w.undernourished_m.loc[hi], 0)}


@question("Food security")
def q09_pou_change_countries(df):
    latest_year = df.year.max()
    latest = df[df.year == latest_year].set_index("area")
    base = df[df.year == 2010].set_index("area")
    both = latest.join(base[["pou_pct"]], rsuffix="_2010", how="inner")
    both["change_pp"] = both.pou_pct - both.pou_pct_2010
    both = both.reset_index()
    worst = both.sort_values("pou_pct", ascending=False).head(15)
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=2, subplot_titles=(f"Highest undernourishment, {latest_year}", f"Largest change 2010 -> {latest_year} (pp)"), horizontal_spacing=0.25)
    fig.add_trace(go.Bar(y=worst.area, x=worst.pou_pct, orientation="h", marker_color=CATEGORICAL[0], name="PoU",
                         hovertemplate="%{y}: %{x:.1f} %<extra></extra>"), row=1, col=1)
    movers = pd.concat([both.sort_values("change_pp").head(8), both.sort_values("change_pp").tail(8)])
    fig.add_trace(go.Bar(y=movers.area, x=movers.change_pp, orientation="h", name="Change",
                         marker_color=[CATEGORICAL[2] if v < 0 else CATEGORICAL[7] for v in movers.change_pp],
                         hovertemplate="%{y}: %{x:+.1f} pp<extra></extra>"), row=1, col=2)
    fig.update_layout(title="Undernourishment: worst-affected countries and biggest movers", height=600, showlegend=False,
                      yaxis=dict(autorange="reversed", gridcolor=viz.SURFACE), yaxis2=dict(autorange="reversed", gridcolor=viz.SURFACE), bargap=0.3)
    imp, wor = both.sort_values("change_pp").iloc[0], both.sort_values("change_pp").iloc[-1]
    findings = [
        f"{worst.area.iloc[0]} ({worst.pou_pct.iloc[0]:.0f} %), {worst.area.iloc[1]} ({worst.pou_pct.iloc[1]:.0f} %) and {worst.area.iloc[2]} ({worst.pou_pct.iloc[2]:.0f} %) have the highest undernourishment in {latest_year}.",
        f"Biggest improvement since 2010: {imp.area} ({imp.change_pp:+.0f} pp to {imp.pou_pct:.0f} %). Biggest deterioration: {wor.area} ({wor.change_pp:+.0f} pp to {wor.pou_pct:.0f} %).",
        f"{(both.change_pp < 0).sum()} of {len(both)} countries improved; {(both.change_pp > 5).sum()} worsened by more than 5 pp.",
    ]
    return fig, findings, {"latest_year": int(latest_year)}, both.sort_values("pou_pct", ascending=False)


@question("Food security")
def q10_fies_gender_gap(df):
    fig = viz.line_chart(df, "year", "gap_pp", "region", "Food insecurity gender gap: women minus men (percentage points, moderate or severe)", "Gap (pp)", hover_fmt=":+.1f", unit=" pp")
    fig.add_hline(y=0, line=dict(color=viz.TEXT_2, width=1))
    latest = df[df.year == df.year.max()].set_index("region")
    w = latest.loc["World"] if "World" in latest.index else latest.iloc[0]
    findings = [
        f"Globally {w.fies_mod_sev_f_pct:.1f} % of women vs {w.fies_mod_sev_m_pct:.1f} % of men were moderately or severely food insecure in {int(df.year.max())} - a gap of {w.gap_pp:+.1f} pp.",
        "Largest gaps: " + ", ".join(f"{r} {v:+.1f} pp" for r, v in latest.gap_pp.drop("World", errors="ignore").sort_values(ascending=False).head(3).items()) + ".",
        f"The world gap peaked at {df[df.region == 'World'].gap_pp.max():+.1f} pp in {int(df[df.region == 'World'].set_index('year').gap_pp.idxmax())} (pandemic years).",
    ]
    return fig, findings, {}


@question("Food security")
def q11_income_vs_pou(df):
    df = df[(df.gdp_cap_ppp > 0) & (df.pou_pct > 0)]
    gx, gy, slope, r = fit_line(df.gdp_cap_ppp, np.log10(df.pou_pct), log_x=True)
    fig = viz.scatter_chart(df, "gdp_cap_ppp", "pou_pct", "Income vs undernourishment (latest year per country)", "GDP per capita, PPP (Int$)", "Undernourishment (%)",
                            log_x=True, log_y=True, size_col="population_m", trend=(gx, 10 ** gy, f"log-log fit (r = {r:.2f})"), hover_extra=["year"])
    findings = [
        f"Across {len(df)} countries the log-log correlation between income and undernourishment is r = {r:.2f}; each doubling of income is associated with a {100 * (1 - 2 ** slope):.0f} % lower PoU.",
        f"Countries above Int$ 30,000 per head have a maximum PoU of {df[df.gdp_cap_ppp > 30000].pou_pct.max():.1f} % (2.5 % is FAO's reporting floor); below Int$ 3,000 the median PoU is {df[df.gdp_cap_ppp < 3000].pou_pct.median():.0f} %.",
    ]
    outliers = df.assign(resid=np.log10(df.pou_pct) - (slope * np.log10(df.gdp_cap_ppp) + (gy[0] - slope * np.log10(gx[0])))).sort_values("resid")
    findings.append(f"Worst performers for their income level: {', '.join(outliers.tail(3).area)}; best: {', '.join(outliers.head(3).area)}.")
    return fig, findings, {"r_income_pou": round(r, 2)}


@question("Food security")
def q12_stunting_vs_supply(df):
    gx, gy, slope, r = fit_line(df.des_adequacy_pct, df.stunting_pct)
    fig = viz.scatter_chart(df, "des_adequacy_pct", "stunting_pct", "Dietary energy supply adequacy vs child stunting", "Dietary energy supply adequacy (% of requirement)", "Children under 5 stunted (%)",
                            trend=(gx, gy, f"linear fit (r = {r:.2f})"), hover_extra=["sanitation_basic_pct", "year"])
    ok = df.dropna(subset=["sanitation_basic_pct"])
    r2 = np.corrcoef(ok.sanitation_basic_pct, ok.stunting_pct)[0, 1]
    findings = [
        f"Energy adequacy alone explains stunting only moderately (r = {r:.2f}, n = {len(df)}); {(df[df.des_adequacy_pct >= 120].stunting_pct > 20).sum()} countries with >= 120 % adequacy still have stunting above 20 %.",
        f"Basic sanitation coverage correlates more strongly with stunting (r = {r2:.2f}) - calories are necessary but not sufficient.",
        f"Highest stunting: " + ", ".join(f"{a} {v:.0f} %" for a, v in df.sort_values('stunting_pct', ascending=False).head(3)[['area', 'stunting_pct']].values) + ".",
    ]
    return fig, findings, {"r_adequacy_stunting": round(r, 2), "r_sanitation_stunting": round(r2, 2)}


@question("Food security")
def q13_obesity_trends(df):
    fig = viz.line_chart(df, "year", "obesity_pct", "region", "Adult obesity prevalence by region (%)", "% of adults", unit=" %", hover_fmt=":.1f")
    w = df[df.region == "World"].set_index("year").obesity_pct
    latest = df[df.year == df.year.max()].set_index("region").obesity_pct
    findings = [
        f"World adult obesity rose from {w.iloc[0]:.1f} % in {w.index[0]} to {w.iloc[-1]:.1f} % in {w.index[-1]} - it has never fallen in a single year.",
        "Latest: " + ", ".join(f"{r} {v:.1f} %" for r, v in latest.drop("World", errors="ignore").sort_values(ascending=False).items()) + ".",
        f"Fastest-rising region: {df[df.region != 'World'].groupby('region').obesity_pct.agg(lambda s: s.iloc[-1] - s.iloc[0]).idxmax()}.",
    ]
    return fig, findings, {"world_obesity_latest": round(w.iloc[-1], 1)}


@question("Food security")
def q14_cereal_import_dependency(df):
    top = df[df.population_m >= 1].head(25)
    fig = viz.bar_chart(top, "area", "cereal_import_dep_pct", "Cereal import dependency ratio (countries >= 1 M people), latest 3-year average", "Imports as % of domestic supply",
                        orientation="h", colour_col="region", unit=" %")
    fig.update_layout(height=700)
    findings = [
        f"{(df.cereal_import_dep_pct >= 99).sum()} countries import essentially all (>= 99 %) of the cereals they consume, led by {', '.join(top.area.head(3))}.",
        f"{(df.cereal_import_dep_pct >= 50).sum()} countries import at least half their cereals; {(df.cereal_import_dep_pct < 0).sum()} are net exporters (negative ratio).",
        f"Regionally the median dependency is " + ", ".join(f"{r} {v:.0f} %" for r, v in df.groupby("region").cereal_import_dep_pct.median().sort_values(ascending=False).items()) + ".",
    ]
    return fig, findings, {}


@question("Food security")
def q15_healthy_diet_affordability(df):
    countries = df[(df.is_aggregate == 0)]
    latest = countries[countries.year == countries.year.max()].dropna(subset=["unaffordable_pct"]).sort_values("unaffordable_pct", ascending=False)
    regions = df[df.is_aggregate == 1].drop(columns=["region"]).rename(columns={"area": "region"})
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Share unable to afford a healthy diet, by region (%)", f"Countries with the highest share, {int(latest.year.iloc[0])}"), horizontal_spacing=0.22, column_widths=[0.5, 0.5])
    for region, g in regions.groupby("region"):
        g = g.sort_values("year")
        fig.add_trace(go.Scatter(x=g.year, y=g.unaffordable_pct, name=region, mode="lines", line=dict(color=viz.colour_for_region(region), width=2),
                                 hovertemplate=f"<b>{region}</b> %{{x}}: %{{y:.1f}} %<extra></extra>"), row=1, col=1)
    top = latest.head(15)
    fig.add_trace(go.Bar(y=top.area, x=top.unaffordable_pct, orientation="h", marker_color=CATEGORICAL[0], showlegend=False,
                         customdata=top.cohd_ppp_per_day, hovertemplate="%{y}: %{x:.1f} % (diet costs %{customdata:.2f} $/day)<extra></extra>"), row=1, col=2)
    fig.update_layout(title="Cost and affordability of a healthy diet", height=600, yaxis2=dict(autorange="reversed", gridcolor=viz.SURFACE), bargap=0.3)
    viz.legend_bottom(fig)
    w = regions[regions.region == "World"].set_index("year")
    findings = [
        f"A healthy diet cost {w.cohd_ppp_per_day.dropna().iloc[-1]:.2f} PPP$ per person per day in {int(w.cohd_ppp_per_day.dropna().index[-1])}, up from {w.cohd_ppp_per_day.dropna().iloc[0]:.2f} in {int(w.cohd_ppp_per_day.dropna().index[0])}.",
        f"{w.unaffordable_pct.iloc[-1]:.1f} % of the world's people ({w.unaffordable_m.iloc[-1]:,.0f} million) could not afford it in {int(w.index[-1])}, down from {w.unaffordable_pct.iloc[0]:.1f} % in {int(w.index[0])}.",
        f"Worst affected: " + ", ".join(f"{a} {v:.0f} %" for a, v in top.head(3)[["area", "unaffordable_pct"]].values) + ".",
    ]
    return fig, findings, {"world_unaffordable_pct": round(w.unaffordable_pct.iloc[-1], 1), "world_unaffordable_m": round(w.unaffordable_m.iloc[-1], 0)}, latest


# ---------------------------------------------------------------------------
# Inputs & land
# ---------------------------------------------------------------------------
@question("Inputs & land")
def q16_nitrogen_by_region(df):
    fig = viz.line_chart(df, "year", "n_kg_per_ha", "region", "Nitrogen fertilizer use per hectare of cropland (kg N/ha)", "kg N per ha", unit=" kg/ha", hover_fmt=":.1f")
    latest = df[df.year == df.year.max()].set_index("region")
    w = df[df.region == "World"].set_index("year")
    findings = [
        f"World nitrogen use is {w.n_kg_per_ha.iloc[-1]:.0f} kg N/ha of cropland ({w.n_use_mt.iloc[-1]:.0f} Mt N in {w.index[-1]}), {w.n_kg_per_ha.iloc[-1] / w.n_kg_per_ha.iloc[0]:.1f}x the {w.index[0]} level.",
        "Latest intensity: " + ", ".join(f"{r} {v:.0f}" for r, v in latest.n_kg_per_ha.drop("World", errors="ignore").sort_values(ascending=False).items()) + " kg N/ha.",
        f"Africa applies {latest.loc['Asia', 'n_kg_per_ha'] / latest.loc['Africa', 'n_kg_per_ha']:.0f}x less nitrogen per hectare than Asia.",
    ]
    return fig, findings, {"world_n_kg_ha": round(w.n_kg_per_ha.iloc[-1], 1)}


@question("Inputs & land")
def q17_fertilizer_vs_yield(df):
    gx, gy, slope, r = fit_line(df.n_kg_per_ha, np.log10(df.cereal_yield_t_ha), log_x=True)
    fig = viz.scatter_chart(df, "n_kg_per_ha", "cereal_yield_t_ha", f"Nitrogen intensity vs cereal yield, {int(df.year.iloc[0])}", "Nitrogen use (kg N per ha cropland, log)", "Cereal yield (t/ha, log)",
                            log_x=True, log_y=True, size_col="area_harvested_ha", trend=(gx, 10 ** gy, f"log-log fit (r = {r:.2f})"))
    findings = [
        f"Across {len(df)} countries yield scales with nitrogen intensity at r = {r:.2f}; a doubling of N/ha is associated with {100 * (2 ** slope - 1):.0f} % higher cereal yields.",
        f"Diminishing returns are visible: countries above 150 kg N/ha average {df[df.n_kg_per_ha > 150].cereal_yield_t_ha.mean():.1f} t/ha vs {df[df.n_kg_per_ha.between(50, 150)].cereal_yield_t_ha.mean():.1f} t/ha for 50-150 kg.",
        f"Most nitrogen-efficient large producers (>= 1 Mha cereals, yield furthest above the fit): " + ", ".join(df[df.area_harvested_ha >= 1e6].assign(res=np.log10(df.cereal_yield_t_ha) - (slope * np.log10(df.n_kg_per_ha) + gy[0] - slope * np.log10(gx[0]))).sort_values("res").tail(3).area) + ".",
    ]
    return fig, findings, {"r_n_yield": round(r, 2)}


@question("Inputs & land")
def q18_land_use_by_region(df):
    latest = df[df.year == df.year.max()].copy()
    latest["other_kha"] = latest.land_area_kha - latest.cropland_kha - latest.pastures_kha - latest.forest_kha
    long = latest.melt(["region"], ["cropland_kha", "pastures_kha", "forest_kha", "other_kha"], var_name="use", value_name="kha")
    names = {"cropland_kha": "Cropland", "pastures_kha": "Permanent meadows & pastures", "forest_kha": "Forest", "other_kha": "Other land"}
    long["use"] = long.use.map(names)
    long["share"] = 100 * long.kha / long.groupby("region").kha.transform("sum")
    fig = go.Figure()
    for i, use in enumerate(names.values()):
        g = long[long.use == use]
        fig.add_trace(go.Bar(x=g.region, y=g.share, name=use, marker_color=[CATEGORICAL[0], CATEGORICAL[2], CATEGORICAL[5], viz.MUTED][i],
                             hovertemplate=f"%{{x}} · {use}: %{{y:.1f}} %<extra></extra>"))
    fig.update_layout(barmode="stack", bargap=0.35, title=f"Land use composition by region, {int(latest.year.iloc[0])} (% of land area)", yaxis_title="% of land area")
    chg = df[df.year.isin([1990, df.year.max()])].sort_values("year").groupby("region").agg(crop0=("cropland_kha", "first"), crop1=("cropland_kha", "last"), for0=("forest_kha", "first"), for1=("forest_kha", "last"), past0=("pastures_kha", "first"), past1=("pastures_kha", "last"))
    chg["cropland_chg_pct"] = 100 * (chg.crop1 / chg.crop0 - 1)
    chg["forest_chg_pct"] = 100 * (chg.for1 / chg.for0 - 1)
    chg["forest_chg_mha"] = (chg.for1 - chg.for0) / 1000
    findings = [
        f"Cropland covers {latest.set_index('region').loc['World'].cropland_kha / latest.set_index('region').loc['World'].land_area_kha * 100:.0f} % of the world's land, pastures {latest.set_index('region').loc['World'].pastures_kha / latest.set_index('region').loc['World'].land_area_kha * 100:.0f} % and forest {latest.set_index('region').loc['World'].forest_kha / latest.set_index('region').loc['World'].land_area_kha * 100:.0f} %.",
        f"Since 1990 forest area fell {abs(chg.loc['World', 'forest_chg_mha']):.0f} Mha globally ({chg.loc['World', 'forest_chg_pct']:+.1f} %); Africa {chg.loc['Africa', 'forest_chg_pct']:+.1f} %, Americas {chg.loc['Americas', 'forest_chg_pct']:+.1f} %, Europe {chg.loc['Europe', 'forest_chg_pct']:+.1f} %, Asia {chg.loc['Asia', 'forest_chg_pct']:+.1f} %.",
        f"Cropland expanded most in Africa ({chg.loc['Africa', 'cropland_chg_pct']:+.0f} %) and contracted in Europe ({chg.loc['Europe', 'cropland_chg_pct']:+.0f} %).",
    ]
    return fig, findings, {}, chg.reset_index()


@question("Inputs & land")
def q19_irrigation_vs_yield(df):
    df = df.assign(irrigation_share_pct=df.irrigation_share_pct.clip(upper=100))
    gx, gy, slope, r = fit_line(df.irrigation_share_pct, df.cereal_yield_t_ha)
    fig = viz.scatter_chart(df, "irrigation_share_pct", "cereal_yield_t_ha", "Share of arable land equipped for irrigation vs cereal yield", "Arable land equipped for irrigation (%)", "Cereal yield (t/ha)",
                            size_col="area_harvested_ha", trend=(gx, gy, f"linear fit (r = {r:.2f})"), hover_extra=["year"])
    findings = [
        f"Irrigation share and cereal yield correlate at r = {r:.2f} across {len(df)} countries; each additional 10 pp of irrigated arable land is associated with +{10 * slope:.2f} t/ha.",
        f"Countries with under 5 % irrigated arable land average {df[df.irrigation_share_pct < 5].cereal_yield_t_ha.mean():.1f} t/ha; those above 40 % average {df[df.irrigation_share_pct > 40].cereal_yield_t_ha.mean():.1f} t/ha.",
        f"Rain-fed high performers (< 10 % irrigated, > 6 t/ha): {', '.join(df[(df.irrigation_share_pct < 10) & (df.cereal_yield_t_ha > 6)].area) or 'none'}.",
        "Data note: FAOSTAT's food-security indicator 21034 reports Egypt at 4 % 'of arable land', i.e. it is effectively expressed against total land area; the ratio here is rebuilt from the land-use domain (RL 6690 / (6621 + 6650)).",
    ]
    return fig, findings, {"r_irrigation_yield": round(r, 2)}


@question("Inputs & land")
def q20_organic_agriculture(df):
    fig = viz.line_chart(df, "year", "organic_share_pct", "region", "Organic agriculture as a share of agricultural land (%)", "% of agricultural land", unit=" %", hover_fmt=":.2f")
    w = df[df.region == "World"].set_index("year")
    latest = df[df.year == df.year.max()].set_index("region")
    findings = [
        f"Organic farming covers {w.organic_agri_kha.iloc[-1] / 1000:.0f} Mha worldwide ({w.organic_share_pct.iloc[-1]:.2f} % of agricultural land) in {w.index[-1]}, {w.organic_agri_kha.iloc[-1] / w.organic_agri_kha.iloc[0]:.1f}x the {w.index[0]} area.",
        "Regional shares: " + ", ".join(f"{r} {v:.2f} %" for r, v in latest.organic_share_pct.drop("World", errors="ignore").sort_values(ascending=False).items()) + ".",
    ]
    return fig, findings, {}


# ---------------------------------------------------------------------------
# Climate & emissions
# ---------------------------------------------------------------------------
@question("Climate & emissions")
def q21_temperature_by_region(df):
    df = df.sort_values(["region", "year"])
    df["rolling5"] = df.groupby("region").temp_change_c.transform(lambda s: s.rolling(5, min_periods=3).mean())
    fig = viz.line_chart(df, "year", "rolling5", "region", "Land temperature change vs 1951-1980 baseline (5-year rolling mean, °C)", "°C", unit=" °C", hover_fmt=":.2f")
    fig.add_hline(y=0, line=dict(color=viz.TEXT_2, width=1))
    recent = df[df.year >= df.year.max() - 4].groupby("region").temp_change_c.mean().sort_values(ascending=False)
    w = df[df.region == "World"].set_index("year")
    findings = [
        f"World land temperature in the last five years averaged {recent['World']:+.2f} °C above the 1951-1980 baseline; the single warmest year was {int(w.temp_change_c.idxmax())} at {w.temp_change_c.max():+.2f} °C.",
        "Five-year mean by region: " + ", ".join(f"{r} {v:+.2f} °C" for r, v in recent.drop("World").items()) + ".",
        f"Europe has warmed fastest; Oceania least. The 1960s world average was {w[w.index < 1970].temp_change_c.mean():+.2f} °C.",
    ]
    return fig, findings, {"world_temp_change_5yr": round(recent["World"], 2)}


@question("Climate & emissions")
def q22_agrifood_emissions_by_region(df):
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Agrifood-system emissions (Gt CO2eq)", "Agrifood share of all emissions incl. LULUCF (%)"), horizontal_spacing=0.08)
    for region, g in df.groupby("region"):
        g = g.sort_values("year")
        c = viz.colour_for_region(region)
        fig.add_trace(go.Scatter(x=g.year, y=g.agrifood_gt, name=region, mode="lines", line=dict(color=c, width=2), legendgroup=region,
                                 hovertemplate=f"<b>{region}</b> %{{x}}: %{{y:.2f}} Gt<extra></extra>"), row=1, col=1)
        fig.add_trace(go.Scatter(x=g.year, y=g.agrifood_share_pct, name=region, mode="lines", line=dict(color=c, width=2), legendgroup=region, showlegend=False,
                                 hovertemplate=f"<b>{region}</b> %{{x}}: %{{y:.1f}} %<extra></extra>"), row=1, col=2)
    fig.update_layout(title="Agrifood-system emissions by region", height=500, hovermode="x unified")
    viz.legend_bottom(fig)
    w = df[df.region == "World"].set_index("year")
    latest = df[df.year == df.year.max()].set_index("region")
    findings = [
        f"Global agrifood systems emitted {w.agrifood_gt.iloc[-1]:.1f} Gt CO2eq in {w.index[-1]} - {w.agrifood_share_pct.iloc[-1]:.0f} % of all anthropogenic emissions - split into farm gate {w.farm_gate_gt.iloc[-1]:.1f} Gt, land-use change {w.luc_gt.iloc[-1]:.1f} Gt and pre/post-production {w.pre_post_gt.iloc[-1]:.1f} Gt.",
        f"Since {w.index[0]} agrifood emissions rose {100 * (w.agrifood_gt.iloc[-1] / w.agrifood_gt.iloc[0] - 1):.0f} % while their share of the total fell from {w.agrifood_share_pct.iloc[0]:.0f} % to {w.agrifood_share_pct.iloc[-1]:.0f} % as energy emissions grew faster.",
        "Latest by region: " + ", ".join(f"{r} {v:.2f} Gt" for r, v in latest.agrifood_gt.drop("World").sort_values(ascending=False).items()) + ".",
    ]
    return fig, findings, {"world_agrifood_gt": round(w.agrifood_gt.iloc[-1], 2), "world_agrifood_share": round(w.agrifood_share_pct.iloc[-1], 1)}


@question("Climate & emissions")
def q23_emissions_per_capita(df):
    top = df.sort_values("agrifood_t_per_cap", ascending=False).head(20)
    fig = viz.bar_chart(top, "area", "agrifood_t_per_cap", f"Agrifood-system emissions per person, {int(df.year.iloc[0])} (countries > 1 M people)", "t CO2eq per person",
                        orientation="h", colour_col="region", unit=" t", hover_fmt=":.2f")
    fig.update_layout(height=600)
    ok = df.dropna(subset=["gdp_cap_ppp"])
    r = np.corrcoef(np.log10(ok.gdp_cap_ppp), np.log10(ok.agrifood_t_per_cap))[0, 1]
    findings = [
        f"{top.area.iloc[0]} ({top.agrifood_t_per_cap.iloc[0]:.1f} t), {top.area.iloc[1]} ({top.agrifood_t_per_cap.iloc[1]:.1f} t) and {top.area.iloc[2]} ({top.agrifood_t_per_cap.iloc[2]:.1f} t) have the highest agrifood emissions per person - land-use change and cattle dominate.",
        f"The population-weighted world average is {(df.agrifood_t_per_cap * df.population_m).sum() / df.population_m.sum():.2f} t per person; the median country is {df.agrifood_t_per_cap.median():.2f} t.",
        f"Per-capita agrifood emissions are only weakly tied to income (log-log r = {r:.2f}) - unlike energy emissions, they follow land and livestock.",
    ]
    return fig, findings, {"r_income_agrifood": round(r, 2)}


@question("Climate & emissions")
def q24_temperature_vs_wheat_yield(df):
    rows = []
    for (area, region), g in df.groupby(["area", "region"]):
        g = g.sort_values("year")
        if len(g) < 20:
            continue
        coef = np.polyfit(g.year, g.wheat_yield_t_ha, 2)
        g = g.assign(yield_anom_pct=100 * (g.wheat_yield_t_ha / np.polyval(coef, g.year) - 1),
                     temp_anom=g.temp_change_c - g.temp_change_c.mean())
        r = np.corrcoef(g.temp_anom, g.yield_anom_pct)[0, 1]
        rows.append(dict(area=area, region=region, r=r, n=len(g), mean_area_ha=g.area_harvested_ha.mean()))
    out = pd.DataFrame(rows).sort_values("r")
    fig = viz.bar_chart(out, "area", "r", "Correlation between temperature anomaly and de-trended wheat yield, by country (1990-2024)", "Pearson r",
                        orientation="h", colour_col="region", hover_fmt=":.2f")
    fig.update_layout(height=900)
    fig.add_vline(x=0, line=dict(color=viz.TEXT_2, width=1))
    neg = (out.r < 0).mean() * 100
    findings = [
        f"In {neg:.0f} % of the {len(out)} major wheat producers, hotter-than-usual years coincide with below-trend yields (negative r); the median correlation is {out.r.median():.2f}.",
        f"Most heat-sensitive: " + ", ".join(f"{a} (r = {v:.2f})" for a, v in out.head(3)[["area", "r"]].values) + ".",
        f"Heat-tolerant or cold-limited systems where warm years help: " + ", ".join(f"{a} (r = {v:+.2f})" for a, v in out.tail(3)[["area", "r"]].values) + ".",
    ]
    return fig, findings, {"share_negative_r": round(neg, 1)}, out


@question("Climate & emissions")
def q25_farm_gate_composition(df):
    df = df.assign(other_gt=df.farm_gate_gt - df.enteric_gt - df.manure_gt - df.rice_gt - df.synthetic_fert_gt)
    parts = {"enteric_gt": "Enteric fermentation", "manure_gt": "Manure management", "rice_gt": "Rice cultivation", "synthetic_fert_gt": "Synthetic fertilizers", "other_gt": "Other farm-gate"}
    fig = go.Figure()
    for i, (col, name) in enumerate(parts.items()):
        fig.add_trace(go.Scatter(x=df.year, y=df[col], name=name, mode="lines", stackgroup="one", line=dict(width=0.5, color=CATEGORICAL[i]), fillcolor=CATEGORICAL[i],
                                 hovertemplate=f"<b>{name}</b> %{{x}}: %{{y:.2f}} Gt<extra></extra>"))
    fig.update_layout(title="World farm-gate emissions by source (Gt CO2eq)", yaxis_title="Gt CO2eq", hovermode="x unified")
    last = df.iloc[-1]
    findings = [
        f"Farm-gate emissions reached {last.farm_gate_gt:.2f} Gt CO2eq in {int(last.year)}: enteric fermentation {100 * last.enteric_gt / last.farm_gate_gt:.0f} %, manure {100 * last.manure_gt / last.farm_gate_gt:.0f} %, synthetic fertilizers {100 * last.synthetic_fert_gt / last.farm_gate_gt:.0f} %, rice {100 * last.rice_gt / last.farm_gate_gt:.0f} %.",
        f"Synthetic-fertilizer emissions grew fastest since {int(df.year.iloc[0])} ({df.synthetic_fert_gt.iloc[-1] / df.synthetic_fert_gt.iloc[0]:.1f}x) versus {df.enteric_gt.iloc[-1] / df.enteric_gt.iloc[0]:.1f}x for enteric fermentation.",
    ]
    return fig, findings, {}


# ---------------------------------------------------------------------------
# People & prices
# ---------------------------------------------------------------------------
@question("People & prices")
def q26_per_capita_cereal(df):
    fig = viz.line_chart(df, "year", "kg_per_capita", "region", "Cereal production per person (kg/year)", "kg per person", unit=" kg", hover_fmt=":.0f")
    w = df[df.region == "World"].set_index("year")
    latest = df[df.year == df.year.max()].set_index("region")
    findings = [
        f"World cereal output per person rose from {w.kg_per_capita.iloc[0]:.0f} kg in {w.index[0]} to {w.kg_per_capita.iloc[-1]:.0f} kg in {w.index[-1]} even as population grew from {w.population_m.iloc[0] / 1000:.1f} to {w.population_m.iloc[-1] / 1000:.1f} billion.",
        "Latest by region: " + ", ".join(f"{r} {v:.0f} kg" for r, v in latest.kg_per_capita.drop("World").sort_values(ascending=False).items()) + ".",
        f"Africa's per-capita output ({latest.loc['Africa', 'kg_per_capita']:.0f} kg) is {latest.loc['Americas', 'kg_per_capita'] / latest.loc['Africa', 'kg_per_capita']:.1f}x below the Americas'.",
    ]
    return fig, findings, {"world_kg_per_capita": round(w.kg_per_capita.iloc[-1], 0)}


@question("People & prices")
def q27_urbanisation_and_land(df):
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Urban share of population (%)", "Agricultural land per person (ha)"), horizontal_spacing=0.08)
    for region, g in df.groupby("region"):
        g = g.sort_values("year")
        c = viz.colour_for_region(region)
        fig.add_trace(go.Scatter(x=g.year, y=g.urban_share_pct, name=region, mode="lines", line=dict(color=c, width=2), legendgroup=region,
                                 hovertemplate=f"<b>{region}</b> %{{x}}: %{{y:.1f}} %<extra></extra>"), row=1, col=1)
        gg = g.dropna(subset=["agri_ha_per_capita"])
        fig.add_trace(go.Scatter(x=gg.year, y=gg.agri_ha_per_capita, name=region, mode="lines", line=dict(color=c, width=2), legendgroup=region, showlegend=False,
                                 hovertemplate=f"<b>{region}</b> %{{x}}: %{{y:.2f}} ha<extra></extra>"), row=1, col=2)
    fig.update_layout(title="Urbanisation and land per person", height=500, hovermode="x unified")
    viz.legend_bottom(fig)
    w = df[df.region == "World"].dropna(subset=["agri_ha_per_capita"]).set_index("year")
    findings = [
        f"The urban share of the world population rose from {w.urban_share_pct.iloc[0]:.0f} % ({w.index[0]}) to {w.urban_share_pct.iloc[-1]:.0f} % ({w.index[-1]}).",
        f"Agricultural land per person fell from {w.agri_ha_per_capita.iloc[0]:.2f} ha to {w.agri_ha_per_capita.iloc[-1]:.2f} ha over the same period ({100 * (w.agri_ha_per_capita.iloc[-1] / w.agri_ha_per_capita.iloc[0] - 1):.0f} %).",
    ]
    return fig, findings, {}


@question("People & prices")
def q28_staple_price_trends(df):
    stats = df.groupby(["item", "year"]).usd_per_tonne.agg(median="median", q1=lambda s: s.quantile(0.25), q3=lambda s: s.quantile(0.75), n="count").reset_index()
    stats = stats[stats.n >= 15]
    fig = go.Figure()
    for item, g in stats.groupby("item"):
        c = CROP_COLOURS.get(item, CATEGORICAL[0])
        g = g.sort_values("year")
        fig.add_trace(go.Scatter(x=list(g.year) + list(g.year[::-1]), y=list(g.q3) + list(g.q1[::-1]), fill="toself", fillcolor=c, opacity=0.12, line=dict(width=0), hoverinfo="skip", showlegend=False, legendgroup=item))
        fig.add_trace(go.Scatter(x=g.year, y=g["median"], name=item, mode="lines", line=dict(color=c, width=2), legendgroup=item,
                                 customdata=g.n, hovertemplate=f"<b>{item}</b> %{{x}}: median %{{y:,.0f}} USD/t (n = %{{customdata}})<extra></extra>"))
    fig.update_layout(title="Producer prices for staples: cross-country median and interquartile band (USD/tonne)", yaxis_title="USD per tonne", hovermode="x unified")
    piv = stats.pivot(index="year", columns="item", values="median")
    findings = []
    for item in piv.columns:
        s = piv[item].dropna()
        findings.append(f"{item}: median producer price {s.iloc[-1]:,.0f} USD/t in {s.index[-1]}, peak {s.max():,.0f} USD/t in {s.idxmax()}; {100 * (s.iloc[-1] / s.loc[2019] - 1):+.0f} % vs 2019.")
    return fig, findings, {}, stats


SHORT_ITEMS = {"Hen eggs in shell, fresh": "Hen eggs", "Raw milk of cattle": "Cow milk", "Maize (corn)": "Maize"}


@question("People & prices")
def q29_price_dispersion(df):
    df = df.assign(item=df.item.map(lambda x: SHORT_ITEMS.get(x, x)))
    order = df.groupby("item").usd_per_tonne.median().sort_values().index
    fig = go.Figure()
    for i, item in enumerate(order):
        g = df[df.item == item]
        fig.add_trace(go.Box(y=g.usd_per_tonne, name=item, boxpoints="all", jitter=0.4, pointpos=0, marker=dict(color=CATEGORICAL[i % 8], size=6, opacity=0.6),
                             line=dict(color=CATEGORICAL[i % 8], width=1.5), fillcolor="rgba(0,0,0,0)", customdata=g.area,
                             hovertemplate="%{customdata}: %{y:,.0f} USD/t<extra></extra>"))
    fig.update_layout(title=f"Producer price dispersion across countries, {int(df.year.max())} (USD/tonne, log scale)", yaxis_type="log", yaxis_title="USD per tonne", showlegend=False, height=520)
    disp = df.groupby("item").usd_per_tonne.agg(lambda s: s.quantile(0.9) / s.quantile(0.1)).sort_values(ascending=False)
    findings = [
        f"The 90th/10th percentile price ratio across countries is widest for {disp.index[0]} ({disp.iloc[0]:.1f}x) and narrowest for {disp.index[-1]} ({disp.iloc[-1]:.1f}x).",
        "Median prices: " + ", ".join(f"{i} {v:,.0f}" for i, v in df.groupby('item').usd_per_tonne.median().sort_values().items()) + " USD/t.",
    ]
    return fig, findings, {}


@question("People & prices")
def q30_production_vs_population_growth(df):
    piv = df.pivot_table(index=["area", "region"], columns="year", values=["production_t", "population"]).dropna()
    out = pd.DataFrame({"prod_growth_pct": 100 * (piv[("production_t", 2024)] / piv[("production_t", 2010)] - 1),
                        "pop_growth_pct": 100 * (piv[("population", 2024)] / piv[("population", 2010)] - 1),
                        "population_m": piv[("population", 2024)] / 1e6}).reset_index()
    out["gap_pp"] = out.prod_growth_pct - out.pop_growth_pct
    out = out[(out.population_m >= 1) & (piv[("production_t", 2010)].values >= 100000)]
    lim = max(abs(out.prod_growth_pct).max(), abs(out.pop_growth_pct).max())
    fig = viz.scatter_chart(out, "pop_growth_pct", "prod_growth_pct", "Cereal production growth vs population growth, 2010 -> 2024", "Population growth (%)", "Cereal production growth (%)",
                            size_col="population_m", trend=([-10, 80], [-10, 80], "production = population"))
    fig.update_yaxes(range=[-60, min(lim, 250)])
    lag = out.sort_values("gap_pp").head(15)
    findings = [
        f"In {(out.gap_pp < 0).sum()} of {len(out)} countries cereal output grew slower than population between 2010 and 2024 (points below the diagonal).",
        f"Largest shortfalls: " + ", ".join(f"{a} ({g:+.0f} pp)" for a, g in lag.head(5)[["area", "gap_pp"]].values) + ".",
        f"{(out.region == 'Africa').sum()} African countries are in the sample; {((out.region == 'Africa') & (out.gap_pp < 0)).sum()} of them fell behind population growth.",
    ]
    return fig, findings, {"countries_lagging": int((out.gap_pp < 0).sum())}, out.sort_values("gap_pp")


# ---------------------------------------------------------------------------
# Composite & governance
# ---------------------------------------------------------------------------
@question("Composite & governance")
def q31_food_system_scorecard(df):
    cols = {"pou_pct": -1, "stunting_pct": -1, "cereal_import_dep_pct": -1, "unaffordable_pct": -1, "agrifood_t_per_cap": -1, "obesity_pct": -1, "cereal_yield_t_ha": 1, "des_adequacy_pct": 1}
    d = df.copy()
    z = pd.DataFrame(index=d.index)
    for c, sign in cols.items():
        s = d[c].astype(float)
        z[c] = (sign * (s - s.mean()) / s.std()).clip(-3, 3)   # winsorise so one outlier cannot dominate
    d["score"] = z.mean(axis=1, skipna=True)
    d["n_indicators"] = z.notna().sum(axis=1)
    d = d[d.n_indicators >= 6].sort_values("score", ascending=False)
    show = pd.concat([d.head(12), d.tail(12)])
    zz = z.loc[show.index].rename(columns={"pou_pct": "Undernourishment", "stunting_pct": "Stunting", "cereal_import_dep_pct": "Import dependency", "unaffordable_pct": "Diet unaffordable", "agrifood_t_per_cap": "Agrifood CO2e/cap", "obesity_pct": "Obesity", "cereal_yield_t_ha": "Cereal yield", "des_adequacy_pct": "Energy adequacy"})
    fig = viz.heatmap(zz.values.round(2), list(zz.columns), list(show.area), "Food-system scorecard: standardised indicator scores (blue = better, red = worse) for the 12 strongest and 12 weakest countries",
                      colorscale=viz.DIVERGING[::-1], zmid=0, fmt=":.2f")
    fig.update_layout(height=760, margin=dict(l=210))
    findings = [
        f"Composite score across {len(cols)} indicators (n = {len(d)} countries with >= 6): strongest {', '.join(d.head(3).area)}; weakest {', '.join(d.tail(3).area)}.",
        f"Median score by region: " + ", ".join(f"{r} {v:+.2f}" for r, v in d.groupby("region").score.median().sort_values(ascending=False).items()) + ".",
        f"Least-developed countries score {d[d.is_ldc == 1].score.median():+.2f} on median versus {d[d.is_ldc == 0].score.median():+.2f} for the rest.",
    ]
    return fig, findings, {}, d[["area", "region", "score", "n_indicators"] + list(cols)]


@question("Composite & governance")
def q32_data_provenance(df):
    df["flag_group"] = df.flag.map({"A": "Official", "E": "Estimated", "I": "Imputed", "X": "External source", "F": "Forecast", "B": "Time-series break", "P": "Provisional"}).fillna("Other / unspecified")
    g = df.groupby(["domain", "flag_group"]).n.sum().reset_index()
    g["share"] = 100 * g.n / g.groupby("domain").n.transform("sum")
    order = ["Official", "External source", "Estimated", "Imputed", "Forecast", "Provisional", "Time-series break", "Other / unspecified"]
    colours = [CATEGORICAL[0], CATEGORICAL[2], CATEGORICAL[1], CATEGORICAL[3], CATEGORICAL[4], CATEGORICAL[6], CATEGORICAL[7], viz.MUTED]
    fig = go.Figure()
    for grp, c in zip(order, colours):
        s = g[g.flag_group == grp]
        if s.empty:
            continue
        fig.add_trace(go.Bar(x=s.domain, y=s.share, name=grp, marker_color=c, hovertemplate=f"%{{x}} · {grp}: %{{y:.1f}} %<extra></extra>"))
    fig.update_layout(barmode="stack", bargap=0.35, title="Provenance of loaded observations by domain (FAOSTAT flags)", yaxis_title="% of rows")
    tot = df.groupby("flag_group").n.sum()
    tot = 100 * tot / tot.sum()
    findings = [
        f"Across all {df.n.sum():,} loaded observations, {tot.get('Official', 0):.0f} % carry the official flag, {tot.get('Estimated', 0):.0f} % are FAO estimates, {tot.get('Imputed', 0):.0f} % imputed and {tot.get('External source', 0):.0f} % come from external organisations (UN population, WHO, World Bank).",
        f"Only the production domain (QCL) is majority official ({g[(g.domain == 'QCL') & (g.flag_group == 'Official')].share.sum():.0f} %); temperature, emissions and healthy-diet indicators are 100 % modelled estimates by construction.",
        "Analyses that lean on FS, RL and RFN should be read as FAO's best estimate rather than reported statistics.",
    ]
    return fig, findings, {}, g


@question("Composite & governance")
def q33_vulnerable_groups(df):
    metrics = {"pou_pct": "Undernourishment (%)", "fies_mod_sev_pct": "Moderate/severe food insecurity (%)", "stunting_pct": "Child stunting (%)", "unaffordable_pct": "Cannot afford healthy diet (%)", "cereal_import_dep_pct": "Cereal import dependency (%)", "cereal_yield_t_ha": "Cereal yield (t/ha)"}
    med = df.groupby("grp")[list(metrics)].median().reindex(["Least developed", "Land-locked developing", "Small island", "Other"])
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=2, cols=3, subplot_titles=list(metrics.values()), vertical_spacing=0.18)
    gcol = {"Least developed": CATEGORICAL[7], "Land-locked developing": CATEGORICAL[1], "Small island": CATEGORICAL[2], "Other": CATEGORICAL[0]}
    for i, (m, label) in enumerate(metrics.items()):
        fig.add_trace(go.Bar(x=med.index, y=med[m], marker_color=[gcol[g] for g in med.index], showlegend=False, hovertemplate="%{x}: %{y:.1f}<extra></extra>"), row=i // 3 + 1, col=i % 3 + 1)
    fig.update_layout(title="Median indicator by UN vulnerability group", height=620, bargap=0.4)
    n = df.grp.value_counts()
    findings = [
        f"Least-developed countries (n = {n.get('Least developed', 0)}) have median undernourishment of {med.loc['Least developed', 'pou_pct']:.0f} % vs {med.loc['Other', 'pou_pct']:.0f} % elsewhere, and {med.loc['Least developed', 'unaffordable_pct']:.0f} % cannot afford a healthy diet.",
        f"Median cereal import dependency: " + ", ".join(f"{g} {v:.0f} %" for g, v in med.cereal_import_dep_pct.sort_values(ascending=False).items()) + f" (n: LDC {n.get('Least developed', 0)}, LLDC {n.get('Land-locked developing', 0)}, SIDS {n.get('Small island', 0)}).",
        f"Cereal yields: LDC median {med.loc['Least developed', 'cereal_yield_t_ha']:.1f} t/ha vs {med.loc['Other', 'cereal_yield_t_ha']:.1f} t/ha for other countries.",
    ]
    return fig, findings, {}, med.reset_index()


@question("Production")
def q34_fastest_growing_commodities(df):
    piv = df.pivot(index="item", columns="year", values="production_mt").dropna()
    piv = piv[piv[2024] >= 20]
    piv["growth_pct"] = 100 * (piv[2024] / piv[2000] - 1)
    piv["added_mt"] = piv[2024] - piv[2000]
    top = piv.sort_values("growth_pct", ascending=False).head(20).reset_index()
    fig = viz.bar_chart(top, "item", "growth_pct", "Fastest-growing commodities in world production, 2000 -> 2024 (items >= 20 Mt in 2024)", "Growth (%)", orientation="h", unit=" %", hover_fmt=":.0f")
    fig.update_layout(height=640)
    big = piv.sort_values("added_mt", ascending=False).head(5)
    findings = [
        f"Fastest growth: {top.item.iloc[0]} (+{top.growth_pct.iloc[0]:.0f} %), {top.item.iloc[1]} (+{top.growth_pct.iloc[1]:.0f} %), {top.item.iloc[2]} (+{top.growth_pct.iloc[2]:.0f} %).",
        f"Largest absolute additions: " + ", ".join(f"{i} +{v:,.0f} Mt" for i, v in big.added_mt.items()) + ".",
    ]
    return fig, findings, {}, top


@question("Production")
def q35_livestock_stocks(df):
    df = df.assign(head_m=np.where(df.element_code == 5112, df.value * 1000, df.value) / 1e6)
    piv = df.pivot(index="year", columns="item", values="head_m")
    idx = piv / piv.iloc[0] * 100
    long = idx.reset_index().melt("year", var_name="item", value_name="index")
    fig = viz.line_chart(long, "year", "index", "item", "World livestock numbers, indexed to 1961 = 100", "Index (1961 = 100)",
                         colour_map={"Chickens": CATEGORICAL[1], "Swine / pigs": CATEGORICAL[4], "Cattle": CATEGORICAL[0], "Sheep": CATEGORICAL[2], "Goats": CATEGORICAL[3]}, hover_fmt=":.0f")
    findings = [
        "Head counts in 2024: " + ", ".join(f"{i} {v:,.0f} M" for i, v in piv.iloc[-1].sort_values(ascending=False).items()) + ".",
        f"Chickens grew {idx.iloc[-1]['Chickens'] / 100:.1f}x since 1961, goats {idx.iloc[-1]['Goats'] / 100:.1f}x, cattle {idx.iloc[-1]['Cattle'] / 100:.1f}x, sheep {idx.iloc[-1]['Sheep'] / 100:.1f}x.",
    ]
    return fig, findings, {}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def run_all(db_path: Path = DB_PATH, only: list[str] | None = None) -> list[Answer]:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    answers: list[Answer] = []
    for slug, (theme, fn) in HANDLERS.items():
        if only and slug not in only:
            continue
        sql, qtext = _sql(slug)
        df = pd.read_sql_query(sql, con)
        result = fn(df)
        fig, findings, numbers = result[0], result[1], result[2]
        table = result[3] if len(result) > 3 else df
        fig_file = FIGURES_DIR / f"{slug}.html"
        write_figure(fig, fig_file, title=qtext)
        tbl_file = TABLES_DIR / f"{slug}.csv"
        table.to_csv(tbl_file, index=False)
        answers.append(Answer(slug.split("_")[0].upper(), slug, qtext, theme, findings, f"figures/{slug}.html", f"tables/{slug}.csv",
                              f"sql/questions/{slug}.sql", numbers))
        print(f"  {slug}: {len(findings)} findings")
    con.close()
    if only:  # partial run: merge into the existing report rather than truncating it
        existing = REPORTS_DIR / "answers.json"
        if existing.exists():
            done = {a.slug: a for a in answers}
            merged = [done.get(x["slug"]) or Answer(**x) for x in json.loads(existing.read_text())]
            answers = merged + [a for a in answers if a.slug not in {m.slug for m in merged}]
    answers.sort(key=lambda a: a.slug)
    write_report(answers)
    return answers


def write_report(answers: list[Answer]) -> None:
    lines = ["# Analysis report", "", "Each question is answered with SQL against `data/faostat.db`, summarised in prose and rendered as an interactive Plotly figure.", ""]
    for theme in dict.fromkeys(a.theme for a in answers):
        lines += [f"## {theme}", ""]
        for a in [x for x in answers if x.theme == theme]:
            lines += [f"### {a.qid}. {a.question}", ""]
            lines += [f"- {f}" for f in a.findings]
            lines += ["", f"Figure: [{a.figure_file}]({a.figure_file}) · Table: [{a.table_file}]({a.table_file}) · SQL: [{a.sql_file}](../{a.sql_file})", ""]
    (REPORTS_DIR / "analysis_report.md").write_text("\n".join(lines))
    (REPORTS_DIR / "answers.json").write_text(json.dumps([a.__dict__ for a in answers], indent=2, default=str))


if __name__ == "__main__":
    import sys
    run_all(only=sys.argv[1:] or None)
