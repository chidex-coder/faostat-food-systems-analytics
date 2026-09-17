-- FAOSTAT food-systems warehouse: one long fact table plus conformed dimensions.
-- Codes are FAOSTAT's own (area / item / element) so every row can be traced
-- back to the source archive. Item codes are TEXT because the food-security
-- domain uses suffixed codes such as 210091F.

PRAGMA journal_mode = WAL;
PRAGMA synchronous = OFF;

DROP TABLE IF EXISTS observation;
DROP TABLE IF EXISTS dim_area;
DROP TABLE IF EXISTS dim_item;
DROP TABLE IF EXISTS dim_element;
DROP TABLE IF EXISTS dim_flag;
DROP TABLE IF EXISTS dim_domain;
DROP TABLE IF EXISTS dq_check;
DROP TABLE IF EXISTS load_log;

CREATE TABLE dim_domain (
    domain          TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    source_file     TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    sha256          TEXT,
    server_last_modified TEXT,
    catalogue_date_update TEXT,
    downloaded_at   TEXT,
    rows_raw        INTEGER,
    rows_loaded     INTEGER,
    rows_dropped_missing INTEGER,
    rows_dropped_filter  INTEGER,
    rows_dropped_dupe    INTEGER,
    notes           TEXT
);

CREATE TABLE dim_area (
    area_code       INTEGER PRIMARY KEY,
    m49_code        TEXT,
    area            TEXT NOT NULL,
    is_aggregate    INTEGER NOT NULL DEFAULT 0,   -- 1 = FAOSTAT region / special group
    iso3            TEXT,
    region          TEXT,          -- UN M49 region (Africa, Americas, Asia, Europe, Oceania)
    subregion       TEXT,          -- UN M49 sub-region
    intermediate_region TEXT,
    is_ldc          INTEGER NOT NULL DEFAULT 0,
    is_lldc         INTEGER NOT NULL DEFAULT 0,
    is_sids         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE dim_item (
    domain          TEXT NOT NULL,
    item_code       TEXT NOT NULL,
    item            TEXT NOT NULL,
    cpc_code        TEXT,
    PRIMARY KEY (domain, item_code)
);

CREATE TABLE dim_element (
    domain          TEXT NOT NULL,
    element_code    INTEGER NOT NULL,
    element         TEXT NOT NULL,
    unit            TEXT,
    PRIMARY KEY (domain, element_code)
);

CREATE TABLE dim_flag (
    domain          TEXT NOT NULL,
    flag            TEXT NOT NULL,
    description     TEXT,
    PRIMARY KEY (domain, flag)
);

CREATE TABLE observation (
    domain          TEXT NOT NULL,
    area_code       INTEGER NOT NULL,
    item_code       TEXT NOT NULL,
    element_code    INTEGER NOT NULL,
    year            INTEGER NOT NULL,   -- for 3-year averages: the middle year
    year_label      TEXT NOT NULL,      -- FAOSTAT's original label, e.g. 2020-2022
    value           REAL NOT NULL,
    flag            TEXT,
    note            TEXT,
    PRIMARY KEY (domain, area_code, item_code, element_code, year)
) WITHOUT ROWID;

CREATE TABLE dq_check (
    run_at          TEXT NOT NULL,
    domain          TEXT,
    check_name      TEXT NOT NULL,
    status          TEXT NOT NULL,      -- pass | warn | fail
    observed        REAL,
    threshold       REAL,
    detail          TEXT
);

CREATE TABLE load_log (
    run_at          TEXT NOT NULL,
    stage           TEXT NOT NULL,
    domain          TEXT,
    seconds         REAL,
    detail          TEXT
);
