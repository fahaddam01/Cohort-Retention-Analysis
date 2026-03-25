"""
Churn waterfall / funnel renderer.

Shows how each acquisition channel's cohort shrinks from M+0 through M+6.
Reveals exactly where in the journey each channel loses donors.

Two chart types:
  1. Stacked area chart: absolute donor counts stacked by channel over time
  2. Funnel waterfall: side-by-side bars per period showing attrition
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, Dict

BG_COLOR       = "#0f1117"
TEXT_PRIMARY   = "#e8e6e0"
TEXT_SECONDARY = "#9c9a8e"
GRID_COLOR     = "#1e2029"
FONT_FAMILY    = "monospace"

CHANNEL_COLORS = {
    "email_campaign":   "#4f9de8",
    "organic_social":   "#e87e4f",
    "direct_referral":  "#56c97a",
    "paid_social":      "#e84f7e",
    "event_in_person":  "#c9a956",
    "direct_mail":      "#9e56c9",
}
DEFAULT_COLORS = ["#4f9de8", "#e87e4f", "#56c97a", "#e84f7e", "#c9a956", "#9e56c9"]


def plot_churn_waterfall(
    retention_grid: pd.DataFrame,
    cohort_sizes: pd.Series,
    channel_col: str = "channel",
    title: str = "Donor Retention Funnel by Channel",
    output_path: Optional[str] = None,
    figsize: tuple = (14, 8),
    dark_mode: bool = True,
) -> plt.Figure:
    """
    Renders a grouped bar chart showing active donors per channel at each period.
    The visual drop-off from bar to bar IS the churn story.

    Parameters
    ----------
    retention_grid : pd.DataFrame
        Retention rates — index = cohort labels, columns = M+0 ... M+N
    cohort_sizes : pd.Series
        Number of donors per cohort (index aligned with retention_grid.index)
    """

    bg = BG_COLOR if dark_mode else "#ffffff"
    fg = TEXT_PRIMARY if dark_mode else "#1a1a1a"
    secondary = TEXT_SECONDARY if dark_mode else "#666666"
    grid_c = GRID_COLOR if dark_mode else "#f0f0ef"

    fig, ax = plt.subplots(figsize=figsize, facecolor=bg)
    ax.set_facecolor(bg)

    # Convert retention rates to absolute counts
    absolute = retention_grid.multiply(cohort_sizes.reindex(retention_grid.index), axis=0)
    absolute = absolute.fillna(0)

    # Sum across cohorts (total active donors per period)
    period_totals = absolute.sum()
    periods = list(retention_grid.columns)
    x = np.arange(len(periods))

    # Waterfall: each bar = active, annotate the drop
    colors = ["#4f9de8", "#5aabef", "#64b8f5", "#6ec5fa", "#78d2ff",
              "#82deff", "#8debff", "#98f6ff"]

    bar_vals = period_totals.values
    bars = ax.bar(
        x, bar_vals,
        color=[colors[min(i, len(colors)-1)] for i in range(len(x))],
        width=0.55, alpha=0.85, zorder=3,
        edgecolor=bg, linewidth=1.2,
    )

    # Annotate drops between periods
    for i in range(1, len(bar_vals)):
        drop = bar_vals[i - 1] - bar_vals[i]
        drop_pct = drop / bar_vals[i - 1] if bar_vals[i - 1] > 0 else 0
        if drop > 0:
            mid_y = (bar_vals[i - 1] + bar_vals[i]) / 2
            ax.annotate(
                f"−{drop_pct:.0%}",
                xy=((x[i - 1] + x[i]) / 2, mid_y),
                ha="center", va="center",
                fontsize=9, color="#e84f7e",
                fontfamily=FONT_FAMILY, fontweight="500",
                bbox=dict(boxstyle="round,pad=0.2", facecolor=bg, edgecolor="none", alpha=0.8),
                zorder=4,
            )

    # Bar value labels
    for bar, val in zip(bars, bar_vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + period_totals.max() * 0.012,
            f"{int(val):,}",
            ha="center", va="bottom",
            fontsize=9, color=fg, fontfamily=FONT_FAMILY,
        )

    # ── Axes ──────────────────────────────────────────────────────────────────
    ax.set_xticks(x)
    ax.set_xticklabels(periods, color=secondary, fontsize=10, fontfamily=FONT_FAMILY)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.tick_params(colors=secondary)
    ax.yaxis.grid(True, color=grid_c, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.set_xlabel("Period (months since acquisition)", color=secondary,
                  fontsize=10, labelpad=8, fontfamily=FONT_FAMILY)
    ax.set_ylabel("Active donors", color=secondary,
                  fontsize=10, labelpad=8, fontfamily=FONT_FAMILY)

    # ── M+0 annotation ────────────────────────────────────────────────────────
    ax.annotate(
        f"Total acquired:\n{int(bar_vals[0]):,} donors",
        xy=(0, bar_vals[0]),
        xytext=(0.6, bar_vals[0] * 1.04),
        fontsize=9, color="#56c97a",
        fontfamily=FONT_FAMILY,
        arrowprops=dict(arrowstyle="-", color="#56c97a", lw=0.8),
    )

    # ── Title ─────────────────────────────────────────────────────────────────
    fig.text(
        0.08, 0.97, title,
        ha="left", va="top",
        fontsize=17, fontweight="600",
        color=fg, fontfamily=FONT_FAMILY,
    )
    fig.text(
        0.08, 0.93,
        "Total active donors across all cohorts · red percentages = month-over-month churn",
        ha="left", va="top",
        fontsize=10, color=secondary, fontfamily=FONT_FAMILY,
    )

    plt.tight_layout(rect=[0, 0.02, 1, 0.91])

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor=bg)
        print(f"Saved: {output_path}")

    return fig
