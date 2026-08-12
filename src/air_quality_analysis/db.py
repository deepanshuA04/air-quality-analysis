"""Loading the cleaned tidy dataset into SQLite and applying the SQL views."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from air_quality_analysis.config import DB_PATH, SQL_DIR

READINGS_TABLE = "readings"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def load_cleaned_to_sqlite(cleaned: pd.DataFrame, db_path: Path = DB_PATH) -> None:
    """Write the cleaned tidy frame (city, datetime, pollutant, value,
    quality_flag) to SQLite as the `readings` table, replacing any
    existing table, then index it for the aggregation queries in sql/.
    """
    out = cleaned.copy()
    out["datetime"] = pd.to_datetime(out["datetime"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection(db_path)
    try:
        out.to_sql(READINGS_TABLE, conn, if_exists="replace", index=False)
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{READINGS_TABLE}_city_pollutant_dt "
            f"ON {READINGS_TABLE}(city, pollutant, datetime)"
        )
        conn.commit()
    finally:
        conn.close()


def apply_sql_views(db_path: Path = DB_PATH, sql_dir: Path = SQL_DIR) -> None:
    """Execute every .sql file in sql_dir (view definitions) against the DB."""
    conn = get_connection(db_path)
    try:
        for sql_file in sorted(sql_dir.glob("*.sql")):
            conn.executescript(sql_file.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
