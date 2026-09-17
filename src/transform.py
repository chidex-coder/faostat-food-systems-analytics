"""Transform stage: turn each FAOSTAT normalized CSV into tidy, typed frames.

Rules applied to every domain (documented here because they are the data
contract downstream code relies on):

1. Column names are mapped to snake_case; the ET domain's `Months` dimension is
   treated as the item dimension so the fact table stays uniform.
2. Only the elements listed in `config.DOMAINS[...]` are kept; the food-security
   confidence-interval elements and monthly price rows are dropped here.
3. Rows whose flag marks a missing value (O, Q, L, M) or whose value is null are
   *counted* and dropped - the fact table has `value NOT NULL`.
4. Years are integers. 3-year averages like "2020-2022" are stored as the middle
   year (2021) with the original label retained in `year_label`.
5. Year window: YEAR_MIN..YEAR_MAX. This removes UN population projections to
   2100 and the FAO 2030/2050 emission scenarios.
6. Exact duplicate keys (domain, area, item, element, year) are resolved by
   keeping the first occurrence; the count is recorded in dim_domain.
7. Areas are enriched with UN M49 region/sub-region via the M49 code, and
   flagged as aggregate when area_code >= 5000. Countries without an M49 match
   (e.g. former countries like "USSR") keep region NULL and are excluded from
   the `v_country` view but retained in the fact table.
"""
from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .config import (AGGREGATE_AREA_CODE_MIN, MISSING_FLAGS, RAW_DIR, REFERENCE_DIR,
                     YEAR_MAX, YEAR_MIN, Domain)

COLUMN_MAP = {
    "Area Code": "area_code",
    "Area Code (M49)": "m49_code",
    "Area": "area",
    "Item Code": "item_code",
    "Item Code (CPC)": "cpc_code",
    "Item": "item",
    "Months Code": "item_code",
    "Months": "item",
    "Element Code": "element_code",
    "Element": "element",
    "Year Code": "year_code",
    "Year": "year_label",
    "Unit": "unit",
    "Value": "value",
    "Flag": "flag",
    "Note": "note",
    "Source Code": "source_code",
    "Source": "source",
}


EXTRA_AGGREGATE_AREA_CODES = {351, 420}  # "China" (M49 159, multi-territory) and "Sub-Saharan Africa" (M49 202)
MANUAL_GEOGRAPHY = {
    214: ("TWN", "Asia", "Eastern Asia"),           # China, Taiwan Province of (M49 158, absent from the UN table)
}


@dataclass
class DomainFrames:
    domain: str
    observations: pd.DataFrame
    items: pd.DataFrame
    elements: pd.DataFrame
    areas: pd.DataFrame
    flags: pd.DataFrame
    stats: dict


def _read_member(zf: zipfile.ZipFile, suffix: str, **kw) -> pd.DataFrame | None:
    names = [n for n in zf.namelist() if n.endswith(suffix)]
    if not names:
        return None
    raw = zf.read(names[0])
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(pd.io.common.BytesIO(raw), encoding=enc, **kw)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"cannot decode {names[0]}")


def year_from_label(label: pd.Series) -> pd.Series:
    """'2021' -> 2021; '2020-2022' -> 2021 (middle year)."""
    s = label.astype(str).str.strip()
    is_range = s.str.contains("-", regex=False)
    start = pd.to_numeric(s.str.slice(0, 4), errors="coerce")
    end = pd.to_numeric(s.where(is_range).str.slice(-4), errors="coerce")
    mid = np.where(is_range, (start + end) // 2, start)
    return pd.Series(mid, index=label.index).astype("Int64")


def transform_domain(dom: Domain, raw_dir: Path = RAW_DIR) -> DomainFrames:
    zf = zipfile.ZipFile(raw_dir / dom.zip_name)
    stats: dict = {"domain": dom.code}
    df = _read_member(zf, "(Normalized).csv", low_memory=False, dtype={"Item Code": str, "Months Code": str,
                                                                     "Area Code (M49)": str, "Note": str})
    stats["rows_raw"] = len(df)
    before = len(df)
    # extra_filters use FAOSTAT's original column names (e.g. "Months Code")
    for col, val in dom.extra_filters.items():
        df = df[df[col].astype(str) == str(val)]
    # exactly one of Item / Months becomes the item dimension
    drop = ("Item Code", "Item") if dom.item_col == "Months" else ("Months Code", "Months")
    df = df.drop(columns=[c for c in drop if c in df.columns])
    df = df.rename(columns=COLUMN_MAP)

    # -- filters ------------------------------------------------------------
    if dom.elements:
        df = df[df["element_code"].isin(dom.elements)]
    df = df.copy()
    df["year"] = year_from_label(df["year_label"])
    df = df[df["year"].between(YEAR_MIN, YEAR_MAX)].copy()
    stats["rows_dropped_filter"] = before - len(df)

    # -- missing values -----------------------------------------------------
    before = len(df)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["flag"] = df["flag"].fillna("").astype(str).str.strip()
    df = df[df["value"].notna() & ~df["flag"].isin(MISSING_FLAGS)]
    stats["rows_dropped_missing"] = before - len(df)

    # -- typing ---------------------------------------------------------------
    df["area_code"] = df["area_code"].astype(int)
    df["element_code"] = df["element_code"].astype(int)
    df["item_code"] = df["item_code"].astype(str).str.strip()
    df["year"] = df["year"].astype(int)
    df["year_label"] = df["year_label"].astype(str)
    df["m49_code"] = df["m49_code"].astype(str).str.replace("'", "", regex=False).str.strip()
    if "note" not in df.columns:
        df["note"] = None
    if "cpc_code" not in df.columns:
        df["cpc_code"] = None

    # -- dimensions -----------------------------------------------------------
    items = (df[["item_code", "item", "cpc_code"]].drop_duplicates("item_code")
             .assign(domain=dom.code)[["domain", "item_code", "item", "cpc_code"]])
    elements = (df[["element_code", "element", "unit"]].drop_duplicates("element_code")
                .assign(domain=dom.code)[["domain", "element_code", "element", "unit"]])
    areas = df[["area_code", "m49_code", "area"]].drop_duplicates("area_code")
    flags = _read_member(zf, "_Flags.csv")
    if flags is None:
        flags = pd.DataFrame(columns=["Flag", "Description"])
    flags.columns = [c.strip() for c in flags.columns]   # FAO ships " Description" with a leading space
    flags = flags.rename(columns={"Flag": "flag", "Description": "description"}).assign(domain=dom.code)
    flags["flag"] = flags["flag"].fillna("").astype(str).str.strip()
    flags = flags[["domain", "flag", "description"]]

    # -- fact -----------------------------------------------------------------
    keys = ["domain", "area_code", "item_code", "element_code", "year"]
    obs = df.assign(domain=dom.code)[keys + ["year_label", "value", "flag", "note"]]
    before = len(obs)
    obs = obs.drop_duplicates(keys, keep="first")
    stats["rows_dropped_dupe"] = before - len(obs)
    stats["rows_loaded"] = len(obs)
    return DomainFrames(dom.code, obs.reset_index(drop=True), items, elements, areas, flags, stats)


def build_area_dimension(area_frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Union the per-domain area lists and enrich with UN M49 geography."""
    areas = (pd.concat(area_frames).drop_duplicates("area_code").sort_values("area_code")
             .reset_index(drop=True))
    m49 = pd.read_csv(REFERENCE_DIR / "un_m49.csv", dtype=str).fillna("")
    m49 = m49.rename(columns={
        "Region Name": "region", "Sub-region Name": "subregion",
        "Intermediate Region Name": "intermediate_region", "M49 Code": "m49_code",
        "ISO-alpha3 Code": "iso3", "Least Developed Countries (LDC)": "ldc",
        "Land Locked Developing Countries (LLDC)": "lldc", "Small Island Developing States (SIDS)": "sids",
    })
    m49["m49_code"] = m49["m49_code"].str.zfill(3)
    areas["m49_code"] = areas["m49_code"].str.zfill(3)
    out = areas.merge(m49[["m49_code", "iso3", "region", "subregion", "intermediate_region",
                           "ldc", "lldc", "sids"]], on="m49_code", how="left")
    out["is_aggregate"] = (out["area_code"] >= AGGREGATE_AREA_CODE_MIN).astype(int)
    # Two aggregates sit below the 5000 boundary: FAOSTAT "China" (351 = mainland
    # + Hong Kong + Macao + Taiwan) and "Sub-Saharan Africa" (M49 202).
    out.loc[out["area_code"].isin(EXTRA_AGGREGATE_AREA_CODES), "is_aggregate"] = 1
    # Territories FAOSTAT reports that the UN M49 table omits.
    for code, (iso3, region, subregion) in MANUAL_GEOGRAPHY.items():
        mask = out["area_code"] == code
        out.loc[mask, ["iso3", "region", "subregion"]] = [iso3, region, subregion]
    for col in ("ldc", "lldc", "sids"):
        out[f"is_{col}"] = (out[col].fillna("").str.strip() != "").astype(int)
    for col in ("region", "subregion", "intermediate_region", "iso3"):
        out[col] = out[col].replace("", np.nan)
    # FAOSTAT's "China" (351) aggregates the mainland plus SARs and Taiwan; the
    # M49 code 156 refers to mainland China which FAOSTAT lists as area 41.
    out.loc[out["is_aggregate"] == 1, ["region", "subregion", "intermediate_region", "iso3"]] = np.nan
    return out[["area_code", "m49_code", "area", "is_aggregate", "iso3", "region", "subregion",
                "intermediate_region", "is_ldc", "is_lldc", "is_sids"]]
