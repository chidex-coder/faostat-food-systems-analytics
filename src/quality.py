"""Data-quality gate: assertions about the loaded warehouse, recorded in dq_check.

Checks are deliberately cheap SQL so they run on every build. `fail` aborts the
pipeline; `warn` is recorded and surfaced in the dashboard's governance tab.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from .config import DB_PATH, DOMAINS, WORLD_AREA_CODE
from .load import connect


def _record(con, run_at, domain, name, status, observed=None, threshold=None, detail=None):
    con.execute("INSERT INTO dq_check VALUES (?,?,?,?,?,?,?)",
                (run_at, domain, name, status, observed, threshold, detail))


def run_checks(con: sqlite3.Connection) -> list[dict]:
    run_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    results = []

    def add(domain, name, status, observed=None, threshold=None, detail=None):
        _record(con, run_at, domain, name, status, observed, threshold, detail)
        results.append(dict(domain=domain, check=name, status=status, observed=observed,
                            threshold=threshold, detail=detail))

    # 1. Every configured domain loaded rows.
    for code in DOMAINS:
        n = con.execute("SELECT COUNT(*) FROM observation WHERE domain = ?", (code,)).fetchone()[0]
        add(code, "domain_has_rows", "pass" if n > 0 else "fail", n, 1)

    # 2. Referential integrity: every fact row resolves to a dimension row.
    orphans = con.execute("""SELECT COUNT(*) FROM observation o
                             LEFT JOIN dim_area a USING (area_code) WHERE a.area_code IS NULL""").fetchone()[0]
    add(None, "orphan_area_codes", "pass" if orphans == 0 else "fail", orphans, 0)
    orphans = con.execute("""SELECT COUNT(*) FROM observation o
                             LEFT JOIN dim_item i ON i.domain = o.domain AND i.item_code = o.item_code
                             WHERE i.item_code IS NULL""").fetchone()[0]
    add(None, "orphan_item_codes", "pass" if orphans == 0 else "fail", orphans, 0)

    # 3. Physical plausibility.
    neg = con.execute("""SELECT COUNT(*) FROM observation
                         WHERE domain IN ('QCL','RFN','RL','OA','PP','CAHD') AND value < 0""").fetchone()[0]
    add(None, "negative_quantities", "pass" if neg == 0 else "warn", neg, 0,
        "quantities, areas, prices and populations must be non-negative")
    # Prevalence indicators must be within 0..100. Ratios such as dietary energy
    # adequacy (>100 = surplus), cereal import dependency (<0 = net exporter) and
    # food imports / merchandise exports (>100) are legitimately outside that range.
    prevalence = ('210041', '210091', '210091F', '210091M', '210401', '21025', '21041',
                  '21042', '21043', '21047', '21048', '7005')
    q = ",".join("?" * len(prevalence))
    pct = con.execute(f"""SELECT COUNT(*) FROM observation WHERE domain IN ('FS','CAHD')
                          AND item_code IN ({q}) AND element_code = 6121
                          AND (value < 0 OR value > 100)""", prevalence).fetchone()[0]
    add(None, "prevalence_in_0_100", "pass" if pct == 0 else "fail", pct, 0,
        "prevalence-type indicators must lie within 0..100 %")

    # 4. Coverage: the World aggregate exists for the headline series in the latest year.
    for domain, item, element in (("QCL", "1717", 5510), ("OA", "3010", 511), ("GT", "6518", 723113)):
        y = con.execute("""SELECT MAX(year) FROM observation WHERE domain=? AND item_code=? AND element_code=?
                           AND area_code=?""", (domain, item, element, WORLD_AREA_CODE)).fetchone()[0]
        add(domain, f"world_series_{item}_{element}_latest_year", "pass" if y and y >= 2020 else "warn", y, 2020)

    # 5. Yield identity: production ≈ area × yield / 1000 for cereals (tolerance 2 %).
    bad = con.execute("""SELECT COUNT(*) FROM v_production
                         WHERE item_code = '1717' AND is_aggregate = 0 AND area_harvested_ha > 1000
                           AND production_t IS NOT NULL AND yield_kg_ha IS NOT NULL
                           AND ABS(production_t - area_harvested_ha * yield_kg_ha / 1000.0) / production_t > 0.02""").fetchone()[0]
    tot = con.execute("""SELECT COUNT(*) FROM v_production WHERE item_code='1717' AND is_aggregate=0
                         AND area_harvested_ha > 1000 AND production_t IS NOT NULL AND yield_kg_ha IS NOT NULL""").fetchone()[0]
    share = bad / tot if tot else 0
    add("QCL", "cereal_yield_identity", "pass" if share < 0.01 else "warn", round(share, 4), 0.01,
        f"{bad} of {tot} country-years violate production = area x yield within 2 %")

    # 6. Country geography coverage.
    n_unmapped = con.execute("""SELECT COUNT(*) FROM dim_area WHERE is_aggregate = 0 AND region IS NULL""").fetchone()[0]
    names = [r[0] for r in con.execute("""SELECT area FROM dim_area WHERE is_aggregate=0 AND region IS NULL
                                          ORDER BY area LIMIT 40""")]
    add(None, "countries_without_m49_region", "pass" if n_unmapped < 25 else "warn", n_unmapped, 25,
        "; ".join(names))

    # 7. Flag provenance share per domain (informational).
    for code in DOMAINS:
        row = con.execute("""SELECT SUM(flag='A')*1.0/COUNT(*), SUM(flag IN ('E','I'))*1.0/COUNT(*),
                                    SUM(flag='X')*1.0/COUNT(*) FROM observation WHERE domain=?""", (code,)).fetchone()
        add(code, "share_official_flag", "pass", round(row[0] or 0, 4), None,
            f"estimated/imputed={round(row[1] or 0, 4)}; external={round(row[2] or 0, 4)}")
    con.commit()
    return results


if __name__ == "__main__":
    con = connect(DB_PATH)
    for r in run_checks(con):
        print(r)
