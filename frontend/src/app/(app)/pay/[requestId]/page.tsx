"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CircleCheck, CircleX, Clock, Loader2, ShieldCheck, Target, Wallet } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { toast } from "sonner";

import { ErrorState, LinkButton, LoadingBlock } from "@/components/common/primitives";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { taka } from "@/lib/format";
import { keys } from "@/lib/queries";
import type { PaymentRequestInfo } from "@/lib/types";

const DONE: Record<string, { title: string; icon: typeof CircleCheck; cls: string }> = {
  paid: { title: "Payment confirmed by the wallet", icon: CircleCheck, cls: "bg-good-soft text-good" },
  cancelled: { title: "Payment declined", icon: CircleX, cls: "bg-bad-soft text-bad" },
  failed: { title: "Payment failed", icon: CircleX, cls: "bg-bad-soft text-bad" },
  expired: { title: "This payment request expired", icon: Clock, cls: "bg-warn-soft text-warn" },
};

function Checkout() {
  const { requestId } = useParams<{ requestId: string }>();
  const params = useSearchParams();
  const qc = useQueryClient();
  const ret = params.get("return");
  const { data: pr, isLoading, error, refetch } = useQuery({
    queryKey: ["payment-request", requestId],
    queryFn: () => api<PaymentRequestInfo>(`/wallet/payment-requests/${requestId}`),
  });
  const act = useMutation({
    mutationFn: (action: "approve" | "decline") =>
      api<PaymentRequestInfo>(`/wallet/payment-requests/${requestId}/sandbox`, { body: { action } }),
    onSuccess: (res) => {
      qc.setQueryData(["payment-request", requestId], res);
      qc.invalidateQueries({ queryKey: keys.group(res.group_id) });
      qc.invalidateQueries({ queryKey: keys.groups });
      qc.invalidateQueries({ queryKey: ["notifications"] });
      if (res.status === "paid") toast.success(`Paid ${taka(res.amount, { decimals: true })}. Recorded in ${res.group_name}.`);
    },
    onError: (e) => toast.error((e as Error).message),
  });

  if (isLoading) return <LoadingBlock rows={4} className="mx-auto max-w-md" />;
  if (error || !pr) return <ErrorState error={error} onRetry={() => refetch()} />;
  const back = ret && ret.startsWith("/g/") ? ret : pr.purpose === "goal_contribution" ? `/g/${pr.group_id}/goals/${pr.goal_id}` : `/g/${pr.group_id}/balances`;
  const done = DONE[pr.status];
  const to = pr.purpose === "settlement" ? pr.payee_name : pr.goal_title;

  return (
    <div className="mx-auto max-w-md">
      <Link href={back} className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-brand-blue hover:underline">
        <ArrowLeft className="size-4" aria-hidden /> Back to {pr.group_name}
      </Link>

      <section className="card-surface overflow-hidden" aria-labelledby="checkout-title">
        <div className="flex items-center justify-between gap-3 bg-brand-blue-deep px-5 py-3 text-white">
          <span className="flex items-center gap-2 text-sm font-bold">
            <Wallet className="size-4" aria-hidden /> Mobile wallet checkout
          </span>
          {pr.is_sandbox && <span className="rounded-full bg-brand-yellow px-2.5 py-0.5 text-xs font-bold text-ink">Sandbox</span>}
        </div>

        <div className="p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">
            {pr.is_request ? "Payment request" : pr.purpose === "settlement" ? "Send money" : "Save to shared goal"}
          </p>
          <h1 id="checkout-title" className="tabular mt-1 text-4xl font-extrabold text-ink">
            {taka(pr.amount, { decimals: true })}
          </h1>
          <dl className="mt-4 divide-y divide-line rounded-xl border border-line text-sm">
            <Row label="From">{pr.payer_name}</Row>
            <Row label="To">
              <span className="inline-flex items-center gap-1.5">
                {pr.purpose === "goal_contribution" && <Target className="size-4 text-brand-blue" aria-hidden />}
                {to}
              </span>
            </Row>
            <Row label="Group">{pr.group_name}</Row>
            <Row label="Reference">
              <span className="font-mono">{pr.reference}</span>
            </Row>
            {pr.provider_txn_id && (
              <Row label="Wallet TrxID">
                <span className="font-mono">{pr.provider_txn_id}</span>
              </Row>
            )}
          </dl>

          {done ? (
            <div className={`mt-4 flex items-start gap-2.5 rounded-xl p-3 ${done.cls}`} role="status">
              <done.icon className="mt-0.5 size-5 shrink-0" aria-hidden />
              <div className="text-sm">
                <p className="font-bold">{done.title}</p>
                {pr.status === "paid" && (
                  <p className="text-ink">
                    Recorded as {pr.purpose === "settlement" ? "a settlement" : "a goal contribution"} at {pr.completed_at ? new Date(pr.completed_at).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" }) : "now"}.
                    Balances and projections are already updated.
                  </p>
                )}
                {pr.status !== "paid" && <p className="text-ink">Nothing was recorded and no money moved.</p>}
              </div>
            </div>
          ) : pr.can_approve ? (
            <>
              {pr.approve_as === "simulate_friend" && (
                <p className="mt-4 rounded-xl bg-brand-yellow-soft p-3 text-sm text-ink">
                  {pr.payer_name} isn&apos;t on GroupWise. With a live wallet integration this request would arrive in{" "}
                  {pr.payer_name}&apos;s wallet app. In the sandbox you can play their part.
                </p>
              )}
              <div className="mt-5 grid grid-cols-2 gap-2">
                <Button variant="outline" disabled={act.isPending} onClick={() => act.mutate("decline")}>
                  Decline
                </Button>
                <Button variant="blue" disabled={act.isPending} onClick={() => act.mutate("approve")}>
                  {act.isPending ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <ShieldCheck className="size-4" aria-hidden />}
                  {pr.approve_as === "simulate_friend" ? `${pr.payer_name} pays` : "Approve"}
                </Button>
              </div>
            </>
          ) : (
            <p className="mt-4 rounded-xl bg-muted p-3 text-sm text-ink" role="status">
              Waiting for {pr.payer_name} to approve this payment in their wallet.
            </p>
          )}

          {done && (
            <LinkButton href={back} className="mt-4 w-full" variant={pr.status === "paid" ? "default" : "outline"}>
              {pr.purpose === "settlement" ? "Back to balances" : "Back to the goal"}
            </LinkButton>
          )}
        </div>
      </section>

      <div className="mt-4 rounded-xl border border-line bg-white p-4 text-xs leading-relaxed text-ink-muted">
        <p className="mb-1 font-bold text-ink">How this works</p>
        GroupWise creates a payment request with a reference. The person approves it in their wallet app. The wallet sends
        GroupWise a signed confirmation (HMAC-SHA256), and only then is the payment recorded. Repeated or tampered
        confirmations are rejected. {pr.is_sandbox && "This sandbox plays the wallet's part, so no real money moves."}
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 px-3 py-2.5">
      <dt className="text-ink-muted">{label}</dt>
      <dd className="min-w-0 truncate text-right font-semibold text-ink">{children}</dd>
    </div>
  );
}

export default function PayPage() {
  return (
    <Suspense>
      <Checkout />
    </Suspense>
  );
}
