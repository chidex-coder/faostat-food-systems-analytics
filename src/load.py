"""Load stage: create the SQLite warehouse and bulk-insert the tidy frames."""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import DB_PATH, DOMAINS, SQL_DIR
from .extract import MANIFEST_PATH
from .transform import build_area_dimension, transform_domain


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def run_script(con: sqlite3.Connection, name: str) -> None:
    con.executescript((SQL_DIR / name).read_text())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_all(db_path: Path = DB_PATH) -> dict:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = connect(db_path)
    run_script(con, "schema.sql")
    manifest = json.loads(MANIFEST_PATH.read_text()) if MANIFEST_PATH.exists() else {}
    run_at = _now()
    area_frames, summary = [], {}
    for code, dom in DOMAINS.items():
        t0 = time.time()
        frames = transform_domain(dom)
        frames.observations.to_sql("observation", con, if_exists="append", index=False, chunksize=100_000)
        frames.items.to_sql("dim_item", con, if_exists="append", index=False)
        frames.elements.to_sql("dim_element", con, if_exists="append", index=False)
        frames.flags.drop_duplicates(["domain", "flag"]).to_sql("dim_flag", con, if_exists="append", index=False)
        area_frames.append(frames.areas)
        m = manifest.get(code, {})
        con.execute(
            """INSERT INTO dim_domain VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (code, dom.name, dom.zip_name, m.get("url", ""), m.get("sha256"), m.get("server_last_modified"),
             m.get("catalogue_date_update"), m.get("downloaded_at"), frames.stats["rows_raw"],
             frames.stats["rows_loaded"], frames.stats["rows_dropped_missing"],
             frames.stats["rows_dropped_filter"], frames.stats["rows_dropped_dupe"], dom.notes),
        )
        secs = time.time() - t0
        con.execute("INSERT INTO load_log VALUES (?,?,?,?,?)", (run_at, "load", code, secs, json.dumps(frames.stats)))
        con.commit()
        summary[code] = {**frames.stats, "seconds": round(secs, 1)}
        print(f"  [{code}] {frames.stats['rows_loaded']:>9,} rows loaded "
              f"({frames.stats['rows_raw']:,} raw) in {secs:.1f}s")
    areas = build_area_dimension(area_frames)
    areas.to_sql("dim_area", con, if_exists="append", index=False)
    run_script(con, "indexes.sql")
    run_script(con, "views.sql")
    con.commit()
    con.close()
    return summary


if __name__ == "__main__":
    print(json.dumps(load_all(), indent=2))
