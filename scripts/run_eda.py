"""Time-series EDA: rolling averages, year-on-year comparison, seasonal
profile, and the quantified winter spike. Writes figures to reports/figures/
and summary tables to reports/.

Run: uv run python scripts/run_eda.py
"""

from __future__ import annotations

import calendar

import matplotlib.pyplot as plt

from air_quality_analysis.config import CITIES, FIGURES_DIR, REPORTS_DIR
from air_quality_analysis.eda import (
    determine_winter_window,
    load_monthly,
    load_monthly_profile,
    load_rolling30,
    quantify_winter_spike,
)
from air_quality_analysis.viz import (
    CITY_COLOR,
    SEQUENTIAL_ORDINAL,
    apply_base_style,
)

MONTH_NAMES = [calendar.month_abbr[m] for m in range(1, 13)]


def fig_rolling30(pollutant: str = "PM2.5") -> None:
    """30-day rolling average per city, small multiples (one panel per
    city, shared y-scale) rather than 8 overlaid lines — at this series
    count the lines are dense/noisy enough that overlay hurts more than
    it helps, and a single hue per panel sidesteps the 8-way CVD limit.
    """
    data = load_rolling30(pollutant)
    fig, axes = plt.subplots(4, 2, figsize=(11, 12), sharex=True, sharey=True)
    ymax = data["rolling_30d_avg"].max() * 1.05
    for ax, city in zip(axes.flat, CITIES, strict=True):
        sub = data[data["city"] == city]
        apply_base_style(ax)
        ax.plot(sub["date"], sub["rolling_30d_avg"], color="#2a78d6", linewidth=1.4)
        ax.set_title(city, loc="left", color="#0b0b0b", fontsize=11, fontweight="bold")
        ax.set_ylim(0, ymax)
    fig.suptitle(
        f"{pollutant} — 30-day rolling average by city (2015-2020)",
        fontsize=14,
        y=1.0,
        color="#0b0b0b",
    )
    fig.supylabel(f"{pollutant} (µg/m³)", color="#52514e")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / f"rolling30_{pollutant.replace('.', '')}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_seasonal_profile(pollutant: str = "PM2.5") -> None:
    """Average by calendar month, one line per city, pooled across years —
    the empirical seasonal profile used to identify the high-risk window.
    """
    profile = load_monthly_profile(pollutant)
    fig, ax = plt.subplots(figsize=(10, 6))
    apply_base_style(ax)
    for city in CITIES:
        sub = profile[profile["city"] == city].sort_values("calendar_month")
        ax.plot(
            sub["calendar_month"],
            sub["avg_value"],
            color=CITY_COLOR[city],
            linewidth=2,
            marker="o",
            markersize=4,
            label=city,
        )
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MONTH_NAMES)
    ax.set_ylabel(f"Mean {pollutant} (µg/m³)")
    ax.set_title(
        f"{pollutant} seasonal profile by calendar month, 2015-2020 (pooled across years)",
        loc="left",
        color="#0b0b0b",
        fontsize=12,
    )
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=9)
    fig.tight_layout()
    fig.savefig(
        FIGURES_DIR / f"seasonal_profile_{pollutant.replace('.', '')}.png",
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(fig)


def fig_yoy(city: str = "Delhi", pollutant: str = "PM2.5") -> None:
    """Year-on-year comparison for one flagship city: monthly average per
    calendar month, one line per year (sequential ramp — years are
    ordinal, so this is a magnitude/order encoding, not identity).
    """
    monthly = load_monthly(pollutant)
    sub = monthly[monthly["city"] == city].copy()
    sub["month"] = sub["month"].astype(int)
    years = sorted(sub["year"].unique())

    fig, ax = plt.subplots(figsize=(9, 5.5))
    apply_base_style(ax)
    for i, year in enumerate(years):
        color = SEQUENTIAL_ORDINAL[i % len(SEQUENTIAL_ORDINAL)]
        yr = sub[sub["year"] == year].sort_values("month")
        ax.plot(yr["month"], yr["avg_value"], color=color, linewidth=2, marker="o", markersize=4, label=year)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MONTH_NAMES)
    ax.set_ylabel(f"Mean {pollutant} (µg/m³)")
    ax.set_title(
        f"{city} — {pollutant} by month, year-on-year",
        loc="left",
        color="#0b0b0b",
        fontsize=12,
    )
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=9, title="Year")
    fig.tight_layout()
    fig.savefig(
        FIGURES_DIR / f"yoy_{city.lower()}_{pollutant.replace('.', '')}.png",
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    fig_rolling30("PM2.5")
    fig_seasonal_profile("PM2.5")
    fig_yoy("Delhi", "PM2.5")

    winter_months = determine_winter_window("PM2.5")
    month_names = [calendar.month_name[m] for m in winter_months]
    print("Empirically-determined high-risk months:", month_names)

    spike = quantify_winter_spike("PM2.5", winter_months)
    spike.to_csv(REPORTS_DIR / "winter_spike_by_city.csv", index=False)
    print(spike.to_string(index=False))
    print("Mean % increase across 8 cities:", round(spike["pct_increase"].mean(), 1))

    profile = load_monthly_profile("PM2.5")
    profile.to_csv(REPORTS_DIR / "seasonal_profile_pm25.csv", index=False)

    with (REPORTS_DIR / "winter_window.txt").open("w", encoding="utf-8") as f:
        f.write(",".join(str(m) for m in winter_months))


if __name__ == "__main__":
    main()
