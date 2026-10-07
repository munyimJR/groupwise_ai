# Demo script (about 2½ minutes, desktop)

**Setup:** open the live URL → **Explore the live demo**. You land on *DIU CSE Squad*. (Every visitor gets a private sandbox, so add and edit freely.)

| # | Do | Say |
|---|---|---|
| 1 | Dashboard | "GroupWise is an expense splitter whose real job is financial intelligence. Here's a friend group's last 30 days: spending, my balance, a transparent health indicator and next week's projection." |
| 2 | Point at **AI insights** | "Every card goes observation → inference → evidence. Food rose; *weekend restaurant* spending drives most of it, mostly through bigger bills. It also caught an unusual ৳16,500 expense and projects next week." |
| 3 | **+ Add expense** → type `Dinner at Kacchi Bhai 16500` | "Natural language: amount, merchant and category are understood, with the confidence and the words that drove it. If it's unsure, it asks." |
| 4 | Save | "Saved. Nothing is blocked, but it's flagged: 8× this group's usual restaurant range, at an odd hour, top 1% by Isolation Forest. The group decides: mark it valid, dismiss it, or fix a typo." |
| 5 | **Insights → Spending analytics** | "The driver decomposition shows which segment changed, by how much, and whether it was frequency or ticket size. All numbers are computed, with unusual one-offs excluded." |
| 6 | **Forecast** | "Next 7 days with an 80% range from the group's own backtests, the pressure days, why, and each member's expected share." |
| 7 | **Goals → Cox's Bazar Trip** | "At the current pace the trip fund is projected at about 74% of target, and the simulated likelihood of making it is under 1%. It's labelled as a projection, never a guarantee." |
| 8 | **What-If** → *Cut dining 15%* | "Real simulation on the forecast: savings per month, pressure, each member's burden, and the goal jumps above 100%. The assumption is shown." |
| 9 | **Ask GroupWise** → "Why did our spending increase?" | "Grounded copilot: the answer cites facts [F1], [F2]…, and every figure is verified against the data. Here's the evidence panel, typed as fact, prediction, assumption or recommendation." |
| 10 | Back to the dashboard → **Recommended action** | "The recommendation engine proposes reducing weekend dining *and simulates the outcome*: goal progress 74% → 106%. You can mark it helpful or dismiss it. AI recommends; the group decides." |
| 11 | (Optional) **Group dynamics** | "Observable payments only: Rony fronts most costs, so it suggests rotating the payer for big expenses. No judgments about people." |
| 12 | **Import from wallet** → **Use a sample statement** | "Most shared costs are already paid from a mobile wallet. This is a wallet statement export (synthetic for the demo). The AI categorizes every purchase and suggests what's shared, skips personal things like a mobile recharge, and notices that sending money to Rony was paying him back. Nothing is added until I confirm." |
| 13 | Import → **Balances** → **Request via wallet** (Shuvo) | "Settle-up runs on the wallet's own rails, like bKash's Request Money. GroupWise creates a payment request with a reference; the wallet confirms with a signed message, and only then is it recorded. The approval screen here is a labeled sandbox, so no real money moves." |
| 14 | **Shuvo pays** → back to balances | "Signed, amount-checked and idempotent, so a replayed or tampered confirmation is rejected. 4 payments settle everyone instead of 10, and that part is exact math, not AI." |
| 15 | (Optional) Goal → **Save via wallet** | "Members can put money toward the trip straight from their wallet. In upay this would be a goal wallet next to the multi-wallets it already has." |

**Closing line:** *"GroupWise AI doesn't just tell groups where their money went. It helps them understand what is happening, anticipate what comes next, and make better financial decisions together."*

### Mobile moment (10 seconds)
Open the same URL on a phone (or the browser's device mode): the bottom nav with the central **+** button, swipeable hero cards, and a one-handed add-expense form with a sticky save button. It installs as an app from the browser menu.

### Questions judges may ask
- *Is the AI just an LLM?* No. Categorization, anomaly detection, forecasting and goal simulation are ML/statistical models with held-out evaluation (see *How the AI works*). The LLM only words verified facts, and it's optional.
- *What if the LLM hallucinates a number?* The grounding check rejects any figure not in the facts and shows the deterministic answer instead.
- *Real data?* The demo data is synthetic. Real-user evidence is being collected with a survey, interviews and a 2-week pilot ([research/](../research/README.md)), and public evidence is in [PROBLEM_EVIDENCE.md](PROBLEM_EVIDENCE.md). We show survey numbers only once collected.
- *Is the wallet link real?* Everything except the wallet's approval screen is real: statement parsing and import, payment requests, and HMAC-signed confirmations with replay and amount checks. A partner integration replaces the sandbox with their API ([MFS_INTEGRATION.md](MFS_INTEGRATION.md)). It is a possible path, not an official partnership.
