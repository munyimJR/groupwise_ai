"use client";

import { ArrowRight, FlaskConical, Gauge, Lightbulb, RotateCcw, Target, Users } from "lucide-react";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

import { MethodNote, ProvenanceBadge } from "@/components/ai/labels";
import { GoalProjectionChart } from "@/components/charts/charts";
import { Card, CardHeading, EmptyState, ErrorState, LoadingBlock, PageHeader } from "@/components/common/primitives";
import { CATEGORY_ICONS } from "@/components/expenses/expense-row";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { fmtDateYear, likelihood, taka } from "@/lib/format";
import { type WhatIfInput, useGoal, useGoals, useWhatIf } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { categoryColor } from "@/lib/viz";

const WEEKS_PER_MONTH = 30.44 / 7;

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

function SliderRow({ label, value, onChange, min = -50, max = 50, hint, color }: { label: string; value: number; onChange: (v: number) => void; min?: number; max?: number; hint?: string; color?: string }) {
  const Icon = CATEGORY_ICONS[label];
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-sm font-semibold text-ink">
          {color && <span className="size-2.5 rounded-[3px]" style={{ background: color }} aria-hidden />}
          {Icon && <Icon className="size-4 text-ink-muted" aria-hidden />}
          {label}
        </span>
        <span className={cn("tabular rounded-md px-2 py-0.5 text-xs font-bold", value < 0 ? "bg-good-soft text-good" : value > 0 ? "bg-warn-soft text-warn" : "bg-muted text-ink-muted")}>
          {value > 0 ? "+" : value < 0 ? "−" : ""}
          {Math.abs(value)}%
        </span>
      </div>
      <Slider aria-label={`${label} change`} min={min} max={max} step={5} value={[value]} onValueChange={(v) => onChange(Array.isArray(v) ? v[0] : (v as number))} />
      {hint && <p className="text-[11px] text-ink-muted">{hint}</p>}
    </div>
  );
}

function WhatIfInner() {
  const { groupId } = useParams<{ groupId: string }>();
  const params = useSearchParams();
  const { data: goals } = useGoals(groupId);
  const activeGoals = useMemo(() => goals?.filter((g) => g.status !== "achieved" && g.status !== "deadline_passed") ?? [], [goals]);

  const [changes, setChanges] = useState<Record<string, number>>(() => {
    const cat = params.get("cat");
    const pct = Number(params.get("pct"));
    return cat && !Number.isNaN(pct) ? { [cat]: pct } : {};
  });
  const [overall, setOverall] = useState(0);
  const [extra, setExtra] = useState("");
  const [redirect, setRedirect] = useState(true);
  const [goalId, setGoalId] = useState<string | null>(params.get("goal"));
  const effectiveGoal = goalId ?? activeGoals[0]?.goal_id ?? null;

  const input: WhatIfInput = useDebounced(
    { category_changes: changes, overall_change_pct: overall, extra_monthly_contribution: Number(extra) || 0, goal_id: effectiveGoal, redirect_savings: redirect },
    250,
  );
  const baseline: WhatIfInput = { category_changes: {}, overall_change_pct: 0, extra_monthly_contribution: 0, goal_id: effectiveGoal, redirect_savings: true };
  const { data: base } = useWhatIf(groupId, baseline);
  const { data, isLoading, error, refetch, isFetching } = useWhatIf(groupId, input);
  const { data: goalPlan } = useGoal(groupId, effectiveGoal ?? "");

  const categories = (base ?? data)?.categories ?? [];
  const reset = () => {
    setChanges({});
    setOverall(0);
    setExtra("");
    setRedirect(true);
  };
  const presets = [
    { label: "Cut dining 15%", apply: () => { reset(); setChanges({ Food: -15 }); } },
    { label: "Expenses +20% next month", apply: () => { reset(); setOverall(20); } },
    { label: `Each member adds ৳500/month`, apply: () => { reset(); setExtra(String(500 * (data?.members.length || 1))); } },
    { label: "Cut dining 25% + entertainment 30%", apply: () => { reset(); setChanges({ Food: -25, Entertainment: -30 }); } },
  ];

  if (isLoading && !data) return <LoadingBlock rows={5} />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (data?.status === "insufficient_data") return <EmptyState icon={FlaskConical} title="Nothing to simulate yet" body={data.message} />;
  if (!data) return null;

  const saving = data.monthly_savings;
  const g = data.goal;

  return (
    <div>
      <PageHeader
        eyebrow="Signature feature"
        title="What if…?"
        subtitle="Change your group's behaviour and see the projected effect on monthly spending, financial pressure and your goal. Real calculations on your data — not hard-coded."
      />
      <div className="no-scrollbar -mx-4 mb-5 flex gap-2 overflow-x-auto px-4 sm:mx-0 sm:flex-wrap sm:px-0">
        {presets.map((p) => (
          <button key={p.label} type="button" onClick={p.apply} className="shrink-0 rounded-full border border-line bg-white px-3 py-1.5 text-sm font-semibold text-ink hover:border-brand-blue hover:bg-brand-blue-soft">
            {p.label}
          </button>
        ))}
        <Button variant="ghost" size="sm" onClick={reset}>
          <RotateCcw className="size-3.5" aria-hidden /> Reset
        </Button>
      </div>

      <div className="grid gap-5 xl:grid-cols-[380px_1fr]">
        <Card className="h-fit space-y-5 xl:sticky xl:top-24">
          <CardHeading icon={FlaskConical} title="Scenario" subtitle={`Baseline: ${data.basis}`} />
          {activeGoals.length > 0 && (
            <div className="space-y-1.5">
              <Label htmlFor="wf-goal">Goal to test against</Label>
              <select id="wf-goal" value={effectiveGoal ?? ""} onChange={(e) => setGoalId(e.target.value)} className="h-10 w-full rounded-lg border border-input bg-white px-3 text-sm">
                {activeGoals.map((x) => (
                  <option key={x.goal_id} value={x.goal_id}>
                    {x.title}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="space-y-4">
            <p className="text-xs font-bold uppercase tracking-wider text-ink-muted">Change spending by category</p>
            {categories.slice(0, 6).map((c) => (
              <SliderRow
                key={c.category}
                label={c.category}
                color={categoryColor(c.category)}
                value={changes[c.category] ?? 0}
                onChange={(v) => setChanges((prev) => ({ ...prev, [c.category]: v }))}
                hint={`Baseline ≈ ${taka(c.baseline)}/month`}
              />
            ))}
          </div>
          <div className="border-t border-line pt-4">
            <SliderRow label="All expenses" value={overall} onChange={setOverall} min={-30} max={50} hint="e.g. +20% for a festival month or price rises" />
          </div>
          <div className="space-y-1.5 border-t border-line pt-4">
            <Label htmlFor="wf-extra">Extra goal contributions (৳/month, whole group)</Label>
            <Input id="wf-extra" type="number" inputMode="numeric" min="0" step="100" placeholder="0" value={extra} onChange={(e) => setExtra(e.target.value)} />
          </div>
          <label className="flex items-start justify-between gap-3 border-t border-line pt-4 text-sm">
            <span>
              <span className="font-semibold text-ink">Redirect savings to the goal</span>
              <span className="block text-xs text-ink-muted">Money not spent is added to goal contributions.</span>
            </span>
            <Switch checked={redirect} onCheckedChange={setRedirect} />
          </label>
        </Card>

        <div className={cn("space-y-5 transition-opacity", isFetching && "opacity-70")} aria-live="polite">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="card-surface p-4">
              <p className="text-xs font-semibold text-ink-muted">Monthly spending · baseline</p>
              <p className="tabular mt-1 text-2xl font-extrabold text-ink">{taka(data.baseline_total)}</p>
            </div>
            <div className="card-surface p-4">
              <p className="text-xs font-semibold text-ink-muted">Monthly spending · scenario</p>
              <p className="tabular mt-1 flex items-center gap-2 text-2xl font-extrabold text-ink">
                <ArrowRight className="size-4 text-ink-muted" aria-hidden />
                {taka(data.scenario_total)}
              </p>
            </div>
            <div className={cn("rounded-2xl border p-4", saving > 0 ? "border-good/20 bg-good-soft" : saving < 0 ? "border-warn/20 bg-warn-soft" : "border-line bg-white")}>
              <p className="text-xs font-semibold text-ink-muted">{saving >= 0 ? "Projected savings" : "Extra spending"}</p>
              <p className={cn("tabular mt-1 text-2xl font-extrabold", saving > 0 ? "text-good" : saving < 0 ? "text-warn" : "text-ink")}>
                {taka(Math.abs(saving))}
                <span className="text-sm font-semibold">/month</span>
              </p>
            </div>
          </div>

          {g && (
            <Card>
              <CardHeading icon={Target} title={`Impact on “${g.title}”`} subtitle={`Target ${taka(g.target)} by ${fmtDateYear(g.deadline)}`} action={<ProvenanceBadge kind="prediction" />} />
              <div className="grid gap-3 sm:grid-cols-2">
                <Compare label="Projected at deadline" before={taka(g.baseline.projected)} after={taka(g.scenario.projected)} better={g.scenario.projected >= g.baseline.projected} />
                <Compare label="Progress vs target" before={`${g.baseline.on_track_pct.toFixed(0)}%`} after={`${g.scenario.on_track_pct.toFixed(0)}%`} better={g.scenario.on_track_pct >= g.baseline.on_track_pct} />
                <Compare
                  label="Vs target at deadline (− short, + surplus)"
                  before={g.baseline.gap > 0 ? `−${taka(g.baseline.gap)}` : `+${taka(-g.baseline.gap)}`}
                  after={g.scenario.gap > 0 ? `−${taka(g.scenario.gap)}` : `+${taka(-g.scenario.gap)}`}
                  better={g.scenario.gap <= g.baseline.gap}
                />
                <Compare label="Simulated likelihood" before={likelihood(g.baseline.likelihood_pct)} after={likelihood(g.scenario.likelihood_pct)} better={g.scenario.likelihood_pct >= g.baseline.likelihood_pct} />
              </div>
              <p className="mt-3 text-sm text-ink">
                Projected completion:{" "}
                <strong>{g.scenario.completion_date ? fmtDateYear(g.scenario.completion_date) : "—"}</strong>
                {g.baseline.completion_date && g.scenario.completion_date !== g.baseline.completion_date && (
                  <span className="text-ink-muted"> (baseline {fmtDateYear(g.baseline.completion_date)})</span>
                )}
                {" · "}
                Going to the goal: <strong>{taka(g.scenario.monthly_to_goal)}/month</strong>
              </p>
              {goalPlan && (
                <div className="mt-4">
                  <GoalProjectionChart
                    weekly={goalPlan.weekly_history}
                    startDate={goalPlan.start_date}
                    deadline={goalPlan.deadline}
                    saved={goalPlan.saved}
                    target={goalPlan.target}
                    rateWeekly={goalPlan.projection.rate_weekly}
                    daysLeft={goalPlan.days_left}
                    scenarioRateWeekly={g.scenario.monthly_to_goal / WEEKS_PER_MONTH}
                    height={220}
                  />
                </div>
              )}
            </Card>
          )}

          {data.recommendation && (
            <div className="flex items-start gap-3 rounded-2xl border border-brand-yellow-strong/50 bg-brand-yellow-soft p-4">
              <Lightbulb className="mt-0.5 size-5 shrink-0 text-brand-blue-deep" aria-hidden />
              <div>
                <p className="text-sm font-bold text-ink">Recommended adjustment</p>
                <p className="text-sm text-ink">{data.recommendation}</p>
              </div>
            </div>
          )}

          <div className="grid gap-5 lg:grid-cols-2">
            {data.pressure && (
              <Card>
                <CardHeading icon={Gauge} title="Financial pressure · next 7 days" />
                <p className="tabular text-2xl font-extrabold text-ink">{taka(data.pressure.next_7_days)}</p>
                <p className="text-sm text-ink-muted">vs a recent weekly average of {taka(data.pressure.recent_weekly_avg)}</p>
                <div className="mt-3 flex items-center gap-2">
                  <span
                    className={cn(
                      "rounded-full px-2.5 py-1 text-xs font-bold",
                      data.pressure.level === "high" ? "bg-bad-soft text-bad" : data.pressure.level === "moderate" ? "bg-warn-soft text-warn" : "bg-good-soft text-good",
                    )}
                  >
                    {data.pressure.level === "high" ? "▲ High" : data.pressure.level === "moderate" ? "● Moderate" : "▼ Low"} pressure
                  </span>
                  <span className="text-xs text-ink-muted">{Math.round(data.pressure.ratio * 100)}% of a typical week</span>
                </div>
                {data.pressure.pressure_days.length > 0 && <p className="mt-2 text-xs text-ink-muted">Peak days: {data.pressure.pressure_days.join(", ")}</p>}
              </Card>
            )}
            <Card>
              <CardHeading icon={Users} title="Monthly share per member" subtitle="Based on recent consumption shares" />
              <ul className="divide-y divide-line">
                {data.members.map((m) => (
                  <li key={m.member_id} className="flex items-center justify-between py-2 text-sm">
                    <span className="text-ink">
                      {m.name}
                      {m.is_you && <span className="text-ink-muted"> (you)</span>}
                    </span>
                    <span className="tabular text-ink">
                      {taka(m.baseline)} <ArrowRight className="inline size-3 text-ink-muted" aria-hidden /> <strong>{taka(m.scenario)}</strong>
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          <Card>
            <CardHeading title="By category" subtitle="Monthly, baseline → scenario" />
            <div className="overflow-x-auto">
              <table className="w-full min-w-[420px] text-sm">
                <thead>
                  <tr className="text-left text-xs text-ink-muted">
                    <th className="py-2 font-semibold">Category</th>
                    <th className="py-2 text-right font-semibold">Baseline</th>
                    <th className="py-2 text-right font-semibold">Scenario</th>
                    <th className="py-2 text-right font-semibold">Change</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {data.categories.map((c) => (
                    <tr key={c.category}>
                      <td className="py-2 font-medium text-ink">
                        <span className="mr-2 inline-block size-2.5 rounded-[3px] align-middle" style={{ background: categoryColor(c.category) }} aria-hidden />
                        {c.category}
                      </td>
                      <td className="tabular py-2 text-right text-ink">{taka(c.baseline)}</td>
                      <td className="tabular py-2 text-right font-semibold text-ink">{taka(c.scenario)}</td>
                      <td className={cn("tabular py-2 text-right font-semibold", c.change < 0 ? "text-good" : c.change > 0 ? "text-warn" : "text-ink-muted")}>
                        {c.change === 0 ? "—" : taka(c.change, { sign: true })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3 space-y-1">
              <p className="flex flex-wrap items-center gap-2 text-[11px] text-ink-muted">
                <ProvenanceBadge kind="assumption" withTooltip={false} /> {data.assumption}
              </p>
              <MethodNote>{data.method}</MethodNote>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Compare({ label, before, after, better }: { label: string; before: string; after: string; better: boolean }) {
  const same = before === after;
  return (
    <div className="rounded-xl bg-surface p-3">
      <p className="text-[11px] font-semibold text-ink-muted">{label}</p>
      <p className="tabular mt-1 flex flex-wrap items-center gap-1.5 text-sm text-ink-muted">
        {before}
        <ArrowRight className="size-3.5" aria-hidden />
        <span className={cn("text-lg font-extrabold", same ? "text-ink" : better ? "text-good" : "text-bad")}>{after}</span>
      </p>
    </div>
  );
}

export default function WhatIfPage() {
  return (
    <Suspense>
      <WhatIfInner />
    </Suspense>
  );
}
