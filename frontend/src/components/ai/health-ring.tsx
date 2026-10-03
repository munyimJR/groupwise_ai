"use client";

import { Info } from "lucide-react";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import type { Health } from "@/lib/types";
import { cn } from "@/lib/utils";

function bandColor(score: number) {
  if (score >= 80) return "#11805a";
  if (score >= 65) return "#0057b8";
  if (score >= 50) return "#b45309";
  return "#c2350c";
}

export function HealthRing({ score, size = 76 }: { score: number; size?: number }) {
  const r = (size - 10) / 2;
  const c = 2 * Math.PI * r;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`Health score ${score} out of 100`}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#eef1f5" strokeWidth={8} />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={bandColor(score)}
        strokeWidth={8}
        strokeLinecap="round"
        strokeDasharray={`${(score / 100) * c} ${c}`}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle" className="fill-ink text-[20px] font-extrabold">
        {score}
      </text>
    </svg>
  );
}

export function HealthExplainer({ health, trigger }: { health: Health; trigger?: React.ReactNode }) {
  return (
    <Popover>
      <PopoverTrigger
        render={
          <button type="button" className="inline-flex items-center gap-1 text-xs font-semibold text-brand-blue hover:text-brand-blue-deep">
            {trigger ?? (
              <>
                <Info className="size-3.5" aria-hidden /> How is this calculated?
              </>
            )}
          </button>
        }
      />
      <PopoverContent className="w-[min(92vw,380px)] p-4" align="start">
        <p className="text-sm font-bold text-ink">How the health score is calculated</p>
        <p className="mt-1 text-xs text-ink-muted">{health.formula}</p>
        <ul className="mt-3 space-y-2.5">
          {health.factors.map((f) => (
            <li key={f.key} className="text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-ink">
                  {f.label} <span className="font-normal text-ink-muted">· weight {Math.round(f.weight * 100)}%</span>
                </span>
                <span className="tabular font-bold text-ink">{f.score === null ? "n/a" : `${f.score}/100`}</span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-brand-blue-soft">
                <div className={cn("h-full rounded-full", f.score === null ? "bg-line" : "bg-brand-blue")} style={{ width: `${f.score ?? 0}%` }} />
              </div>
              <p className="mt-1 text-ink-muted">
                {f.value} — {f.explanation}
              </p>
            </li>
          ))}
        </ul>
        <p className="mt-3 rounded-lg bg-warn-soft px-2.5 py-2 text-[11px] text-warn">{health.disclaimer}</p>
      </PopoverContent>
    </Popover>
  );
}
