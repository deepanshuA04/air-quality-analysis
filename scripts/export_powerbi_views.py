"""Export every SQL view to a CSV that Power BI reads directly, so metric
definitions live in SQL (sql/views.sql) rather than being re-derived in DAX.

Run: uv run python scripts/export_powerbi_views.py
"""

from __future__ import annotations

import sqlite3

import pandas as pd

from air_quality_analysis.config import DB_PATH, ROOT

POWERBI_DIR = ROOT / "powerbi" / "data"

VIEWS = [
    "v_city_pollutant_daily",
    "v_city_pollutant_daily_rolling30",
    "v_city_pollutant_monthly",
    "v_city_pollutant_monthly_mom",
    "v_city_monthly_profile",
    "v_pm25_exceedance_days",
    "v_pm25_exceedance_summary",
]


def main() -> None:
    POWERBI_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        for view in VIEWS:
            df = pd.read_sql(f"SELECT * FROM {view}", conn)
            out_path = POWERBI_DIR / f"{view}.csv"
            df.to_csv(out_path, index=False)
            print(f"{view}: {len(df):,} rows -> {out_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
