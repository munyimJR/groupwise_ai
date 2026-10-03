"use client";

import { Bot, Calculator, Eye, Lightbulb, Scale, TrendingUp } from "lucide-react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export type Provenance = "fact" | "prediction" | "assumption" | "recommendation" | "explanation" | "deterministic";

const STYLES: Record<Provenance, { label: string; icon: typeof Eye; cls: string; help: string }> = {
  fact: { label: "Observed fact", icon: Eye, cls: "bg-[#eef2f7] text-[#344054]", help: "Computed directly from your group's recorded transactions." },
  prediction: { label: "Model prediction", icon: TrendingUp, cls: "bg-brand-blue-soft text-brand-blue-deep", help: "An estimate from a statistical/ML model. Not a guarantee." },
  assumption: { label: "Assumption", icon: Scale, cls: "bg-warn-soft text-warn", help: "A stated assumption used in a projection or simulation." },
  recommendation: { label: "Recommendation", icon: Lightbulb, cls: "bg-brand-yellow-soft text-[#7a5b00]", help: "A suggestion. AI recommends — your group decides." },
  explanation: { label: "AI explanation", icon: Bot, cls: "bg-[#f1edfd] text-[#4a3aa7]", help: "Natural language generated from computed facts." },
  deterministic: { label: "Exact calculation", icon: Calculator, cls: "bg-[#eef2f7] text-[#344054]", help: "Deterministic financial logic — not AI." },
};

export function ProvenanceBadge({ kind, className, withTooltip = true }: { kind: Provenance; className?: string; withTooltip?: boolean }) {
  const s = STYLES[kind];
  const Icon = s.icon;
  const badge = (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold", s.cls, className)}>
      <Icon className="size-3" aria-hidden />
      {s.label}
    </span>
  );
  if (!withTooltip) return badge;
  return (
    <Tooltip>
      <TooltipTrigger render={<span className="inline-flex cursor-help" tabIndex={0} />}>{badge}</TooltipTrigger>
      <TooltipContent className="max-w-60">{s.help}</TooltipContent>
    </Tooltip>
  );
}

export function ConfidenceMeter({ level, basis, className }: { level: "high" | "medium" | "low"; basis?: string; className?: string }) {
  const bars = level === "high" ? 3 : level === "medium" ? 2 : 1;
  const label = `${level[0].toUpperCase()}${level.slice(1)} confidence`;
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-[11px] font-semibold text-ink-muted", className)} title={basis ? `${label} — ${basis}` : label}>
      <span className="flex items-end gap-[2px]" aria-hidden>
        {[1, 2, 3].map((i) => (
          <span key={i} className={cn("w-[3px] rounded-sm", i <= bars ? "bg-brand-blue" : "bg-line")} style={{ height: 4 + i * 3 }} />
        ))}
      </span>
      {label}
      {basis && <span className="font-normal">· {basis}</span>}
    </span>
  );
}

export function MethodNote({ children }: { children: React.ReactNode }) {
  return <p className="text-[11px] leading-snug text-ink-muted">Method: {children}</p>;
}
