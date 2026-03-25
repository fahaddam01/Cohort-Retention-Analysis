"""
LTV curves renderer.

Produces a multi-line chart showing cumulative average LTV per acquired donor
by acquisition channel over time. Each channel gets a distinct color with
confidence band (if multiple cohorts available).
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, Dict


BG_COLOR    = "#0f1117"
TEXT_PRIMARY   = "#e8e6e0"
TEXT_SECONDARY = "#9c9a8e"
GRID_COLOR  = "#1e2029"
FONT_FAMILY = "monospace"

CHANNEL_COLORS = {
    "email_campaign":   "#4f9de8",
    "organic_social":   "#e87e4f",
    "direct_referral":  "#56c97a",
    "paid_social":      "#e84f7e",
    "event_in_person":  "#c9a956",
    "direct_mail":      "#9e56c9",
}
DEFAULT_COLOR_CYCLE = ["#4f9de8", "#e87e4f", "#56c97a", "#e84f7e", "#c9a956", "#9e56c9"]


def plot_ltv_curves(
    ltv_by_channel: pd.DataFrame,
    cac_by_channel: Optional[Dict[str, float]] = None,
    title: str = "Cumulative LTV by Acquisition Channel",
    output_path: Optional[str] = None,
    figsize: tuple = (14, 8),
    dark_mode: bool = True,
) -> plt.Figure:
    """
    Render LTV curves for each acquisition channel.

    Parameters
    ----------
    ltv_by_channel : pd.DataFrame
        Output of LTVCalculator.compute_ltv_by_channel()
        Index = channel names, columns = M+0, M+1, ..., M+N
    cac_by_channel : dict, optional
        CAC per channel — draws horizontal reference lines for payback visualization
    """

    bg = BG_COLOR if dark_mode else "#ffffff"
    fg = TEXT_PRIMARY if dark_mode else "#1a1a1a"
    secondary = TEXT_SECONDARY if dark_mode else "#666666"
    grid_c = GRID_COLOR if dark_mode else "#f0f0ef"

    fig, ax = plt.subplots(figsize=figsize, facecolor=bg)
    ax.set_facecolor(bg)

    # Parse period numbers from column names for x-axis
    periods = [int(c.replace("M+", "")) for c in ltv_by_channel.columns]

    for i, channel in enumerate(ltv_by_channel.index):
        color = CHANNEL_COLORS.get(channel, DEFAULT_COLOR_CYCLE[i % len(DEFAULT_COLOR_CYCLE)])
        ltv_values = ltv_by_channel.loc[channel].values

        # Main LTV curve
        ax.plot(
            periods, ltv_values,
            color=color, linewidth=2.5,
            marker="o", markersize=5, markevery=1,
            label=channel.replace("_", " ").title(),
            zorder=3,
        )

        # Subtle area fill under curve
        ax.fill_between(periods, ltv_values, alpha=0.08, color=color)

        # End-of-line label
        last_period = periods[-1]
        last_val = ltv_values[-1]
        ax.annotate(
            f"${last_val:,.0f}",
            xy=(last_period, last_val),
            xytext=(8, 0), textcoords="offset points",
            fontsize=9, color=color, va="center",
            fontfamily=FONT_FAMILY, fontweight="500",
        )

    # ── CAC reference lines ────────────────────────────────────────────────────
    if cac_by_channel:
        for channel, cac in cac_by_channel.items():
            color = CHANNEL_COLORS.get(channel, "#666666")
            ax.axhline(
                cac, color=color, linewidth=1,
                linestyle="--", alpha=0.5, zorder=2,
            )
            ax.text(
                periods[0] - 0.3, cac + 3,
                f"CAC: ${cac:.0f}",
                fontsize=8, color=color, alpha=0.7,
                fontfamily=FONT_FAMILY, va="bottom",
            )

    # ── Axes ──────────────────────────────────────────────────────────────────
    ax.set_xlim(periods[0] - 0.5, periods[-1] + 1.5)
    ax.set_xticks(periods)
    ax.set_xticklabels([f"M+{p}" for p in periods],
                       color=secondary, fontsize=9, fontfamily=FONT_FAMILY)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.tick_params(colors=secondary, which="both")

    # Grid
    ax.yaxis.grid(True, color=grid_c, linewidth=0.6, zorder=0)
    ax.xaxis.grid(True, color=grid_c, linewidth=0.3, zorder=0)
    ax.set_axisbelow(True)

    for spine in ax.spines.values():
        spine.set_visible(False)

    # ── Labels ────────────────────────────────────────────────────────────────
    ax.set_xlabel("Months since acquisition", color=secondary, fontsize=10,
                  labelpad=8, fontfamily=FONT_FAMILY)
    ax.set_ylabel("Avg cumulative LTV per acquired donor", color=secondary,
                  fontsize=10, labelpad=8, fontfamily=FONT_FAMILY)

    # ── Legend ────────────────────────────────────────────────────────────────
    legend = ax.legend(
        loc="upper left",
        framealpha=0,
        labelcolor=fg,
        fontsize=10,
        prop={"family": FONT_FAMILY},
    )

    # ── Title ─────────────────────────────────────────────────────────────────
    fig.text(
        0.09, 0.97, title,
        ha="left", va="top",
        fontsize=17, fontweight="600",
        color=fg, fontfamily=FONT_FAMILY,
    )
    fig.text(
        0.09, 0.93,
        "Average cumulative donation per acquired donor · by acquisition channel",
        ha="left", va="top",
        fontsize=10, color=secondary, fontfamily=FONT_FAMILY,
    )

    plt.tight_layout(rect=[0, 0.02, 1, 0.91])

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor=bg)
        print(f"Saved: {output_path}")

    return fig
