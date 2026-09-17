# Model card

Four models live in this repository. They share one purpose - to help a reader
decide where to look first in FAO's food-systems data - and one constraint: they
are descriptive tools trained on published statistics, not causal models of
food security.

## 1. Cereal-yield forecast (Ridge regression)

| | |
|---|---|
| **Task** | One-step-ahead national cereal yield (t/ha), countries with ≥ 20 kha harvested |
| **Training data** | `v_production` + lagged inputs (fertiliser N/ha, temperature anomaly, irrigation share), 1993-2018 |
| **Evaluation** | Held-out 2019-2024, 897 country-years. MAE 0.271 t/ha, RMSE 0.428, R² 0.957, MAPE 11.1 % |
| **Baselines** | Persistence (last year's yield) MAE 0.323; gradient boosting MAE 0.298 |
| **Intended use** | Planning ranges for next season at national scale; sanity-checking a reported figure |
| **Not for** | Sub-national or farm-level decisions; years with known shocks (drought, conflict) the lags cannot see |
| **Known failure mode** | Mean reversion after an extreme year: a drought-year base produces a large "expected recovery" that may not happen |

## 2. Undernourishment-risk classifier (gradient boosting)

| | |
|---|---|
| **Task** | Probability that a country-year has prevalence of undernourishment ≥ 15 % |
| **Features** | Structural only: income, cereal output per head, trade dependence, water and sanitation access, urbanisation, irrigation, fertiliser use, temperature change, agrifood emissions per head, forest share, LDC/LLDC/SIDS, region |
| **Deliberately excluded** | Dietary energy supply and adequacy - PoU is computed from them, so they would be leakage |
| **Evaluation** | Held-out 2017-2024, 806 country-years, 34 % positive. ROC-AUC 0.926, PR-AUC 0.893, F1 0.80, balanced accuracy 0.84 |
| **Intended use** | Screening: which countries look at risk given their structure, and which have PoU far from what their structure predicts |
| **Not for** | Resource allocation, ranking countries for funding, or any claim that a feature *causes* undernourishment |
| **Target caveat** | The label is FAO's modelled PoU, not a survey measurement. The model learns FAO's estimation method as much as reality |

## 3. Food-system typology (k-means, k = 4)

| | |
|---|---|
| **Task** | Group 174 countries by their latest 12-indicator profile |
| **Selection** | k chosen by silhouette over k = 3..7 (best 0.22 - clusters are indicative, not sharp) |
| **Intended use** | Finding peers: "which countries face a similar mix of problems?" |
| **Not for** | Treating a cluster label as a category with policy meaning; boundaries are fuzzy |

## 4. Regional cereal projections (log-linear trend)

| | |
|---|---|
| **Task** | Regional cereal production to 2030 |
| **Method** | Log-linear fit 2005-2024 with a 95 % prediction interval from residual variance |
| **Intended use** | A transparent baseline: "if the last 20 years' growth rate continues" |
| **Not for** | Scenario analysis; the trend has no notion of climate, policy or price |

## Shared limitations

* Country-years are not independent samples; every metric above is optimistic for a genuinely unseen country.
* Validation windows (2017-2024, 2019-2024) contain few structural breaks, so behaviour under shocks is untested.
* All inputs are FAO estimates with the provenance mix shown on the dashboard's *Data & governance* tab (31 % official, 57 % FAO-estimated, 4 % external).
* Models are retrained on every pipeline run with a fixed seed; there is no drift monitoring because there is no production deployment.
