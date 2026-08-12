"""Hypothesis testing: GRAP before/after (Welch's t-test) and a one-way
ANOVA comparing PM2.5 across the 8 cities.

GRAP (Graded Response Action Plan) was notified for Delhi-NCR on
17 Jan 2017 and first operationally enforced from 17 Oct 2017
(https://www.cseindia.org/graded-response-action-plan-to-control-air-pollution-in-delhi-ncr-in-very-poor-and-severe-categories-comes-into-effect-from-october-17-2017-says-epca-8506).
Comparison uses the same calendar months (Oct-Feb) in every year so the
pre/post split isn't confounded by season: 2 pre-GRAP winters
(2015-16, 2016-17) vs. 3 post-GRAP winters (2017-18, 2018-19, 2019-20).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from air_quality_analysis.config import CITIES, DB_PATH

WINTER_MONTHS = {10, 11, 12, 1, 2}
PRE_GRAP_WINTERS = {"2015-2016", "2016-2017"}
POST_GRAP_WINTERS = {"2017-2018", "2018-2019", "2019-2020"}
MIN_N_PER_GROUP = 10


def winter_label(date: pd.Timestamp) -> str | None:
    """Label a date with its Oct-Feb "winter season", e.g. 2017-10-05 and
    2018-02-10 both fall in winter "2017-2018". Non-winter months -> None.
    """
    if date.month in (10, 11, 12):
        return f"{date.year}-{date.year + 1}"
    if date.month in (1, 2):
        return f"{date.year - 1}-{date.year}"
    return None


def _load_daily_pm25(city: str, db_path: Path = DB_PATH) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql(
            "SELECT date, avg_value FROM v_city_pollutant_daily "
            "WHERE pollutant = 'PM2.5' AND city = ? AND avg_value IS NOT NULL",
            conn,
            params=[city],
            parse_dates=["date"],
        )
    finally:
        conn.close()


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's d for two independent samples, pooled standard deviation."""
    n_a, n_b = len(a), len(b)
    pooled_sd = np.sqrt(((n_a - 1) * a.var(ddof=1) + (n_b - 1) * b.var(ddof=1)) / (n_a + n_b - 2))
    return (a.mean() - b.mean()) / pooled_sd


def grap_pre_post_ttest(pre: pd.Series, post: pd.Series, min_n: int = MIN_N_PER_GROUP) -> dict:
    """Welch's t-test of post vs. pre GRAP daily PM2.5 values.

    Returns a result dict; if either group has fewer than min_n
    observations, status is "insufficient_data" and no test is run
    (rather than reporting a statistic computed from a handful of days).
    """
    n_pre, n_post = len(pre), len(post)
    if n_pre < min_n or n_post < min_n:
        return {
            "status": "insufficient_data",
            "n_pre": n_pre,
            "n_post": n_post,
            "mean_pre": pre.mean() if n_pre else np.nan,
            "mean_post": post.mean() if n_post else np.nan,
        }

    t_stat, p_value = scipy_stats.ttest_ind(post, pre, equal_var=False)
    mean_pre, mean_post = pre.mean(), post.mean()
    return {
        "status": "tested",
        "n_pre": n_pre,
        "n_post": n_post,
        "mean_pre": round(mean_pre, 2),
        "mean_post": round(mean_post, 2),
        "mean_diff": round(mean_post - mean_pre, 2),
        "pct_change": round(100 * (mean_post / mean_pre - 1), 1),
        "t_stat": round(t_stat, 3),
        "p_value": p_value,
        "cohens_d": round(cohens_d(post.to_numpy(), pre.to_numpy()), 3),
        "significant_at_05": bool(p_value < 0.05),
    }


def run_grap_analysis(cities: list[str] = CITIES, db_path: Path = DB_PATH) -> pd.DataFrame:
    rows = []
    for city in cities:
        daily = _load_daily_pm25(city, db_path=db_path)
        daily["winter"] = daily["date"].apply(winter_label)
        pre = daily.loc[daily["winter"].isin(PRE_GRAP_WINTERS), "avg_value"]
        post = daily.loc[daily["winter"].isin(POST_GRAP_WINTERS), "avg_value"]
        result = grap_pre_post_ttest(pre, post)
        result["city"] = city
        rows.append(result)
    cols = [
        "city", "status", "n_pre", "n_post", "mean_pre", "mean_post",
        "mean_diff", "pct_change", "t_stat", "p_value", "cohens_d", "significant_at_05",
    ]
    return pd.DataFrame(rows)[cols]


def one_way_anova_across_cities(
    pollutant: str = "PM2.5", cities: list[str] = CITIES, db_path: Path = DB_PATH
) -> dict:
    """One-way ANOVA of daily pollutant means across all 8 cities (full
    study period), plus eta-squared as the effect size.
    """
    conn = sqlite3.connect(db_path)
    try:
        daily = pd.read_sql(
            "SELECT city, avg_value FROM v_city_pollutant_daily "
            "WHERE pollutant = ? AND avg_value IS NOT NULL",
            conn,
            params=[pollutant],
        )
    finally:
        conn.close()
    daily = daily[daily["city"].isin(cities)]

    groups = [g["avg_value"].to_numpy() for _, g in daily.groupby("city")]
    f_stat, p_value = scipy_stats.f_oneway(*groups)

    grand_mean = daily["avg_value"].mean()
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
    ss_total = ((daily["avg_value"] - grand_mean) ** 2).sum()
    eta_squared = ss_between / ss_total

    group_means = daily.groupby("city")["avg_value"].agg(["mean", "std", "count"]).round(2)
    group_means = group_means.rename(columns={"mean": "mean_pm25", "std": "sd_pm25", "count": "n_days"})

    return {
        "f_stat": round(f_stat, 2),
        "p_value": p_value,
        "eta_squared": round(eta_squared, 4),
        "group_means": group_means.reset_index(),
    }
