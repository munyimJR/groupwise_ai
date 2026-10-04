"use client";

import { AlertTriangle, ArrowRight, CalendarClock, ChevronDown, CircleCheck, Lightbulb, Scale, Target, TrendingUp, Users } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import type { Insight } from "@/lib/types";
import { cn } from "@/lib/utils";

import { ConfidenceMeter, ProvenanceBadge } from "./labels";

const KIND_ICON = {
  spending_trend: TrendingUp,
  anomaly: AlertTriangle,
  forecast: CalendarClock,
  goal: Target,
  dynamics: Users,
  settlement: Scale,
} as const;

const SEVERITY = {
  alert: { ring: "border-l-bad", icon: "bg-bad-soft text-bad", word: "Needs review" },
  warning: { ring: "border-l-warn", icon: "bg-warn-soft text-warn", word: "Heads-up" },
  info: { ring: "border-l-brand-blue", icon: "bg-brand-blue-soft text-brand-blue", word: "Info" },
  positive: { ring: "border-l-good", icon: "bg-good-soft text-good", word: "Going well" },
} as const;

export function InsightCard({ insight, defaultOpen = false, compact = false }: { insight: Insight; defaultOpen?: boolean; compact?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const Icon = insight.severity === "positive" ? CircleCheck : KIND_ICON[insight.kind] ?? Lightbulb;
  const sev = SEVERITY[insight.severity] ?? SEVERITY.info;
  const isPrediction = insight.kind === "forecast" || insight.kind === "goal" || insight.kind === "anomaly";
  const hasDetail = insight.why.length > 0 || !!insight.inference;

  return (
    <article className={cn("rounded-2xl border border-line border-l-4 bg-white p-4 transition-shadow hover:shadow-[var(--shadow-card)]", sev.ring)}>
      <div className="flex items-start gap-3">
        <span className={cn("grid size-9 shrink-0 place-items-center rounded-xl", sev.icon)}>
          <Icon className="size-[18px]" aria-hidden />
          <span className="sr-only">{sev.word}</span>
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="text-[15px] font-bold leading-snug text-ink">{insight.title}</h3>
          <p className="mt-1 text-sm text-ink-muted">{insight.observation}</p>
          {!compact && insight.inference && (
            <p className="mt-2 text-sm font-medium text-ink">
              <span className="sr-only">Inference: </span>
              {insight.inference}
            </p>
          )}
        </div>
      </div>

      {hasDetail && (
        <div className="mt-3 pl-12">
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            className="tap-target inline-flex items-center gap-1 rounded-md text-xs font-semibold text-brand-blue hover:text-brand-blue-deep"
          >
            Why? <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} aria-hidden />
          </button>
          {open && (
            <div className="mt-2 space-y-2 rounded-xl bg-brand-blue-softer p-3">
              <div className="flex flex-wrap gap-1.5">
                <ProvenanceBadge kind="fact" />
                {isPrediction && <ProvenanceBadge kind="prediction" />}
                {insight.action && <ProvenanceBadge kind="recommendation" />}
              </div>
              {compact && insight.inference && <p className="text-sm font-medium text-ink">{insight.inference}</p>}
              {insight.why.length > 0 && (
                <ul className="space-y-1.5">
                  {insight.why.map((w) => (
                    <li key={w} className="flex gap-2 text-[13px] leading-snug text-ink">
                      <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-brand-blue" aria-hidden />
                      {w}
                    </li>
                  ))}
                </ul>
              )}
              <p className="text-xs text-ink-muted">Method: {insight.method}</p>
            </div>
          )}
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 pl-12">
        <ConfidenceMeter level={insight.confidence.level} basis={compact ? undefined : insight.confidence.basis} />
        {insight.action && (
          <Link href={insight.action.link} className="tap-target group inline-flex items-center gap-1 text-[13px] font-semibold text-brand-blue hover:text-brand-blue-deep">
            {compact ? "Open" : "Take action"}
            <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden />
          </Link>
        )}
      </div>
      {!compact && insight.action && <p className="mt-2 pl-12 text-[13px] text-ink-muted">{insight.action.text}</p>}
    </article>
  );
}
