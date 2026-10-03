import { cn } from "@/lib/utils";

/** GroupWise mark: three connected members (the group) on the brand-yellow tile. */
export function LogoMark({ className, title = "GroupWise AI" }: { className?: string; title?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={cn("size-9 shrink-0", className)} role="img" aria-label={title}>
      <rect width="40" height="40" rx="11" fill="#FFD429" />
      <path d="M12.5 26.5 20 14l7.5 12.5Z" fill="none" stroke="#003B7A" strokeWidth="2.4" strokeLinejoin="round" />
      <circle cx="20" cy="14" r="4.2" fill="#0057B8" />
      <circle cx="12.5" cy="26.5" r="4.2" fill="#0057B8" />
      <circle cx="27.5" cy="26.5" r="4.2" fill="#003B7A" />
      <circle cx="31" cy="9" r="2" fill="#003B7A" />
    </svg>
  );
}

export function Logo({ className, compact = false }: { className?: string; compact?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark />
      {!compact && (
        <span className="flex flex-col leading-none">
          <span className="text-[17px] font-extrabold tracking-tight text-ink">
            GroupWise <span className="text-brand-blue">AI</span>
          </span>
          <span className="mt-1 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-ink-muted">Shared Financial Intelligence</span>
        </span>
      )}
    </span>
  );
}
