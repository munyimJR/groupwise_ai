"use client";

import { AlertTriangle, BarChart3, CalendarDays, Lightbulb, Store, TrendingUp } from "lucide-react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { InsightCard } from "@/components/ai/insight-card";
import { MethodNote, ProvenanceBadge } from "@/components/ai/labels";
import { RecommendationCard } from "@/components/ai/recommendation-card";
import { CategoryBars, LegendRow, SpendTrendChart } from "@/components/charts/charts";
import { Card, CardHeading, Delta, EmptyState, ErrorState, LoadingBlock, PageHeader, StatTile } from "@/components/common/primitives";
import { ExpenseRow } from "@/components/expenses/expense-row";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { fmtDate, taka } from "@/lib/format";
import { useInsights, useSpending } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { chart } from "@/lib/viz";

function InsightsTab({ groupId }: { groupId: string }) {
  const { data, isLoading, error, refetch } = useInsights(groupId);
  if (isLoading) return <LoadingBlock rows={4} />;
  if (error || !data) return <ErrorState error={error} onRetry={() => refetch()} />;
  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
      <div className="space-y-3">
        {data.insights.length ? (
          data.insights.map((i) => <InsightCard key={i.id} insight={i} defaultOpen={i.kind === "spending_trend"} />)
        ) : (
          <EmptyState icon={Lightbulb} title="No insights yet" body="More transaction history is needed to generate reliable insights." />
        )}
      </div>
      <div className="space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-ink-muted">Recommended actions</h2>
        {data.recommendations.length ? (
          data.recommendations.map((r, i) => <RecommendationCard key={r.key} rec={r} groupId={groupId} variant={i === 0 ? "hero" : "row"} />)
        ) : (
          <p className="text-sm text-ink-muted">Nothing needs your attention right now.</p>
        )}
      </div>
    </div>
  );
}

function SpendingTab({ groupId }: { groupId: string }) {
  const [days, setDays] = useState(30);
  const { data, isLoading, error, refetch, isFetching } = useSpending(groupId, days);
  if (isLoading) return <LoadingBlock rows={4} />;
  if (error || !data) return <ErrorState error={error} onRetry={() => refetch()} />;
  const maxDow = Math.max(...data.by_weekday.map((d) => d.total), 1);

  return (
    <div className={cn("space-y-5 transition-opacity", isFetching && "opacity-60")}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-xl border border-line bg-white p-1" role="group" aria-label="Period">
          {[7, 30, 90].map((d) => (
            <button
              key={d}
              type="button"
              aria-pressed={days === d}
              onClick={() => setDays(d)}
              className={cn("rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors pointer-coarse:min-h-10", days === d ? "bg-brand-yellow text-ink" : "text-ink-muted hover:text-ink")}
            >
              {d} days
            </button>
          ))}
        </div>
        <p className="text-xs text-ink-muted">{data.basis}</p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label={`Spent · ${days} days`} value={taka(data.total)} sub={<Delta value={data.change_pct} suffix="vs previous period" />} accent />
        <StatTile label="Excluding unusual" value={data.change_pct_excluding_unusual === null ? "—" : `${data.change_pct_excluding_unusual > 0 ? "+" : ""}${data.change_pct_excluding_unusual.toFixed(0)}%`} sub={<span className="text-xs text-ink-muted">{data.unusual_in_period.length} unusual expense(s) left out</span>} />
        <StatTile label="Average expense" value={taka(data.average_expense)} sub={<span className="text-xs text-ink-muted">{data.count} expenses</span>} />
        <StatTile label="Largest expense" value={data.largest_expense ? taka(data.largest_expense.amount) : "—"} sub={<span className="line-clamp-1 text-xs text-ink-muted">{data.largest_expense?.description}</span>} />
      </div>

      {data.focus && data.drivers.length > 0 && (
        <Card>
          <CardHeading
            icon={TrendingUp}
            title={`Why ${data.focus.category} changed ${data.focus.change_pct !== null ? `${data.focus.change_pct > 0 ? "+" : ""}${data.focus.change_pct.toFixed(0)}%` : ""}`}
            subtitle={`${taka(data.focus.previous)} → ${taka(data.focus.current)} · regular spending, unusual one-offs excluded`}
            action={<ProvenanceBadge kind="fact" />}
          />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <caption className="sr-only">Driver decomposition of the change</caption>
              <thead>
                <tr className="text-left text-xs text-ink-muted">
                  <th className="py-2 font-semibold">Segment</th>
                  <th className="py-2 text-right font-semibold">Before → now</th>
                  <th className="py-2 text-right font-semibold">Share of change</th>
                  <th className="py-2 text-right font-semibold">How often</th>
                  <th className="py-2 text-right font-semibold">Avg bill</th>
                  <th className="py-2 pl-3 font-semibold">Mainly</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.drivers.map((d) => (
                  <tr key={d.segment}>
                    <td className="py-2.5 font-semibold text-ink">{d.segment}</td>
                    <td className="tabular py-2.5 text-right text-ink">
                      {taka(d.previous)} → {taka(d.current)}
                    </td>
                    <td className="tabular py-2.5 text-right font-bold text-ink">{Math.min(d.share_of_change_pct, 100).toFixed(0)}%</td>
                    <td className="tabular py-2.5 text-right text-ink">
                      {d.count_previous} → {d.count_current}
                    </td>
                    <td className="tabular py-2.5 text-right text-ink">
                      {taka(d.avg_previous)} → {taka(d.avg_current)}
                    </td>
                    <td className="py-2.5 pl-3 text-ink-muted">{d.mainly === "frequency" ? "More often" : "Bigger bills"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <MethodNote>change = (Δ number of expenses × previous average) + (current number × Δ average). Weekend = Thursday evening to Saturday. Shares can add up to more than 100% when other segments fell.</MethodNote>
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeading icon={BarChart3} title="Daily spending" subtitle="Last 90 days" />
          <SpendTrendChart data={data.daily_series} days={90} />
        </Card>
        <Card>
          <CardHeading icon={BarChart3} title="By category" subtitle={`Last ${days} days · change vs the ${days} days before`} />
          <CategoryBars rows={data.categories} showChange max={8} />
        </Card>
        <Card>
          <CardHeading icon={CalendarDays} title="By day of week" subtitle={`Weekend (Thu evening–Sat) is ${data.weekend_share_pct.toFixed(0)}% of spending`} />
          <ul className="flex h-40 items-end gap-2" aria-label="Spending by weekday">
            {data.by_weekday.map((d) => (
              <li key={d.dow} className="flex flex-1 flex-col items-center gap-1">
                <span className="tabular text-xs font-semibold text-ink-muted">{taka(d.total).replace("৳", "")}</span>
                <span className="w-full max-w-6 rounded-t-[4px]" style={{ height: `${(d.total / maxDow) * 100}px`, background: ["Thu", "Fri", "Sat"].includes(d.dow) ? "#f5c400" : chart.primary }} />
                <span className="text-xs font-semibold text-ink">{d.dow}</span>
              </li>
            ))}
          </ul>
          <div className="mt-3">
            <LegendRow items={[{ label: "Weekday", color: chart.primary }, { label: "Weekend days", color: "#f5c400" }]} />
          </div>
        </Card>
        <Card>
          <CardHeading icon={Store} title="Top merchants" />
          {data.top_merchants.length ? (
            <ul className="divide-y divide-line">
              {data.top_merchants.map((m) => (
                <li key={m.merchant} className="flex items-center justify-between py-2 text-sm">
                  <span className="font-medium text-ink">{m.merchant}</span>
                  <span className="tabular text-ink">
                    {taka(m.total)} <span className="text-xs text-ink-muted">· {m.count}×</span>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-ink-muted">No merchant names recorded in this period.</p>
          )}
        </Card>
      </div>

      <Card>
        <CardHeading title="Who paid upfront this period" subtitle="Paid = money fronted; consumed = their share of expenses" />
        <ul className="space-y-2">
          {data.members.map((m) => (
            <li key={m.member_id} className="grid grid-cols-[120px_1fr_auto] items-center gap-3 text-sm">
              <span className="truncate font-medium text-ink">{m.name}</span>
              <span className="h-2.5 overflow-hidden rounded-full bg-[#f1f4f8]">
                <span className="block h-full rounded-full" style={{ width: `${m.paid_share_pct}%`, background: chart.primary }} />
              </span>
              <span className="tabular text-xs text-ink">
                {taka(m.paid)} paid · {taka(m.consumed)} consumed
              </span>
            </li>
          ))}
        </ul>
      </Card>
      <p className="text-xs text-ink-muted">
        Period {fmtDate(data.period.start)} – {fmtDate(data.period.end)}. {data.method}.
      </p>
    </div>
  );
}

function UnusualTab({ groupId }: { groupId: string }) {
  const { data, isLoading, error, refetch } = useInsights(groupId);
  if (isLoading) return <LoadingBlock rows={4} />;
  if (error || !data) return <ErrorState error={error} onRetry={() => refetch()} />;
  const pending = data.anomalies.filter((a) => a.anomaly.status === "flagged");
  const reviewed = data.anomalies.filter((a) => a.anomaly.status !== "flagged");
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Card>
        <CardHeading icon={AlertTriangle} title="Waiting for review" subtitle="Flagged by the anomaly model — nothing is blocked" action={<ProvenanceBadge kind="prediction" />} />
        {pending.length ? (
          <ul className="divide-y divide-line">
            {pending.map((e) => (
              <li key={e.id}>
                <ExpenseRow expense={{ ...e, anomaly: { ...e.anomaly, reasons: e.reasons ?? [] } }} groupId={groupId} />
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="All clear" body="No unusual expenses are waiting for review." />
        )}
      </Card>
      <Card>
        <CardHeading title="Reviewed" subtitle="Confirmed as valid or dismissed by the group" />
        {reviewed.length ? (
          <ul className="divide-y divide-line">
            {reviewed.map((e) => (
              <li key={e.id}>
                <ExpenseRow expense={e} groupId={groupId} />
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-ink-muted">Nothing reviewed yet.</p>
        )}
        <MethodNote>Isolation Forest + robust statistics vs this group&apos;s history + duplicate/time rules. Score ≥ 60% is flagged.</MethodNote>
      </Card>
    </div>
  );
}

function InsightsInner() {
  const { groupId } = useParams<{ groupId: string }>();
  const params = useSearchParams();
  const router = useRouter();
  const tab = params.get("tab") ?? "insights";
  return (
    <div>
      <PageHeader eyebrow="Intelligence" title="AI insights & spending analytics" subtitle="What changed, why it changed, and what looks unusual — computed from your group's transactions." />
      <Tabs value={tab} onValueChange={(v) => router.replace(`/g/${groupId}/insights?tab=${v}`, { scroll: false })}>
        <TabsList className="mb-5">
          <TabsTrigger value="insights">Insights</TabsTrigger>
          <TabsTrigger value="spending">Spending analytics</TabsTrigger>
          <TabsTrigger value="unusual">Unusual expenses</TabsTrigger>
        </TabsList>
        <TabsContent value="insights">
          <InsightsTab groupId={groupId} />
        </TabsContent>
        <TabsContent value="spending">
          <SpendingTab groupId={groupId} />
        </TabsContent>
        <TabsContent value="unusual">
          <UnusualTab groupId={groupId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default function InsightsPage() {
  return (
    <Suspense>
      <InsightsInner />
    </Suspense>
  );
}

