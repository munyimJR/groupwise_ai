# Controlled pilot experiment `smart_nudges_v1` (pre-registered)

Written **before** any data is collected, so the outcomes and the analysis can't be chosen after seeing results.

## Question

Does GroupWise's AI layer (insights, recommendations, forecasts and nudges) change how student groups handle
shared money, compared with the same app **without** it?

## Design

| Item | Decision |
|---|---|
| Unit of randomization | **The group** (members influence each other, so individuals can't be split) |
| Arms | **Control:** exact ledger, settle-up including the wallet flow, and goals; no AI insights, recommendations, forecasts or nudges. **Treatment:** the full product |
| Assignment | 50/50 by a hash of the group id at creation, stored in `experiment_assignments`; nobody chooses the arm |
| Who | Real accounts only. Demo sandboxes and groups created before the start are excluded and always see the full product |
| How to run | Deploy the API with `EXPERIMENT_ENABLED=true`; every new group of a real user is randomized |
| Duration | 3 weeks (2 weeks of use plus a buffer for late settlements) |
| Target size | **≥ 10 groups per arm** (30–50 students). This is pilot-sized: it detects only large effects (see power below) |

## Outcomes (computed by `python -m scripts.experiment_report`)

| Role | Outcome | Definition | Better if |
|---|---|---|---|
| **Primary** | Median days to settle a debt | Per group, median days from an expense to its repayment (FIFO reimbursement ledger) | Lower |
| Secondary | Share of spending still unsettled | Outstanding balance ÷ total spent at the end of the pilot | Lower |
| Secondary | Goals on track | Share of active goals projected to reach their target, or reached | Higher |
| Secondary | Week-2 retention | Members who used the group again 7–13 days after first use | Higher |
| Secondary | Wallet transactions per group-week | Settlements and goal contributions through the wallet flow, plus imported wallet transactions | Higher |
| Secondary | Wallet volume per group-week (৳) | Amount moved through the wallet flow (sandbox during the pilot, so this measures intent) | Higher |
| Secondary | Expenses logged per group-week | Engagement | Higher |
| Descriptive | Recommendation acceptance | Accepted ÷ (accepted + dismissed); treatment only, so not compared | — |

## Analysis

- One value per group per outcome, then **treatment − control** with a **95% bootstrap interval over groups**.
- An effect counts as "supported" only if the interval for the **primary** outcome excludes zero in the expected
  direction. Secondary outcomes are reported as direction with uncertainty, without multiple-testing claims.
- No peeking: the report runs once, at the end. Every outcome is reported, including ones that go the wrong way.

## Power (why the pilot is small and honest about it)

For a difference in means δ with between-group standard deviation σ, groups needed per arm ≈
`2 × (1.96 + 0.84)² × σ² / δ²` (5% significance, 80% power).

| Effect on days-to-settle (σ ≈ 3 days, an assumption) | Groups per arm |
|---|---|
| 3 days faster (large) | ≈ 16 |
| 2 days faster | ≈ 36 |
| 1 day faster | ≈ 142 |

A 10-per-arm pilot can show the direction and rough size. A partner rollout (thousands of groups) is where
smaller effects become measurable. The same code runs unchanged at that scale.

## Ethics and data

Same consent and data rules as the [pilot plan](../pilot/pilot_plan.md). Control groups still get a complete,
working expense app; nothing is withheld that they'd need to manage their money. Only aggregates are reported.

## Threats and mitigations

| Threat | Mitigation |
|---|---|
| A student in two groups sees both arms | Report how many people overlap; sensitivity analysis excluding them |
| Novelty effect | Compare week 1 and week 2 within each arm |
| Few groups | Report intervals, not p-values alone; treat as direction-finding |
| Wallet is a sandbox | Wallet volume measures intent during the pilot; real volume needs a partner integration |
