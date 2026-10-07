"use client";

import { Lightbulb, ThumbsUp, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { LinkButton } from "@/components/common/primitives";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useInvalidateGroup } from "@/lib/queries";
import type { Recommendation } from "@/lib/types";
import { cn } from "@/lib/utils";

import { ProvenanceBadge } from "./labels";

export function RecommendationCard({ rec, groupId, variant = "hero", compact = false }: { rec: Recommendation; groupId: string; variant?: "hero" | "row"; compact?: boolean }) {
  const invalidate = useInvalidateGroup(groupId);
  const [state, setState] = useState<"idle" | "accepted" | "dismissed">("idle");

  async function act(action: "accepted" | "dismissed") {
    try {
      const res = await api<{ message: string }>(`/groups/${groupId}/recommendations/${encodeURIComponent(rec.key)}/action`, { body: { action } });
      setState(action);
      toast.success(res.message);
      if (action === "dismissed") invalidate();
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  if (state === "dismissed") return null;
  const hero = variant === "hero";
  return (
    <article className={cn("relative overflow-hidden rounded-xl border bg-white p-4 sm:p-5", hero ? "border-brand-yellow-strong/60" : "border-line")}>
      <div className="relative flex items-start gap-3">
        <span className={cn("mt-0.5 shrink-0", hero ? "text-[#7a5b00]" : "text-ink-muted")}>
          <Lightbulb className="size-[17px]" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex flex-wrap items-center gap-2">
            {hero && <span className="text-xs font-bold uppercase tracking-[0.12em] text-brand-blue-deep">Recommended next step</span>}
            <ProvenanceBadge kind="recommendation" />
          </div>
          <h3 className="text-[15px] font-bold leading-snug text-ink">{rec.title}</h3>
          <p className={cn("mt-1 text-sm text-ink", compact && "line-clamp-2 leading-5")}>{rec.text}</p>
          {rec.expected_outcome && (
            <p className="mt-2 rounded-lg bg-surface px-3 py-2 text-[13px] text-ink">
              <span className="font-semibold text-brand-blue-deep">Projected: </span>
              {rec.expected_outcome}
            </p>
          )}
          {rec.assumption && (
            compact ? (
              <details className="mt-2 text-xs text-ink-muted">
                <summary className="cursor-pointer font-semibold text-brand-blue">How this is estimated</summary>
                <p className="mt-1 leading-5">{rec.assumption}</p>
              </details>
            ) : (
              <p className="mt-2 text-xs text-ink-muted">Assumption: {rec.assumption}</p>
            )
          )}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <LinkButton href={rec.link} size="sm" variant={hero ? "blue" : "outline"}>
              {rec.kind === "goal" ? (compact ? "Try in What-If" : "Simulate in What-If") : "Open"}
            </LinkButton>
            {state === "accepted" ? (
              <span className="text-xs font-semibold text-good">Marked as helpful — you decide what to do next.</span>
            ) : (
              <>
                <Button size="sm" variant="ghost" onClick={() => act("accepted")}>
                  <ThumbsUp className="size-3.5" aria-hidden /> Helpful
                </Button>
                <Button size="sm" variant="ghost" onClick={() => act("dismissed")} aria-label="Dismiss recommendation for 7 days">
                  <X className="size-3.5" aria-hidden /> Dismiss
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}
