"""
LTVCalculator — computes cumulative donor lifetime value curves by cohort and channel.

LTV at period N for cohort C =
    sum of all transaction amounts from all donors in cohort C
    through period N, divided by cohort_size.

This gives "average cumulative LTV per acquired donor" — the right metric
for budget allocation and payback period analysis.
"""

import pandas as pd
import numpy as np
from typing import Optional


class LTVCalculator:
    """
    Computes LTV curves and payback periods.

    Parameters
    ----------
    max_periods : int
        Number of months to project LTV. Default 12.
    """

    def __init__(self, max_periods: int = 12):
        self.max_periods = max_periods

    def compute_cumulative_ltv(
        self,
        df: pd.DataFrame,
        donor_col: str = "donor_id",
        cohort_col: str = "cohort_month",
        period_col: str = "period_number",
        amount_col: str = "amount",
        size_col: str = "cohort_size",
    ) -> pd.DataFrame:
        """
        Cumulative average LTV per acquired donor at each period offset.

        Returns
        -------
        pd.DataFrame
            Index = cohort_month
            Columns = M+0, M+1, ..., M+N
            Values = cumulative avg LTV per donor (USD)
        """
        df = df[df[period_col] <= self.max_periods].copy()

        # Revenue per cohort per period
        period_revenue = (
            df.groupby([cohort_col, period_col])[amount_col]
            .sum()
            .reset_index()
            .rename(columns={amount_col: "period_revenue"})
        )

        # Cohort sizes
        cohort_sizes = df[[cohort_col, size_col]].drop_duplicates()
        period_revenue = period_revenue.merge(cohort_sizes, on=cohort_col, how="left")
        period_revenue["avg_revenue"] = period_revenue["period_revenue"] / period_revenue[size_col]

        # Pivot to grid
        grid = period_revenue.pivot(
            index=cohort_col,
            columns=period_col,
            values="avg_revenue",
        ).fillna(0)

        # Cumulative sum across periods (LTV compounds)
        grid_cumulative = grid.cumsum(axis=1)
        grid_cumulative.columns = [f"M+{c}" for c in grid_cumulative.columns]
        grid_cumulative.index = grid_cumulative.index.astype(str)

        return grid_cumulative.round(2)

    def compute_ltv_by_channel(
        self,
        df: pd.DataFrame,
        channel_col: str = "acquisition_channel",
        donor_col: str = "donor_id",
        cohort_col: str = "cohort_month",
        period_col: str = "period_number",
        amount_col: str = "amount",
        size_col: str = "cohort_size",
    ) -> pd.DataFrame:
        """
        Average cumulative LTV by channel, aggregated across all cohorts.
        Returns one LTV curve per channel.

        Returns
        -------
        pd.DataFrame
            Index = channel name
            Columns = M+0, M+1, ..., M+N
            Values = mean cumulative LTV across cohorts
        """
        if channel_col not in df.columns:
            raise ValueError(f"Column '{channel_col}' not found.")

        df = df[df[period_col] <= self.max_periods].copy()

        # Revenue per channel per period
        channel_revenue = (
            df.groupby([channel_col, period_col])
            .agg(
                total_revenue=(amount_col, "sum"),
                donor_count=(donor_col, "nunique"),
            )
            .reset_index()
        )
        channel_revenue["avg_ltv"] = (
            channel_revenue["total_revenue"] / channel_revenue["donor_count"]
        )

        grid = channel_revenue.pivot(
            index=channel_col,
            columns=period_col,
            values="avg_ltv",
        ).fillna(0)

        grid_cumulative = grid.cumsum(axis=1)
        grid_cumulative.columns = [f"M+{c}" for c in grid_cumulative.columns]

        return grid_cumulative.round(2)

    def compute_payback_period(
        self,
        ltv_by_channel: pd.DataFrame,
        cac_by_channel: dict,
    ) -> pd.DataFrame:
        """
        Find the period at which cumulative LTV exceeds CAC for each channel.

        Parameters
        ----------
        ltv_by_channel : pd.DataFrame
            Output of compute_ltv_by_channel()
        cac_by_channel : dict
            e.g. {"email_campaign": 45, "paid_social": 72, ...}

        Returns
        -------
        pd.DataFrame
            One row per channel with:
            - cac: input CAC
            - payback_period_months: first period where LTV > CAC (or NaN if never)
            - ltv_at_12m: LTV at M+12 (or last available period)
            - ltv_cac_ratio: LTV/CAC at 12 months
        """
        results = []
        last_period = ltv_by_channel.columns[-1]

        for channel in ltv_by_channel.index:
            cac = cac_by_channel.get(channel, np.nan)
            ltv_curve = ltv_by_channel.loc[channel]
            ltv_12m = ltv_curve.get("M+12", ltv_curve.iloc[-1])

            # Find first period where LTV > CAC
            payback = np.nan
            if not np.isnan(cac):
                exceeds = ltv_curve[ltv_curve > cac]
                if not exceeds.empty:
                    payback = int(exceeds.index[0].replace("M+", ""))

            results.append({
                "channel": channel,
                "cac": cac,
                "payback_period_months": payback,
                "ltv_at_12m": round(ltv_12m, 2),
                "ltv_cac_ratio": round(ltv_12m / cac, 2) if not np.isnan(cac) and cac > 0 else np.nan,
            })

        return pd.DataFrame(results).set_index("channel").sort_values("ltv_at_12m", ascending=False)
