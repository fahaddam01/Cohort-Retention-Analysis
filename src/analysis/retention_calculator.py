"""
RetentionCalculator — computes retention grids from cohort-enriched transaction data.

Retention rate(cohort C, period N) = 
    donors who transacted in period N from cohort C
    -----------------------------------------------
    total donors acquired in cohort C (cohort_size)

Outputs:
    - retention_grid: DataFrame pivoted as cohort × period, values = retention %
    - absolute_grid:  cohort × period, values = raw active donor count
    - by_channel:     dict of retention grids, one per acquisition channel
"""

import pandas as pd
import numpy as np
from typing import Optional


class RetentionCalculator:
    """
    Computes cohort retention grids.

    Parameters
    ----------
    max_periods : int
        Maximum number of periods (months) to track. Default 12.
    min_cohort_size : int
        Cohorts smaller than this are excluded (avoids noisy small samples).
        Default 20.
    """

    def __init__(self, max_periods: int = 12, min_cohort_size: int = 20):
        self.max_periods = max_periods
        self.min_cohort_size = min_cohort_size

    def compute_retention_grid(
        self,
        df: pd.DataFrame,
        donor_col: str = "donor_id",
        cohort_col: str = "cohort_month",
        period_col: str = "period_number",
        size_col: str = "cohort_size",
    ) -> pd.DataFrame:
        """
        Compute retention rates as a cohort × period pivot table.

        Returns
        -------
        pd.DataFrame
            Index = cohort_month (str)
            Columns = period_0, period_1, ..., period_N
            Values = retention rate (0.0 to 1.0)
        """
        # Filter to relevant periods
        df = df[df[period_col] <= self.max_periods].copy()

        # Count active donors per cohort per period
        active_counts = (
            df.groupby([cohort_col, period_col])[donor_col]
            .nunique()
            .reset_index()
            .rename(columns={donor_col: "active_donors"})
        )

        # Attach cohort sizes
        cohort_sizes = (
            df[[cohort_col, size_col]]
            .drop_duplicates()
            .rename(columns={size_col: "cohort_size"})
        )
        active_counts = active_counts.merge(cohort_sizes, on=cohort_col, how="left")

        # Filter small cohorts
        active_counts = active_counts[active_counts["cohort_size"] >= self.min_cohort_size]

        # Compute retention rate
        active_counts["retention_rate"] = (
            active_counts["active_donors"] / active_counts["cohort_size"]
        )

        # Pivot to grid
        grid = active_counts.pivot(
            index=cohort_col,
            columns=period_col,
            values="retention_rate",
        )
        grid.columns = [f"M+{c}" for c in grid.columns]
        grid.index = grid.index.astype(str)

        # Period 0 should always be 1.0 (everyone present at acquisition)
        if "M+0" in grid.columns:
            grid["M+0"] = 1.0

        return grid.round(4)

    def compute_absolute_grid(
        self,
        df: pd.DataFrame,
        donor_col: str = "donor_id",
        cohort_col: str = "cohort_month",
        period_col: str = "period_number",
        size_col: str = "cohort_size",
    ) -> pd.DataFrame:
        """
        Same as retention grid but values = raw active donor counts (not rates).
        Useful for understanding absolute scale.
        """
        df = df[df[period_col] <= self.max_periods].copy()

        absolute = (
            df.groupby([cohort_col, period_col])[donor_col]
            .nunique()
            .reset_index()
            .rename(columns={donor_id: "active_donors"})
        )

        # Filter small cohorts
        cohort_sizes = df[[cohort_col, size_col]].drop_duplicates()
        absolute = absolute.merge(cohort_sizes, on=cohort_col, how="left")
        absolute = absolute[absolute[size_col] >= self.min_cohort_size]

        grid = absolute.pivot(
            index=cohort_col,
            columns=period_col,
            values="active_donors",
        )
        grid.columns = [f"M+{c}" for c in grid.columns]
        grid.index = grid.index.astype(str)
        return grid

    def compute_by_channel(
        self,
        df: pd.DataFrame,
        channel_col: str = "acquisition_channel",
        donor_col: str = "donor_id",
        cohort_col: str = "cohort_month",
        period_col: str = "period_number",
        size_col: str = "cohort_size",
    ) -> dict:
        """
        Compute retention grid separately for each acquisition channel.

        Returns
        -------
        dict[str, pd.DataFrame]
            Keys = channel names, values = retention grids
        """
        if channel_col not in df.columns:
            raise ValueError(f"Column '{channel_col}' not found. Run CohortBuilder.get_acquisition_channel() first.")

        results = {}
        for channel in df[channel_col].dropna().unique():
            channel_df = df[df[channel_col] == channel]
            try:
                grid = self.compute_retention_grid(
                    channel_df, donor_col, cohort_col, period_col, size_col
                )
                results[channel] = grid
            except Exception:
                # Skip channels with insufficient data
                pass

        return results

    def summary_stats(
        self,
        retention_grid: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Compute summary stats across cohorts for each period.
        Returns mean, median, min, max retention rate per period.
        """
        stats = pd.DataFrame({
            "mean_retention":   retention_grid.mean(),
            "median_retention": retention_grid.median(),
            "min_retention":    retention_grid.min(),
            "max_retention":    retention_grid.max(),
            "cohorts_tracked":  retention_grid.count(),
        })
        return stats.round(4)
