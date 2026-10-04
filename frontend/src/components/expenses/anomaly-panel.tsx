"use client";

import { AlertTriangle, CheckCircle2, RotateCcw, XCircle } from "lucide-react";

import { ProvenanceBadge } from "@/components/ai/labels";
import { Button } from "@/components/ui/button";
import type { AnomalyReason } from "@/lib/types";
import { cn } from "@/lib/utils";

export function AnomalyScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-semibold text-ink-muted">Anomaly score</span>
        <span className="tabular text-2xl font-extrabold text-ink">{pct}%</span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-bad-soft" role="meter" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Anomaly score">
        <div className={cn("h-full rounded-full", pct >= 80 ? "bg-bad" : "bg-warn")} style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-1 text-xs text-ink-muted">Flag threshold 60% · compared with this group&apos;s own history</p>
    </div>
  );
}

export function ReasonList({ reasons }: { reasons: AnomalyReason[] }) {
  if (!reasons.length) return <p className="text-sm text-ink-muted">No unusual signals.</p>;
  return (
    <ul className="space-y-2">
      {reasons.map((r) => (
        <li key={r.signal + r.text} className="flex gap-2 text-sm text-ink">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warn" aria-hidden />
          <span>{r.text}</span>
        </li>
      ))}
    </ul>
  );
}

export function AnomalyPanel({
  score,
  status,
  reasons,
  onAction,
  busy,
}: {
  score: number;
  status: "none" | "flagged" | "valid" | "dismissed";
  reasons: AnomalyReason[];
  onAction?: (a: "valid" | "dismiss" | "reopen") => void;
  busy?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-bad/20 bg-white p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-sm font-extrabold uppercase tracking-wide text-bad">
          <AlertTriangle className="size-4" aria-hidden /> Unusual expense detected
        </p>
        <ProvenanceBadge kind="prediction" />
      </div>
      <AnomalyScoreBar score={score} />
      <p className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wider text-ink-muted">Why</p>
      <ReasonList reasons={reasons} />
      <p className="mt-3 text-xs text-ink-muted">
        Method: Isolation Forest + robust statistics + rules. Unusual doesn&apos;t mean wrong — nothing is blocked; your group decides.
      </p>
      {onAction && (
        <div className="mt-4 flex flex-wrap gap-2">
          {status === "flagged" ? (
            <>
              <Button size="sm" variant="blue" disabled={busy} onClick={() => onAction("valid")}>
                <CheckCircle2 className="size-4" aria-hidden /> It&apos;s correct — mark as valid
              </Button>
              <Button size="sm" variant="outline" disabled={busy} onClick={() => onAction("dismiss")}>
                <XCircle className="size-4" aria-hidden /> Not unusual — dismiss
              </Button>
            </>
          ) : (
            <>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-good-soft px-2.5 py-1 text-xs font-semibold text-good">
                <CheckCircle2 className="size-3.5" aria-hidden /> {status === "valid" ? "Reviewed — confirmed as valid" : "Reviewed — alert dismissed"}
              </span>
              <Button size="sm" variant="ghost" disabled={busy} onClick={() => onAction("reopen")}>
                <RotateCcw className="size-3.5" aria-hidden /> Reopen review
              </Button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
