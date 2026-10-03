"use client";

import { ArrowLeft, CircleCheck, FlaskConical, Loader2, PiggyBank, Plus, Target, TriangleAlert, Users } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { MethodNote, ProvenanceBadge } from "@/components/ai/labels";
import { GoalProjectionChart } from "@/components/charts/charts";
import { Card, CardHeading, ErrorState, LinkButton, LoadingBlock, MemberAvatar } from "@/components/common/primitives";
import { GOAL_STATUS, GoalBar } from "@/components/goals/goal-mini";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { fmtDate, fmtDateYear, likelihood, taka } from "@/lib/format";
import { useGoal, useGroup, useInvalidateGroup } from "@/lib/queries";
import { cn } from "@/lib/utils";

export default function GoalDetailPage() {
  const { groupId, goalId } = useParams<{ groupId: string; goalId: string }>();
  const { data: g, isLoading, error, refetch } = useGoal(groupId, goalId);
  const { data: group } = useGroup(groupId);
  const invalidate = useInvalidateGroup(groupId);
  const [open, setOpen] = useState(false);
  const [member, setMember] = useState("");
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);

  async function contribute(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api(`/groups/${groupId}/goals/${goalId}/contributions`, { body: { member_id: member || group?.my_member_id, amount: Number(amount) } });
      invalidate();
      toast.success(`Added ${taka(Number(amount) * 100)} to the goal. Projection updated.`);
      setOpen(false);
      setAmount("");
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (isLoading) return <LoadingBlock rows={4} />;
  if (error || !g) return <ErrorState error={error} onRetry={() => refetch()} />;
  const p = g.projection;
  const st = GOAL_STATUS[g.status];
  const good = g.status === "on_track" || g.status === "achieved";
  const reduce = g.scenarios.find((s) => s.key === "reduce_dining");

  return (
    <div>
      <Link href={`/g/${groupId}/goals`} className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-brand-blue hover:underline">
        <ArrowLeft className="size-4" aria-hidden /> All goals
      </Link>
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-[0.1em] text-brand-blue">Goal planner</p>
          <h1 className="flex flex-wrap items-center gap-3 text-2xl font-extrabold text-ink sm:text-[28px]">
            {g.title}
            <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold", st.cls)}>
              {good ? <CircleCheck className="size-3.5" aria-hidden /> : <TriangleAlert className="size-3.5" aria-hidden />}
              {st.label}
            </span>
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            Target {taka(g.target)} by {fmtDateYear(g.deadline)} · {g.days_left > 0 ? `${g.days_left} days left` : "deadline reached"}
            {g.description ? ` · ${g.description}` : ""}
          </p>
        </div>
        <div className="flex gap-2">
          <LinkButton href={`/g/${groupId}/what-if?goal=${goalId}${reduce ? `&cat=Food&pct=-${Math.min(40, Math.ceil((reduce.reduction_pct ?? 10) / 5) * 5)}` : ""}`} variant="outline">
            <FlaskConical className="size-4" aria-hidden /> What-If
          </LinkButton>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger render={<Button />}>
              <Plus className="size-4" aria-hidden /> Add contribution
            </DialogTrigger>
            <DialogContent className="sm:max-w-sm">
              <form onSubmit={contribute} className="space-y-4">
                <DialogHeader>
                  <DialogTitle>Add a contribution</DialogTitle>
                  <DialogDescription>Record money put aside for “{g.title}”.</DialogDescription>
                </DialogHeader>
                <div className="space-y-1.5">
                  <Label htmlFor="c-member">Contributed by</Label>
                  <select
                    id="c-member"
                    value={member || group?.my_member_id || ""}
                    onChange={(e) => setMember(e.target.value)}
                    className="h-10 w-full rounded-lg border border-input bg-white px-3 text-sm"
                  >
                    {group?.members_detail
                      .filter((m) => m.status === "active")
                      .map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.display_name}
                          {m.is_you ? " (you)" : ""}
                        </option>
                      ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="c-amount">Amount (৳)</Label>
                  <Input id="c-amount" type="number" inputMode="decimal" min="1" required value={amount} onChange={(e) => setAmount(e.target.value)} />
                </div>
                <DialogFooter>
                  <Button type="submit" disabled={busy || !(Number(amount) > 0)}>
                    {busy && <Loader2 className="size-4 animate-spin" aria-hidden />} Add contribution
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <div className="space-y-5">
          <Card>
            <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Metric label="Saved so far" value={taka(g.saved)} sub={`${g.progress_pct.toFixed(0)}% of target`} kind="fact" />
              <Metric label="Projected at deadline" value={taka(p.projected_amount)} sub={`${p.on_track_pct.toFixed(0)}% of target`} kind="prediction" />
              <Metric label={p.gap > 0 ? "Projected shortfall" : "Projected surplus"} value={taka(Math.abs(p.gap))} sub="at current pace" kind="prediction" />
              <Metric label="Simulated likelihood" value={likelihood(p.likelihood_pct)} sub={`${p.simulations.toLocaleString()} simulations`} kind="prediction" />
            </div>
            <GoalBar goal={g} />
            <p className="mt-4 rounded-xl bg-brand-blue-softer p-3 text-sm text-ink">{g.explanation}</p>
          </Card>

          <Card>
            <CardHeading icon={Target} title="Projection" subtitle="Solid: actual contributions · dashed: projected at the current pace" />
            <GoalProjectionChart weekly={g.weekly_history} startDate={g.start_date} deadline={g.deadline} saved={g.saved} target={g.target} rateWeekly={p.rate_weekly} daysLeft={g.days_left} />
            <p className="mt-2 text-xs text-ink-muted">
              Simulated range at the deadline (10th–90th percentile): {taka(p.simulated_range.p10)} – {taka(p.simulated_range.p90)}.
            </p>
            <MethodNote>{g.method}. Each simulated future re-samples the group&apos;s own weekly contribution history.</MethodNote>
          </Card>

          {g.scenarios.length > 0 && (
            <Card>
              <CardHeading icon={FlaskConical} title="What would close the gap" subtitle="Options computed from your group's data — you choose" action={<ProvenanceBadge kind="recommendation" />} />
              <ul className="space-y-3">
                {g.scenarios.map((s) => (
                  <li key={s.key} className="rounded-xl border border-line p-3">
                    <p className="text-sm font-bold text-ink">{s.label}</p>
                    <p className="mt-0.5 text-sm text-ink">{s.text}</p>
                    {s.assumption && <p className="mt-1 text-[11px] text-ink-muted">Assumption: {s.assumption}</p>}
                    {s.key === "reduce_dining" && (
                      <Link href={`/g/${groupId}/what-if?goal=${goalId}&cat=Food&pct=-${Math.min(40, Math.ceil((s.reduction_pct ?? 10) / 5) * 5)}`} className="mt-2 inline-block text-sm font-semibold text-brand-blue hover:underline">
                        Simulate it in What-If →
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>

        <div className="space-y-5">
          <Card>
            <CardHeading icon={PiggyBank} title="Pace" />
            <dl className="space-y-2 text-sm">
              <Row label="Current pace" value={`${taka(p.rate_monthly)}/month`} />
              <Row label="Last 4 weeks" value={`${taka(p.recent_rate_weekly)}/week`} />
              <Row label="Needed from now" value={`${taka(p.required_monthly)}/month`} strong />
              {p.gap_monthly > 0 && <Row label="Monthly gap" value={`${taka(p.gap_monthly)}/month`} strong />}
              <Row label="Done at current pace" value={p.completion_date_at_current_rate ? fmtDateYear(p.completion_date_at_current_rate) : "—"} />
            </dl>
          </Card>
          <Card>
            <CardHeading icon={Users} title="Contributors" />
            <ul className="space-y-2">
              {g.contributors.map((c) => (
                <li key={c.member_id} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <MemberAvatar name={c.name} size={26} color={group?.members_detail.find((m) => m.id === c.member_id)?.avatar_color} />
                    {c.name}
                  </span>
                  <span className="tabular font-semibold text-ink">
                    {taka(c.amount)} <span className="text-xs font-normal text-ink-muted">{c.share_pct.toFixed(0)}%</span>
                  </span>
                </li>
              ))}
              {!g.contributors.length && <p className="text-sm text-ink-muted">No contributions yet.</p>}
            </ul>
          </Card>
          {!!g.recent_contributions?.length && (
            <Card>
              <CardHeading title="Recent contributions" />
              <ul className="divide-y divide-line">
                {g.recent_contributions.slice(0, 8).map((c) => (
                  <li key={c.id} className="flex justify-between py-2 text-sm">
                    <span className="text-ink">
                      {c.name} <span className="text-xs text-ink-muted">· {fmtDate(c.occurred_at)}</span>
                    </span>
                    <span className="tabular font-semibold text-ink">{taka(c.amount)}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value, sub, kind }: { label: string; value: string; sub: string; kind: "fact" | "prediction" }) {
  return (
    <div className="rounded-xl bg-surface p-3">
      <p className="text-[11px] font-semibold text-ink-muted">{label}</p>
      <p className="tabular mt-0.5 text-xl font-extrabold text-ink">{value}</p>
      <p className="text-[11px] text-ink-muted">{sub}</p>
      <ProvenanceBadge kind={kind} className="mt-1.5" withTooltip={false} />
    </div>
  );
}

function Row({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-ink-muted">{label}</dt>
      <dd className={cn("tabular text-right text-ink", strong && "font-bold")}>{value}</dd>
    </div>
  );
}
