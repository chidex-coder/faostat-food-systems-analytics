"""End-to-end build: extract -> transform/load -> quality gate -> analysis -> ML -> dashboard.

    python run_pipeline.py            # full build
    python run_pipeline.py --skip-extract   # reuse archives already in data/raw
    python run_pipeline.py --only analysis dashboard
"""
from __future__ import annotations

import argparse
import sys
import time

from src import analysis, dashboard, extract, load, ml, quality
from src.config import DB_PATH

STAGES = ["extract", "load", "quality", "analysis", "ml", "dashboard"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-extract", action="store_true", help="do not re-download FAOSTAT archives")
    ap.add_argument("--only", nargs="+", choices=STAGES, help="run only these stages")
    args = ap.parse_args()
    stages = args.only or STAGES
    if args.skip_extract and "extract" in stages:
        stages = [s for s in stages if s != "extract"]
    t0 = time.time()
    for stage in stages:
        print(f"\n== {stage} ==")
        ts = time.time()
        if stage == "extract":
            extract.extract_bulk()
        elif stage == "load":
            load.load_all()
        elif stage == "quality":
            con = load.connect(DB_PATH)
            results = quality.run_checks(con)
            con.close()
            failed = [r for r in results if r["status"] == "fail"]
            warned = [r for r in results if r["status"] == "warn"]
            for r in failed + warned:
                print(f"  {r['status'].upper():5} {r['check']} [{r['domain'] or 'all'}] observed={r['observed']} threshold={r['threshold']} {r['detail'] or ''}")
            print(f"  {len(results)} checks: {len(failed)} failed, {len(warned)} warnings")
            if failed:
                print("quality gate failed; stopping")
                return 1
        elif stage == "analysis":
            analysis.run_all()
        elif stage == "ml":
            ml.run_all()
        elif stage == "dashboard":
            dashboard.build()
        print(f"  ({time.time() - ts:.0f}s)")
    print(f"\ndone in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
