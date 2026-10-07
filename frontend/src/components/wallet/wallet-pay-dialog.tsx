"use client";

import { Loader2, Wallet } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import type { PaymentRequestInfo } from "@/lib/types";

interface Props {
  groupId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  purpose: "settlement" | "goal_contribution";
  payeeMemberId?: string;
  payeeName?: string;
  /** Set to request money from someone else (they pay you) */
  payerMemberId?: string;
  payerName?: string;
  goalId?: string;
  goalTitle?: string;
  /** Suggested amount in paisa */
  defaultAmount?: number;
  /** Where the checkout page sends the person afterwards */
  returnTo: string;
}

/** Creates a wallet payment request and opens the wallet checkout. Nothing is recorded until the wallet confirms. */
export function WalletPayDialog({ groupId, open, onOpenChange, purpose, payeeMemberId, payeeName, payerMemberId, payerName, goalId, goalTitle, defaultAmount, returnTo }: Props) {
  const isRequest = !!payerMemberId;
  const router = useRouter();
  const [amount, setAmount] = useState(defaultAmount ? (defaultAmount / 100).toFixed(2) : "");
  const [busy, setBusy] = useState(false);

  async function start(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const pr = await api<PaymentRequestInfo>(`/groups/${groupId}/wallet/payment-requests`, {
        body: { purpose, amount: Number(amount), payee_member_id: payeeMemberId, payer_member_id: payerMemberId, goal_id: goalId },
      });
      router.push(`${pr.checkout_url}?return=${encodeURIComponent(returnTo)}`);
    } catch (err) {
      toast.error((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <form onSubmit={start} className="space-y-4">
          <DialogHeader>
            <DialogTitle>
              {isRequest ? `Request ${payerName} to pay you` : purpose === "settlement" ? `Pay ${payeeName} via wallet` : `Save to “${goalTitle}” via wallet`}
            </DialogTitle>
            <DialogDescription>
              {isRequest
                ? `${payerName} gets a payment request in their wallet. When they approve it, the wallet confirms and GroupWise records the payment.`
                : "Your mobile wallet moves the money. GroupWise records it only after the wallet confirms the payment, so balances never drift from what really happened."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="w-amount">Amount (৳)</Label>
            <Input id="w-amount" type="number" inputMode="decimal" min="1" step="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
          <p className="rounded-lg bg-brand-yellow-soft px-3 py-2 text-xs text-ink">
            Prototype: payments go to a <strong>wallet sandbox</strong> that simulates the MFS checkout. No real money moves.
          </p>
          <DialogFooter>
            <Button type="submit" variant="blue" disabled={busy || !(Number(amount) > 0)}>
              {busy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Wallet className="size-4" aria-hidden />} {isRequest ? "Send request" : "Continue to wallet"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
