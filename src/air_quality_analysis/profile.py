"""Pre-cleaning data-quality profile: row counts, missingness, and impossible
values per city, per pollutant, per year. Computed on the raw tidy frame
before any cleaning rule runs, so the "before" numbers are real.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from air_quality_analysis.config import PLAUSIBLE_CEILING, ZERO_IS_IMPOSSIBLE


def is_impossible(pollutant: str, value: float) -> bool:
    if pd.isna(value):
        return False
    if value < 0:
        return True
    if value > PLAUSIBLE_CEILING[pollutant]:
        return True
    return pollutant in ZERO_IS_IMPOSSIBLE and value == 0


def _city_windows(tidy: pd.DataFrame) -> pd.DataFrame:
    """First/last timestamp seen for each city, across any pollutant."""
    return tidy.groupby("city")["datetime"].agg(window_start="min", window_end="max")


def build_quality_profile(tidy: pd.DataFrame) -> pd.DataFrame:
    """Return one row per (city, pollutant, year) with quality metrics.

    expected_hours is the number of calendar hours in that year that fall
    inside the city's overall monitoring window (its first-to-last
    timestamp across all pollutants) — i.e. hours the station could
    plausibly have reported, not padded to a fixed 2019-2024 range.
    """
    tidy = tidy.copy()
    tidy["year"] = tidy["datetime"].dt.year
    windows = _city_windows(tidy)

    rows = []
    for (city, pollutant, year), grp in tidy.groupby(["city", "pollutant", "year"]):
        window_start = windows.loc[city, "window_start"]
        window_end = windows.loc[city, "window_end"]
        year_start = max(pd.Timestamp(year=year, month=1, day=1), window_start)
        year_end = min(pd.Timestamp(year=year + 1, month=1, day=1), window_end + pd.Timedelta(hours=1))
        expected_hours = max(int((year_end - year_start) / pd.Timedelta(hours=1)), 0)

        non_null = grp["value"].notna()
        n_present = int(non_null.sum())
        values = grp["value"]
        impossible_mask = non_null & ((values < 0) | (values > PLAUSIBLE_CEILING[pollutant]))
        if pollutant in ZERO_IS_IMPOSSIBLE:
            impossible_mask = impossible_mask | (non_null & (values == 0))
        n_impossible = int(impossible_mask.sum())

        rows.append(
            {
                "city": city,
                "pollutant": pollutant,
                "year": year,
                "expected_hours": expected_hours,
                "rows_in_file": len(grp),
                "non_null_readings": n_present,
                "pct_missing": round(100 * (1 - n_present / expected_hours), 2) if expected_hours else np.nan,
                "min_value": grp.loc[non_null, "value"].min() if n_present else np.nan,
                "max_value": grp.loc[non_null, "value"].max() if n_present else np.nan,
                "n_impossible": n_impossible,
                "pct_impossible_of_readings": round(100 * n_impossible / n_present, 3) if n_present else np.nan,
            }
        )

    return pd.DataFrame(rows).sort_values(["city", "pollutant", "year"]).reset_index(drop=True)


def summarize_by_city(profile: pd.DataFrame) -> pd.DataFrame:
    """Collapse the profile across pollutants+years into one row per city."""
    g = profile.groupby("city").agg(
        expected_hours=("expected_hours", "sum"),
        non_null_readings=("non_null_readings", "sum"),
        n_impossible=("n_impossible", "sum"),
    )
    g["pct_missing"] = round(100 * (1 - g["non_null_readings"] / g["expected_hours"]), 2)
    g["pct_impossible_of_readings"] = round(100 * g["n_impossible"] / g["non_null_readings"], 3)
    return g.reset_index()


def summarize_by_pollutant(profile: pd.DataFrame) -> pd.DataFrame:
    """Collapse the profile across cities+years into one row per pollutant."""
    g = profile.groupby("pollutant").agg(
        expected_hours=("expected_hours", "sum"),
        non_null_readings=("non_null_readings", "sum"),
        n_impossible=("n_impossible", "sum"),
    )
    g["pct_missing"] = round(100 * (1 - g["non_null_readings"] / g["expected_hours"]), 2)
    g["pct_impossible_of_readings"] = round(100 * g["n_impossible"] / g["non_null_readings"], 3)
    return g.reset_index()
