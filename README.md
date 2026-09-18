# FAOSTAT Food Systems Analytics

An end-to-end analytics project on the FAO statistical database: a resumable ETL
that pulls nine FAOSTAT domains into a SQLite warehouse, 35 analytical questions
answered in SQL with interactive Plotly figures, four predictive models, and a
self-contained interactive dashboard.

**Live dashboard:** https://chidex-coder.github.io/faostat-food-systems-analytics/
**Notebook:** [notebooks/food_systems_analysis.ipynb](notebooks/food_systems_analysis.ipynb) ([interactive on nbviewer](https://nbviewer.org/github/chidex-coder/faostat-food-systems-analytics/blob/main/notebooks/food_systems_analysis.ipynb))
**Written findings:** [reports/analysis_report.md](reports/analysis_report.md)
**Model record:** [models/metrics.json](models/metrics.json) · [models/MODEL_CARD.md](models/MODEL_CARD.md)

## 🏗️ Solution Architecture

```
                  +----------------------------------+
                  |   FAOSTAT Bulk Download Bucket   |
                  |  9 domains · zipped normalised   |
                  |  CSV · public · ETag-versioned   |
                  +----------------+-----------------+
                                   |
                                   v
                      Resumable Extractor (Python)
                 Range resume · If-None-Match · SHA-256
                 pinned release hashes · polite back-off
                                   |
                                   v
                          Raw Archive Store
                       data/raw/*.zip + manifest
                                   |
                                   v
                    pandas Transformation Jobs
        Typing · Year normalisation · Missing-flag drop
        Dedup on key · UN M49 geography · Aggregate flag
                                   |
                                   v
                        SQLite Warehouse (7.3 M rows)
            +----------------------+----------------------+
            |                      |                      |
            v                      v                      v
       dim_area              observation            dim_domain
       dim_item        (domain, area, item,         dim_flag
       dim_element      element, year) PK           dq_check
            \                     |                      /
             \                    |                     /
              +-------------------+--------------------+
                                  |
                                  v
                     Named Analytical Views
        v_production · v_food_security · v_land · v_fertilizer
        v_temperature · v_emissions · v_healthy_diet · v_price_usd
                                  |
                                  v
                          Quality Gate (27 checks)
                    integrity · plausibility · identity
                       fail => build stops · warn => shown
                                  |
            +---------------------+---------------------+
            |                                           |
            v                                           v
   35 SQL Questions                          scikit-learn Models
   Plotly figures · findings          Yield forecast · Risk classifier
   reports/ (tables, report.md)       Typology · 2030 projections
            |                                           |
            +---------------------+---------------------+
                                  |
                                  v
                    Executed Jupyter Notebook
              SQL · figures (Plotly + PNG) · models
                                  |
            +---------------------+---------------------+
            |                     |                     |
            v                     v                     v
   Static HTML Dashboard      Dash App          Streamlit App
   GitHub Pages · SRI-pinned  port 8767          port 8768
   filters · maps · Notebook  (Notebook tab)     (Notebook tab)
            |
            v
   Pytest Suite (16) · run_pipeline.py orchestrator
```

## Quick start

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.lock   # exact versions; requirements.txt = minimums
.venv/bin/python run_pipeline.py            # ~80 MB download, then ~2 minutes
.venv/bin/python -m http.server 8766 --directory docs   # open http://localhost:8766
.venv/bin/python -m pytest -q
```

`run_pipeline.py --skip-extract` reuses archives already in `data/raw`;
`--only analysis dashboard` re-runs individual stages; `--skip-notebook` skips
executing the notebook (it needs `requirements-apps.txt`). Downloaded archives are
checked against the reviewed hashes in `data/reference/archive_pins.json`; when
FAO publishes a new release the build stops and asks for `--update-pins`.
Setting `FAOSTAT_TOKEN`
enables the REST client in `src/extract.py` (`FaostatApi`) for ad-hoc queries;
the bulk archives remain the build path because they need no credentials.

## Notebook and apps

```bash
.venv/bin/pip install -r requirements-apps.txt
.venv/bin/python -m src.notebook                       # execute notebooks/food_systems_analysis.ipynb, export docs/notebook.html
.venv/bin/jupyter lab notebooks/food_systems_analysis.ipynb
.venv/bin/python apps/dash_app.py                      # Dash    → http://127.0.0.1:8767
.venv/bin/streamlit run apps/streamlit_app.py --server.port 8768   # Streamlit
```

The notebook walks through the warehouse, all 35 questions (SQL shown, figure,
generated findings), the four models and the dashboard, calling the same
functions the pipeline runs. Figures are stored as Plotly JSON plus PNG, so they
are interactive in Jupyter/nbviewer and visible on GitHub. The static HTML
dashboard, the Dash app and the Streamlit app each have a **Notebook** tab
linking to it and embedding the executed copy; the Dash and Streamlit apps are
thin views over the committed artefacts (`reports/`, `models/`, `docs/`) and run
without the 600 MB warehouse.

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

Handled (details and residuals in [SECURITY.md](SECURITY.md)):

* **Supply chain of the page.** Every emitted HTML - 39 figures and the dashboard -
  loads one pinned Plotly.js build with a Subresource Integrity hash and
  `crossorigin="anonymous"` ([src/web.py](src/web.py)). A tampered CDN response
  is refused by the browser. [tests/test_web.py](tests/test_web.py) fails if any
  file drifts from the pin.
* **Supply chain of the data.** FAO publishes no signatures, so the project pins
  the SHA-256 of every archive it has reviewed
  ([data/reference/archive_pins.json](data/reference/archive_pins.json)). A
  download whose hash differs aborts the build until `--update-pins` is passed
  after review - the hash now proves "the same bytes that were reviewed", not
  merely "what was fetched". Size and zip-integrity checks run before hashing.
* **Dependencies** are locked to exact versions in `requirements.lock`.
* **Credentials.** None needed to build. The optional API token is read from the
  environment only, sent as a bearer header, and masked in `repr` so it cannot
  leak into a traceback.
* **Polite client.** Identifying User-Agent, conditional requests
  (`If-None-Match` - an unchanged archive is never re-downloaded), one request
  per second at most, exponential back-off with jitter, and written guidance not
  to schedule extraction more than weekly.
* **Publication boundary.** The dashboard inlines its data, so everything on the
  page is visible in view-source. The builder enforces an allowlist of blocks
  and fields (`PUBLISHABLE` in [src/dashboard.py](src/dashboard.py)) and refuses
  to build unless `meta.data_classification == "public"`; the page states that
  classification. Per-viewer preferences stay in `localStorage` under try/catch.
* **Model risk.** [models/MODEL_CARD.md](models/MODEL_CARD.md) records intended
  use, exclusions and known failure modes for all four models; `metrics.json`
  carries the same `intended_use` / `limitations`; the *Predictions* tab opens
  with the warning that the models are descriptive screening aids trained on
  FAO's modelled series.
* FAO's terms of use are stated in the dashboard footer; no personal data is
  processed anywhere.

Still absent, by choice or by circumstance:

* **First-use trust.** The initial archive pin is trust-on-first-use over HTTPS;
  only FAO signing its releases would close that.
* **No wheel hash-pinning** (`pip --require-hashes`); the lock file pins versions,
  not artefact hashes.
* **No access control** on the dashboard - public by design. Reusing the inlined
  pattern on restricted data would be wrong; SECURITY.md says what to do instead.
* **No drift monitoring** for the models - there is no production deployment to
  monitor; they are retrained on every build with a fixed seed.

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
src/web.py               pinned Plotly.js build + SRI hash, figure writer
src/dashboard.py         packs data + template into docs/index.html
src/notebook.py          builds, executes and exports the analysis notebook
apps/                    common.py, dash_app.py, streamlit_app.py (Notebook tab in each)
notebooks/               food_systems_analysis.ipynb (executed)
sql/schema.sql, views.sql, indexes.sql, questions/*.sql
reports/                 analysis_report.md, answers.json, figures/, tables/
models/                  metrics.json, MODEL_CARD.md, predictions, importances, clusters, projections
docs/                    dashboard (template.html → index.html), notebook.html, copied figures
data/reference/          un_m49.csv (UN geography), archive_pins.json (reviewed FAO release hashes)
SECURITY.md              controls, residual risks, publication boundary
tests/
```

## Data sources

* FAO. FAOSTAT bulk downloads, https://bulks-faostat.fao.org/production/ (accessed 17 Sep 2026). Domains QCL, FS, RFN, RL, ET, GT, OA, PP, CAHD.
* United Nations Statistics Division. Standard country or area codes for statistical use (M49).
