"""
run_analysis.py — end-to-end cohort analysis runner.

Usage:
    python src/run_analysis.py --data data/sample/transactions_sample.csv
    python src/run_analysis.py --data data/sample/transactions_sample.csv --max-periods 12
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent))

from analysis.cohort_builder      import CohortBuilder
from analysis.retention_calculator import RetentionCalculator
from analysis.ltv_calculator       import LTVCalculator
from visualization.heatmap         import plot_retention_heatmap
from visualization.ltv_curves      import plot_ltv_curves
from visualization.churn_waterfall  import plot_churn_waterfall


# CAC estimates per channel (dollars) — adjust to your actual data
DEFAULT_CAC = {
    "email_campaign":   38,
    "organic_social":   12,
    "direct_referral":  55,
    "paid_social":      72,
    "event_in_person":  90,
    "direct_mail":      44,
}


def parse_args():
    p = argparse.ArgumentParser(description="Run cohort retention analysis")
    p.add_argument("--data",        required=True,  help="Path to transactions CSV")
    p.add_argument("--output-dir",  default="outputs", help="Output directory for figures and tables")
    p.add_argument("--max-periods", type=int, default=12, help="Max cohort periods to analyze")
    p.add_argument("--min-cohort",  type=int, default=15, help="Min cohort size to include")
    p.add_argument("--light-mode",  action="store_true", help="Use light background for charts")
    return p.parse_args()


def run(args):
    dark_mode = not args.light_mode
    figures_dir = Path(args.output_dir) / "figures"
    tables_dir  = Path(args.output_dir) / "tables"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*55}")
    print("  Cohort Retention Analysis")
    print(f"{'='*55}")

    # ── Load data ─────────────────────────────────────────────────────────────
    print(f"\n[1/6] Loading data from {args.data}...")
    df = pd.read_csv(args.data, parse_dates=["transaction_date"])
    print(f"      {len(df):,} transactions · {df['donor_id'].nunique():,} donors")

    # ── Build cohorts ─────────────────────────────────────────────────────────
    print("\n[2/6] Building cohorts...")
    builder = CohortBuilder()
    df = builder.build(df)
    df = builder.get_acquisition_channel(df)

    cohort_summary = builder.build_cohort_summary(df)
    print(f"      {len(cohort_summary)} cohort months identified")

    # ── Compute retention ─────────────────────────────────────────────────────
    print("\n[3/6] Computing retention grids...")
    calc = RetentionCalculator(max_periods=args.max_periods, min_cohort_size=args.min_cohort)
    retention_grid   = calc.compute_retention_grid(df)
    retention_by_channel = calc.compute_by_channel(df)

    print(f"      Overall grid: {retention_grid.shape[0]} cohorts × {retention_grid.shape[1]} periods")
    print(f"      Channels with sufficient data: {list(retention_by_channel.keys())}")

    # Print retention summary
    stats = calc.summary_stats(retention_grid)
    print(f"\n      Retention summary (mean across cohorts):")
    for period in ["M+1", "M+3", "M+6", "M+12"]:
        if period in stats.index:
            rate = stats.loc[period, "mean_retention"]
            print(f"        {period}: {rate:.1%}")

    # ── Compute LTV ───────────────────────────────────────────────────────────
    print("\n[4/6] Computing LTV curves...")
    ltv_calc = LTVCalculator(max_periods=args.max_periods)
    ltv_by_channel = ltv_calc.compute_ltv_by_channel(df)
    payback        = ltv_calc.compute_payback_period(ltv_by_channel, DEFAULT_CAC)

    print("\n      LTV at M+12 and payback periods:")
    print(payback[["ltv_at_12m", "payback_period_months", "ltv_cac_ratio"]].to_string())

    # ── Generate charts ────────────────────────────────────────────────────────
    print("\n[5/6] Generating charts...")

    cohort_sizes = cohort_summary.set_index("cohort_month")["cohort_size"]
    cohort_sizes.index = cohort_sizes.index.astype(str)

    plot_retention_heatmap(
        retention_grid,
        cohort_sizes=cohort_sizes,
        title="Donor Cohort Retention Heatmap",
        output_path=str(figures_dir / "retention_heatmap.png"),
        dark_mode=dark_mode,
    )

    plot_ltv_curves(
        ltv_by_channel,
        cac_by_channel=DEFAULT_CAC,
        title="Cumulative LTV by Acquisition Channel",
        output_path=str(figures_dir / "ltv_curves_by_channel.png"),
        dark_mode=dark_mode,
    )

    plot_churn_waterfall(
        retention_grid,
        cohort_sizes,
        title="Donor Retention Funnel",
        output_path=str(figures_dir / "churn_waterfall.png"),
        dark_mode=dark_mode,
    )

    print("      Charts saved to outputs/figures/")

    # ── Export tables ──────────────────────────────────────────────────────────
    print("\n[6/6] Exporting tables...")

    retention_grid.to_csv(tables_dir / "retention_grid.csv")
    ltv_by_channel.to_csv(tables_dir / "ltv_by_channel.csv")
    payback.to_csv(tables_dir / "payback_analysis.csv")
    cohort_summary.to_csv(tables_dir / "cohort_summary.csv", index=False)

    print("      Tables saved to outputs/tables/")

    print(f"\n{'='*55}")
    print("  Analysis complete.")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    run(parse_args())
