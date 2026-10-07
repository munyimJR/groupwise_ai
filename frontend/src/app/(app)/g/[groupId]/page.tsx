"use client";

import { ArrowLeftRight, ArrowRight, CalendarClock, Lightbulb, Receipt, Target, TrendingUp, Wallet } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { InsightCard } from "@/components/ai/insight-card";
import { ConfidenceMeter, ProvenanceBadge } from "@/components/ai/labels";
import { RecommendationCard } from "@/components/ai/recommendation-card";
import { CategoryBars, SpendTrendChart } from "@/components/charts/charts";
import { ExpenseRow } from "@/components/expenses/expense-row";
import { GoalMiniCard } from "@/components/goals/goal-mini";
import { BalanceTag, Card, CardHeading, Delta, EmptyState, ErrorState, LinkButton, LoadingBlock, PageHeader, StatTile } from "@/components/common/primitives";
import { Skeleton } from "@/components/ui/skeleton";
import { taka } from "@/lib/format";
import { useDashboard } from "@/lib/queries";

const TYPE_LABEL: Record<string, string> = { friends: "Friends", roommates: "Roommates", trip: "Trip", event: "Event", other: "Group" };

export default function DashboardPage() {
  const { groupId } = useParams<{ groupId: string }>();
  const { data, isLoading, error, refetch } = useDashboard(groupId);

  if (isLoading) return <DashboardSkeleton />;
  if (error || !data) return <ErrorState error={error} onRetry={() => refetch()} />;

  const fc = data.forecast;
  const hasExpenses = data.spending.count > 0 || data.recent_expenses.length > 0;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow={`${TYPE_LABEL[data.group.group_type] ?? "Group"} · ${data.group.member_count} member${data.group.member_count === 1 ? "" : "s"}`}
        title={data.group.name}
        subtitle="Shared money at a glance."
      />

      {!hasExpenses ? (
        <EmptyState
          icon={Receipt}
          title="No shared expenses yet"
          body="Add your first shared expense to start building group financial intelligence."
          action={<LinkButton href={`/g/${groupId}/add`}>Add the first expense</LinkButton>}
        />
      ) : (
        <>
          <div className="no-scrollbar -mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-1 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-visible sm:px-0 lg:grid-cols-3">
            <StatTile
              className="min-w-[78%] snap-start sm:min-w-0"
              accent
              icon={Wallet}
              label={`Spending · ${data.spending.period_days} days`}
              value={<span className="text-[34px]">{taka(data.spending.total)}</span>}
              sub={<Delta value={data.spending.change_pct} suffix="vs prior period" />}
            />
            <StatTile
              className="min-w-[78%] snap-start sm:min-w-0"
              icon={ArrowLeftRight}
              label="Your balance"
              value={taka(Math.abs(data.me.net), { decimals: true })}
              sub={
                <span className="flex flex-wrap items-center gap-2">
                  <BalanceTag net={data.me.net} size="sm" you />
                  <Link href={`/g/${groupId}/balances`} className="tap-target text-xs font-semibold text-brand-blue hover:underline">
                    Settle up
                  </Link>
                </span>
              }
            />
            <div className="card-surface flex min-w-[78%] snap-start flex-col gap-1.5 p-4 sm:min-w-0">
                <p className="flex items-center gap-1.5 text-xs font-semibold text-ink-muted">
                <CalendarClock className="size-3.5 text-brand-blue" aria-hidden /> Next 7 days
              </p>
              {fc.status === "ok" ? (
                <>
                  <p className="text-[26px] font-extrabold leading-none text-ink">≈ {taka(fc.total)}</p>
                  <p className="text-xs text-ink-muted">
                    Projected range {taka(fc.interval!.low)}–{taka(fc.interval!.high)}
                    {fc.pressure_days?.length ? ` · peak ${fc.pressure_days.map((p) => p.dow).join(", ")}` : ""}
                  </p>
                  <div className="flex items-center justify-between gap-2">
                    <ConfidenceMeter level={fc.confidence!} />
                    <Link href={`/g/${groupId}/forecast`} className="tap-target text-xs font-semibold text-brand-blue hover:underline">
                      Details
                    </Link>
                  </div>
                </>
              ) : (
                <p className="text-sm text-ink-muted">{fc.message}</p>
              )}
            </div>
          </div>

          <div className="grid gap-5 xl:grid-cols-12">
            <div className="space-y-5 xl:col-span-8">
              {data.recommendation && <RecommendationCard rec={data.recommendation} groupId={groupId} compact />}

              <Card>
                <CardHeading
                  icon={Lightbulb}
                  title="AI insights"
                  subtitle="Trends, anomalies, and forecasts."
                  action={
                    <Link href={`/g/${groupId}/insights`} className="tap-target inline-flex shrink-0 items-center gap-1 text-sm font-semibold text-brand-blue hover:underline">
                      All insights <ArrowRight className="size-3.5" aria-hidden />
                    </Link>
                  }
                />
                {data.insights.length ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    {data.insights.slice(0, 4).map((i) => (
                      <InsightCard key={i.id} insight={i} compact />
                    ))}
                  </div>
                ) : (
                  <EmptyState title="No insights yet" body="More transaction history is needed to generate reliable insights." />
                )}
              </Card>

              <Card>
                <CardHeading
                  icon={TrendingUp}
                  title="Spending trend"
                  subtitle={data.spending.basis}
                  action={<ProvenanceBadge kind="fact" />}
                />
                <div className="grid gap-6 lg:grid-cols-5">
                  <div className="lg:col-span-3">
                    <SpendTrendChart data={data.spending.daily_series} days={60} />
                  </div>
                  <div className="lg:col-span-2">
                    <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-ink-muted">Where it went · 30 days</p>
                    <CategoryBars rows={data.spending.categories} max={6} />
                  </div>
                </div>
              </Card>
            </div>

            <div className="space-y-5 xl:col-span-4">
              {data.goals.length > 0 ? (
                data.goals.slice(0, 2).map((g) => <GoalMiniCard key={g.goal_id} goal={g} groupId={groupId} />)
              ) : (
                <Card>
                  <CardHeading icon={Target} title="Shared goal" />
                  <p className="text-sm text-ink-muted">Saving for a trip or a shared purchase? Set a goal and GroupWise projects whether you&apos;ll make it.</p>
                  <LinkButton href={`/g/${groupId}/goals`} variant="soft" className="mt-3">
                    Create a goal
                  </LinkButton>
                </Card>
              )}

              <Card>
                <CardHeading
                  icon={Receipt}
                  title="Recent activity"
                  action={
                    <Link href={`/g/${groupId}/transactions`} className="tap-target text-sm font-semibold text-brand-blue hover:underline">
                      See all
                    </Link>
                  }
                />
                <ul className="-mx-2 divide-y divide-line">
                  {data.recent_expenses.slice(0, 5).map((e) => (
                    <li key={e.id}>
                      <ExpenseRow expense={e} groupId={groupId} dense />
                    </li>
                  ))}
                </ul>
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-5" aria-busy="true" aria-label="Loading dashboard">
      <Skeleton className="h-10 w-64 rounded-xl bg-line/60" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-32 rounded-2xl bg-line/60" />
        ))}
      </div>
      <div className="grid gap-5 xl:grid-cols-12">
        <LoadingBlock rows={4} className="xl:col-span-8" />
        <LoadingBlock rows={3} className="xl:col-span-4" />
      </div>
    </div>
  );
}
