import pandas as pd

from air_quality_analysis.profile import build_quality_profile, is_impossible


def test_is_impossible_negative_value():
    assert is_impossible("PM2.5", -5.0) is True


def test_is_impossible_above_ceiling():
    assert is_impossible("CO", 100.0) is True  # ceiling is 50 mg/m3


def test_is_impossible_zero_for_particulate():
    assert is_impossible("PM2.5", 0.0) is True
    assert is_impossible("PM10", 0.0) is True


def test_zero_is_plausible_for_gases():
    # CO/Benzene legitimately read near-zero at their detection limit.
    assert is_impossible("CO", 0.0) is False
    assert is_impossible("Benzene", 0.0) is False


def test_is_impossible_plausible_value():
    assert is_impossible("PM2.5", 45.2) is False


def test_is_impossible_nan_is_not_impossible():
    assert is_impossible("PM2.5", float("nan")) is False


def test_build_quality_profile_counts_missing_and_impossible():
    tidy = pd.DataFrame(
        {
            "city": ["X"] * 4,
            "datetime": pd.date_range("2020-01-01", periods=4, freq="h"),
            "pollutant": ["PM2.5"] * 4,
            "value": [10.0, None, -5.0, 2000.0],
        }
    )
    profile = build_quality_profile(tidy)
    row = profile.iloc[0]
    assert row["expected_hours"] == 4
    assert row["non_null_readings"] == 3
    assert row["n_impossible"] == 2  # -5.0 and 2000.0
    assert row["pct_missing"] == 25.0
