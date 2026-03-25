# Cohort Analysis Methodology

## What is cohort retention analysis?

A cohort is a group of donors/customers acquired in the same time period (here: calendar month).
Retention analysis tracks what fraction of each cohort returns to transact in each subsequent month.

This gives a cleaner signal than aggregate retention metrics because it controls for acquisition mix changes over time. If October acquisitions always churn faster than March acquisitions, a blended retention rate will look different every month — not because the product changed, but because the acquisition mix changed.

## Cohort construction

**Acquisition date**: The date of a donor's first-ever transaction in the dataset.

**Cohort month**: Calendar month of acquisition date (e.g., 2024-01).

**Period number**: Integer offset in months from acquisition month.
- Period 0 = acquisition month (always 1.0 by definition)
- Period 1 = one calendar month after acquisition
- Period N = N calendar months after acquisition

A donor is "active" in period N if they made at least one transaction in that month.
We do not require continuous activity — a donor who skips period 3 but transacts in period 4 counts as retained in period 4.

## Retention rate formula

```
retention_rate(cohort C, period N) = 
    |donors in cohort C active in period N|
    ----------------------------------------
    |cohort_size(C)|
```

where `cohort_size(C)` = total unique donors acquired in cohort month C.

## Why period 0 is always 1.0

Every donor acquired in month M made at least one transaction in month M (that's what makes them acquired). So period 0 retention is trivially 100% by definition.

## LTV computation

Cumulative LTV at period N = sum of all transaction amounts from all cohort donors through period N, divided by cohort_size.

This gives **average cumulative LTV per acquired donor** — the right unit for comparing channels with different acquisition volumes. A channel that acquires 1,000 low-LTV donors is correctly valued the same as a channel that acquires 100 high-LTV donors if their per-donor LTV curves are equivalent.

## Payback period

Payback period = first period N where cumulative LTV per donor > CAC (cost to acquire).

CAC values are configured in `src/run_analysis.py` and should be updated to reflect your actual acquisition costs per channel.

A channel with payback period > 6 months is cash-flow negative for over half a year per acquired donor. At scale, this is a significant working capital consideration.

## Key limitations

1. **No cross-device tracking**: A donor who donates on mobile then desktop appears as two donors unless email deduplication is applied upstream.

2. **Time-truncation bias**: Recent cohorts (e.g., 2024-08) have fewer observed periods than older cohorts (2023-01). Retention rates at periods near the data cutoff should be interpreted cautiously.

3. **Attribution is first-touch**: Acquisition channel is assigned based on the channel tagged on the first transaction. This understates the role of multi-touch nurture sequences.

4. **Calendar month periods**: Months have unequal lengths. A 31-day January and a 28-day February are both "period 1" for their respective cohorts, introducing minor noise.
