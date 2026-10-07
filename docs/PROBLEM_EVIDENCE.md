# Problem evidence

## 1. The problem, narrowed to one mobile-wallet use case

> **Student groups in Bangladesh pay shared costs from mobile wallets, but nothing connects those payments into a
> shared picture. They lose track of who paid, wait days to be paid back, and their shared savings goals quietly fail.**

GroupWise targets **one use case: shared spending plus one shared goal** for a group of 3–8 students (a flat, a
friend group or a trip). Every feature serves that single job:

```
Wallet payments  →  one shared ledger  →  settle up through the wallet  →  save toward the goal on time
   (import)            (AI sorts it)          (pay / request)                (goal planner + What-If)
```

Insights, forecasts and the copilot exist to keep that loop working, not as separate products.

## 2. Public evidence (secondary sources)

| Fact | Why it matters for GroupWise | Source |
|---|---|---|
| Bangladesh had **239.3 million MFS accounts** in January 2025, and MFS transactions reached **about Tk 1.72 trillion in that one month** (Bangladesh Bank data). | Everyday money, including students' shared costs, already moves through wallets. These are the rails GroupWise plugs into. Accounts are not people: many people hold several. | The Financial Express, 23 Mar 2025 — [link](https://thefinancialexpress.com.bd/trade/bangladesh-mfs-accounts-surge-by-20-million-in-a-year-transactions-up-32pc) |
| About **4.82 million students** studied in public universities and their affiliated colleges (UGC annual report, 2023 data). | A large, concentrated target group that shares housing, food and travel. | Prothom Alo, 4 Oct 2025 — [link](https://en.prothomalo.com/amp/story/youth/education/6pij7mhk3g) |
| bKash's *Request Money* lets a user request money from up to 10 people, individually or as a group request. The article's example is a user splitting a bill among five friends. | Splitting costs among friends inside a wallet is real, established behavior. Wallets move the money but do not keep a shared ledger, explain the group's spending or manage a shared goal. That is the gap GroupWise fills. | The Financial Express, 4 Nov 2024 — [link](https://thefinancialexpress.com.bd/trade/fund-arrangements-during-need-now-easier-with-bkashs-request-money) |
| upay offers **multiple wallets in one account** (primary, salary, remittance and disbursement wallets), which won a fintech innovation award. | A shared **group-goal wallet** is a natural next wallet type. That is the concrete place GroupWise's goal pocket would live inside upay. | Prothom Alo, 2 Dec 2021 — [link](https://en.prothomalo.com/corporate/local/upay-wins-fintech-innovation-award-for-its-multi-wallet-feature) |

We cite only what these sources state. We make no claims about upay's current user numbers or plans.
GroupWise is an independent prototype and is not affiliated with upay.

## 3. Primary evidence from real users (in progress)

The judges were right that the Phase 1 report had no user evidence. The full research kit is in
[`research/`](../research/README.md):

| Method | Status | Output |
|---|---|---|
| Anonymous survey of DIU students (3 min, target ≥ 100) | Questionnaire and Google Form generator ready | `research/results/survey_summary.md` |
| 5–8 user interviews | Guide and note template ready | Themes and anonymous quotes |
| 2-week pilot with 5–8 real groups on the deployed app | Plan, consent text and automatic metrics (`pilot_metrics.py`) ready | `research/results/pilot_metrics.md` |

**Results are added here only once collected. Until then we publish no estimates.**

### Hypotheses (set before collecting data)

| # | Hypothesis | Measured by | Supports the problem if |
|---|---|---|---|
| H1 | Sharing costs is frequent for students | Survey Q2 | Most respondents share costs at least weekly |
| H2 | Money for shared costs already moves through wallets | Survey Q4, Q14 | Most respondents settle with bKash, Nagad, upay or Rocket |
| H3 | Tracking is informal and creates delay, loss and friction | Survey Q5–Q9 | Many track by memory or chat, wait more than 3 days, or report losses or arguments |
| H4 | Groups lack visibility and miss shared goals | Survey Q10, Q11 | Many don't know group spending; many group goals finish late or are abandoned |
| H5 | People want this inside their wallet | Survey Q12, Q13 | Wallet settle-up, import or a goal pocket rank among the top features; most rate 4–5 of 5 |
| H6 | The product changes behavior | Pilot metrics | Faster settlement than the survey baseline; AI categories accepted; goals stay on track |

If a hypothesis fails, we report it and adjust the product. For example, if few people care about forecasts, we
drop them from the core flow.

## 4. What the prototype measures today (synthetic data, clearly labeled)

Model quality is measured on held-out **synthetic** data (see [MODEL_EVALUATION.md](MODEL_EVALUATION.md)).
These numbers show that the AI works technically. They are **not** evidence of customer demand, which is what
sections 2 and 3 are for.
