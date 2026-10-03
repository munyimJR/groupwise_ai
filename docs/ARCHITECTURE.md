# Architecture

## Layers (kept logically separate)

| # | Layer | Where | Notes |
|---|---|---|---|
| 1 | Authentication | `backend/app/auth/security.py`, `frontend/src/lib/auth.tsx` | Supabase Auth tokens (JWKS or legacy HS256) **or** API-issued HS256 tokens for local accounts and demo sandboxes. scrypt password hashing. 401 → "session expired" flow in the client. |
| 2 | Data | `backend/app/models.py`, `db.py` | SQLAlchemy 2 models. Money = BIGINT paisa. `occurred_at` = Asia/Dhaka wall-clock. Every financial mutation bumps `groups.data_version`. |
| 3 | Deterministic finance | `backend/app/core/` | Splits (equal/percentage/exact), balance sheet with a zero-sum invariant, pairwise debts, greedy min-cash-flow simplification. **Not AI.** |
| 4 | Analytics & ML inference | `backend/app/analytics/`, `backend/app/ml/` | Pure functions over a cached `GroupSnapshot`. |
| 5 | Recommendations | `backend/app/analytics/insights.py` | Rule-based candidates whose impact is computed with the What-If engine. Dismissals are respected for 7 days. |
| 6 | LLM explanation | `backend/app/copilot/`, `backend/app/llm/` | Typed facts → Claude → numeric grounding check → deterministic fallback. |
| 7 | Presentation | `frontend/` | Next.js App Router, client-rendered behind auth, TanStack Query cache invalidated per group on every mutation. |

## Request flow: adding an expense

```
POST /api/groups/{id}/expenses
  → membership check (non-members get 404)
  → money parsed to paisa, split computed exactly (core/splits.py)
  → categorizer: per-group correction memory first, else ML prediction (+ known-merchant prior)
  → anomaly model fitted on this group's history, expense scored, reasons attached
  → AIOutput audit rows (categorization, anomaly) written
  → data_version += 1 (invalidates every cached analysis for the group)
  → notifications for other app-user members (+ anomaly alert if flagged)
  ← expense + categorization + anomaly result (the UI shows the review dialog; nothing is blocked)
```

## Request flow: Ask GroupWise

```
POST /api/groups/{id}/copilot  {question, history}
  → rate limit, length cap
  → intent: injection / regulated-advice / greeting rules → topic rules → TF-IDF classifier
  → fact builders call the same analytics the UI uses → FactSet [{id, type, statement, source}]
  → deterministic template answer composed from the facts (always available)
  → if an LLM is configured: system prompt + <group_facts> JSON + <question> → Claude
       → grounding.check(answer, facts, question): every number must match a fact (rounding allowed)
       → pass: LLM answer · fail: template answer + notice listing rejected figures
  → AIOutput audit row (intent, mode, grounding result)
  ← answer, facts, cited ids, grounding stats, basis, follow-ups
```

## Caching

`load_snapshot()` reads a group's members, expenses + splits, settlements, goals and contributions into dataclasses once, keyed by `(group_id, data_version, local date)`. Analyses are memoized on the snapshot (`memo(snap, key, fn)`), so a dashboard request computes balances, spending, forecast, dynamics, goals, health and recommendations from a single read in about 0.1 s. Any mutation bumps `data_version`, so stale results are impossible.

## Data model (abridged)

```
users ─┬─< group_members >─┬─ groups ─┬─< expenses ─< expense_splits
       │                   │          ├─< settlements
       │                   │          ├─< goals ─< goal_contributions
       │                   │          ├─< category_feedback   (human corrections → training signal)
       │                   │          ├─< ai_outputs          (prediction, confidence, model + version)
       │                   │          └─< recommendation_actions (accepted / dismissed)
       └─< notifications
```

Guest members (`user_id = NULL`) let a group track people who don't use the app yet. They can claim their spot through the invite link.

## Security

- Every group endpoint requires active membership, and non-members get `404`, so ids can't be probed.
- Postgres deployments enable **row-level security with no policies** on every table. The public anon/authenticated roles therefore cannot read anything through Supabase's Data API, and the API's server-side connection is the only path.
- Only the Supabase **anon** key is ever sent to the browser. The API never needs the service-role key.
- Production refuses to start with the default `JWT_SECRET`. Rate limits apply to login, sign-up, demo creation and the copilot. Security headers are set on both apps. Unhandled errors return a generic message.
- LLM safety: no tools, no write access, a fenced data block, prompt-injection and advice detection, and numeric grounding.

## Fallback behaviour

| Failure | Effect |
|---|---|
| LLM key missing / API down / refusal / timeout | Copilot answers deterministically with a notice. Everything else is unaffected. A 60 s circuit breaker avoids repeated slow failures. |
| Too little history | Each feature shows an explicit empty state ("More transaction history is needed…"), never a fabricated number. |
| Inactive group (e.g. finished trip) | Forecast returns `inactive`, and the insight feed surfaces the open settle-up plan instead. |
| Network loss in the browser | The API client shows a friendly error and offers Retry. The PWA serves an offline page and never caches financial data. |
