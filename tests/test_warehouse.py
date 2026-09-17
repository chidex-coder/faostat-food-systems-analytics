"""Integration checks against the built warehouse (skipped when data/faostat.db is absent)."""
import sqlite3

import pytest

from src.config import DB_PATH, DOMAINS


pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="warehouse not built")


@pytest.fixture(scope="module")
def con():
    c = sqlite3.connect(DB_PATH)
    yield c
    c.close()


def test_every_domain_loaded(con):
    loaded = {r[0] for r in con.execute("SELECT DISTINCT domain FROM observation")}
    assert loaded == set(DOMAINS)


def test_no_nulls_in_fact_keys_or_values(con):
    n = con.execute("SELECT COUNT(*) FROM observation WHERE value IS NULL OR year IS NULL OR item_code IS NULL").fetchone()[0]
    assert n == 0


def test_aggregates_never_appear_in_country_view(con):
    n = con.execute("SELECT COUNT(*) FROM v_country WHERE area_code >= 5000 OR area_code IN (351, 420)").fetchone()[0]
    assert n == 0


def test_quality_gate_has_no_failures(con):
    n = con.execute("SELECT COUNT(*) FROM dq_check WHERE status = 'fail' AND run_at = (SELECT MAX(run_at) FROM dq_check)").fetchone()[0]
    assert n == 0


def test_world_cereal_production_is_plausible(con):
    v = con.execute("SELECT production_t FROM v_production WHERE area_code = 5000 AND item_code = '1717' ORDER BY year DESC LIMIT 1").fetchone()[0]
    assert 2.5e9 < v < 4e9
