import sqlite3

import pandas as pd

from air_quality_analysis.db import load_cleaned_to_sqlite


def test_load_cleaned_to_sqlite_writes_readings_table(tmp_path):
    df = pd.DataFrame(
        {
            "city": ["Delhi", "Delhi"],
            "datetime": pd.to_datetime(["2020-01-01 00:00:00", "2020-01-01 01:00:00"]),
            "pollutant": ["PM2.5", "PM2.5"],
            "value": [55.0, 60.0],
            "quality_flag": ["ok", "ok"],
        }
    )
    db_path = tmp_path / "test.sqlite"
    load_cleaned_to_sqlite(df, db_path=db_path)

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT city, pollutant, value FROM readings ORDER BY datetime").fetchall()
    finally:
        conn.close()
    assert rows == [("Delhi", "PM2.5", 55.0), ("Delhi", "PM2.5", 60.0)]
