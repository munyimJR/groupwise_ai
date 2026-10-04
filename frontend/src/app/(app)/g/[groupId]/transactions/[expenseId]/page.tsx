"use client";

import { ArrowLeft, Loader2, Pencil, Sparkles, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ProvenanceBadge } from "@/components/ai/labels";
import { Card, CardHeading, ErrorState, LoadingBlock, MemberAvatar } from "@/components/common/primitives";
import { AnomalyPanel } from "@/components/expenses/anomaly-panel";
import { CategorySelect } from "@/components/expenses/category-select";
import { CategoryIcon } from "@/components/expenses/expense-row";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { fmtTime, fmtWeekday, taka } from "@/lib/format";
import { useExpense, useGroup, useInvalidateGroup } from "@/lib/queries";
import { selectClass } from "@/lib/utils";
import type { Expense } from "@/lib/types";

const METHOD_LABEL: Record<string, string> = { mobile_wallet: "Mobile wallet", cash: "Cash", card: "Card", bank_transfer: "Bank transfer" };
const SOURCE_LABEL = { ai: "Suggested by AI", user: "Chosen by a group member", feedback: "Learned from an earlier correction" } as const;

export default function ExpenseDetailPage() {
  const { groupId, expenseId } = useParams<{ groupId: string; expenseId: string }>();
  const router = useRouter();
  const invalidate = useInvalidateGroup(groupId);
  const { data: e, isLoading, error, refetch } = useExpense(groupId, expenseId);
  const { data: group } = useGroup(groupId);
  const [busy, setBusy] = useState(false);
  const [editingCat, setEditingCat] = useState(false);
  const [sub, setSub] = useState<string>("");

  async function review(action: "valid" | "dismiss" | "reopen") {
    setBusy(true);
    try {
      await api<Expense>(`/groups/${groupId}/expenses/${expenseId}/review`, { body: { action } });
      invalidate();
      toast.success(action === "valid" ? "Marked as valid — thanks for reviewing." : action === "dismiss" ? "Alert dismissed." : "Review reopened.");
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function saveCategory() {
    setBusy(true);
    try {
      const res = await api<{ message: string }>(`/groups/${groupId}/expenses/${expenseId}/category`, { body: { subcategory: sub } });
      invalidate();
      toast.success(res.message);
      setEditingCat(false);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      await api(`/groups/${groupId}/expenses/${expenseId}`, { method: "DELETE" });
      invalidate();
      toast.success("Expense deleted. Balances updated.");
      router.push(`/g/${groupId}/transactions`);
    } catch (err) {
      toast.error((err as Error).message);
      setBusy(false);
    }
  }

  if (isLoading) return <LoadingBlock rows={4} />;
  if (error || !e) return <ErrorState error={error} onRetry={() => refetch()} />;

  const score = e.anomaly.score ?? 0;
  const showAnomaly = e.anomaly.status !== "none" || score >= 0.6;

  return (
    <div className="mx-auto max-w-4xl">
      <Link href={`/g/${groupId}/transactions`} className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-brand-blue hover:underline">
        <ArrowLeft className="size-4" aria-hidden /> All transactions
      </Link>

      <Card className="mb-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <CategoryIcon category={e.category} size={52} />
            <div className="min-w-0">
              <h1 className="text-xl font-extrabold text-ink">{e.description}</h1>
              <p className="text-sm text-ink-muted">
                {fmtWeekday(e.occurred_at)}, {fmtTime(e.occurred_at)} · {METHOD_LABEL[e.payment_method] ?? e.payment_method}
                {e.merchant ? ` · ${e.merchant}` : ""}
              </p>
            </div>
          </div>
          <p className="tabular text-[34px] font-extrabold text-ink">{taka(e.amount, { decimals: true })}</p>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <EditDialog expense={e} groupId={groupId} members={group?.members_detail.filter((m) => m.status === "active") ?? []} onSaved={invalidate} />
          <Dialog>
            <DialogTrigger render={<Button variant="ghost" size="sm" className="text-bad hover:bg-bad-soft hover:text-bad" />}>
              <Trash2 className="size-4" aria-hidden /> Delete
            </DialogTrigger>
            <DialogContent className="sm:max-w-sm">
              <DialogHeader>
                <DialogTitle>Delete this expense?</DialogTitle>
                <DialogDescription>Balances, insights and forecasts will be recalculated without it.</DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="destructive" onClick={remove} disabled={busy}>
                  Delete expense
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="space-y-5">
          {showAnomaly && <AnomalyPanel score={score} status={e.anomaly.status} reasons={e.anomaly.reasons ?? []} onAction={review} busy={busy} />}

          <Card>
            <CardHeading icon={Sparkles} title="Category" subtitle={SOURCE_LABEL[e.category_source]} action={<ProvenanceBadge kind={e.category_source === "ai" ? "prediction" : "fact"} />} />
            {editingCat ? (
              <div className="space-y-3">
                <CategorySelect value={sub || e.subcategory} onChange={setSub} />
                <div className="flex gap-2">
                  <Button size="sm" variant="blue" onClick={saveCategory} disabled={busy || !sub || sub === e.subcategory}>
                    {busy && <Loader2 className="size-3.5 animate-spin" aria-hidden />} Save correction
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setEditingCat(false)}>
                    Cancel
                  </Button>
                </div>
                <p className="text-xs text-ink-muted">Corrections are stored as feedback and reused for similar expenses in this group.</p>
              </div>
            ) : (
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-bold text-ink">
                    {e.category} › {e.subcategory_label}
                  </p>
                  <p className="text-sm text-ink-muted">
                    {e.expense_type}
                    {e.category_confidence !== null && e.category_source === "ai" ? ` · model confidence ${Math.round(e.category_confidence * 100)}%` : ""}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setSub(e.subcategory);
                    setEditingCat(true);
                  }}
                >
                  Correct
                </Button>
              </div>
            )}
          </Card>
        </div>

        <Card>
          <CardHeading title="Split" subtitle={`Equal split between ${e.participants?.length ?? 0} · exact to the paisa`} action={<ProvenanceBadge kind="deterministic" />} />
          <ul className="divide-y divide-line">
            {e.participants?.map((p) => (
              <li key={p.member_id} className="flex items-center justify-between py-2.5">
                <span className="flex items-center gap-2.5 text-sm font-medium text-ink">
                  <MemberAvatar name={p.name} size={30} color={group?.members_detail.find((m) => m.id === p.member_id)?.avatar_color} />
                  {p.name}
                  {p.member_id === e.payer_member_id && <span className="rounded-full bg-brand-yellow-soft px-2 py-0.5 text-xs font-bold">Paid</span>}
                </span>
                <span className="tabular text-sm font-semibold text-ink">{taka(p.share, { decimals: true })}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-ink-muted">
            {e.payer_name} paid {taka(e.amount, { decimals: true })} upfront; everyone else owes their share to them until settled.
          </p>
          {e.notes && <p className="mt-3 rounded-xl bg-surface p-3 text-sm text-ink">{e.notes}</p>}
        </Card>
      </div>
    </div>
  );
}

function EditDialog({ expense, groupId, members, onSaved }: { expense: Expense; groupId: string; members: { id: string; display_name: string }[]; onSaved: () => void }) {
  const [open, setOpen] = useState(false);
  const [description, setDescription] = useState(expense.description);
  const [amount, setAmount] = useState(String(expense.amount / 100));
  const [payer, setPayer] = useState(expense.payer_member_id);
  const [busy, setBusy] = useState(false);

  async function save(ev: React.FormEvent) {
    ev.preventDefault();
    setBusy(true);
    try {
      await api(`/groups/${groupId}/expenses/${expense.id}`, { method: "PATCH", body: { description, amount: Number(amount), payer_member_id: payer } });
      onSaved();
      toast.success("Expense updated. Balances and the anomaly check were re-run.");
      setOpen(false);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="outline" size="sm" />}>
        <Pencil className="size-4" aria-hidden /> Edit
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={save} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Edit expense</DialogTitle>
            <DialogDescription>Fix a typo or wrong amount — e.g. ৳16,500 that should have been ৳1,650.</DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="e-desc">Description</Label>
            <Input id="e-desc" value={description} maxLength={200} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="e-amount">Amount (৳)</Label>
            <Input id="e-amount" type="number" inputMode="decimal" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="e-payer">Paid by</Label>
            <select id="e-payer" value={payer} onChange={(e) => setPayer(e.target.value)} className={selectClass}>
              {members.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.display_name}
                </option>
              ))}
            </select>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={busy || !(Number(amount) > 0) || !description.trim()}>
              {busy && <Loader2 className="size-4 animate-spin" aria-hidden />} Save changes
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
