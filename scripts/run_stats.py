"""GRAP before/after Welch's t-test (per city) and a one-way ANOVA of
PM2.5 across the 8 cities. Writes tables to reports/ and a summary figure
to reports/figures/.

Run: uv run python scripts/run_stats.py
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from air_quality_analysis.config import CITIES, FIGURES_DIR, REPORTS_DIR
from air_quality_analysis.stats_tests import one_way_anova_across_cities, run_grap_analysis
from air_quality_analysis.viz import CITY_COLOR, apply_base_style


def fig_grap_group_means(grap: pd.DataFrame) -> None:
    tested = grap[grap["status"] == "tested"].copy()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    apply_base_style(ax)
    x = np.arange(len(tested))
    width = 0.35
    ax.bar(x - width / 2, tested["mean_pre"], width, color="#c3c2b7", label="Pre-GRAP winters (2015-16, 2016-17)")
    ax.bar(
        x + width / 2,
        tested["mean_post"],
        width,
        color=[CITY_COLOR[c] for c in tested["city"]],
        label="Post-GRAP winters (2017-18 to 2019-20)",
    )
    ymax = float(tested[["mean_pre", "mean_post"]].to_numpy().max())
    ax.set_ylim(0, ymax * 1.15)
    for i, row in enumerate(tested.itertuples()):
        marker = "*" if row.significant_at_05 else "ns"
        ax.text(
            i, max(row.mean_pre, row.mean_post) + ymax * 0.02, marker,
            ha="center", fontsize=11, color="#0b0b0b",
        )
    ax.set_xticks(x)
    ax.set_xticklabels(tested["city"], rotation=20, ha="right")
    ax.set_ylabel("Mean winter (Oct-Feb) PM2.5 (µg/m³)")
    ax.set_title(
        "GRAP before/after: winter PM2.5 by city (* = p<0.05 Welch's t-test, ns = not significant)",
        loc="left",
        fontsize=11,
        color="#0b0b0b",
    )
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.14), ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "grap_before_after_pm25.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    grap = run_grap_analysis(CITIES)
    grap.to_csv(REPORTS_DIR / "grap_before_after.csv", index=False)
    print("=== GRAP before/after, per city ===")
    print(grap.to_string(index=False))

    fig_grap_group_means(grap)

    anova = one_way_anova_across_cities("PM2.5", CITIES)
    anova["group_means"].to_csv(REPORTS_DIR / "anova_pm25_group_means.csv", index=False)
    print("\n=== One-way ANOVA, PM2.5 across 8 cities ===")
    print(f"F = {anova['f_stat']}, p = {anova['p_value']:.3e}, eta^2 = {anova['eta_squared']}")
    print(anova["group_means"].to_string(index=False))


if __name__ == "__main__":
    main()
