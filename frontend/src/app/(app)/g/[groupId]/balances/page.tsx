"use client";

import { ArrowRight, CheckCircle2, Loader2, Scale, Shuffle, Wallet } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ProvenanceBadge } from "@/components/ai/labels";
import { BalanceTag, Card, CardHeading, EmptyState, ErrorState, LoadingBlock, MemberAvatar, PageHeader } from "@/components/common/primitives";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { WalletPayDialog } from "@/components/wallet/wallet-pay-dialog";
import { api } from "@/lib/api";
import { fmtDate, taka } from "@/lib/format";
import { useBalances, useInvalidateGroup, useSettlements } from "@/lib/queries";
import type { Balances } from "@/lib/types";
import { cn } from "@/lib/utils";

type Transfer = Balances["transfers"][number];

export default function BalancesPage() {
  const { groupId } = useParams<{ groupId: string }>();
  const { data, isLoading, error, refetch } = useBalances(groupId);
  const { data: history } = useSettlements(groupId);
  const invalidate = useInvalidateGroup(groupId);
  const [pending, setPending] = useState<Transfer | null>(null);
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [walletPay, setWalletPay] = useState<Transfer | null>(null);

  async function record() {
    if (!pending) return;
    setBusy(true);
    try {
      await api(`/groups/${groupId}/settlements`, {
        body: { from_member_id: pending.from_member_id, to_member_id: pending.to_member_id, amount: Number(amount), note: "Recorded in GroupWise" },
      });
      invalidate();
      toast.success(`Recorded: ${pending.from_name} paid ${pending.to_name} ${taka(Number(amount) * 100, { decimals: true })}`);
      setPending(null);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (isLoading) return <LoadingBlock rows={5} />;
  if (error || !data) return <ErrorState error={error} onRetry={() => refetch()} />;
  const maxAbs = Math.max(...data.members.map((m) => Math.abs(m.net)), 1);

  return (
    <div>
      <PageHeader eyebrow="Balances" title="Who owes whom" subtitle="Exact balances from every expense and settlement, and the fewest payments needed to clear them." />
      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeading icon={Scale} title="Net balances" subtitle={`Total spent so far: ${taka(data.total_spent)}`} action={<ProvenanceBadge kind="deterministic" />} />
          <ul className="space-y-3">
            {data.members.map((m) => (
              <li key={m.member_id} className="rounded-xl border border-line p-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="flex min-w-0 items-center gap-2.5">
                    <MemberAvatar name={m.name} color={m.color} size={34} />
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-bold text-ink">
                        {m.name}
                        {m.is_you && <span className="font-medium text-ink-muted"> (you)</span>}
                      </span>
                      <span className="block text-xs text-ink-muted">
                        paid {taka(m.paid)} · share {taka(m.share)}
                      </span>
                    </span>
                  </span>
                  <BalanceTag net={m.net} size="sm" you={m.is_you} />
                </div>
                <div className="mt-2 grid grid-cols-2 gap-1" aria-hidden>
                  <div className="flex justify-end">
                    {m.net < 0 && <div className="h-1.5 rounded-l-full bg-bad/70" style={{ width: `${(Math.abs(m.net) / maxAbs) * 100}%` }} />}
                  </div>
                  <div>{m.net > 0 && <div className="h-1.5 rounded-r-full bg-good/70" style={{ width: `${(m.net / maxAbs) * 100}%` }} />}</div>
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-ink-muted">Net = paid upfront − your share + settlements sent − settlements received. Balances always sum to zero.</p>
        </Card>

        <div className="space-y-5">
          <Card>
            <CardHeading icon={Shuffle} title="Settle-up plan" subtitle="Debt simplification — a deterministic algorithm, not AI" />
            {data.transfers.length === 0 ? (
              <EmptyState icon={CheckCircle2} title="Everyone is settled up" body="No payments needed right now." />
            ) : (
              <>
                <div className="mb-4 flex items-center gap-3 rounded-xl bg-brand-yellow-soft p-3">
                  <span className="tabular text-3xl font-extrabold text-ink">{data.simplified_transfer_count}</span>
                  <p className="text-sm text-ink">
                    payment{data.simplified_transfer_count === 1 ? "" : "s"} clear{data.simplified_transfer_count === 1 ? "s" : ""} {taka(data.outstanding_total)} —
                    instead of <strong>{data.naive_transfer_count}</strong> if everyone paid each person back separately.
                  </p>
                </div>
                <ul className="space-y-2">
                  {data.transfers.map((t) => (
                    <li key={`${t.from_member_id}-${t.to_member_id}`} className={cn("flex flex-wrap items-center gap-3 rounded-xl border p-3", t.involves_you ? "border-brand-blue/30 bg-brand-blue-softer" : "border-line")}>
                      <span className="flex min-w-0 flex-1 items-center gap-2 text-sm">
                        <strong className="truncate text-ink">{t.from_member_id === data.my_member_id ? "You" : t.from_name}</strong>
                        <ArrowRight className="size-4 shrink-0 text-ink-muted" aria-label="pays" />
                        <strong className="truncate text-ink">{t.to_member_id === data.my_member_id ? "you" : t.to_name}</strong>
                      </span>
                      <span className="tabular font-extrabold text-ink">{taka(t.amount, { decimals: true })}</span>
                      {t.from_member_id === data.my_member_id && (
                        <Button size="sm" variant="blue" onClick={() => setWalletPay(t)}>
                          <Wallet className="size-3.5" aria-hidden /> Pay via wallet
                        </Button>
                      )}
                      {t.to_member_id === data.my_member_id && (
                        <Button size="sm" variant="blue" onClick={() => setWalletPay(t)}>
                          <Wallet className="size-3.5" aria-hidden /> Request via wallet
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setPending(t);
                          setAmount((t.amount / 100).toFixed(2));
                        }}
                      >
                        {t.involves_you ? "Record" : "Record payment"}
                      </Button>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </Card>

          <Card>
            <CardHeading title="Settlement history" />
            {!history?.length ? (
              <p className="text-sm text-ink-muted">No settlements recorded yet.</p>
            ) : (
              <ul className="divide-y divide-line">
                {history.slice(0, 10).map((s) => (
                  <li key={s.id} className="flex items-center justify-between py-2 text-sm">
                    <span className="text-ink">
                      {s.from_name} → {s.to_name}
                      <span className="block text-xs text-ink-muted">{fmtDate(s.occurred_at)}</span>
                    </span>
                    <span className="tabular font-semibold text-ink">{taka(s.amount, { decimals: true })}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>

      {walletPay && (
        <WalletPayDialog
          key={`${walletPay.to_member_id}-${walletPay.amount}`}
          groupId={groupId}
          open={!!walletPay}
          onOpenChange={(o) => !o && setWalletPay(null)}
          purpose="settlement"
          payeeMemberId={walletPay.to_member_id}
          payeeName={walletPay.to_name}
          payerMemberId={walletPay.from_member_id === data.my_member_id ? undefined : walletPay.from_member_id}
          payerName={walletPay.from_name}
          defaultAmount={walletPay.amount}
          returnTo={`/g/${groupId}/balances`}
        />
      )}

      <Dialog open={!!pending} onOpenChange={(o) => !o && setPending(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Record a payment</DialogTitle>
            <DialogDescription>
              {pending?.from_name} paid {pending?.to_name}. GroupWise records it — the money itself moves outside the app.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="s-amount">Amount (৳)</Label>
            <Input id="s-amount" type="number" inputMode="decimal" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
          <DialogFooter>
            <Button onClick={record} disabled={busy || !(Number(amount) > 0)}>
              {busy && <Loader2 className="size-4 animate-spin" aria-hidden />} Confirm payment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
