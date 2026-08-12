"""Cleaning pipeline: impossible-value removal, gap-aware interpolation, and
seasonal (per city+pollutant+month) outlier flagging.

Each rule is a standalone, unit-testable function; clean_pipeline wires them
together in the order the README documents.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from air_quality_analysis.config import PLAUSIBLE_CEILING, SHORT_GAP_MAX_HOURS, ZERO_IS_IMPOSSIBLE


def flag_impossible_values(df: pd.DataFrame) -> pd.DataFrame:
    """Null out physically-impossible readings (negative, above the
    per-pollutant plausibility ceiling, or exact-zero for particulate
    matter). Returns a copy with `value` updated; impossible values are
    dropped, not kept, per the project's cleaning rules.
    """
    out = df.copy()
    non_null = out["value"].notna()
    ceiling = out["pollutant"].map(PLAUSIBLE_CEILING)
    impossible = non_null & ((out["value"] < 0) | (out["value"] > ceiling))
    zero_rule = non_null & out["pollutant"].isin(ZERO_IS_IMPOSSIBLE) & (out["value"] == 0)
    out.loc[impossible | zero_rule, "value"] = np.nan
    return out


def _interpolate_series(series: pd.Series, max_gap_hours: int) -> tuple[pd.Series, pd.Series]:
    """Interpolate one regularly-spaced hourly series (indexed by datetime).

    Returns (filled_values, quality_flag) where quality_flag is one of
    "ok" (was never missing), "interpolated" (gap <= max_gap_hours, filled),
    or "missing_long_gap" (still NaN: gap too long, or unbounded at an edge).

    pandas' `interpolate(limit=...)` caps the number of NaNs filled *from
    each edge of a gap* rather than skipping gaps longer than the limit
    entirely, so gap length is computed explicitly here instead.
    """
    was_missing = series.isna()
    # Fills every interior (bounded-on-both-sides) gap regardless of
    # length; leaves gaps touching either edge of the series as NaN.
    filled_interior = series.interpolate(method="time", limit_area="inside")

    run_id = (~was_missing).cumsum()
    run_length = was_missing.astype(int).groupby(run_id).transform("sum")

    is_short_bounded = was_missing & filled_interior.notna() & (run_length <= max_gap_hours)

    filled = series.copy()
    filled[is_short_bounded] = filled_interior[is_short_bounded]

    flag = pd.Series("ok", index=series.index, dtype=object)
    flag[is_short_bounded] = "interpolated"
    flag[was_missing & ~is_short_bounded] = "missing_long_gap"
    return filled, flag


def interpolate_short_gaps(
    df: pd.DataFrame, max_gap_hours: int = SHORT_GAP_MAX_HOURS
) -> pd.DataFrame:
    """Apply _interpolate_series per (city, pollutant) group.

    Short gaps (<= max_gap_hours consecutive missing hours) are filled by
    time-based linear interpolation. Long gaps are left missing rather than
    invented. Requires df sorted by datetime within each group and a
    regular hourly grid (true for this dataset; see the coverage check in
    the data-quality profile).
    """
    out = df.sort_values(["city", "pollutant", "datetime"]).copy()

    def _apply(group: pd.DataFrame) -> pd.DataFrame:
        s = group.set_index("datetime")["value"]
        filled, flag = _interpolate_series(s, max_gap_hours)
        group = group.copy()
        group["value"] = filled.to_numpy()
        group["quality_flag"] = flag.to_numpy()
        return group

    out = out.groupby(["city", "pollutant"], group_keys=False)[out.columns].apply(_apply)
    return out.reset_index(drop=True)


def flag_outliers_iqr(df: pd.DataFrame, iqr_multiplier: float = 1.5) -> pd.DataFrame:
    """Flag seasonal outliers among genuine ("ok") readings only.

    IQR fences are computed per (city, pollutant, calendar month), pooling
    across all years, so a Delhi PM2.5 reading is judged against Delhi's
    own winter distribution rather than a single global threshold (which
    would flag nearly every winter night in Delhi as an outlier). Values
    outside the fence are flagged "outlier_seasonal" but kept — this rule
    marks readings as unusual for their city-month, not wrong.
    """
    out = df.copy()
    out["month"] = pd.to_datetime(out["datetime"]).dt.month

    def _fences(s: pd.Series) -> tuple[float, float]:
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        return q1 - iqr_multiplier * iqr, q3 + iqr_multiplier * iqr

    ok_mask = out["quality_flag"] == "ok"
    fences = (
        out[ok_mask]
        .groupby(["city", "pollutant", "month"])["value"]
        .apply(_fences)
        .rename("fences")
    )
    lo = fences.apply(lambda t: t[0])
    hi = fences.apply(lambda t: t[1])
    key = list(zip(out["city"], out["pollutant"], out["month"], strict=True))
    lo_vals = pd.Series(key, index=out.index).map(lo)
    hi_vals = pd.Series(key, index=out.index).map(hi)

    outlier_mask = ok_mask & ((out["value"] < lo_vals) | (out["value"] > hi_vals))
    out.loc[outlier_mask, "quality_flag"] = "outlier_seasonal"
    return out.drop(columns="month")


def clean_pipeline(tidy: pd.DataFrame, max_gap_hours: int = SHORT_GAP_MAX_HOURS) -> pd.DataFrame:
    """Run the full cleaning pipeline in order: impossible -> gaps -> outliers.

    Input: tidy long frame with columns city, datetime, pollutant, value.
    Output: same shape plus quality_flag, one of
    {ok, interpolated, missing_long_gap, outlier_seasonal}.
    """
    step1 = flag_impossible_values(tidy)
    step2 = interpolate_short_gaps(step1, max_gap_hours=max_gap_hours)
    step3 = flag_outliers_iqr(step2)
    return step3[["city", "datetime", "pollutant", "value", "quality_flag"]]
