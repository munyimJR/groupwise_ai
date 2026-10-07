# Business case: GroupWise inside a mobile wallet

A **possible** case for a wallet such as upay (not an official partnership). The structure is: what the wallet
gains, a transparent scenario model, and how the pilot replaces each assumption with a measurement. We do not
estimate revenue: fees, float income and customer-acquisition costs are the wallet operator's own numbers.

## What a wallet gains

| Lever | How GroupWise creates it | Measured by |
|---|---|---|
| **More transactions in the wallet** | Settle-up and money requests run on the wallet's send-money and request-money rails instead of cash | Experiment: wallet-flow settlements per group-week |
| **Balances held in the wallet** | Shared goals (trip, flat, event funds) live in a goal pocket, like upay's existing multi-wallet | Pilot: goal contributions and saved ÷ target |
| **New customers** | Every group includes friends on other wallets or cash; paying back or saving invites them in | Partner A/B test of invite-to-pay links |
| **Engagement and retention** | A shared ledger, insights and goals bring people back weekly, not only when sending money | Experiment: week-2 retention, treatment vs control |
| **Differentiation** | bKash already offers group *Request Money* (moving money). A shared ledger, spending intelligence and goal planning on top is not offered | Survey Q12 and Q13: demand for these features inside a wallet |

## Scenario model

`python research/business_case.py` (inputs in `research/business_case_assumptions.json`). The only cited fact is
the student population. **Every other input is an illustrative assumption**, listed with the measurement that
replaces it.

| Output (per month unless noted) | Conservative | Base | Optimistic |
|---|---|---|---|
| Active users | 24.1k | 96.4k | 241.1k |
| Active groups | 5.8k | 28.9k | 96.4k |
| Shared spending organized per month (৳) | 43.4m | 470.1m | 3.1bn |
| Pay-backs through the wallet per month | 24.1k | 202.5k | 819.6k |
| Pay-back volume through the wallet per month (৳) | 12.1m | 141.7m | 737.6m |
| Balances held in goal pockets (৳) | 5.2m | 101.2m | 964.2m |
| New wallet customers from group invites | 521 | 7.1k | 46.3k |

| Assumption | Conservative | Base | Optimistic | Replaced by |
|---|---|---|---|---|
| Students using GroupWise inside the wallet | 0.5% | 2.0% | 5.0% | Partner rollout data; survey Q13 as an early signal |
| Groups each user is in | 1.2 | 1.5 | 2.0 | Survey Q3 |
| Members per group | 5 | 5 | 5 | Pilot: members per group |
| Shared expenses per group per month | 15 | 25 | 40 | Pilot: expenses per group per week × 4.3 |
| Average shared expense (৳) | 500 | 650 | 800 | Pilot: average expense amount |
| Pay-backs per user per month | 2 | 3 | 4 | Pilot: settlements per member per month |
| Average pay-back (৳) | 500 | 700 | 900 | Pilot: average settlement amount |
| Pay-backs done through the wallet flow | 50% | 70% | 85% | Experiment: wallet-flow share of settlements |
| Groups with a funded shared goal | 20% | 35% | 50% | Pilot: groups with goal contributions |
| Average goal target (৳) | 15,000 | 25,000 | 40,000 | Pilot: goal targets |
| Average share of the target held in the goal pocket | 30% | 40% | 50% | Pilot: saved ÷ target over time |
| Group members who don't use this wallet yet | 60% | 70% | 80% | Survey Q14 |
| Of those, members who open the wallet to settle or save | 3% | 7% | 12% | Partner A/B test of invite-to-pay links |

Fact: 4,821,165 students in public universities and affiliated colleges (UGC annual report, 2023 data; Prothom Alo, 4 Oct 2025).
For scale, Bangladesh's MFS transactions were about Tk 1.72 trillion in January 2025 alone (Bangladesh Bank data;
The Financial Express, 23 Mar 2025). Even the optimistic scenario is a small share of that.

## What we have measured, and what we have not

| Claim | Status |
|---|---|
| The product works end to end (ledger, wallet flows, AI) | **Demonstrated** in the working prototype and its tests |
| The models beat simple rules on held-out synthetic data | **Measured** ([MODEL_VALIDATION.md](MODEL_VALIDATION.md)) |
| Students have the problem and want this inside a wallet | **Being measured** (survey and interviews, [research/](../research/README.md)) |
| The AI layer changes behavior (faster settling, goals met, retention) | **Being measured** (controlled experiment, [EXPERIMENT_PLAN.md](../research/experiment/EXPERIMENT_PLAN.md)) |
| Wallet volume, customers and balances at scale | **Scenario only** until a partner pilot |

Phase 1 figures such as "10 debts → 4 payments", "saves ৳7,722 a month" and "goal 74% → 122%" are **outputs of
the algorithms on synthetic data**, which show what the product computes. They are not customer impact, and we no
longer present them as impact.
