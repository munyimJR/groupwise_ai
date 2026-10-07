"use client";

import { ArrowRight, Check, FileUp, Loader2, ShieldCheck, Sparkles, Wallet } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { MethodNote, ProvenanceBadge } from "@/components/ai/labels";
import { Card, CardHeading, EmptyState, MemberAvatar, PageHeader } from "@/components/common/primitives";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { fmtDate, fmtTime, taka } from "@/lib/format";
import { useGroup, useInvalidateGroup } from "@/lib/queries";
import type { StatementItem, StatementPreview } from "@/lib/types";
import { cn, selectClass } from "@/lib/utils";

type Choice = { action: "expense" | "settlement" | "skip"; to_member_id?: string | null };

const PURCHASE_KINDS = new Set(["payment", "bill_pay", "recharge"]);

export default function WalletImportPage() {
  const { groupId } = useParams<{ groupId: string }>();
  const router = useRouter();
  const { data: group } = useGroup(groupId);
  const invalidate = useInvalidateGroup(groupId);
  const fileRef = useRef<HTMLInputElement>(null);
  const [csv, setCsv] = useState("");
  const [source, setSource] = useState<string | null>(null);
  const [preview, setPreview] = useState<StatementPreview | null>(null);
  const [choices, setChoices] = useState<Record<string, Choice>>({});
  const [participants, setParticipants] = useState<string[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);

  const active = useMemo(() => group?.members_detail.filter((m) => m.status === "active") ?? [], [group]);
  const others = active.filter((m) => m.id !== group?.my_member_id);
  const split = participants ?? active.map((m) => m.id);

  async function analyse(text: string, label: string) {
    setLoading(true);
    try {
      const res = await api<StatementPreview>(`/groups/${groupId}/wallet/statement/preview`, { body: { csv: text } });
      setCsv(text);
      setSource(label);
      setPreview(res);
      setChoices(Object.fromEntries(res.items.map((i) => [i.txn_id, { action: i.suggestion, to_member_id: i.to_member_id }])));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onFile(file: File | undefined) {
    if (!file) return;
    if (file.size > 200_000) return toast.error("That file is too large. Export a shorter date range.");
    analyse(await file.text(), file.name);
  }

  async function useSample() {
    setLoading(true);
    try {
      const res = await api<{ csv: string }>(`/groups/${groupId}/wallet/sample-statement`);
      await analyse(res.csv, "Sample statement (synthetic)");
    } catch (e) {
      toast.error((e as Error).message);
      setLoading(false);
    }
  }

  const selected = preview?.items.filter((i) => choices[i.txn_id]?.action && choices[i.txn_id].action !== "skip") ?? [];
  const nExpenses = selected.filter((i) => choices[i.txn_id].action === "expense").length;
  const nPayments = selected.length - nExpenses;

  async function doImport() {
    setImporting(true);
    try {
      const res = await api<{ expenses: number; settlements: number; skipped: number; flagged: number }>(
        `/groups/${groupId}/wallet/statement/import`,
        {
          body: {
            csv,
            participant_ids: split,
            selections: selected.map((i) => ({
              txn_id: i.txn_id,
              action: choices[i.txn_id].action,
              to_member_id: choices[i.txn_id].to_member_id,
              subcategory: i.subcategory,
            })),
          },
        },
      );
      invalidate();
      toast.success(
        `Imported ${res.expenses} expense${res.expenses === 1 ? "" : "s"} and ${res.settlements} payment${res.settlements === 1 ? "" : "s"} back.` +
          (res.flagged ? ` ${res.flagged} ${res.flagged === 1 ? "looks" : "look"} unusual and ${res.flagged === 1 ? "needs" : "need"} a quick review.` : ""),
      );
      router.push(`/g/${groupId}/transactions`);
    } catch (e) {
      toast.error((e as Error).message);
      setImporting(false);
    }
  }

  return (
    <div className="pb-24">
      <PageHeader
        eyebrow="Mobile wallet"
        title="Import from your wallet"
        subtitle="Upload your wallet's transaction export. GroupWise reads each transaction, sorts it into a category and suggests which ones the group shares. Nothing is added until you confirm."
      />

      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <div className="space-y-5">
          <Card>
            <CardHeading icon={FileUp} title="1. Choose a statement" subtitle="CSV export from your wallet app (Date, Type, To/From, Amount, TrxID)" />
            <div className="flex flex-wrap gap-2">
              <input ref={fileRef} type="file" accept=".csv,text/csv,text/plain" className="sr-only" id="statement-file" onChange={(e) => onFile(e.target.files?.[0])} />
              <Button variant="blue" disabled={loading} onClick={() => fileRef.current?.click()}>
                <FileUp className="size-4" aria-hidden /> Upload CSV
              </Button>
              <Button variant="outline" disabled={loading} onClick={useSample}>
                {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Sparkles className="size-4" aria-hidden />} Use a sample statement
              </Button>
            </div>
            {source && (
              <p className="mt-3 text-sm text-ink-muted">
                Reading <strong className="text-ink">{source}</strong>
                {source.includes("synthetic") && " — made-up transactions for the demo, not real data"}.
              </p>
            )}
          </Card>

          {preview && (
            <Card>
              <CardHeading
                icon={Sparkles}
                title="2. Review the suggestions"
                subtitle={`${preview.summary.rows} transactions · ${taka(preview.summary.total_out)} spent from the wallet`}
                action={<ProvenanceBadge kind="prediction" />}
              />
              {preview.items.length === 0 ? (
                <EmptyState title="No transactions found" />
              ) : (
                <ul className="space-y-2">
                  {preview.items.map((item) => (
                    <StatementRow
                      key={item.txn_id}
                      item={item}
                      choice={choices[item.txn_id]}
                      others={others.map((m) => ({ id: m.id, name: m.display_name }))}
                      onChange={(c) => setChoices((prev) => ({ ...prev, [item.txn_id]: c }))}
                    />
                  ))}
                </ul>
              )}
              <div className="mt-3">
                <MethodNote>{preview.method}</MethodNote>
              </div>
            </Card>
          )}
        </div>

        <div className="space-y-5">
          {preview && (
            <Card>
              <CardHeading title="3. Split shared expenses between" />
              <div className="flex flex-wrap gap-2" role="group" aria-label="Split imported expenses between">
                {active.map((m) => {
                  const on = split.includes(m.id);
                  return (
                    <button
                      key={m.id}
                      type="button"
                      aria-pressed={on}
                      onClick={() => setParticipants(on ? split.filter((p) => p !== m.id) : [...split, m.id])}
                      className={cn(
                        "inline-flex min-h-11 items-center gap-2 rounded-full border py-1 pr-3 pl-1 text-sm font-semibold transition-colors",
                        on ? "border-brand-blue bg-brand-blue-soft text-brand-blue-deep" : "border-line bg-white text-ink-muted",
                      )}
                    >
                      <MemberAvatar name={m.display_name} color={m.avatar_color} size={28} />
                      {m.is_you ? "You" : m.display_name}
                      {on && <Check className="size-3.5" aria-hidden />}
                    </button>
                  );
                })}
              </div>
              <p className="mt-2 text-xs text-ink-muted">Each shared expense is split equally. You can change any expense afterwards.</p>
            </Card>
          )}
          <Card className="bg-brand-blue-softer">
            <CardHeading icon={ShieldCheck} title="Your data" />
            <ul className="space-y-1.5 text-sm text-ink">
              <li>The statement is read for this import only and is not stored.</li>
              <li>Only the transactions you import are saved, with their TrxID so nothing is counted twice.</li>
              <li>Personal spending stays out of the group unless you choose to add it.</li>
            </ul>
          </Card>
          <Card>
            <CardHeading icon={Wallet} title="Why import?" />
            <p className="text-sm text-ink-muted">
              Most shared costs are already paid from a mobile wallet. Importing turns those payments into the group&apos;s
              ledger in seconds, and recognizes when you paid a friend back.
            </p>
          </Card>
        </div>
      </div>

      {preview && (
        <div className="fixed inset-x-0 bottom-[calc(62px+env(safe-area-inset-bottom))] z-30 border-t border-line bg-white/95 backdrop-blur lg:bottom-0 lg:left-[264px]">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
            <p className="text-sm text-ink">
              <strong>{nExpenses}</strong> shared expense{nExpenses === 1 ? "" : "s"} · <strong>{nPayments}</strong> payment{nPayments === 1 ? "" : "s"} back
            </p>
            <Button onClick={doImport} disabled={importing || selected.length === 0 || (nExpenses > 0 && split.length === 0)}>
              {importing ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <ArrowRight className="size-4" aria-hidden />} Import {selected.length}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function StatementRow({ item, choice, others, onChange }: { item: StatementItem; choice?: Choice; others: { id: string; name: string }[]; onChange: (c: Choice) => void }) {
  const canExpense = item.direction === "out" && PURCHASE_KINDS.has(item.kind) && !item.already_imported;
  const canSettle = item.direction === "out" && item.kind === "send_money" && !item.already_imported;
  const value = choice?.action === "settlement" ? `settle:${choice.to_member_id}` : choice?.action ?? "skip";
  const active = value !== "skip";
  const conf = item.confidence !== null ? Math.round(item.confidence * 100) : null;

  return (
    <li className={cn("rounded-xl border p-3", active ? "border-brand-blue/30 bg-brand-blue-softer" : "border-line", item.already_imported && "opacity-60")}>
      <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1">
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-ink">{item.counterparty || item.kind_label}</p>
          <p className="text-xs text-ink-muted">
            {fmtDate(item.occurred_at)} · {fmtTime(item.occurred_at)} · {item.kind_label}
            {item.description ? ` · ${item.description}` : ""}
          </p>
        </div>
        <p className={cn("tabular text-sm font-extrabold", item.direction === "in" ? "text-good" : "text-ink")}>
          {item.direction === "in" ? "+" : "−"}
          {taka(item.amount, { decimals: true })}
        </p>
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-ink-muted">
          {item.subcategory_label && (
            <span className="mr-1.5 inline-flex items-center rounded-full bg-white px-2 py-0.5 font-semibold text-ink ring-1 ring-line">
              {item.category} › {item.subcategory_label}
              {conf !== null && <span className="ml-1 font-normal text-ink-muted">{conf}%</span>}
            </span>
          )}
          {item.reason}
        </p>
        {(canExpense || canSettle) && (
          <select
            aria-label={`What to do with ${item.counterparty || item.kind_label}, ${taka(item.amount)}`}
            value={value}
            onChange={(e) => {
              const v = e.target.value;
              if (v.startsWith("settle:")) onChange({ action: "settlement", to_member_id: v.slice(7) });
              else onChange({ action: v as Choice["action"] });
            }}
            className={cn(selectClass, "h-9 w-auto min-w-44")}
          >
            {canExpense && <option value="expense">Add as shared expense</option>}
            {canSettle &&
              others.map((m) => (
                <option key={m.id} value={`settle:${m.id}`}>
                  Paid back {m.name}
                </option>
              ))}
            <option value="skip">Skip (personal)</option>
          </select>
        )}
      </div>
    </li>
  );
}
