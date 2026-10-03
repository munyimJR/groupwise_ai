"use client";

import { ArrowLeftRight, ArrowRight, CalendarClock, HeartPulse, Lightbulb, Plus, Receipt, Sparkles, Target, TrendingUp, Wallet } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { HealthExplainer, HealthRing } from "@/components/ai/health-ring";
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
        eyebrow={`${TYPE_LABEL[data.group.group_type] ?? "Group"} · ${data.group.member_count} members`}
        title={data.group.name}
        subtitle="Your group's money at a glance — what happened, what's likely next, and what to do about it."
        actions={
          <>
            <LinkButton href={`/g/${groupId}/ask`} variant="outline" className="hidden sm:inline-flex">
              <Sparkles className="size-4 text-brand-blue" aria-hidden /> Ask GroupWise
            </LinkButton>
            <LinkButton href={`/g/${groupId}/add`}>
              <Plus className="size-4" aria-hidden /> Add expense
            </LinkButton>
          </>
        }
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
          {/* Hero tiles — swipeable on mobile */}
          <div className="no-scrollbar -mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-1 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-visible sm:px-0 xl:grid-cols-4">
            <StatTile
              className="min-w-[78%] snap-start sm:min-w-0"
              accent
              icon={Wallet}
              label={`Total spending · last ${data.spending.period_days} days`}
              value={<span className="text-[34px]">{taka(data.spending.total)}</span>}
              sub={<Delta value={data.spending.change_pct} suffix={`vs previous ${data.spending.period_days} days`} />}
            />
            <StatTile
              className="min-w-[78%] snap-start sm:min-w-0"
              icon={ArrowLeftRight}
              label="Your net balance"
              value={taka(Math.abs(data.me.net), { decimals: true })}
              sub={
                <span className="flex flex-wrap items-center gap-2">
                  <BalanceTag net={data.me.net} size="sm" you />
                  <Link href={`/g/${groupId}/balances`} className="text-xs font-semibold text-brand-blue hover:underline">
                    Settle up
                  </Link>
                </span>
              }
            />
            <div className="card-surface flex min-w-[78%] snap-start items-center gap-4 p-4 sm:min-w-0">
              {data.health.status === "ok" && data.health.score !== undefined ? (
                <>
                  <HealthRing score={data.health.score} />
                  <div className="min-w-0">
                    <p className="flex items-center gap-1.5 text-xs font-semibold text-ink-muted">
                      <HeartPulse className="size-3.5 text-brand-blue" aria-hidden /> Financial health
                    </p>
                    <p className="text-lg font-extrabold capitalize text-ink">{data.health.band}</p>
                    <p className="text-[11px] text-ink-muted">Prototype indicator</p>
                    <HealthExplainer health={data.health} />
                  </div>
                </>
              ) : (
                <p className="text-sm text-ink-muted">{data.health.message ?? "More history is needed for a health indicator."}</p>
              )}
            </div>
            <div className="card-surface flex min-w-[78%] snap-start flex-col gap-1.5 p-4 sm:min-w-0">
              <p className="flex items-center gap-1.5 text-xs font-semibold text-ink-muted">
                <CalendarClock className="size-3.5 text-brand-blue" aria-hidden /> Next 7 days · projected
              </p>
              {fc.status === "ok" ? (
                <>
                  <p className="text-[26px] font-extrabold leading-none text-ink">≈ {taka(fc.total)}</p>
                  <p className="text-xs text-ink-muted">
                    Likely {taka(fc.interval!.low)}–{taka(fc.interval!.high)}
                    {fc.pressure_days?.length ? ` · peak ${fc.pressure_days.map((p) => p.dow).join(", ")}` : ""}
                  </p>
                  <div className="flex items-center justify-between gap-2">
                    <ConfidenceMeter level={fc.confidence!} />
                    <Link href={`/g/${groupId}/forecast`} className="text-xs font-semibold text-brand-blue hover:underline">
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
              {data.recommendation && <RecommendationCard rec={data.recommendation} groupId={groupId} />}

              <Card>
                <CardHeading
                  icon={Lightbulb}
                  title="AI insights"
                  subtitle="Every number below is computed from your group's own transactions."
                  action={
                    <Link href={`/g/${groupId}/insights`} className="inline-flex shrink-0 items-center gap-1 text-sm font-semibold text-brand-blue hover:underline">
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
                  <p className="text-sm text-ink-muted">Saving for a trip or a shared purchase? Set a goal and GroupWise projects whether you'll make it.</p>
                  <LinkButton href={`/g/${groupId}/goals`} variant="soft" className="mt-3">
                    Create a goal
                  </LinkButton>
                </Card>
              )}

              {data.dynamics.status === "ok" && (
                <Card>
                  <CardHeading
                    icon={ArrowLeftRight}
                    title="Group dynamics"
                    subtitle="Who fronts the money — observable payments only"
                    action={
                      <Link href={`/g/${groupId}/dynamics`} className="text-sm font-semibold text-brand-blue hover:underline">
                        Open
                      </Link>
                    }
                  />
                  {data.dynamics.insights[0] && (
                    <p className="mb-3 rounded-xl bg-brand-blue-softer p-3 text-sm text-ink">{data.dynamics.insights[0].text}</p>
                  )}
                  <ul className="space-y-2">
                    {data.dynamics.members.slice(0, 4).map((m) => (
                      <li key={m.member_id} className="text-xs">
                        <div className="flex justify-between font-medium text-ink">
                          <span>
                            {m.name}
                            {m.is_you && <span className="text-ink-muted"> (you)</span>}
                          </span>
                          <span className="tabular">
                            paid {m.paid_share_pct.toFixed(0)}% · used {m.consumed_share_pct.toFixed(0)}%
                          </span>
                        </div>
                        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-[#f1f4f8]">
                          <div className="h-full rounded-full bg-brand-blue" style={{ width: `${Math.min(100, m.paid_share_pct)}%` }} />
                        </div>
                      </li>
                    ))}
                  </ul>
                </Card>
              )}

              <Card>
                <CardHeading
                  icon={Receipt}
                  title="Recent activity"
                  action={
                    <Link href={`/g/${groupId}/transactions`} className="text-sm font-semibold text-brand-blue hover:underline">
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
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
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
