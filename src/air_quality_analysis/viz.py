"""Shared chart styling: fixed city->color mapping and mark defaults.

Palette is the validated categorical set from the dataviz skill (8 hues,
fixed order, adjacent pairs clear the CVD floor in both modes). city->hue
is assigned once here and reused across every figure so a city's color
means the same thing in every chart in this project.
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from air_quality_analysis.config import CITIES

CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
CITY_COLOR = dict(zip(CITIES, CATEGORICAL, strict=True))

INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
SURFACE = "#fcfcfb"

# Sequential blue ramp, ordinal-safe steps (light mode floor: no lighter
# than step 250), used for ordered series like year-on-year comparisons.
SEQUENTIAL_ORDINAL = ["#86b6ef", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]


def apply_base_style(ax: plt.Axes) -> None:
    ax.set_facecolor(SURFACE)
    ax.figure.set_facecolor(SURFACE)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(BASELINE)
    ax.tick_params(colors=INK_SECONDARY, labelsize=9)
    ax.yaxis.grid(True, color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.xaxis.label.set_color(INK_SECONDARY)
    ax.yaxis.label.set_color(INK_SECONDARY)
