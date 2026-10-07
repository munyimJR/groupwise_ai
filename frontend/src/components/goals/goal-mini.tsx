"use client";

import { CircleCheck, Target, TriangleAlert } from "lucide-react";
import Link from "next/link";

import { Card, CardHeading } from "@/components/common/primitives";
import { fmtDateYear, likelihood, taka } from "@/lib/format";
import type { GoalPlan } from "@/lib/types";
import { cn } from "@/lib/utils";

export const GOAL_STATUS: Record<GoalPlan["status"], { label: string; cls: string }> = {
  on_track: { label: "On track", cls: "bg-good-soft text-good" },
  achieved: { label: "Achieved", cls: "bg-good-soft text-good" },
  at_risk: { label: "At risk", cls: "bg-warn-soft text-warn" },
  off_track: { label: "Behind", cls: "bg-bad-soft text-bad" },
  not_started: { label: "Not started", cls: "bg-muted text-ink-muted" },
  deadline_passed: { label: "Deadline passed", cls: "bg-muted text-ink-muted" },
};

/** Progress bar showing saved (solid) and projected-by-deadline (marker) against the target. */
export function GoalBar({ goal }: { goal: GoalPlan }) {
  const saved = Math.min(100, goal.progress_pct);
  const projected = Math.min(100, goal.projection.on_track_pct);
  return (
    <div>
      <div className="relative h-3 overflow-hidden rounded-full bg-brand-blue-soft">
        <div className="absolute inset-y-0 left-0 rounded-full bg-[#3987e5]" style={{ width: `${projected}%` }} />
        <div className="absolute inset-y-0 left-0 rounded-full bg-brand-blue" style={{ width: `${saved}%` }} />
      </div>
      <div className="mt-1.5 flex justify-between text-xs text-ink-muted">
        <span>
          <span className="mr-1 inline-block size-2 rounded-full bg-brand-blue align-middle" aria-hidden />
          Saved {taka(goal.saved)}
        </span>
        <span>
          <span className="mr-1 inline-block size-2 rounded-full bg-[#3987e5] align-middle" aria-hidden />
          Projected {taka(goal.projection.projected_amount)}
        </span>
      </div>
    </div>
  );
}

export function GoalMiniCard({ goal, groupId }: { goal: GoalPlan; groupId: string }) {
  const st = GOAL_STATUS[goal.status];
  const good = goal.status === "on_track" || goal.status === "achieved";
  return (
    <Card>
      <CardHeading
        icon={Target}
        title={goal.title}
        subtitle={`Target ${taka(goal.target)} by ${fmtDateYear(goal.deadline)}`}
        action={<span className={cn("inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs font-bold", st.cls)}>
          {good ? <CircleCheck className="size-3" aria-hidden /> : <TriangleAlert className="size-3" aria-hidden />}
          {st.label}
        </span>}
      />
      <p className="mb-3 text-[28px] font-extrabold leading-none text-ink">
        {Math.round(goal.projection.on_track_pct)}%<span className="ml-2 text-sm font-semibold text-ink-muted">projected on track</span>
      </p>
      <GoalBar goal={goal} />
      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-surface px-3 py-2">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">Current pace</p>
          <p className="mt-0.5 text-sm font-bold text-ink">{taka(goal.projection.rate_monthly)}<span className="text-xs font-medium text-ink-muted">/mo</span></p>
        </div>
        <div className="rounded-lg bg-surface px-3 py-2">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">On-time chance</p>
          <p className="mt-0.5 text-sm font-bold text-ink">{likelihood(goal.projection.likelihood_pct)}</p>
        </div>
      </div>
      <Link href={`/g/${groupId}/goals/${goal.goal_id}`} className="tap-target mt-3 inline-block text-sm font-semibold text-brand-blue hover:underline">
        Open planner →
      </Link>
    </Card>
  );
}
