"""
Retention heatmap renderer.

Produces a cohort × period heatmap with:
- Color intensity = retention rate (dark = high, light = low)
- Annotations showing exact % in each cell
- Cohort size bar on the left
- Clean, publication-quality styling
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional


# ── Color system ──────────────────────────────────────────────────────────────
CMAP_RETENTION = "YlOrRd_r"   # High retention = dark teal/green feel via reversal
CMAP_SIZE      = "Blues"
BG_COLOR       = "#0f1117"
TEXT_PRIMARY   = "#e8e6e0"
TEXT_SECONDARY = "#9c9a8e"
GRID_COLOR     = "#1e2029"
ACCENT_COLOR   = "#4f9de8"
FONT_FAMILY    = "monospace"


def plot_retention_heatmap(
    retention_grid: pd.DataFrame,
    cohort_sizes: Optional[pd.Series] = None,
    title: str = "Cohort Retention Heatmap",
    output_path: Optional[str] = None,
    figsize: tuple = (16, 9),
    dark_mode: bool = True,
) -> plt.Figure:
    """
    Render a retention heatmap.

    Parameters
    ----------
    retention_grid : pd.DataFrame
        Output of RetentionCalculator.compute_retention_grid()
        Index = cohort labels, columns = M+0, M+1, ...
    cohort_sizes : pd.Series, optional
        Cohort sizes indexed by cohort label. Adds a size bar on the right.
    title : str
        Chart title
    output_path : str, optional
        If provided, saves figure to this path
    figsize : tuple
        Figure dimensions
    dark_mode : bool
        Use dark background (default True — looks better in GitHub README)
    """

    bg = BG_COLOR if dark_mode else "#ffffff"
    fg = TEXT_PRIMARY if dark_mode else "#1a1a1a"
    grid_c = GRID_COLOR if dark_mode else "#f0f0f0"
    secondary = TEXT_SECONDARY if dark_mode else "#666666"

    fig = plt.figure(figsize=figsize, facecolor=bg)

    if cohort_sizes is not None:
        # Two panels: heatmap (wide) + size bar (narrow)
        gs = fig.add_gridspec(1, 2, width_ratios=[12, 1], wspace=0.04)
        ax_heat  = fig.add_subplot(gs[0])
        ax_sizes = fig.add_subplot(gs[1])
    else:
        ax_heat = fig.add_subplot(111)
        ax_sizes = None

    # ── Main heatmap ──────────────────────────────────────────────────────────
    grid_values = retention_grid.values.astype(float)

    # Mask period 0 (always 1.0) to distinguish from actual retention
    masked = np.ma.masked_where(np.isnan(grid_values), grid_values)

    im = ax_heat.imshow(
        masked,
        cmap="RdYlGn",
        aspect="auto",
        vmin=0,
        vmax=1,
        interpolation="nearest",
    )

    # Cell annotations
    for r in range(len(retention_grid.index)):
        for c in range(len(retention_grid.columns)):
            val = grid_values[r, c]
            if np.isnan(val):
                continue
            pct_text = f"{val:.0%}"
            # High contrast text color based on cell intensity
            text_color = fg if val > 0.45 else (secondary if val > 0.15 else "#ff6b6b")
            ax_heat.text(
                c, r, pct_text,
                ha="center", va="center",
                fontsize=8.5, fontweight="500",
                color=text_color, fontfamily=FONT_FAMILY,
            )

    # Axes formatting
    ax_heat.set_facecolor(bg)
    ax_heat.set_xticks(range(len(retention_grid.columns)))
    ax_heat.set_xticklabels(retention_grid.columns, color=fg, fontsize=9, fontfamily=FONT_FAMILY)
    ax_heat.set_yticks(range(len(retention_grid.index)))
    ax_heat.set_yticklabels(retention_grid.index, color=fg, fontsize=9, fontfamily=FONT_FAMILY)
    ax_heat.xaxis.set_ticks_position("top")
    ax_heat.xaxis.set_label_position("top")

    # Thin grid lines between cells
    ax_heat.set_xticks(np.arange(-0.5, len(retention_grid.columns), 1), minor=True)
    ax_heat.set_yticks(np.arange(-0.5, len(retention_grid.index), 1), minor=True)
    ax_heat.grid(which="minor", color=grid_c, linewidth=0.5)
    ax_heat.tick_params(which="minor", length=0)
    ax_heat.tick_params(which="major", length=0)

    for spine in ax_heat.spines.values():
        spine.set_visible(False)

    ax_heat.set_xlabel("Months since acquisition →", color=secondary, fontsize=10,
                        labelpad=10, fontfamily=FONT_FAMILY)
    ax_heat.xaxis.set_label_position("bottom")

    # ── Cohort size bar (right panel) ─────────────────────────────────────────
    if ax_sizes is not None and cohort_sizes is not None:
        aligned_sizes = cohort_sizes.reindex(retention_grid.index).fillna(0)
        bar_colors = [ACCENT_COLOR] * len(aligned_sizes)

        bars = ax_sizes.barh(
            range(len(aligned_sizes)),
            aligned_sizes.values,
            color=bar_colors,
            alpha=0.75,
            height=0.7,
        )

        # Size labels
        for i, (bar, val) in enumerate(zip(bars, aligned_sizes.values)):
            ax_sizes.text(
                val + aligned_sizes.max() * 0.03,
                i,
                f"{int(val):,}",
                va="center", ha="left",
                fontsize=8, color=secondary, fontfamily=FONT_FAMILY,
            )

        ax_sizes.set_facecolor(bg)
        ax_sizes.set_yticks([])
        ax_sizes.set_xticks([])
        ax_sizes.set_ylim(-0.5, len(aligned_sizes) - 0.5)
        ax_sizes.invert_yaxis()
        for spine in ax_sizes.spines.values():
            spine.set_visible(False)
        ax_sizes.set_title("Cohort\nsize", color=secondary, fontsize=8,
                           fontfamily=FONT_FAMILY, pad=4)

    # ── Colorbar ──────────────────────────────────────────────────────────────
    cbar_ax = fig.add_axes([0.13, 0.04, 0.35, 0.018])
    cb = fig.colorbar(im, cax=cbar_ax, orientation="horizontal")
    cb.ax.tick_params(colors=secondary, labelsize=8)
    cb.set_label("Retention rate", color=secondary, fontsize=9, fontfamily=FONT_FAMILY)
    cb.ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    cbar_ax.set_facecolor(bg)
    cb.outline.set_visible(False)

    # ── Title & subtitle ──────────────────────────────────────────────────────
    fig.text(
        0.13, 0.97, title,
        ha="left", va="top",
        fontsize=18, fontweight="600",
        color=fg, fontfamily=FONT_FAMILY,
    )
    fig.text(
        0.13, 0.93,
        "% of acquired donors who transacted in each subsequent month",
        ha="left", va="top",
        fontsize=11, color=secondary, fontfamily=FONT_FAMILY,
    )

    plt.tight_layout(rect=[0, 0.08, 1, 0.91])

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor=bg)
        print(f"Saved: {output_path}")

    return fig
