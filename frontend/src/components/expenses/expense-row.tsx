"use client";

import {
  AlertTriangle,
  Bus,
  CircleDot,
  Clapperboard,
  GraduationCap,
  HeartPulse,
  House,
  Plane,
  ShoppingBag,
  ShoppingBasket,
  Utensils,
  Zap,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";

import { dayLabel, fmtTime, taka } from "@/lib/format";
import type { Expense } from "@/lib/types";
import { cn } from "@/lib/utils";
import { categoryColor } from "@/lib/viz";

export const CATEGORY_ICONS: Record<string, LucideIcon> = {
  Food: Utensils,
  Groceries: ShoppingBasket,
  Transport: Bus,
  Travel: Plane,
  Housing: House,
  Utilities: Zap,
  Entertainment: Clapperboard,
  Education: GraduationCap,
  Shopping: ShoppingBag,
  Health: HeartPulse,
  Other: CircleDot,
};

export function CategoryIcon({ category, size = 40 }: { category: string; size?: number }) {
  const Icon = CATEGORY_ICONS[category] ?? CircleDot;
  const color = categoryColor(category);
  return (
    <span className="grid shrink-0 place-items-center rounded-xl" style={{ width: size, height: size, background: `${color}1a`, color }} aria-hidden>
      <Icon className="size-[18px]" />
    </span>
  );
}

export function AnomalyChip({ expense }: { expense: Expense }) {
  const s = expense.anomaly.status;
  if (s === "flagged")
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-bad-soft px-2 py-0.5 text-[11px] font-semibold text-bad">
        <AlertTriangle className="size-3" aria-hidden /> Unusual · review
      </span>
    );
  if ((s === "valid" || s === "dismissed") && (expense.anomaly.score ?? 0) >= 0.6)
    return <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[11px] font-semibold text-ink-muted">Reviewed</span>;
  return null;
}

export function ExpenseRow({ expense, groupId, dense = false }: { expense: Expense; groupId: string; dense?: boolean }) {
  return (
    <Link
      href={`/g/${groupId}/transactions/${expense.id}`}
      className={cn("flex items-center gap-3 rounded-xl px-2 transition-colors hover:bg-surface", dense ? "py-2.5" : "py-3")}
    >
      <CategoryIcon category={expense.category} size={dense ? 36 : 40} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-ink">{expense.description}</p>
        <p className="truncate text-xs text-ink-muted">
          {expense.payer_name} paid · {expense.subcategory_label}
          {!dense && ` · ${dayLabel(expense.occurred_at)}, ${fmtTime(expense.occurred_at)}`}
        </p>
        {!dense && expense.anomaly.status === "flagged" && expense.anomaly.reasons?.[0] && (
          <p className="mt-0.5 truncate text-xs text-bad">{expense.anomaly.reasons[0].text}</p>
        )}
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <span className="tabular text-sm font-bold text-ink">{taka(expense.amount, { decimals: true })}</span>
        {dense ? <span className="text-[11px] text-ink-muted">{dayLabel(expense.occurred_at)}</span> : <AnomalyChip expense={expense} />}
      </div>
    </Link>
  );
}
