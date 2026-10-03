"use client";

import { CalendarClock, Gauge, ListChecks, Repeat, Users } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

import { ConfidenceMeter, MethodNote, ProvenanceBadge } from "@/components/ai/labels";
import { CategoryBars, ForecastChart } from "@/components/charts/charts";
import { Card, CardHeading, EmptyState, ErrorState, LoadingBlock, PageHeader } from "@/components/common/primitives";
import { fmtDate, taka } from "@/lib/format";
import { useForecast } from "@/lib/queries";
import { cn } from "@/lib/utils";

export default function ForecastPage() {
  const { groupId } = useParams<{ groupId: string }>();
  const [horizon, setHorizon] = useState(7);
  const { data: fc, isLoading, error, refetch, isFetching } = useForecast(groupId, horizon);

  return (
    <div>
      <PageHeader
        eyebrow="Prediction"
        title="Group cash-flow forecast"
        subtitle="What the group is likely to spend next — and when the pressure peaks. Based on your group's own history."
        actions={
          <div className="inline-flex rounded-xl border border-line bg-white p-1" role="group" aria-label="Forecast horizon">
            {[7, 14, 30].map((h) => (
              <button
                key={h}
                type="button"
                aria-pressed={horizon === h}
                onClick={() => setHorizon(h)}
                className={cn("rounded-lg px-3 py-1.5 text-sm font-semibold", horizon === h ? "bg-brand-yellow text-ink" : "text-ink-muted hover:text-ink")}
              >
                Next {h} days
              </button>
            ))}
          </div>
        }
      />
      {isLoading ? (
        <LoadingBlock rows={4} />
      ) : error || !fc ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : fc.status !== "ok" ? (
        <EmptyState icon={CalendarClock} title={fc.status === "inactive" ? "No recent activity to project" : "Not enough history yet"} body={fc.message} />
      ) : (
        <div className={cn("space-y-5 transition-opacity", isFetching && "opacity-60")}>
          <div className="grid gap-5 lg:grid-cols-[340px_1fr]">
            <Card className="flex flex-col justify-between bg-brand-yellow-soft">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-xs font-bold uppercase tracking-wider text-brand-blue-deep">Expected spending · next {horizon} days</p>
                </div>
                <p className="mt-2 text-[52px] font-extrabold leading-none tracking-tight text-ink">{taka(fc.total)}</p>
                <p className="mt-2 text-sm text-ink">
                  80% likely between <strong>{taka(fc.interval!.low)}</strong> and <strong>{taka(fc.interval!.high)}</strong>
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <ProvenanceBadge kind="prediction" />
                  <ConfidenceMeter level={fc.confidence!} />
                </div>
              </div>
              <div className="mt-5 space-y-2 rounded-xl bg-white/80 p-3 text-sm">
                <p className="flex justify-between">
                  <span className="text-ink-muted">Actual, previous {horizon} days</span>
                  <span className="tabular font-semibold text-ink">{taka(fc.comparison!.last_period_actual)}</span>
                </p>
                <p className="flex justify-between">
                  <span className="text-ink-muted">8-week daily average</span>
                  <span className="tabular font-semibold text-ink">{taka(fc.comparison!.avg_daily_8w)}/day</span>
                </p>
                {fc.pressure_days!.length > 0 && (
                  <p className="flex justify-between gap-3">
                    <span className="text-ink-muted">High-pressure days</span>
                    <span className="text-right font-semibold text-ink">▲ {fc.pressure_days!.map((p) => `${p.dow} ${fmtDate(p.date)}`).join(", ")}</span>
                  </p>
                )}
              </div>
            </Card>
            <Card>
              <CardHeading icon={CalendarClock} title="Day by day" subtitle="Bars show the projection; whiskers show the 80% range" />
              <ForecastChart daily={fc.daily!} pressureDates={fc.pressure_days!.map((p) => p.date)} height={horizon > 14 ? 260 : 240} />
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-3">
            <Card>
              <CardHeading icon={ListChecks} title="Why this forecast" subtitle="Evidence from your history" />
              {fc.drivers!.length ? (
                <ul className="space-y-2.5">
                  {fc.drivers!.map((d) => (
                    <li key={d.text} className="flex gap-2 text-sm text-ink">
                      <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-brand-blue" aria-hidden />
                      {d.text}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-ink-muted">Spending has been steady; no single driver stands out.</p>
              )}
              {!!fc.excluded_unusual && (
                <p className="mt-3 text-xs text-ink-muted">{fc.excluded_unusual} unusual one-off expense(s) were excluded so they don&apos;t distort the projection.</p>
              )}
            </Card>
            <Card>
              <CardHeading icon={Gauge} title="By category" subtitle={`Projected over ${horizon} days`} />
              <CategoryBars rows={fc.by_category!.map((c) => ({ category: c.category, current: c.total }))} />
            </Card>
            <Card>
              <CardHeading icon={Users} title="Expected share per member" subtitle="Based on each member's recent share of spending" />
              <ul className="divide-y divide-line">
                {fc.member_shares?.map((m) => (
                  <li key={m.member_id} className="flex justify-between py-2 text-sm">
                    <span className="text-ink">{m.name}</span>
                    <span className="tabular font-semibold text-ink">
                      ≈ {taka(m.expected)} <span className="text-xs font-normal text-ink-muted">({m.share_pct.toFixed(0)}%)</span>
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          {fc.recurring!.length > 0 && (
            <Card>
              <CardHeading icon={Repeat} title="Recurring bills detected" subtitle="Scheduled on their usual day of the month" />
              <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {fc.recurring!.map((r) => (
                  <li key={r.label} className="rounded-xl border border-line p-3 text-sm">
                    <p className="font-semibold text-ink">{r.label}</p>
                    <p className="text-xs text-ink-muted">
                      ≈ {taka(r.amount)} · next {fmtDate(r.next_date)} · seen {r.occurrences}×
                    </p>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          <Card className="bg-brand-blue-softer">
            <CardHeading title="How accurate is this?" subtitle="Rolling-origin backtest on this group's own past weeks" />
            {fc.backtest && fc.backtest.n_windows > 0 ? (
              <p className="text-sm text-ink">
                Re-running the model at {fc.backtest.n_windows} past cut-off dates, its 7-day totals were off by{" "}
                <strong>{Math.round((fc.backtest.weekly_mape ?? 0) * 100)}%</strong> on average
                {fc.backtest.mae_7day !== undefined && fc.backtest.baseline_mean28_mae_7day !== undefined && (
                  <>
                    {" "}
                    (average miss {taka((fc.backtest.mae_7day ?? 0) * 100)} vs {taka((fc.backtest.baseline_mean28_mae_7day ?? 0) * 100)} for a simple
                    28-day average)
                  </>
                )}
                . The range above comes from those errors.
              </p>
            ) : (
              <p className="text-sm text-ink">Not enough past weeks to backtest yet, so the range is wider and confidence is low.</p>
            )}
            <MethodNote>{fc.model?.method}. Based on {fc.transactions_used} transactions over {fc.history_days} days.</MethodNote>
          </Card>
        </div>
      )}
    </div>
  );
}
