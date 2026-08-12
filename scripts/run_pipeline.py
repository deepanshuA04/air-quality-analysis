"""Run the full pipeline in one command: quality profile -> clean -> load
into SQLite -> EDA figures -> hypothesis tests -> Power BI CSV export.

Assumes the raw CSVs already exist in data/raw/ (run
scripts/download_data.py once first — it needs live Kaggle credentials, so
it isn't chained into this script). Every number in the README is produced
by one of the steps below.

Run: uv run python scripts/run_pipeline.py
"""

from __future__ import annotations

import build_quality_profile
import clean_and_load
import export_powerbi_views
import run_eda
import run_stats

from air_quality_analysis.config import CITY_HOUR_CSV

STEPS = [
    ("Data-quality profile", build_quality_profile.main),
    ("Clean + load SQLite + SQL views", clean_and_load.main),
    ("Time-series EDA", run_eda.main),
    ("Hypothesis testing", run_stats.main),
    ("Power BI CSV export", export_powerbi_views.main),
]


def main() -> None:
    if not CITY_HOUR_CSV.exists():
        raise SystemExit(
            f"{CITY_HOUR_CSV} not found. Run `uv run python scripts/download_data.py` "
            "first (requires a Kaggle API token)."
        )

    for label, step in STEPS:
        print(f"\n=== {label} ===")
        step()


if __name__ == "__main__":
    main()
