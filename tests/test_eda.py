import pandas as pd

from air_quality_analysis.db import apply_sql_views, load_cleaned_to_sqlite
from air_quality_analysis.eda import determine_winter_window, quantify_winter_spike


def _fixture_df() -> pd.DataFrame:
    # Two winter months (Dec, Jan) at ~150, two summer months (Jun, Jul) at
    # ~50, for two cities, so the winter window and spike % are known exactly.
    rows = []
    for city, winter_val, summer_val in [("A", 150.0, 50.0), ("B", 90.0, 30.0)]:
        for month, value in [(12, winter_val), (1, winter_val), (6, summer_val), (7, summer_val)]:
            year = 2020 if month != 1 else 2021
            for day in range(1, 6):  # 5 full days/month, 24h each
                date = pd.Timestamp(year=year, month=month, day=day)
                for h in range(24):
                    rows.append(
                        {
                            "city": city,
                            "datetime": date + pd.Timedelta(hours=h),
                            "pollutant": "PM2.5",
                            "value": value,
                            "quality_flag": "ok",
                        }
                    )
    return pd.DataFrame(rows)


def test_determine_winter_window_and_spike(tmp_path):
    db_path = tmp_path / "test.sqlite"
    load_cleaned_to_sqlite(_fixture_df(), db_path=db_path)
    apply_sql_views(db_path=db_path)

    winter_months = determine_winter_window("PM2.5", db_path=db_path)
    assert set(winter_months) == {12, 1}

    spike = quantify_winter_spike("PM2.5", winter_months, cities=["A", "B"], db_path=db_path)
    row_a = spike.set_index("city").loc["A"]
    assert row_a["winter_mean"] == 150.0
    assert row_a["non_winter_mean"] == 50.0
    assert row_a["pct_increase"] == 200.0  # 150 is 200% higher than 50
