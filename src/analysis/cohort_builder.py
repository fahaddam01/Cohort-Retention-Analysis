"""
CohortBuilder — assigns donors to acquisition cohorts and computes period offsets.

Cohort definition:
    - cohort_month: month of a donor's FIRST transaction (acquisition month)
    - period_number: integer offset in months between cohort_month and a subsequent transaction
      - period 0 = acquisition month
      - period 1 = one month after acquisition
      - period N = N months after acquisition

Output:
    A transaction-level DataFrame with cohort_month, period_number, and cohort_size columns.
    Ready to pivot into a retention grid.
"""

import pandas as pd
import numpy as np
from typing import Optional


class CohortBuilder:
    """
    Transforms raw transactions into cohort-indexed data.

    Parameters
    ----------
    date_col : str
        Column name for transaction date (must be datetime-castable)
    donor_col : str
        Column name for donor/customer identifier
    amount_col : str
        Column name for transaction amount
    channel_col : str, optional
        Column name for acquisition channel. If provided, cohorts are further
        segmented by channel.
    """

    def __init__(
        self,
        date_col: str = "transaction_date",
        donor_col: str = "donor_id",
        amount_col: str = "amount",
        channel_col: Optional[str] = "channel",
    ):
        self.date_col = date_col
        self.donor_col = donor_col
        self.amount_col = amount_col
        self.channel_col = channel_col

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Assign cohort_month and period_number to every transaction.

        Returns
        -------
        pd.DataFrame
            Original dataframe enriched with:
            - cohort_month       : pd.Period (monthly)
            - period_number      : int (months since acquisition)
            - cohort_size        : int (total donors acquired in that cohort_month)
        """
        df = df.copy()
        df[self.date_col] = pd.to_datetime(df[self.date_col])

        # Acquisition month = month of first transaction per donor
        first_tx = (
            df.groupby(self.donor_col)[self.date_col]
            .min()
            .dt.to_period("M")
            .rename("cohort_month")
        )
        df = df.join(first_tx, on=self.donor_col)

        # Period number = months between transaction and acquisition
        df["tx_month"] = df[self.date_col].dt.to_period("M")
        df["period_number"] = (df["tx_month"] - df["cohort_month"]).apply(lambda x: x.n)

        # Cohort size = distinct donors per cohort_month
        cohort_sizes = (
            df.groupby("cohort_month")[self.donor_col]
            .nunique()
            .rename("cohort_size")
        )
        df = df.join(cohort_sizes, on="cohort_month")

        return df

    def get_acquisition_channel(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Attach acquisition channel (channel at first transaction) to each donor.
        Handles cases where a donor's channel changes between transactions
        by always using the channel on the earliest transaction.
        """
        if self.channel_col is None or self.channel_col not in df.columns:
            return df

        df = df.copy()
        df[self.date_col] = pd.to_datetime(df[self.date_col])

        acq_channel = (
            df.sort_values(self.date_col)
            .groupby(self.donor_col)[self.channel_col]
            .first()
            .rename("acquisition_channel")
        )
        df = df.join(acq_channel, on=self.donor_col)
        return df

    def build_cohort_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Returns a cohort-level summary with acquisition stats.
        One row per cohort_month.
        """
        enriched = self.build(df)

        summary = (
            enriched[enriched["period_number"] == 0]
            .groupby("cohort_month")
            .agg(
                cohort_size=(self.donor_col, "nunique"),
                total_acquisition_revenue=(self.amount_col, "sum"),
                avg_first_gift=(self.amount_col, "mean"),
                median_first_gift=(self.amount_col, "median"),
            )
            .reset_index()
        )
        summary["avg_first_gift"] = summary["avg_first_gift"].round(2)
        summary["median_first_gift"] = summary["median_first_gift"].round(2)
        summary["total_acquisition_revenue"] = summary["total_acquisition_revenue"].round(2)

        return summary
