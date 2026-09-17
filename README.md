# FAOSTAT Food Systems Analytics

An end-to-end analytics project on the FAO statistical database: a resumable ETL
that pulls nine FAOSTAT domains into a SQLite warehouse, 35 analytical questions
answered in SQL with interactive Plotly figures, four predictive models, and a
self-contained interactive dashboard.

**Live dashboard:** https://chidex-coder.github.io/faostat-food-systems-analytics/
**Written findings:** [reports/analysis_report.md](reports/analysis_report.md)
**Model record:** [models/metrics.json](models/metrics.json)

```
FAOSTAT bulk archives ──► data/raw/*.zip (sha256 manifest)
        │  src/extract.py     resumable download, catalogue + ETag capture
        ▼
tidy frames ────────────► data/faostat.db (7.3 M rows, 9 domains)
        │  src/transform.py   typing, year normalisation, flag handling, M49 geography
        │  src/load.py        star-ish schema + views, sql/schema.sql, sql/views.sql
        │  src/quality.py     dq_check gate (fails the build)
        ▼
sql/questions/*.sql ─────► reports/figures/*.html · reports/tables/*.csv · reports/analysis_report.md
        │  src/analysis.py    35 questions, one figure + written findings each
        ▼
src/ml.py ───────────────► models/*.csv · models/metrics.json · reports/figures/ml_*.html
        ▼
src/dashboard.py ────────► docs/index.html (GitHub Pages)
```

## Quick start

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run_pipeline.py            # ~80 MB download, then ~2 minutes
.venv/bin/python -m http.server 8766 --directory docs   # open http://localhost:8766
.venv/bin/python -m pytest -q
```

`run_pipeline.py --skip-extract` reuses archives already in `data/raw`;
`--only analysis dashboard` re-runs individual stages. Setting `FAOSTAT_TOKEN`
enables the REST client in `src/extract.py` (`FaostatApi`) for ad-hoc queries;
the bulk archives remain the build path because they need no credentials.

## What is in the warehouse

| Domain | FAOSTAT dataset | Rows loaded | Used for |
|---|---|---:|---|
| QCL | Production: crops and livestock | 4,114,755 | production, area, yield, herds |
| GT | Emissions totals (FAO Tier 1) | 1,362,938 | agrifood, farm-gate and sectoral CO2eq |
| ET | Temperature change on land | 568,179 | warming anomaly vs 1951-80 |
| RL | Land use | 421,774 | cropland, pasture, forest, irrigation, organic |
| PP | Producer prices (annual) | 338,803 | USD and LCU per tonne |
| RFN | Fertilizers by nutrient | 256,244 | N, P2O5, K2O use and intensity |
| FS | Suite of food security indicators | 182,339 | PoU, FIES, stunting, obesity, import dependency |
| OA | Annual population | 81,901 | totals, urban/rural |
| CAHD | Cost and affordability of a healthy diet | 6,894 | CoHD, share unable to afford |

Geography comes from the UN M49 standard (`data/reference/un_m49.csv`), giving
every country a region, sub-region and LDC / LLDC / SIDS flags.

---

## The five lenses

### 1. Tech: what runs, and why

* **Python 3.12 + pandas** for transformation. The largest archive is 4.2 M rows;
  pandas handles it in memory in ~15 s, so Spark/Polars would add dependencies
  without changing the outcome.
* **SQLite** as the warehouse. The whole dataset is 600 MB on disk, single-writer,
  read by one analyst at a time. A server database would add operations without
  adding capability. Views (`sql/views.sql`) turn the long fact table into
  wide, named slices so analytical SQL reads as prose.
* **Bulk archives over the REST API.** FAOSTAT's API now requires a personal
  bearer token; the bulk bucket is public, versioned (ETag + last-modified), and
  ships the code lists with the data. The API client exists (`FaostatApi`) for
  targeted pulls, but the reproducible build path is the one anyone can run.
* **Plotly** for figures because the same library renders in notebooks, static
  HTML and the dashboard. Every figure is written with `include_plotlyjs="cdn"`,
  so 39 interactive figures cost ~350 KB in the repo.
* **scikit-learn** for models: gradient boosting, random forest, ridge, logistic
  regression, k-means, PCA. Enough to test whether non-linear models earn their
  complexity (spoiler: for yield forecasting they do not).
* **A single static HTML dashboard** (`docs/index.html`) with all data inlined.
  No server, no build tool, works from `file://` and GitHub Pages. 9 MB raw,
  ~1.5 MB gzipped over the wire.

### 2. Algorithms and mechanisms: what makes the claims true

* **Year normalisation.** FAO publishes 3-year averages as "2020-2022". They are
  stored at the middle year with the original label retained, and the primary
  key `(domain, area, item, element, year)` is enforced by SQLite, so a silent
  collision between an annual and a 3-year series would fail the load rather
  than overwrite.
* **Missing-value semantics.** Flags `O`, `Q`, `L`, `M` mean "no value" in every
  domain; those rows are counted in `dim_domain.rows_dropped_missing` and not
  loaded, so `value` is `NOT NULL` and every aggregate in SQL is over real data.
* **Aggregate isolation.** Regions are FAOSTAT's own aggregates (area code ≥ 5000
  plus two sub-5000 groups, "China" 351 and "Sub-Saharan Africa" 420). They are
  flagged and excluded from `v_country`, so a "top producers" query can never
  rank *Asia* against *India*.
* **Growth decomposition (Q05)** uses log-points: `ln(P1/P0) = ln(A1/A0) + ln(Y1/Y0)`,
  which is exact, unlike percentage shares.
* **Volatility (Q07)** is the coefficient of variation of residuals around a
  linear trend, so a country growing steadily is not called "volatile".
* **Heat sensitivity (Q24)** correlates temperature anomalies with yield
  anomalies from a quadratic trend, per country, so the secular yield rise does
  not masquerade as a temperature effect.
* **Irrigation (Q19)** is rebuilt as `land equipped for irrigation / (arable +
  permanent crops)` from the land-use domain, because FAOSTAT's own
  food-security indicator 21034 is evidently expressed against total land area
  (Egypt = 4 %).
* **Yield forecast** is one-step-ahead with a *time-based split* (train < 2019,
  test ≥ 2019). Persistence is the baseline every model must beat; the target
  year's own weather is excluded because a planner does not have it.
  Result on 897 held-out country-years: persistence MAE 0.323 t/ha, ridge 0.271,
  gradient boosting 0.298. **Ridge wins** - lags carry almost all the signal.
* **Undernourishment-risk classifier** predicts PoU ≥ 15 % from structural
  features only. Dietary-energy inputs are excluded because PoU is computed from
  them - including them would be leakage, not prediction. Gradient boosting:
  ROC-AUC 0.926, PR-AUC 0.893, F1 0.80 on 806 held-out country-years (2017+).
  Top drivers: sanitation access, income, cereal output per head.
* **Typology**: k-means on 12 standardised indicators, k chosen by silhouette
  (k = 4), PCA only for display. Cluster names are generated from the two
  indicators whose cluster median deviates most from the global median.
* **Projections** are log-linear trends (2005-2024) with a proper prediction
  interval from the residual variance - simple enough that the reader can see
  exactly what assumption is being made.
* **Composite scorecard (Q31)** winsorises z-scores at ±3 so one extreme
  indicator (e.g. a 1,000 % import ratio) cannot dominate a country's score.

### 3. Decisions and trade-offs

| Optimised for | Knowingly sacrificed |
|---|---|
| Reproducibility: one command rebuilds everything from public URLs, hashed | Freshness: no scheduler; a rebuild is manual |
| Auditability: every number traces to a SQL file and FAOSTAT codes | Query convenience: some SQL is verbose because codes, not names, are the contract |
| Zero-infrastructure delivery (static HTML, SQLite) | Concurrency and scale beyond one analyst / tens of millions of rows |
| Honest model evaluation (time splits, persistence baselines) | Headline accuracy: a random split would have reported far rosier numbers |
| Breadth of questions (35) | Depth per question: each gets one figure and 2-4 findings, not a paper |
| Dashboard file size vs. interactivity: all data inlined | ~9 MB page; GitHub Pages' gzip mitigates but does not remove the cost |
| Keeping FAO's regional aggregates rather than recomputing them | Regions missing an FAO aggregate for an indicator (e.g. the Americas in FS) simply have no line |
| Curated crop list in the dashboard (20 items) | The other ~280 commodities are only in the warehouse and static figures |

Two decisions worth calling out. First, the FS indicators use the 3-year
averages as the primary series even though annual variants exist, because FAO
publishes annuals only for aggregates; mixing them would make countries and
regions non-comparable. Second, the emissions domain is loaded from FAO Tier 1
only, not the UNFCCC submissions, so every country is on the same method.

### 4. Governance: contracts, versioning, ownership of quality

* **Schema contract** lives in `sql/schema.sql`; every downstream consumer reads
  the views in `sql/views.sql`, so a change to the fact table is a change in one
  place, reviewed in one diff.
* **Provenance** is recorded per domain in `dim_domain`: source URL, SHA-256,
  server last-modified, FAO catalogue release date, download timestamp, raw row
  count and every category of dropped row. The dashboard's *Data & governance*
  tab renders it.
* **Quality gate** (`src/quality.py`) runs 27 checks on every build - domain
  coverage, referential integrity, negative quantities, prevalence ranges, the
  `production = area × yield` identity, geography coverage, and the official /
  estimated / external flag mix - and writes them to `dq_check`. A `fail`
  aborts the pipeline; `warn` is surfaced, not hidden.
* **Data lineage in the report**: every question links its SQL, its result
  table and its figure. Findings are generated from the data, not typed in, so
  a rebuild cannot leave stale prose.
* **Versioning**: FAO releases are pinned by hash in `data/raw/manifest.json`
  (git-ignored because archives are re-downloadable; the manifest values are
  copied into `dim_domain` and into the dashboard, which *is* committed).
* **Ownership of quality**: FAO owns the estimates; this project owns the
  *reading* of them. Only 31 % of loaded rows carry FAO's official flag; 57 %
  are FAO estimates and 4 % come from external organisations. Q32 and the
  governance tab make this explicit so nobody mistakes modelled series for
  reported statistics.
* **Tests**: `tests/test_transform.py` pins the transformation rules on a
  synthetic archive; `tests/test_warehouse.py` asserts invariants on the built
  database.

### 5. Security and policy

Handled:

* No credentials are needed to build. The optional API token is read from the
  environment, never logged, never written to disk, and the client is opt-in.
* Downloads are verified: size against `Content-Length`, zip integrity via
  `testzip()`, and SHA-256 recorded. A corrupt archive is deleted and the build
  stops.
* The dashboard loads exactly one external script (Plotly.js from cdn.plot.ly)
  and no external data; per-viewer preferences (theme, filters) stay in
  `localStorage` wrapped in try/catch.
* FAO's terms of use are stated in the dashboard footer; the data are FAO's and
  are redistributed here only as derived aggregates and figures.
* No personal data of any kind is processed.

Silently absent, and worth knowing:

* **No pinning of Plotly.js by integrity hash** - a compromised CDN would run in
  the viewer's browser. Adding `integrity`/`crossorigin` attributes is the fix.
* **No signature verification of FAO archives** - FAO does not publish
  signatures; the hash proves *what* was downloaded, not *who* published it.
* **No rate limiting or retries with jitter** against the FAO bucket beyond
  simple exponential back-off; a scheduled hourly rebuild would be rude.
* **No access control on the dashboard** - it is public by design; if the same
  pattern were applied to non-public data, the inlined-JSON approach would leak
  everything in view-source.
* **No dependency pinning to exact versions** in `requirements.txt` (only
  minimums). A lock file would make the build bit-for-bit reproducible.
* **Model risk**: the risk classifier is descriptive, not causal, and is trained
  on FAO's modelled PoU. It is a screening aid; it should not be used to
  allocate resources without a human reading the country context.

## Repository layout

```
run_pipeline.py          orchestrator (extract → load → quality → analysis → ml → dashboard)
src/config.py            domain registry, code lists, paths
src/extract.py           bulk downloader + optional REST client
src/transform.py         normalisation rules and M49 enrichment
src/load.py              SQLite loader
src/quality.py           data-quality gate
src/analysis.py          35 questions → figures, tables, findings
src/ml.py                yield forecast, risk classifier, typology, projections
src/viz.py               shared Plotly theme (entity-stable colours)
src/dashboard.py         packs data + template into docs/index.html
sql/schema.sql, views.sql, indexes.sql, questions/*.sql
reports/                 analysis_report.md, answers.json, figures/, tables/
models/                  metrics.json, predictions, importances, clusters, projections
docs/                    dashboard (template.html → index.html), copied figures
data/reference/un_m49.csv
tests/
```

## Data sources

* FAO. FAOSTAT bulk downloads, https://bulks-faostat.fao.org/production/ (accessed 17 Sep 2026). Domains QCL, FS, RFN, RL, ET, GT, OA, PP, CAHD.
* United Nations Statistics Division. Standard country or area codes for statistical use (M49).
