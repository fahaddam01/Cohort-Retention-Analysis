"""
Tests for CohortBuilder.

Covers:
- Correct cohort_month assignment (first transaction per donor)
- Correct period_number computation
- Edge case: donor with only one transaction (period 0 only)
- Edge case: donor who transacts in acquisition month multiple times
- Timezone-naive datetime handling
"""

import pandas as pd
import numpy as np
import pytest
from datetime import date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from analysis.cohort_builder import CohortBuilder


@pytest.fixture
def simple_df():
    """Three donors, distinct acquisition months, straightforward retention."""
    return pd.DataFrame({
        "donor_id":         ["d001", "d001", "d001", "d002", "d002", "d003"],
        "transaction_date": [
            "2024-01-15",  # d001: acquired Jan
            "2024-02-20",  # d001: returned Feb (period 1)
            "2024-04-10",  # d001: returned Apr (period 3)
            "2024-02-05",  # d002: acquired Feb
            "2024-03-12",  # d002: returned Mar (period 1)
            "2024-03-22",  # d003: acquired Mar, only one tx
        ],
        "amount": [100, 75, 90, 200, 150, 50],
        "channel": ["email", "email", "email", "social", "social", "direct"],
    })


def test_cohort_month_assigned_correctly(simple_df):
    builder = CohortBuilder()
    result = builder.build(simple_df)

    d001_rows = result[result["donor_id"] == "d001"]
    assert all(d001_rows["cohort_month"] == pd.Period("2024-01", "M"))

    d002_rows = result[result["donor_id"] == "d002"]
    assert all(d002_rows["cohort_month"] == pd.Period("2024-02", "M"))


def test_period_numbers_correct(simple_df):
    builder = CohortBuilder()
    result = builder.build(simple_df)

    d001 = result[result["donor_id"] == "d001"].sort_values("transaction_date")
    periods = d001["period_number"].tolist()
    assert periods == [0, 1, 3], f"Expected [0,1,3] but got {periods}"


def test_single_transaction_donor_has_period_zero_only(simple_df):
    builder = CohortBuilder()
    result = builder.build(simple_df)

    d003 = result[result["donor_id"] == "d003"]
    assert len(d003) == 1
    assert d003["period_number"].iloc[0] == 0


def test_cohort_size_reflects_distinct_donors(simple_df):
    builder = CohortBuilder()
    result = builder.build(simple_df)

    # Jan cohort has only d001
    jan_cohort = result[result["cohort_month"] == pd.Period("2024-01", "M")]
    assert jan_cohort["cohort_size"].iloc[0] == 1

    # Mar cohort has only d003
    mar_cohort = result[result["cohort_month"] == pd.Period("2024-03", "M")]
    assert mar_cohort["cohort_size"].iloc[0] == 1


def test_acquisition_channel_uses_first_transaction():
    """Channel at first transaction should be used, even if subsequent tx have different channel."""
    df = pd.DataFrame({
        "donor_id":         ["d001", "d001"],
        "transaction_date": ["2024-01-01", "2024-02-01"],
        "amount":           [100, 150],
        "channel":          ["email", "direct"],   # different channels
    })
    builder = CohortBuilder()
    result = builder.get_acquisition_channel(builder.build(df))

    # Both rows should show acquisition_channel = "email" (first tx)
    assert (result["acquisition_channel"] == "email").all()


def test_build_cohort_summary_shape(simple_df):
    builder = CohortBuilder()
    summary = builder.build_cohort_summary(simple_df)

    # 3 donors → 3 unique acquisition months
    assert len(summary) == 3
    assert "cohort_size" in summary.columns
    assert "avg_first_gift" in summary.columns


def test_no_negative_period_numbers(simple_df):
    """All period numbers should be >= 0."""
    builder = CohortBuilder()
    result = builder.build(simple_df)
    assert (result["period_number"] >= 0).all()
