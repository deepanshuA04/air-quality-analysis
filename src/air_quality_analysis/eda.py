"""Time-series EDA: rolling averages, year-on-year comparison, and the
empirical seasonal ("winter window") profile. Reads from the SQL views in
sql/views.sql rather than recomputing aggregates in Pandas.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from air_quality_analysis.config import CITIES, DB_PATH


def _conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def load_rolling30(pollutant: str, db_path: Path = DB_PATH) -> pd.DataFrame:
    conn = _conn(db_path)
    try:
        return pd.read_sql(
            "SELECT city, date, avg_value, rolling_30d_avg "
            "FROM v_city_pollutant_daily_rolling30 WHERE pollutant = ? ORDER BY city, date",
            conn,
            params=[pollutant],
            parse_dates=["date"],
        )
    finally:
        conn.close()


def load_monthly(pollutant: str, db_path: Path = DB_PATH) -> pd.DataFrame:
    conn = _conn(db_path)
    try:
        return pd.read_sql(
            "SELECT city, year, month, year_month, avg_value "
            "FROM v_city_pollutant_monthly WHERE pollutant = ? ORDER BY city, year_month",
            conn,
            params=[pollutant],
        )
    finally:
        conn.close()


def load_monthly_profile(pollutant: str, db_path: Path = DB_PATH) -> pd.DataFrame:
    conn = _conn(db_path)
    try:
        return pd.read_sql(
            "SELECT city, calendar_month, avg_value, n_days_with_data "
            "FROM v_city_monthly_profile WHERE pollutant = ? ORDER BY city, calendar_month",
            conn,
            params=[pollutant],
        )
    finally:
        conn.close()


def determine_winter_window(pollutant: str = "PM2.5", db_path: Path = DB_PATH) -> list[int]:
    """Empirically identify the high-pollution months: calendar months whose
    pooled (unweighted mean-of-city-means) PM2.5 average exceeds the pooled
    mean-of-monthly-means for the year, rather than assuming Oct-Jan.
    """
    profile = load_monthly_profile(pollutant, db_path=db_path)
    pooled_by_month = profile.groupby("calendar_month")["avg_value"].mean()
    overall_mean = pooled_by_month.mean()
    winter_months = sorted(pooled_by_month[pooled_by_month > overall_mean].index.tolist())
    return winter_months


def quantify_winter_spike(
    pollutant: str = "PM2.5",
    winter_months: list[int] | None = None,
    cities: list[str] = CITIES,
    db_path: Path = DB_PATH,
) -> pd.DataFrame:
    """Per-city winter-window vs non-winter-window daily mean and % increase."""
    if winter_months is None:
        winter_months = determine_winter_window(pollutant, db_path=db_path)

    conn = _conn(db_path)
    try:
        daily = pd.read_sql(
            "SELECT city, date, avg_value FROM v_city_pollutant_daily "
            "WHERE pollutant = ? AND avg_value IS NOT NULL",
            conn,
            params=[pollutant],
            parse_dates=["date"],
        )
    finally:
        conn.close()

    daily = daily[daily["city"].isin(cities)].copy()
    daily["month"] = daily["date"].dt.month
    daily["is_winter"] = daily["month"].isin(winter_months)

    rows = []
    for city, grp in daily.groupby("city"):
        winter_mean = grp.loc[grp["is_winter"], "avg_value"].mean()
        non_winter_mean = grp.loc[~grp["is_winter"], "avg_value"].mean()
        pct_increase = 100 * (winter_mean / non_winter_mean - 1)
        rows.append(
            {
                "city": city,
                "winter_mean": round(winter_mean, 2),
                "non_winter_mean": round(non_winter_mean, 2),
                "pct_increase": round(pct_increase, 1),
            }
        )
    out = pd.DataFrame(rows).sort_values("pct_increase", ascending=False).reset_index(drop=True)
    return out
