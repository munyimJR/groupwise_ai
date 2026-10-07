# Phase 1 design refinement

## To-do

- [x] Read all seven judging categories and audit the existing interface.
- [x] Simplify navigation around shared expenses, balances, goals and insights.
- [x] Remove group-dynamics and prototype health-score surfaces from the main product experience.
- [x] Refine the dashboard and shared shell without changing ledger behavior.
- [x] Reduce the landing-page feature inventory and clarify prototype claims.
- [x] Verify desktop/mobile layouts, keyboard access and core workflows.
- [x] Run lint, TypeScript, production build and relevant regression checks.

## Design audit and decisions

This is a refinement of an existing product. Preserve the GroupWise logo, Plus Jakarta Sans, blue/yellow identity, authentication, expense entry, exact balances, settlement records, goal contributions, model explanations and What-If calculations.

The current shell exposes 14 destinations, duplicates account actions and promotes every AI tool equally. The dashboard mixes four headline tiles, four insight cards, recommendations, charts, two goal cards, member behavior analysis and recent expenses. Bright yellow panels, repeated icon containers, bold text and nested cards compete for attention.

Direction: a familiar shared-finance workspace. DESIGN_VARIANCE: 3, MOTION_INTENSITY: 2, VISUAL_DENSITY: 4. Keep the existing shadcn/Base UI system. Use blue for actions/selection, yellow sparingly as brand identity, neutral surfaces, 12px panel corners and 8px controls. Preserve existing light-theme product behavior rather than introducing an unrelated theme feature.

## Scope decisions from judging

| Feedback | Product response |
| --- | --- |
| Narrow the use case | Lead with recording shared spending, settling balances and funding a shared goal. |
| Group dynamics is sensitive | Retire its dedicated UI, promotional copy and surfaced recommendations. Old page links should reach balances. Keep legacy backend contracts intact for compatibility. |
| Synthetic metrics and scenario outcomes are not measured impact | Keep sample-data disclosure, call What-If results simulations, show actual saved money ahead of projected goal completion. |
| Preserve strong end-to-end implementation | Keep existing money calculations, mutations and authorization paths. |
| Insight / What-If / action is distinctive | Keep insights, forecasting, What-If and grounded questions with contextual access instead of equal navigation prominence. |
| Wallet integration is conceptual | State that payments happen outside GroupWise at the settlement decision point. Do not add a nonfunctional payment button. |

## Follow-up evidence work

Design changes cannot establish real user validation, measured retention, wallet transaction volume, fairness, model calibration or production readiness. Phase 2 still needs a governed user study; baseline/ablation and leakage checks; concurrent database/load testing; authorization, audit-log and session review; and a real wallet integration agreement. No new claims about these are introduced here.

## Verification

Frontend lint, production build and TypeScript checks pass. The local dashboard was checked at mobile and desktop widths. The mobile shell exposes Home, Activity, Add, Balances and Plan; the desktop shell exposes Money, Planning, Group and Account sections. Existing route slugs remain available, with the retired dynamics URL redirecting to balances.

## Minimalism pass

The follow-up visual pass keeps the same brand but removes visual weight across the whole site: smaller radii, almost-flat cards, quieter shadows, lighter surfaces, simpler heading icons, calmer navigation states, and a plain auth panel. The landing hero keeps the existing product story and component preview but removes the decorative yellow glow. This preserves the product's recognizable identity while making dense financial screens easier to scan.
