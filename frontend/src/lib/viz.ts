/**
 * Chart tokens. Category colours follow the entity (never rank) and come from a validated
 * colour-blind-safe categorical palette (7 slots, adjacent CVD ΔE ≥ 9). Categories beyond the
 * seventh fold into "Other". Three slots are below 3:1 contrast on white, so every chart that uses
 * them ships with a legend / direct labels.
 */
export const CATEGORY_COLORS: Record<string, string> = {
  Food: "#2a78d6",
  Transport: "#eb6834",
  Groceries: "#1baf7a",
  Housing: "#eda100",
  Utilities: "#e87ba4",
  Entertainment: "#008300",
  Travel: "#4a3aa7",
};
export const OTHER_COLOR = "#98a2b3";

export function categoryColor(category: string): string {
  return CATEGORY_COLORS[category] ?? OTHER_COLOR;
}

/** Collapse categories without a palette slot into a single "Other" row. */
export function foldCategories<T extends { category: string }>(rows: T[], value: (r: T) => number): { category: string; value: number; color: string }[] {
  const out: { category: string; value: number; color: string }[] = [];
  let other = 0;
  for (const r of rows) {
    if (CATEGORY_COLORS[r.category]) out.push({ category: r.category, value: value(r), color: CATEGORY_COLORS[r.category] });
    else other += value(r);
  }
  out.sort((a, b) => b.value - a.value);
  if (other > 0) out.push({ category: "Other", value: other, color: OTHER_COLOR });
  return out;
}

export const chart = {
  grid: "#eef1f5",
  axis: "#98a2b3",
  ink: "#162033",
  inkMuted: "#667085",
  primary: "#0057b8",
  primarySoft: "rgba(0, 87, 184, 0.10)",
  highlight: "#ffd429",
  baseline: "#d0d5dd",
  surface: "#ffffff",
};
