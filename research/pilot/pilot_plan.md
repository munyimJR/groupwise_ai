# Two-week pilot with real student groups

**Goal:** measure whether GroupWise changes real behavior, using real (consenting) groups instead of synthetic data.

## Who and how many

- 5–8 real groups from Daffodil International University (flats, friend groups, a trip or club group), 3–6 people each.
- Each person signs up with their own account on the deployed app (Supabase), not the demo sandbox.
- Duration: 14 days.

## Consent (read before sign-up)

> GroupWise AI is a student hackathon prototype. During this two-week pilot your group's expenses are stored in
> our database so we can test the app. Only the team can see the data. We report only totals (for example
> "groups settled debts in 2 days on average"), never names or individual expenses. You can delete your group
> at any time, and we delete all pilot data within 30 days after the hackathon. Real money never moves through
> GroupWise. The wallet checkout in the app is a sandbox.

## What groups do

1. Day 1: create the group, invite members, set one shared goal (for example a trip or a dinner fund).
2. Every day: add shared expenses (type one sentence) or import them from a wallet statement export.
3. When paying someone back with a real wallet, record it in GroupWise (or import the statement later).
4. Day 7 and day 14: open Insights, Forecast and the goal, and try one What-If.
5. Day 14: a 5-minute exit survey (questions Q10, Q12 and Q13 again, plus "What would make you keep using it?").

## What we measure (automatically)

Run `python -m scripts.pilot_metrics --out ../research/results` from `backend/` against the pilot database.
Only real accounts are counted. Demo sandboxes and synthetic members are excluded.

| Hypothesis | Metric | Target for "promising" |
|---|---|---|
| H1 Logging is easy enough to keep up | Expenses per group per week | ≥ 5 |
| H2 The AI categories are trusted | AI category accepted without correction | ≥ 75% |
| H3 Debts get settled faster | Median days to settle (vs survey Q6 baseline) | Shorter than the survey's typical wait |
| H4 Unusual expenses get reviewed | Flagged expenses that were reviewed | ≥ 60% |
| H5 Recommendations are useful | Recommendations marked helpful | ≥ 50% |
| H6 Goals stay on track | Active goals projected on track at day 14 | Higher than survey Q11 success rate |
| H7 Wallet link matters | Expenses imported from wallet statements; settlements through the wallet flow | Used by most groups |

Targets are hypotheses decided before the pilot, so the results can't be cherry-picked afterwards. Report
every metric, including the ones that miss.
