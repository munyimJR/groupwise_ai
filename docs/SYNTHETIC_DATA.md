# Synthetic data strategy & assumptions

GroupWise uses **synthetic data only**. Nothing is copied from real people, and merchant names are public businesses used as plausible descriptions.

## Generator design (`backend/app/synthetic/generator.py`)

Groups are simulated day by day from explicit behaviour specs:

| Spec | Meaning |
|---|---|
| `MemberSpec` | Payer propensity (how often someone fronts the bill), settle cadence (every 1–2 days vs 7–11 days) and the fraction they repay each time |
| `PatternSpec` | A spending habit: subcategory, daily rate, median amount and log-normal spread, hours, weekday multipliers, month-start/month-end multipliers, party size, optional recent trend, optional active window (trips) |
| `RecurringSpec` | Monthly bills on a day of the month with jitter (rent, internet, gas, electricity, water, maid) |
| `FixedExpense` | One-off bookings (bus tickets, resort) and **labelled anomalies** |
| `GoalSpec` | Target, start, duration, weekly contribution rate and noise, contributor weights |

Settlements come from a pairwise ledger: each member settles what they owe their creditors on their own cadence. Reimbursement delays are therefore an emergent property, not a hard-coded number.

## Assumptions

- Bangladesh weekend = Friday & Saturday, and **Thursday evening counts as the start of the weekend**.
- Student allowance arrives early in the month (days 1–7 are busier), and spending tightens at month-end.
- Amounts are log-normal around realistic Dhaka prices (lunch ≈ ৳850 for a group, dinner ≈ ৳1,800, rides ≈ ৳240, rent ৳28,000 for four).
- Shared expenses involve at least two people, and the payer is chosen among participants by payer propensity.
- Expense times are local wall-clock (Asia/Dhaka, UTC+6).

## Demo groups (`scenarios.py`)

| Group | Members | What the AI should find |
|---|---|---|
| **DIU CSE Squad** (friends, 150 days) | 5 | Weekend restaurant dining up ~25–35% in the last 30 days (Food +~30% excluding one-offs); a ৳16,500 sound-system rental (amount anomaly); a 3 AM ৳4,200 delivery (time anomaly); a duplicate ৳2,340 dinner; an older laptop repair reviewed as valid; Rony fronts ~45% of costs while consuming ~20%; Nahid settles slowly; the "Cox's Bazar Trip" goal (৳40,000) is behind |
| **Mirpur Flat 7C** (roommates, 150 days) | 4 | Rent and utilities detected as recurring bills; an electricity recharge 3.4× normal; Asif fronts rent; the Emergency Fund goal is on track |
| **Sajek Valley Tour** (trip, finished ~38 days ago) | 6 | Inactive group, so no forecast; open balances, where 5 simplified payments replace 15 pairwise ones |

Every demo visitor gets these three groups **seeded through the same models as live data**. The categorizer labels descriptions (where it disagrees with the scenario's ground truth, the expense is stored as a human correction), and the anomaly detector scores every expense. Alerts older than 30 days are stored as already reviewed, as an active group would have done.

### Narrative stability

The demo is generated relative to *today*, so it must hold on any day. Demo scenarios use **systematic (low-variance) sampling** of daily event counts so the designed behaviour isn't drowned by sampling noise. `python -m scripts.check_demo_robustness` regenerates the demo for 28 different dates and prints the key computed facts (trend, top driver, anomalies flagged, goal progress).

## Evaluation data (kept separate)

`eval_scenario(seed)` jitters the friends/roommates scenarios (rates ×0.7–1.3, medians ×0.8–1.25, 3–5 members, 110–180 days), switches back to **full Poisson noise**, removes the demo anomalies and injects 4–8 fresh labelled anomalies per group:

- **amount**: 5–10× the median of a common subcategory
- **time**: 2.5–4× median at 2–4:30 AM
- **category**: ৳6,000–15,000 in a subcategory the group never uses
- **duplicate**: same amount and description 1–9 minutes after the original

Seeds 0–39 were used for tuning (validation). Reported metrics come from **seeds 100–139 (anomaly) and 100–119 (forecast)**, which were never used during development. The categorizer's corpus is split so that **held-out merchants and held-out phrasings appear only in the test set**.
