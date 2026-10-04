"use client";

import { Target } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { EmptyState, ErrorState, LoadingBlock, PageHeader } from "@/components/common/primitives";
import { CreateGoalDialog } from "@/components/goals/create-goal-dialog";
import { GOAL_STATUS, GoalBar } from "@/components/goals/goal-mini";
import { fmtDateYear, likelihood, taka } from "@/lib/format";
import { useGoals } from "@/lib/queries";
import { cn } from "@/lib/utils";

export default function GoalsPage() {
  const { groupId } = useParams<{ groupId: string }>();
  const { data, isLoading, error, refetch } = useGoals(groupId);
  return (
    <div>
      <PageHeader
        eyebrow="Planning"
        title="Shared goals"
        subtitle="Projections and simulated likelihoods are based on current behaviour — estimates, not guarantees."
        actions={<CreateGoalDialog groupId={groupId} />}
      />
      {isLoading ? (
        <LoadingBlock rows={3} />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data?.length ? (
        <EmptyState icon={Target} title="No goals yet" body="Saving for a trip, a shared purchase or an emergency buffer? Create a goal to see if you're on track." action={<CreateGoalDialog groupId={groupId} />} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {data.map((g) => {
            const st = GOAL_STATUS[g.status];
            return (
              <Link key={g.goal_id} href={`/g/${groupId}/goals/${g.goal_id}`} className="card-surface block p-5 transition-shadow hover:shadow-[var(--shadow-lift)]">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-extrabold text-ink">{g.title}</h2>
                    <p className="text-xs text-ink-muted">
                      {taka(g.target)} by {fmtDateYear(g.deadline)} · {g.days_left > 0 ? `${g.days_left} days left` : "deadline reached"}
                    </p>
                  </div>
                  <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-xs font-bold", st.cls)}>{st.label}</span>
                </div>
                <GoalBar goal={g} />
                <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-xl bg-surface p-2">
                    <p className="text-xs text-ink-muted">Saved</p>
                    <p className="tabular font-bold text-ink">{g.progress_pct.toFixed(0)}%</p>
                  </div>
                  <div className="rounded-xl bg-surface p-2">
                    <p className="text-xs text-ink-muted">Projected</p>
                    <p className="tabular font-bold text-ink">{g.projection.on_track_pct.toFixed(0)}%</p>
                  </div>
                  <div className="rounded-xl bg-surface p-2">
                    <p className="text-xs text-ink-muted">Likelihood</p>
                    <p className="tabular font-bold text-ink">{likelihood(g.projection.likelihood_pct)}</p>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
