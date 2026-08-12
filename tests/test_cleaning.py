import numpy as np
import pandas as pd
import pytest

from air_quality_analysis.cleaning import (
    clean_pipeline,
    flag_impossible_values,
    flag_outliers_iqr,
    interpolate_short_gaps,
)


def test_flag_impossible_values_nulls_negative_and_above_ceiling():
    df = pd.DataFrame(
        {
            "city": ["X"] * 3,
            "datetime": pd.date_range("2020-01-01", periods=3, freq="h"),
            "pollutant": ["PM2.5"] * 3,
            "value": [-1.0, 50.0, 5000.0],  # negative, plausible, above ceiling (1000)
        }
    )
    out = flag_impossible_values(df)
    assert out["value"].tolist()[0] is None or np.isnan(out["value"].tolist()[0])
    assert out["value"].tolist()[1] == 50.0
    assert np.isnan(out["value"].tolist()[2])


def test_flag_impossible_values_zero_only_for_particulates():
    df = pd.DataFrame(
        {
            "city": ["X"] * 2,
            "datetime": pd.date_range("2020-01-01", periods=2, freq="h"),
            "pollutant": ["PM2.5", "CO"],
            "value": [0.0, 0.0],
        }
    )
    out = flag_impossible_values(df)
    assert np.isnan(out.loc[0, "value"])  # PM2.5 zero -> impossible
    assert out.loc[1, "value"] == 0.0  # CO zero -> plausible, kept


def _hourly_fixture(values: list[float]) -> pd.DataFrame:
    n = len(values)
    return pd.DataFrame(
        {
            "city": ["X"] * n,
            "datetime": pd.date_range("2020-01-01", periods=n, freq="h"),
            "pollutant": ["PM2.5"] * n,
            "value": values,
        }
    )


def test_interpolate_short_gaps_fills_short_gap_only():
    # index 0: unbounded edge NaN; 1-2: valid; 3-5: 3-hour gap (short, <=3);
    # 6: valid; 7-14: 8-hour gap (long, >3); 15: valid.
    values = (
        [np.nan]
        + [10.0, 20.0]
        + [np.nan, np.nan, np.nan]
        + [60.0]
        + [np.nan] * 8
        + [150.0]
    )
    df = _hourly_fixture(values)
    out = interpolate_short_gaps(df, max_gap_hours=3)
    out = out.sort_values("datetime").reset_index(drop=True)

    assert out.loc[0, "quality_flag"] == "missing_long_gap"  # unbounded edge
    assert out.loc[1, "quality_flag"] == "ok"
    # short gap (indices 3,4,5) linearly interpolated between 20 and 60
    assert out.loc[3, "quality_flag"] == "interpolated"
    assert out.loc[4, "value"] == pytest.approx(40.0)
    # long gap (indices 7..14) stays missing
    assert (out.loc[7:14, "quality_flag"] == "missing_long_gap").all()
    assert out.loc[7:14, "value"].isna().all()


def test_flag_outliers_iqr_flags_extreme_value_within_city_month():
    # 10 "normal" January PM2.5 readings around 50, plus one extreme 900.
    n = 11
    values = [45, 48, 50, 52, 49, 51, 47, 53, 50, 46, 900.0]
    df = pd.DataFrame(
        {
            "city": ["Delhi"] * n,
            "datetime": pd.date_range("2020-01-01", periods=n, freq="h"),
            "pollutant": ["PM2.5"] * n,
            "value": values,
            "quality_flag": ["ok"] * n,
        }
    )
    out = flag_outliers_iqr(df)
    assert out.iloc[-1]["quality_flag"] == "outlier_seasonal"
    assert out.iloc[-1]["value"] == 900.0  # value is kept, not removed
    assert (out.iloc[:-1]["quality_flag"] == "ok").all()


def test_clean_pipeline_end_to_end_columns():
    df = _hourly_fixture([10.0, -5.0, np.nan, np.nan, 30.0])
    out = clean_pipeline(df, max_gap_hours=6)
    assert list(out.columns) == ["city", "datetime", "pollutant", "value", "quality_flag"]
    assert set(out["quality_flag"]).issubset(
        {"ok", "interpolated", "missing_long_gap", "outlier_seasonal"}
    )
