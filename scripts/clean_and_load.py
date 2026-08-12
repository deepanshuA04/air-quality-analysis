"""Run the cleaning pipeline on the raw tidy data and load it into SQLite.

Run: uv run python scripts/clean_and_load.py
"""

from __future__ import annotations

import pandas as pd

from air_quality_analysis.cleaning import clean_pipeline
from air_quality_analysis.config import DB_PATH, REPORTS_DIR
from air_quality_analysis.db import load_cleaned_to_sqlite
from air_quality_analysis.io_utils import load_tidy


def main() -> None:
    tidy = load_tidy()
    cleaned = clean_pipeline(tidy)

    load_cleaned_to_sqlite(cleaned, db_path=DB_PATH)
    print(f"Loaded {len(cleaned):,} rows into {DB_PATH}")

    counts = cleaned["quality_flag"].value_counts()
    pct = (100 * counts / len(cleaned)).round(2)
    summary = pd.DataFrame({"rows": counts, "pct": pct})
    print(summary)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(REPORTS_DIR / "cleaning_summary.csv")


if __name__ == "__main__":
    main()
