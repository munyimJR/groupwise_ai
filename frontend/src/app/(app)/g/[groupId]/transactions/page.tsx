"use client";

import { AlertTriangle, Plus, Receipt, Search } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Card, EmptyState, ErrorState, LinkButton, LoadingBlock, PageHeader } from "@/components/common/primitives";
import { ExpenseRow } from "@/components/expenses/expense-row";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { dayLabel, taka } from "@/lib/format";
import { useExpenses, useTaxonomy } from "@/lib/queries";
import type { Expense } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function TransactionsPage() {
  const { groupId } = useParams<{ groupId: string }>();
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string | undefined>();
  const [flagged, setFlagged] = useState(false);
  const { data: taxonomy } = useTaxonomy();

  useEffect(() => {
    const t = setTimeout(() => setQuery(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  const { data, isLoading, error, refetch, fetchNextPage, hasNextPage, isFetchingNextPage, isFetching } = useExpenses(groupId, { q: query, category, flagged });
  const items = useMemo(() => data?.pages.flatMap((p) => p.items) ?? [], [data]);
  const total = data?.pages[0]?.total ?? 0;

  const grouped = useMemo(() => {
    const out: { day: string; items: Expense[]; total: number }[] = [];
    for (const e of items) {
      const day = e.occurred_at.slice(0, 10);
      const last = out[out.length - 1];
      if (last && last.day === day) {
        last.items.push(e);
        last.total += e.amount;
      } else out.push({ day, items: [e], total: e.amount });
    }
    return out;
  }, [items]);

  return (
    <div>
      <PageHeader
        eyebrow="Transactions"
        title="Shared expenses"
        subtitle="Every expense, how it was split, and anything that looked unusual."
        actions={
          <LinkButton href={`/g/${groupId}/add`}>
            <Plus className="size-4" aria-hidden /> Add expense
          </LinkButton>
        }
      />
      <Card className="mb-4 space-y-3 p-3 sm:p-4">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-muted" aria-hidden />
          <Input aria-label="Search expenses" placeholder="Search description or merchant" value={q} onChange={(e) => setQ(e.target.value)} className="h-11 pl-9" />
        </div>
        <div className="no-scrollbar -mx-1 flex gap-2 overflow-x-auto px-1">
          <Chip active={!category && !flagged} onClick={() => { setCategory(undefined); setFlagged(false); }}>All</Chip>
          <Chip active={flagged} onClick={() => setFlagged(!flagged)}>
            <AlertTriangle className="size-3.5" aria-hidden /> Unusual
          </Chip>
          {taxonomy?.map((c) => (
            <Chip key={c.category} active={category === c.category} onClick={() => setCategory(category === c.category ? undefined : c.category)}>
              {c.category}
            </Chip>
          ))}
        </div>
      </Card>

      {isLoading ? (
        <LoadingBlock rows={6} />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Receipt}
          title={query || category || flagged ? "No matching expenses" : "No expenses yet"}
          body={query || category || flagged ? "Try a different search or filter." : "Add your first shared expense to start building group financial intelligence."}
          action={!query && !category && !flagged ? <LinkButton href={`/g/${groupId}/add`}>Add expense</LinkButton> : undefined}
        />
      ) : (
        <div className={cn("space-y-4 transition-opacity", isFetching && !isFetchingNextPage && "opacity-60")}>
          <p className="text-xs text-ink-muted">
            Showing {items.length} of {total} expenses
          </p>
          {grouped.map((g) => (
            <Card key={g.day} className="p-2 sm:p-3">
              <div className="flex items-center justify-between px-2 pb-1 pt-1">
                <h2 className="text-xs font-bold uppercase tracking-wider text-ink-muted">{dayLabel(g.day)}</h2>
                <span className="tabular text-xs font-semibold text-ink-muted">{taka(g.total)}</span>
              </div>
              <ul className="divide-y divide-line">
                {g.items.map((e) => (
                  <li key={e.id}>
                    <ExpenseRow expense={e} groupId={groupId} />
                  </li>
                ))}
              </ul>
            </Card>
          ))}
          {hasNextPage && (
            <div className="flex justify-center">
              <Button variant="outline" onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
                {isFetchingNextPage ? "Loading…" : "Load more"}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors pointer-coarse:min-h-11 pointer-coarse:px-4",
        active ? "border-brand-blue bg-brand-blue text-white" : "border-line bg-white text-ink hover:border-brand-blue/40",
      )}
    >
      {children}
    </button>
  );
}
