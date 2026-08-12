import numpy as np
import pandas as pd
import pytest

from air_quality_analysis.db import apply_sql_views, load_cleaned_to_sqlite
from air_quality_analysis.stats_tests import (
    cohens_d,
    grap_pre_post_ttest,
    one_way_anova_across_cities,
    winter_label,
)


@pytest.mark.parametrize(
    "date_str,expected",
    [
        ("2017-10-05", "2017-2018"),
        ("2017-12-25", "2017-2018"),
        ("2018-01-10", "2017-2018"),
        ("2018-02-28", "2017-2018"),
        ("2018-06-15", None),
    ],
)
def test_winter_label(date_str, expected):
    assert winter_label(pd.Timestamp(date_str)) == expected


def test_cohens_d_known_values():
    a = np.array([10.0, 10.0, 10.0, 10.0])  # no variance in either group
    b = np.array([12.0, 12.0, 12.0, 12.0])
    # pooled sd is 0 here, which would divide by zero -- use slightly
    # varying data instead to keep the test well-defined.
    a = np.array([8.0, 10.0, 10.0, 12.0])
    b = np.array([10.0, 12.0, 12.0, 14.0])
    d = cohens_d(a, b)
    assert d < 0  # a's mean (10) is below b's mean (12)


def test_grap_ttest_insufficient_data_when_group_too_small():
    pre = pd.Series([50.0, 55.0, 60.0])  # only 3 obs, below MIN_N_PER_GROUP
    post = pd.Series([40.0] * 20)
    result = grap_pre_post_ttest(pre, post, min_n=10)
    assert result["status"] == "insufficient_data"
    assert result["n_pre"] == 3


def test_grap_ttest_detects_clear_difference():
    rng = np.random.default_rng(42)
    pre = pd.Series(rng.normal(150, 10, 100))
    post = pd.Series(rng.normal(100, 10, 100))
    result = grap_pre_post_ttest(pre, post, min_n=10)
    assert result["status"] == "tested"
    assert result["significant_at_05"] is True
    assert result["mean_diff"] < 0  # post is lower than pre
    assert result["p_value"] < 0.05


def test_one_way_anova_across_cities(tmp_path):
    rows = []
    # Three cities with clearly different PM2.5 levels -> ANOVA should be
    # significant with a large eta-squared.
    for city, base in [("A", 30.0), ("B", 80.0), ("C", 150.0)]:
        for day in range(1, 21):
            date = pd.Timestamp("2020-01-01") + pd.Timedelta(days=day)
            for h in range(24):
                rows.append(
                    {
                        "city": city,
                        "datetime": date + pd.Timedelta(hours=h),
                        "pollutant": "PM2.5",
                        "value": base + (h % 3),  # tiny within-group noise
                        "quality_flag": "ok",
                    }
                )
    df = pd.DataFrame(rows)
    db_path = tmp_path / "test.sqlite"
    load_cleaned_to_sqlite(df, db_path=db_path)
    apply_sql_views(db_path=db_path)

    result = one_way_anova_across_cities(cities=["A", "B", "C"], db_path=db_path)
    assert result["p_value"] < 0.001
    assert result["eta_squared"] > 0.9  # groups are almost entirely separated
    assert set(result["group_means"]["city"]) == {"A", "B", "C"}
