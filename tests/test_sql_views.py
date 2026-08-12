import sqlite3

import pandas as pd

from air_quality_analysis.db import apply_sql_views, load_cleaned_to_sqlite


def _fixture_df() -> pd.DataFrame:
    # 3 days x 24 hours of PM2.5 for one city, with day 2 sparse (<18h)
    # so its daily average should be NULL, and one exceedance day (>60).
    rows = []
    for day, hours_present, values in [
        ("2021-01-01", 24, [70.0] * 24),  # full day, avg 70 -> exceedance
        ("2021-01-02", 10, [10.0] * 10),  # sparse day -> NULL average
        ("2021-01-03", 24, [20.0] * 24),  # full day, avg 20 -> not exceedance
    ]:
        for h in range(hours_present):
            rows.append(
                {
                    "city": "TestCity",
                    "datetime": pd.Timestamp(f"{day} {h:02d}:00:00"),
                    "pollutant": "PM2.5",
                    "value": values[h],
                    "quality_flag": "ok",
                }
            )
    return pd.DataFrame(rows)


def test_views_apply_and_compute_daily_and_exceedance(tmp_path):
    db_path = tmp_path / "test.sqlite"
    load_cleaned_to_sqlite(_fixture_df(), db_path=db_path)
    apply_sql_views(db_path=db_path)

    conn = sqlite3.connect(db_path)
    try:
        daily = pd.read_sql(
            "SELECT * FROM v_city_pollutant_daily ORDER BY date", conn
        )
        exceedance = pd.read_sql(
            "SELECT * FROM v_pm25_exceedance_days ORDER BY date", conn
        )
    finally:
        conn.close()

    assert daily.loc[daily["date"] == "2021-01-01", "avg_value"].iloc[0] == 70.0
    # sparse day (<18 readings) is reported as NULL, not averaged from 10 hours
    assert pd.isna(daily.loc[daily["date"] == "2021-01-02", "avg_value"].iloc[0])
    assert daily.loc[daily["date"] == "2021-01-03", "avg_value"].iloc[0] == 20.0

    # only the two full days have valid (non-NULL) averages -> 2 exceedance rows
    assert len(exceedance) == 2
    assert exceedance.loc[exceedance["date"] == "2021-01-01", "is_exceedance"].iloc[0] == 1
    assert exceedance.loc[exceedance["date"] == "2021-01-03", "is_exceedance"].iloc[0] == 0
