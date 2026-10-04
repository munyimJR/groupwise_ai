"use client";

import { Banknote, Check, CreditCard, Landmark, Loader2, Sparkles, Smartphone, Wand2 } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { ProvenanceBadge } from "@/components/ai/labels";
import { Card, CardHeading, ErrorState, LoadingBlock, MemberAvatar, PageHeader } from "@/components/common/primitives";
import { AnomalyPanel } from "@/components/expenses/anomaly-panel";
import { CategorySelect } from "@/components/expenses/category-select";
import { CategoryIcon } from "@/components/expenses/expense-row";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { taka, toLocalInputValue } from "@/lib/format";
import { useCategorize, useGroup, useInvalidateGroup } from "@/lib/queries";
import type { AnomalyResult, Expense, Prediction } from "@/lib/types";
import { cn } from "@/lib/utils";

const METHODS = [
  { value: "mobile_wallet", label: "Mobile wallet", icon: Smartphone },
  { value: "cash", label: "Cash", icon: Banknote },
  { value: "card", label: "Card", icon: CreditCard },
  { value: "bank_transfer", label: "Bank", icon: Landmark },
] as const;

const EXAMPLES = ["Lunch at restaurant 850", "Uber to campus 280", "Hotel booking 4800", "Foodpanda biryani 1450", "DESCO bill 1800"];

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

function Suggestion({ p, onPick, overridden }: { p: Prediction; onPick: (sub: string) => void; overridden: boolean }) {
  const pct = Math.round(p.confidence * 100);
  return (
    <div className={cn("rounded-2xl border p-3.5", p.needs_confirmation ? "border-warn/30 bg-warn-soft/50" : "border-brand-blue/15 bg-brand-blue-softer")}>
      <div className="flex items-start gap-3">
        <CategoryIcon category={p.category} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-brand-blue">
              <Sparkles className="size-3" aria-hidden /> {p.source === "feedback" ? "Learned from your group" : "AI suggestion"}
            </span>
            {overridden && <span className="text-xs font-semibold text-ink-muted">(you chose a different category)</span>}
          </div>
          <p className="text-[15px] font-bold text-ink">
            {p.category} › {p.subcategory_label} <span className="font-medium text-ink-muted">· {p.expense_type}</span>
          </p>
          <div className="mt-1.5 flex items-center gap-2">
            <div className="h-1.5 w-28 overflow-hidden rounded-full bg-white" aria-hidden>
              <div className={cn("h-full rounded-full", p.needs_confirmation ? "bg-warn" : "bg-brand-blue")} style={{ width: `${pct}%` }} />
            </div>
            <span className="text-xs font-semibold text-ink">{pct}% confident</span>
          </div>
          {p.note && <p className="mt-1 text-xs text-ink-muted">{p.note}</p>}
          {p.signals.length > 0 && (
            <p className="mt-1.5 text-xs text-ink-muted">
              Why: {p.signals.map((s) => `“${s}”`).join(", ")}
              {p.known_merchant ? ` · known merchant ${p.known_merchant}` : ""}
            </p>
          )}
          {p.needs_confirmation && (
            <div className="mt-2">
              <p className="text-xs font-semibold text-warn">Not sure — please confirm the category:</p>
              <div className="mt-1.5 flex flex-wrap gap-2">
                {p.alternatives.map((a) => (
                  <button
                    key={a.subcategory}
                    type="button"
                    onClick={() => onPick(a.subcategory)}
                    className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-semibold text-ink hover:border-brand-blue pointer-coarse:min-h-11"
                  >
                    {a.category} › {a.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function AddExpensePage() {
  const { groupId } = useParams<{ groupId: string }>();
  const router = useRouter();
  const invalidate = useInvalidateGroup(groupId);
  const { data: group, isLoading, error, refetch } = useGroup(groupId);

  const [text, setText] = useState("");
  const [amountInput, setAmountInput] = useState("");
  const [amountTouched, setAmountTouched] = useState(false);
  const [payerChoice, setPayer] = useState<string | null>(null);
  const [participantChoice, setParticipants] = useState<string[] | null>(null);
  const [when, setWhen] = useState(() => toLocalInputValue());
  const [method, setMethod] = useState<string>("mobile_wallet");
  const [notes, setNotes] = useState("");
  const [subOverride, setSubOverride] = useState<string | null>(null);
  const [showCategory, setShowCategory] = useState(false);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{ description?: string; amount?: string; participants?: string }>({});
  const descRef = useRef<HTMLInputElement>(null);
  const amountRef = useRef<HTMLInputElement>(null);
  const participantsRef = useRef<HTMLDivElement>(null);
  const [flagged, setFlagged] = useState<{ expense: Expense; anomaly: AnomalyResult } | null>(null);

  const active = useMemo(() => group?.members_detail.filter((m) => m.status === "active") ?? [], [group]);
  const payer = payerChoice ?? group?.my_member_id ?? "";
  const participants = participantChoice ?? active.map((m) => m.id);

  const debounced = useDebounced(text, 350);
  const { data: cat, isFetching: categorizing } = useCategorize(debounced, groupId);
  const prediction = debounced.trim().length >= 3 ? cat?.prediction : undefined;

  // Until the user types an amount, use the one parsed from the description.
  const parsedAmount = debounced.trim().length >= 3 && cat?.parsed.amount ? String(cat.parsed.amount) : "";
  const amount = amountTouched ? amountInput : parsedAmount || amountInput;

  const amountNum = Number(amount);
  const perHead = participants.length && amountNum > 0 ? (amountNum * 100) / participants.length : 0;
  const description = cat?.parsed.description && debounced === text ? cat.parsed.description : text.trim();
  const chosenSub = subOverride ?? prediction?.subcategory ?? "other";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    const errs: typeof fieldErrors = {};
    if (!description) errs.description = "Describe what the expense was for, e.g. “Lunch at Kacchi Bhai”.";
    if (!(amountNum > 0)) errs.amount = "Enter an amount greater than ৳0.";
    if (!participants.length) errs.participants = "Choose at least one person to split this expense with.";
    setFieldErrors(errs);
    if (errs.description) return descRef.current?.focus();
    if (errs.amount) return amountRef.current?.focus();
    if (errs.participants) return participantsRef.current?.querySelector("button")?.focus();
    setBusy(true);
    try {
      const res = await api<{ expense: Expense; categorization: Prediction; anomaly: AnomalyResult }>(`/groups/${groupId}/expenses`, {
        body: {
          description,
          amount: amountNum,
          payer_member_id: payer,
          participant_ids: participants,
          occurred_at: when,
          subcategory: subOverride ?? null,
          merchant: cat?.parsed.merchant ?? null,
          payment_method: method,
          notes: notes || null,
        },
      });
      invalidate();
      if (res.anomaly.flagged) {
        setFlagged({ expense: res.expense, anomaly: res.anomaly });
      } else {
        toast.success(`Saved · ${res.expense.category} › ${res.expense.subcategory_label}`, { description: `${taka(res.expense.amount)} split ${participants.length} ways` });
        router.push(`/g/${groupId}`);
      }
    } catch (err) {
      setFormError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function review(action: "valid" | "dismiss" | "reopen") {
    if (!flagged) return;
    await api(`/groups/${groupId}/expenses/${flagged.expense.id}/review`, { body: { action } });
    invalidate();
    toast.success(action === "valid" ? "Marked as valid. Thanks for reviewing." : "Alert dismissed.");
    router.push(`/g/${groupId}/transactions/${flagged.expense.id}`);
  }

  if (isLoading) return <LoadingBlock rows={5} />;
  if (error || !group) return <ErrorState error={error} onRetry={() => refetch()} />;

  return (
    <div>
      <PageHeader eyebrow={group.name} title="Add an expense" subtitle="Describe it naturally — GroupWise reads the amount, merchant and category for you. You can always change it." />
      <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
        <form onSubmit={submit} className="space-y-5" noValidate>
          <Card className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="desc" className="flex items-center gap-1.5">
                <Wand2 className="size-4 text-brand-blue" aria-hidden /> What was it for?
              </Label>
              <Input
                ref={descRef}
                id="desc"
                aria-invalid={!!fieldErrors.description}
                aria-describedby={fieldErrors.description ? "desc-error" : undefined}
                autoFocus
                autoComplete="off"
                maxLength={200}
                placeholder="e.g. Dinner at Kacchi Bhai 1650"
                value={text}
                onChange={(e) => {
                  setText(e.target.value);
                  setSubOverride(null);
                  if (fieldErrors.description) setFieldErrors((f) => ({ ...f, description: undefined }));
                }}
                className="h-12 text-base"
              />
              {fieldErrors.description && (
                <p id="desc-error" role="alert" className="text-sm text-bad">
                  {fieldErrors.description}
                </p>
              )}
              <div className="flex flex-wrap gap-2 pt-1">
                {EXAMPLES.map((ex) => (
                  <button
                    key={ex}
                    type="button"
                    onClick={() => {
                      setText(ex);
                      setAmountTouched(false);
                      setSubOverride(null);
                    }}
                    className="rounded-full bg-surface px-3 py-1.5 text-xs text-ink-muted transition-colors hover:bg-brand-blue-soft hover:text-brand-blue-deep pointer-coarse:min-h-11"
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>

            <div aria-live="polite">
              {categorizing && !prediction && (
                <p className="flex items-center gap-2 text-sm text-ink-muted">
                  <Loader2 className="size-4 animate-spin" aria-hidden /> Reading your expense…
                </p>
              )}
              {prediction && <Suggestion p={prediction} overridden={!!subOverride && subOverride !== prediction.subcategory} onPick={(s) => setSubOverride(s)} />}
            </div>
            {prediction && (
              <div>
                {showCategory ? (
                  <div className="space-y-1.5">
                    <Label htmlFor="category">Category</Label>
                    <CategorySelect value={chosenSub} onChange={setSubOverride} />
                    <p className="text-xs text-ink-muted">Your choice is saved as feedback and remembered for similar expenses in this group.</p>
                  </div>
                ) : (
                  <button type="button" onClick={() => setShowCategory(true)} className="tap-target text-sm font-semibold text-brand-blue hover:underline">
                    Change category
                  </button>
                )}
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="amount">Amount (৳)</Label>
                <Input
                  ref={amountRef}
                  id="amount"
                  aria-invalid={!!fieldErrors.amount}
                  aria-describedby={fieldErrors.amount ? "amount-error" : undefined}
                  inputMode="decimal"
                  type="number"
                  min="0.01"
                  step="0.01"
                  placeholder="0"
                  value={amount}
                  onChange={(e) => {
                    setAmountInput(e.target.value);
                    setAmountTouched(true);
                    if (fieldErrors.amount) setFieldErrors((f) => ({ ...f, amount: undefined }));
                  }}
                  className="tabular h-12 text-lg font-bold"
                />
                {fieldErrors.amount && (
                  <p id="amount-error" role="alert" className="text-sm text-bad">
                    {fieldErrors.amount}
                  </p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="when">Date & time</Label>
                <Input id="when" type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} className="h-12" />
              </div>
            </div>
          </Card>

          <Card className="space-y-4">
            <fieldset>
              <legend className="mb-2 text-sm font-semibold text-ink">Paid by</legend>
              <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Paid by">
                {active.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    role="radio"
                    aria-checked={payer === m.id}
                    onClick={() => setPayer(m.id)}
                    className={cn(
                      "flex items-center gap-2 rounded-full border py-1 pl-1 pr-3 text-sm font-semibold transition-colors pointer-coarse:min-h-11",
                      payer === m.id ? "border-brand-blue bg-brand-blue-soft text-brand-blue-deep" : "border-line bg-white text-ink hover:border-brand-blue/40",
                    )}
                  >
                    <MemberAvatar name={m.display_name} color={m.avatar_color} size={26} />
                    {m.is_you ? "You" : m.display_name.split(" ")[0]}
                    {payer === m.id && <Check className="size-3.5" aria-hidden />}
                  </button>
                ))}
              </div>
            </fieldset>
            <fieldset>
              <div className="mb-2 flex items-center justify-between">
                <legend className="text-sm font-semibold text-ink">Split equally between</legend>
                <button
                  type="button"
                  className="tap-target text-xs font-semibold text-brand-blue hover:underline"
                  onClick={() => setParticipants(participants.length === active.length ? [payer] : active.map((m) => m.id))}
                >
                  {participants.length === active.length ? "Only payer" : "Everyone"}
                </button>
              </div>
              <div ref={participantsRef} className="flex flex-wrap gap-2" role="group" aria-label="Split equally between" aria-describedby={fieldErrors.participants ? "participants-error" : undefined}>
                {active.map((m) => {
                  const on = participants.includes(m.id);
                  return (
                    <button
                      key={m.id}
                      type="button"
                      role="checkbox"
                      aria-checked={on}
                      onClick={() => {
                        setParticipants(on ? participants.filter((p) => p !== m.id) : [...participants, m.id]);
                        if (fieldErrors.participants) setFieldErrors((f) => ({ ...f, participants: undefined }));
                      }}
                      className={cn(
                        "flex items-center gap-2 rounded-full border py-1 pl-1 pr-3 text-sm font-semibold transition-colors pointer-coarse:min-h-11",
                        on ? "border-brand-yellow-strong bg-brand-yellow-soft text-ink" : "border-line bg-white text-ink-muted line-through decoration-1",
                      )}
                    >
                      <MemberAvatar name={m.display_name} color={on ? m.avatar_color : "#98a2b3"} size={26} />
                      {m.is_you ? "You" : m.display_name.split(" ")[0]}
                    </button>
                  );
                })}
              </div>
              {fieldErrors.participants && (
                <p id="participants-error" role="alert" className="mt-2 text-sm text-bad">
                  {fieldErrors.participants}
                </p>
              )}
              <p className="mt-2 text-sm text-ink-muted">
                {participants.length ? (
                  <>
                    {participants.length} {participants.length === 1 ? "person" : "people"} ·{" "}
                    <strong className="tabular text-ink">{perHead ? taka(perHead, { decimals: true }) : "৳0"} each</strong>
                  </>
                ) : (
                  "Select who shared this expense."
                )}
              </p>
            </fieldset>
            <fieldset>
              <legend className="mb-2 text-sm font-semibold text-ink">Paid with</legend>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4" role="radiogroup" aria-label="Paid with">
                {METHODS.map((m) => (
                  <button
                    key={m.value}
                    type="button"
                    role="radio"
                    aria-checked={method === m.value}
                    onClick={() => setMethod(m.value)}
                    className={cn(
                      "flex min-h-10 items-center justify-center gap-1.5 rounded-xl border px-2 py-2 text-xs font-semibold transition-colors pointer-coarse:min-h-11",
                      method === m.value ? "border-brand-blue bg-brand-blue-soft text-brand-blue-deep" : "border-line bg-white text-ink",
                    )}
                  >
                    <m.icon className="size-4" aria-hidden /> {m.label}
                  </button>
                ))}
              </div>
            </fieldset>
            <div className="space-y-1.5">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Textarea id="notes" rows={2} maxLength={500} value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
          </Card>

          {formError && (
            <p role="alert" className="rounded-xl bg-bad-soft px-3 py-2 text-sm text-bad">
              {formError}
            </p>
          )}
          <div className="sticky bottom-20 z-20 lg:static">
            <Button type="submit" size="lg" className="w-full shadow-[var(--shadow-lift)] lg:w-auto lg:shadow-none" disabled={busy}>
              {busy && <Loader2 className="size-4 animate-spin" aria-hidden />}
              {busy ? "Saving & checking…" : `Save expense${amountNum > 0 ? ` · ${taka(amountNum * 100, { decimals: true })}` : ""}`}
            </Button>
          </div>
        </form>

        <aside className="space-y-4">
          <Card>
            <CardHeading icon={Sparkles} title="What happens when you save" />
            <ol className="space-y-3 text-sm text-ink">
              <li>
                <strong>1. Categorized</strong> — an ML classifier reads your description.{" "}
                <span className="text-ink-muted">You can override it; corrections are remembered.</span>
              </li>
              <li>
                <strong>2. Split exactly</strong> — equal shares to the paisa, deterministic.
              </li>
              <li>
                <strong>3. Checked for anything unusual</strong> — compared with this group&apos;s history.{" "}
                <span className="text-ink-muted">Nothing is ever blocked.</span>
              </li>
              <li>
                <strong>4. Insights update</strong> — balances, forecast and goals refresh instantly.
              </li>
            </ol>
            <div className="mt-3 flex flex-wrap gap-1.5">
              <ProvenanceBadge kind="prediction" />
              <ProvenanceBadge kind="deterministic" />
            </div>
          </Card>
        </aside>
      </div>

      <Dialog open={!!flagged} onOpenChange={(o) => !o && flagged && router.push(`/g/${groupId}/transactions/${flagged.expense.id}`)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Saved — but this one looks unusual</DialogTitle>
            <DialogDescription>
              “{flagged?.expense.description}” · {flagged ? taka(flagged.expense.amount, { decimals: true }) : ""}. It&apos;s recorded and nothing is blocked. Take a quick look before anyone settles up.
            </DialogDescription>
          </DialogHeader>
          {flagged && (
            <AnomalyPanel score={flagged.anomaly.score} status="flagged" reasons={flagged.anomaly.reasons} onAction={(a) => review(a)} />
          )}
          <Button variant="ghost" onClick={() => flagged && router.push(`/g/${groupId}/transactions/${flagged.expense.id}`)}>
            Review later
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}
