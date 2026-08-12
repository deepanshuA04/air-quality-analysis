"""Loading the raw CPCB CSV into a tidy long-format frame."""

from __future__ import annotations

import pandas as pd

from air_quality_analysis.config import CITIES, CITY_HOUR_CSV, POLLUTANTS


def load_raw_city_hour(path=CITY_HOUR_CSV) -> pd.DataFrame:
    """Read city_hour.csv as-is (wide format, all 26 cities)."""
    df = pd.read_csv(path, parse_dates=["Datetime"])
    return df


def to_tidy_long(df: pd.DataFrame, cities: list[str] = CITIES) -> pd.DataFrame:
    """Melt the wide raw frame to tidy long format for the selected cities.

    Output columns: city, datetime, pollutant, value.
    Rows where the source value is NaN are kept (they represent an hour
    with no reading at all) so downstream profiling/cleaning can count
    them as missing.
    """
    sub = df[df["City"].isin(cities)]
    long = sub.melt(
        id_vars=["City", "Datetime"],
        value_vars=[p for p in POLLUTANTS if p in sub.columns],
        var_name="pollutant",
        value_name="value",
    )
    long = long.rename(columns={"City": "city", "Datetime": "datetime"})
    return long.sort_values(["city", "pollutant", "datetime"]).reset_index(drop=True)


def load_tidy(cities: list[str] = CITIES) -> pd.DataFrame:
    return to_tidy_long(load_raw_city_hour(), cities=cities)
