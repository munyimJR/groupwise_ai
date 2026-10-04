"use client";

import { ArrowLeftRight, Clock, Lightbulb, Scale, ShieldCheck, UserRound } from "lucide-react";
import { useParams } from "next/navigation";

import { MethodNote, ProvenanceBadge } from "@/components/ai/labels";
import { LegendRow } from "@/components/charts/charts";
import { Card, CardHeading, EmptyState, ErrorState, LoadingBlock, MemberAvatar, PageHeader, StatTile } from "@/components/common/primitives";
import { taka } from "@/lib/format";
import { useDynamics } from "@/lib/queries";
import { cn } from "@/lib/utils";

export default function DynamicsPage() {
  const { groupId } = useParams<{ groupId: string }>();
  const { data, isLoading, error, refetch } = useDynamics(groupId);

  if (isLoading) return <LoadingBlock rows={5} />;
  if (error || !data) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (data.status !== "ok")
    return (
      <div>
        <PageHeader eyebrow="Behaviour" title="Group financial dynamics" />
        <EmptyState icon={ArrowLeftRight} title="Not enough activity yet" body={data.message} />
      </div>
    );

  const members = data.members!;
  const cbi = data.contribution_balance_index!;
  const maxShare = Math.max(...members.map((m) => Math.max(m.paid_share_pct, m.consumed_share_pct)), 1);

  return (
    <div>
      <PageHeader
        eyebrow="Behaviour"
        title="Group financial dynamics"
        subtitle="How financial responsibility is distributed in the group — who fronts the money, and how long reimbursements take."
      />
      <p className="mb-5 flex items-start gap-2 rounded-xl border border-good/20 bg-good-soft px-3 py-2.5 text-sm text-good">
        <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden />
        {data.responsible_note}
      </p>

      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile icon={Scale} label="Contribution balance index" value={cbi.toFixed(2)} sub={<span className="text-xs text-ink-muted">1.00 = everyone fronts money in proportion to use</span>} accent />
        <StatTile icon={Clock} label="Median settle time" value={data.median_settle_days !== null && data.median_settle_days !== undefined ? `${data.median_settle_days} days` : "—"} sub={<span className="text-xs text-ink-muted">Until a balance owed is cleared</span>} />
        <StatTile icon={ArrowLeftRight} label="Analysed" value={taka(data.total!)} sub={<span className="text-xs text-ink-muted">{data.basis}</span>} />
        <StatTile icon={UserRound} label="High-value expense" value={`≥ ${taka(data.high_value_threshold!)}`} sub={<span className="text-xs text-ink-muted">Top quarter by amount</span>} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
        <Card>
          <CardHeading icon={ArrowLeftRight} title="Paid upfront vs. consumed" subtitle={`Last ${data.window_days} days`} action={<ProvenanceBadge kind="fact" />} />
          <LegendRow items={[{ label: "Share of upfront payments", color: "#0057b8" }, { label: "Share of what the group consumed", color: "#3987e5" }]} />
          <ul className="mt-4 space-y-4">
            {members.map((m) => (
              <li key={m.member_id}>
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2 text-sm font-semibold text-ink">
                    <MemberAvatar name={m.name} color={m.color} size={26} />
                    {m.name}
                    {m.is_you && <span className="font-normal text-ink-muted">(you)</span>}
                  </span>
                  <span className={cn("tabular rounded-md px-2 py-0.5 text-xs font-bold", m.imbalance_pct >= 10 ? "bg-warn-soft text-warn" : m.imbalance_pct <= -10 ? "bg-brand-blue-soft text-brand-blue-deep" : "bg-muted text-ink-muted")}>
                    {m.imbalance_pct > 0 ? "+" : ""}
                    {m.imbalance_pct.toFixed(0)} pts {m.imbalance_pct >= 10 ? "fronts more" : m.imbalance_pct <= -10 ? "fronts less" : "balanced"}
                  </span>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-[#f1f4f8]">
                      <div className="h-full rounded-full bg-brand-blue" style={{ width: `${(m.paid_share_pct / maxShare) * 100}%` }} />
                    </div>
                    <span className="tabular w-24 text-right text-xs text-ink">paid {m.paid_share_pct.toFixed(0)}%</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-[#f1f4f8]">
                      <div className="h-full rounded-full bg-[#3987e5]" style={{ width: `${(m.consumed_share_pct / maxShare) * 100}%` }} />
                    </div>
                    <span className="tabular w-24 text-right text-xs text-ink">used {m.consumed_share_pct.toFixed(0)}%</span>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        <div className="space-y-5">
          {data.insights!.map((ins) => (
            <Card key={ins.kind} className={ins.severity === "warning" ? "border-warn/30" : ins.severity === "positive" ? "border-good/30" : ""}>
              <CardHeading icon={Lightbulb} title={ins.title} action={<ProvenanceBadge kind="fact" />} />
              <p className="text-sm text-ink">{ins.text}</p>
            </Card>
          ))}
          {data.recommendations!.map((r) => (
            <div key={r.key} className="rounded-2xl border border-brand-yellow-strong/50 bg-brand-yellow-soft p-4">
              <div className="mb-1 flex items-center gap-2">
                <ProvenanceBadge kind="recommendation" />
              </div>
              <p className="font-bold text-ink">{r.title}</p>
              <p className="mt-1 text-sm text-ink">{r.text}</p>
              {r.suggested_next_payer && (
                <p className="mt-2 text-sm text-ink">
                  Suggested next payer for a big expense: <strong>{r.suggested_next_payer.name}</strong>
                </p>
              )}
            </div>
          ))}
        </div>
      </div>

      <Card className="mt-5">
        <CardHeading icon={Clock} title="Reimbursement timing" subtitle="Amount-weighted days; still-open balances count at their current age" />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="text-left text-xs text-ink-muted">
                <th className="py-2 font-semibold">Member</th>
                <th className="py-2 text-right font-semibold">Paid upfront</th>
                <th className="py-2 text-right font-semibold">High-value share</th>
                <th className="py-2 text-right font-semibold">Avg days to settle what they owe</th>
                <th className="py-2 text-right font-semibold">Avg days waiting to be repaid</th>
                <th className="py-2 text-right font-semibold">Open balance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {members.map((m) => (
                <tr key={m.member_id}>
                  <td className="py-2.5 font-medium text-ink">
                    {m.name}
                    {m.is_you && <span className="text-ink-muted"> (you)</span>}
                  </td>
                  <td className="tabular py-2.5 text-right text-ink">
                    {taka(m.paid)} <span className="text-xs text-ink-muted">· {m.paid_count}×</span>
                  </td>
                  <td className="tabular py-2.5 text-right text-ink">{m.high_value_paid_share_pct.toFixed(0)}%</td>
                  <td className="tabular py-2.5 text-right text-ink">{m.avg_settle_days ?? "—"}</td>
                  <td className="tabular py-2.5 text-right text-ink">{m.avg_wait_days ?? "—"}</td>
                  <td className="tabular py-2.5 text-right text-ink">
                    {m.open_debt ? `${taka(m.open_debt)} owed${m.oldest_open_debt_days ? ` · ${m.oldest_open_debt_days}d` : ""}` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <MethodNote>{data.method}. Contribution balance index = 1 − ½·Σ|paid share − consumed share|.</MethodNote>
      </Card>
    </div>
  );
}
