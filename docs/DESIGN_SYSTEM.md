# Design system: upay-inspired fintech

GroupWise AI uses a **yellow / white / blue** direction inspired by Bangladesh MFS apps. It is not an official upay product and uses no upay assets. The style is *Banking/Traditional Finance*: minimal, Swiss-style, accessible, trust blue with a gold/yellow accent. Fintech "dark glassmorphism" was deliberately not used.

Tokens live in `frontend/src/app/globals.css`, and chart tokens live in `frontend/src/lib/viz.ts`.

## Colour roles

| Role | Token | Hex | Use |
|---|---|---|---|
| Brand yellow | `brand-yellow` | `#FFD429` | Primary actions, brand surfaces, highlights, selected states |
| Yellow (pressed) | `brand-yellow-strong` | `#F5C400` | Hover/pressed primary, high-pressure days in charts |
| Yellow soft | `brand-yellow-soft` | `#FFF7D1` | Recommendation and hero tiles |
| Trust blue | `brand-blue` | `#0057B8` | Navigation, headings accents, icons, links, structural UI |
| Deep blue | `brand-blue-deep` | `#003B7A` | Text on blue-soft, dark sections |
| Blue soft | `brand-blue-soft` | `#E9F1FB` | Active nav, icon tiles, selected chips |
| Ink | `ink` | `#162033` | Primary text |
| Ink muted | `ink-muted` | `#5D6678` | Secondary text (≥ 5:1 on every surface) |
| Surface | `surface` | `#F6F8FB` | Page background (white cards dominate) |
| Good / warn / bad | `good` `warn` `bad` | `#0F7A55` `#B45309` `#C2350C` | Always paired with an icon or word, never colour alone |
| Field boundary | `--input` | `#8A94A6` | Input/select/switch-track borders (≥ 3:1) |

### Verified contrast (WCAG 2.2)

| Pair | Ratio |
|---|---|
| Ink on white / on yellow | 16.3 / 11.4 |
| White on trust blue | 6.9 |
| Blue on white / on blue-soft | 6.9 / 6.0 |
| Ink-muted on white · surface · muted chip · bad-soft | 5.8 · 5.4 · 5.1 · 5.1 |
| Good · warn · bad on their soft tints | 4.8 · 4.6 · 4.9 |
| Input border on white (non-text) | 3.1 |
| Chart axis text | 5.8 |
| Chart data marks (other category, neutral bars, projections) | ≥ 3.0 |

## Typography
Plus Jakarta Sans for everything, with tabular figures for money. The minimum text size is 12px, and inputs use 16px on phones so iOS doesn't zoom in on focus. Headings are bold (700–800) with balanced wrapping.

## Interaction & layout rules
- **Touch targets:** ≥ 44×44px on touch screens (`pointer-coarse:` sizes on buttons, inputs, selects and chips; the `tap-target` utility enlarges hit areas of compact text links without changing layout). Chips are spaced ≥ 8px apart.
- **One primary action per screen:** the yellow button. On mobile the central **+** in the bottom nav adds expenses; on desktop it's the sidebar button.
- **Navigation:** sidebar on ≥ 1024px; bottom nav with five labelled items and the central add button on phones. The active item is highlighted with colour, a yellow indicator bar and weight.
- **Focus:** a 2px blue outline on every focusable element. `scroll-padding` keeps focused fields clear of the sticky header and bottom nav. A skip link goes to `#main`.
- **Safe areas:** the header sits below `env(safe-area-inset-top)` and the bottom nav pads `env(safe-area-inset-bottom)`, for installed-app (PWA) use on notched phones.
- **Forms:** visible labels; errors appear under the field with `aria-describedby`, and focus moves to the first invalid field. Optional fields are marked "(optional)". Passwords have a show/hide toggle and work with password managers and paste.
- **Feedback:** loading states on every async button, skeletons for pages, toasts for success, and destructive actions confirmed in a dialog.
- **Motion:** short colour/opacity transitions only; `prefers-reduced-motion` disables animation.
- **Light-only by design:** the `dark:` variant applies only under a `.dark` class, so an OS-level dark mode can't partially restyle the UI.

## Data visualisation
A fixed colour per category (colour follows the entity, never its rank), drawn from a colour-blind-safe palette validated with the dataviz checker. Categories beyond seven fold into "Other". Every chart has a legend or direct labels, a tooltip, hairline grids and a screen-reader caption, and charts are keyboard-navigable (Recharts accessibility layer).

## Audit log
A UI/UX audit with the *ui-ux-pro-max* rules on the fintech profile found and fixed:
- three sub-4.5:1 text pairs
- faint input borders (1.4:1)
- 59 instances of 10–11px text
- sub-44px touch targets on buttons, chips, links and icon buttons
- 14px selects that triggered iOS zoom
- missing pointer cursors on native buttons
- a missing skip link and safe-area handling
- form errors shown far from their fields, and no password visibility toggle
- OS dark mode partially restyling inputs
