"""Unit tests for the pure transformation logic (no network, no full archives)."""
import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from src.config import Domain
from src.transform import build_area_dimension, transform_domain, year_from_label


def test_year_from_label_handles_single_years_and_ranges():
    s = pd.Series(["2021", "2020-2022", "2000-2002", " 1999 "])
    assert year_from_label(s).tolist() == [2021, 2021, 2001, 1999]


def _archive(tmp_path: Path, rows: list[dict], item_col: str = "Item") -> Path:
    cols = ["Area Code", "Area Code (M49)", "Area", f"{item_col} Code", item_col, "Element Code", "Element",
            "Year Code", "Year", "Unit", "Value", "Flag", "Note"]
    df = pd.DataFrame(rows, columns=cols)
    z = tmp_path / "Test_E_All_Data_(Normalized).zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("Test_E_All_Data_(Normalized).csv", df.to_csv(index=False))
        zf.writestr("Test_E_Flags.csv", "Flag, Description\nA,Official figure\nE,Estimated value\nO,Missing value\n")
    return z


def test_transform_filters_missing_flags_duplicates_and_year_window(tmp_path):
    base = dict(**{"Area Code": 2, "Area Code (M49)": "'004", "Area": "Afghanistan", "Item Code": "15", "Item": "Wheat",
                   "Element Code": 5510, "Element": "Production", "Unit": "t", "Note": ""})
    rows = [
        {**base, "Year Code": 2020, "Year": "2020", "Value": 100, "Flag": "A"},
        {**base, "Year Code": 2020, "Year": "2020", "Value": 999, "Flag": "E"},          # duplicate key -> dropped
        {**base, "Year Code": 2021, "Year": "2021", "Value": None, "Flag": "O"},         # missing -> dropped
        {**base, "Year Code": 2030, "Year": "2030", "Value": 5, "Flag": "E"},            # beyond window -> dropped
        {**base, "Year Code": 2022, "Year": "2022", "Value": 120, "Flag": "E", "Element Code": 9999, "Element": "Other"},  # element filtered
        {**base, "Year Code": 20202022, "Year": "2020-2022", "Value": 110, "Flag": "E", "Element Code": 5510},
    ]
    z = _archive(tmp_path, rows)
    dom = Domain("TST", "test", z.name, elements=(5510,))
    frames = transform_domain(dom, raw_dir=tmp_path)
    obs = frames.observations
    assert frames.stats["rows_raw"] == 6
    assert frames.stats["rows_dropped_dupe"] == 1
    assert frames.stats["rows_dropped_missing"] == 1
    assert set(obs.year) == {2020, 2021}
    # the 3-year average lands on the middle year with its original label kept
    assert obs.loc[obs.year == 2021, "year_label"].item() == "2020-2022"
    assert obs.loc[obs.year == 2020, "value"].item() == 100  # first occurrence wins
    assert frames.flags.columns.tolist() == ["domain", "flag", "description"]


def test_area_dimension_marks_aggregates_and_enriches_geography():
    areas = pd.DataFrame({"area_code": [2, 5000, 351, 214], "m49_code": ["004", "001", "159", "158"],
                          "area": ["Afghanistan", "World", "China", "China, Taiwan Province of"]})
    dim = build_area_dimension([areas]).set_index("area_code")
    assert dim.loc[2, "region"] == "Asia" and dim.loc[2, "iso3"] == "AFG" and dim.loc[2, "is_ldc"] == 1
    assert dim.loc[5000, "is_aggregate"] == 1 and pd.isna(dim.loc[5000, "region"])
    assert dim.loc[351, "is_aggregate"] == 1
    assert dim.loc[214, "region"] == "Asia" and dim.loc[214, "iso3"] == "TWN"
