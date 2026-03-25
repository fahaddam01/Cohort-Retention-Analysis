"""
Generates realistic anonymized donor transaction data for demo purposes.

Simulates multiple acquisition channels with distinct retention profiles,
seasonal giving patterns (Ramadan, year-end), and realistic churn curves.

Usage:
    python src/data/generator.py --n 5000 --output data/sample/transactions_sample.csv
"""

import argparse
import hashlib
from datetime import date, timedelta

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)

# Each channel has a distinct behavioral signature
CHANNEL_PROFILES = {
    "email_campaign": {
        "weight": 0.18,
        "m1_retention": 0.41,
        "monthly_churn": 0.22,
        "avg_amount": 185,
        "amount_std": 95,
        "recurring_rate": 0.28,
    },
    "organic_social": {
        "weight": 0.35,
        "m1_retention": 0.14,
        "monthly_churn": 0.55,
        "avg_amount": 65,
        "amount_std": 40,
        "recurring_rate": 0.06,
    },
    "direct_referral": {
        "weight": 0.10,
        "m1_retention": 0.52,
        "monthly_churn": 0.18,
        "avg_amount": 310,
        "amount_std": 180,
        "recurring_rate": 0.35,
    },
    "paid_social": {
        "weight": 0.28,
        "m1_retention": 0.11,
        "monthly_churn": 0.60,
        "avg_amount": 55,
        "amount_std": 35,
        "recurring_rate": 0.04,
    },
    "event_in_person": {
        "weight": 0.06,
        "m1_retention": 0.63,
        "monthly_churn": 0.15,
        "avg_amount": 425,
        "amount_std": 250,
        "recurring_rate": 0.42,
    },
    "direct_mail": {
        "weight": 0.03,
        "m1_retention": 0.35,
        "monthly_churn": 0.28,
        "avg_amount": 140,
        "amount_std": 80,
        "recurring_rate": 0.20,
    },
}

CAMPAIGN_START = date(2023, 1, 1)
CAMPAIGN_END = date(2024, 9, 30)


def _seasonal_multiplier(d: date) -> float:
    """Ramadan + year-end giving bumps."""
    month = d.month
    if month == 3:
        return 2.4
    if month == 4:
        return 1.8
    if month == 12:
        return 2.1
    if month == 11:
        return 1.4
    if month in (6, 7, 8):
        return 0.7
    return 1.0


def _hash_donor_id(raw_id: str) -> str:
    return hashlib.md5(raw_id.encode()).hexdigest()[:12]


def generate_transactions(n_donors: int = 5000) -> pd.DataFrame:
    channels = list(CHANNEL_PROFILES.keys())
    weights = [CHANNEL_PROFILES[c]["weight"] for c in channels]
    total_days = (CAMPAIGN_END - CAMPAIGN_START).days

    all_rows = []

    for i in range(n_donors):
        channel = RNG.choice(channels, p=weights)
        profile = CHANNEL_PROFILES[channel]

        # Acquisition date — acceptance-reject sampling weighted by seasonality
        for _ in range(100):
            acq_date = CAMPAIGN_START + timedelta(days=int(RNG.integers(0, total_days)))
            if RNG.random() < _seasonal_multiplier(acq_date) / 3.0:
                break

        donor_id = _hash_donor_id(f"donor_{channel}_{i:06d}")

        # First donation
        amount = max(5.0, RNG.normal(profile["avg_amount"], profile["amount_std"]))
        all_rows.append({
            "donor_id": donor_id,
            "channel": channel,
            "transaction_date": acq_date,
            "amount": round(float(amount), 2),
            "is_recurring": bool(RNG.random() < profile["recurring_rate"]),
            "is_first_donation": True,
        })

        # Simulate subsequent donations until churn
        if RNG.random() >= profile["m1_retention"]:
            continue

        current_date = acq_date
        months_active = 1

        while True:
            next_date = current_date + timedelta(days=30 + int(RNG.integers(-5, 5)))
            if next_date > CAMPAIGN_END:
                break
            # Churn probability increases slightly with age (fatigue)
            churn_prob = profile["monthly_churn"] * (1 + months_active * 0.02)
            if RNG.random() < churn_prob:
                break

            seasonal = _seasonal_multiplier(next_date)
            amount = max(5.0, RNG.normal(
                profile["avg_amount"] * seasonal * 0.85,
                profile["amount_std"] * 0.7,
            ))
            all_rows.append({
                "donor_id": donor_id,
                "channel": channel,
                "transaction_date": next_date,
                "amount": round(float(amount), 2),
                "is_recurring": bool(RNG.random() < profile["recurring_rate"]),
                "is_first_donation": False,
            })
            current_date = next_date
            months_active += 1

    df = pd.DataFrame(all_rows)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df = df.sort_values("transaction_date").reset_index(drop=True)
    df.insert(0, "transaction_id", [f"txn_{i:08d}" for i in range(len(df))])
    return df


def main():
    parser = argparse.ArgumentParser(description="Generate sample donor transaction data")
    parser.add_argument("--n", type=int, default=5000, help="Number of unique donors to generate")
    parser.add_argument("--output", default="data/sample/transactions_sample.csv")
    args = parser.parse_args()

    print(f"Generating {args.n:,} donors...")
    df = generate_transactions(args.n)
    df.to_csv(args.output, index=False)

    print(f"\nGenerated {len(df):,} transactions from {df['donor_id'].nunique():,} donors")
    print(f"Date range: {df['transaction_date'].min().date()} → {df['transaction_date'].max().date()}")
    print(f"Saved: {args.output}")
    print("\nChannel breakdown (first donations only):")
    print(df[df["is_first_donation"]].groupby("channel")["donor_id"].count().sort_values(ascending=False))


if __name__ == "__main__":
    main()
