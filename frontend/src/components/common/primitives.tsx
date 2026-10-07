"use client";

import { AlertTriangle, ArrowDownRight, ArrowUpRight, CheckCircle2, Info, Minus, RefreshCw, type LucideIcon } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { initials, taka } from "@/lib/format";
import { cn } from "@/lib/utils";

export function Card({ className, children, ...props }: React.ComponentProps<"section">) {
  return (
    <section className={cn("card-surface p-4 sm:p-5", className)} {...props}>
      {children}
    </section>
  );
}

export function CardHeading({ title, subtitle, icon: Icon, action, className }: { title: string; subtitle?: React.ReactNode; icon?: LucideIcon; action?: React.ReactNode; className?: string }) {
  return (
    <div className={cn("mb-3 flex items-start justify-between gap-3", className)}>
      <div className="flex min-w-0 items-start gap-2.5">
        {Icon && <Icon className="mt-1 size-4 shrink-0 text-brand-blue" aria-hidden />}
        <div className="min-w-0">
          <h2 className="text-[15px] font-bold leading-tight text-ink">{title}</h2>
          {subtitle && <p className="mt-0.5 text-xs text-ink-muted">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions, eyebrow }: { title: string; subtitle?: React.ReactNode; actions?: React.ReactNode; eyebrow?: string }) {
  return (
    <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow && <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-muted">{eyebrow}</p>}
        <h1 className="text-2xl font-bold leading-tight text-ink sm:text-[28px]">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-ink-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

/** Net balance shown with icon + word + colour so meaning never relies on colour alone. */
export function BalanceTag({ net, size = "md", you = false }: { net: number; size?: "sm" | "md" | "lg"; you?: boolean }) {
  const gets = net > 0;
  const settled = net === 0;
  const Icon = settled ? CheckCircle2 : gets ? ArrowDownRight : ArrowUpRight;
  const label = settled ? "Settled up" : gets ? (you ? "You get" : "Gets") : you ? "You owe" : "Owes";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full font-semibold tabular",
        size === "sm" && "px-2 py-0.5 text-xs",
        size === "md" && "px-2.5 py-1 text-sm",
        size === "lg" && "px-3 py-1.5 text-base",
        settled ? "bg-muted text-ink-muted" : gets ? "bg-good-soft text-good" : "bg-bad-soft text-bad",
      )}
    >
      <Icon className={size === "sm" ? "size-3.5" : "size-4"} aria-hidden />
      <span>
        {label}
        {!settled && <> {taka(Math.abs(net), { decimals: true })}</>}
      </span>
    </span>
  );
}

export function Delta({ value, goodWhenDown = true, suffix = "vs previous period" }: { value: number | null | undefined; goodWhenDown?: boolean; suffix?: string }) {
  if (value === null || value === undefined) return <span className="text-xs text-ink-muted">No earlier data to compare</span>;
  const up = value > 0.05;
  const down = value < -0.05;
  const good = goodWhenDown ? down : up;
  const Icon = up ? ArrowUpRight : down ? ArrowDownRight : Minus;
  return (
    <span className="inline-flex flex-wrap items-center gap-1 text-xs">
      <span className={cn("inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 font-semibold", !up && !down ? "bg-muted text-ink-muted" : good ? "bg-good-soft text-good" : "bg-warn-soft text-warn")}>
        <Icon className="size-3.5" aria-hidden />
        {up ? "+" : down ? "−" : ""}
        {Math.abs(value).toFixed(0)}%
      </span>
      <span className="text-ink-muted">{suffix}</span>
    </span>
  );
}

export function MemberAvatar({ name, color, size = 32, ring = false }: { name: string; color?: string; size?: number; ring?: boolean }) {
  return (
    <span
      className={cn("inline-grid shrink-0 place-items-center rounded-full font-bold text-white", ring && "ring-2 ring-white")}
      style={{ width: size, height: size, background: color ?? "#0057B8", fontSize: Math.max(10, size * 0.36) }}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}

export function AvatarStack({ members, max = 4 }: { members: { name: string; color: string }[]; max?: number }) {
  return (
    <span className="flex -space-x-2" aria-label={members.map((m) => m.name).join(", ")}>
      {members.slice(0, max).map((m) => (
        <MemberAvatar key={m.name} name={m.name} color={m.color} size={26} ring />
      ))}
      {members.length > max && (
        <span className="inline-grid size-[26px] place-items-center rounded-full bg-muted text-xs font-bold text-ink-muted ring-2 ring-white">+{members.length - max}</span>
      )}
    </span>
  );
}

export function EmptyState({ icon: Icon = Info, title, body, action }: { icon?: LucideIcon; title: string; body?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-line bg-transparent px-6 py-10 text-center">
      <span className="mb-3 grid size-10 place-items-center rounded-lg bg-surface text-brand-blue-deep">
        <Icon className="size-5" aria-hidden />
      </span>
      <p className="font-bold text-ink">{title}</p>
      {body && <p className="mt-1 max-w-sm text-sm text-ink-muted">{body}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry, compact = false }: { error: unknown; onRetry?: () => void; compact?: boolean }) {
  const message = error instanceof ApiError ? error.message : "Something went wrong while loading this.";
  const notFound = error instanceof ApiError && error.status === 404;
  return (
    <div role="alert" className={cn("flex flex-col items-center justify-center rounded-2xl border border-bad/20 bg-bad-soft/50 text-center", compact ? "px-4 py-5" : "px-6 py-10")}>
      <AlertTriangle className="mb-2 size-6 text-bad" aria-hidden />
      <p className="font-semibold text-ink">{notFound ? "Not found" : "Couldn't load this"}</p>
      <p className="mt-1 max-w-sm text-sm text-ink-muted">{message}</p>
      <div className="mt-4 flex gap-2">
        {onRetry && !notFound && (
          <Button variant="outline" onClick={onRetry}>
            <RefreshCw className="size-4" aria-hidden /> Try again
          </Button>
        )}
        {notFound && (
          <Button variant="outline" nativeButton={false} render={<Link href="/groups" />}>
            Go to my groups
          </Button>
        )}
      </div>
    </div>
  );
}

export function LoadingBlock({ rows = 3, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("space-y-3", className)} aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-16 w-full rounded-xl bg-line/60" />
      ))}
    </div>
  );
}

export function StatTile({ label, value, sub, icon: Icon, accent = false, className }: { label: string; value: React.ReactNode; sub?: React.ReactNode; icon?: LucideIcon; accent?: boolean; className?: string }) {
  return (
    <div className={cn("card-surface flex min-w-0 flex-col gap-1.5 p-4", accent && "border-t-2 border-t-brand-yellow-strong", className)}>
      <div className="flex items-center gap-1.5 text-xs font-semibold text-ink-muted">
        {Icon && <Icon className="size-3.5 text-brand-blue" aria-hidden />}
        {label}
      </div>
      <div className="text-[26px] font-extrabold leading-none tracking-tight text-ink">{value}</div>
      {sub && <div className="min-h-5">{sub}</div>}
    </div>
  );
}

/** A Button rendered as a Next.js link (Base UI `render` prop). */
export function LinkButton({ href, ...props }: React.ComponentProps<typeof Button> & { href: string }) {
  return <Button nativeButton={false} render={<Link href={href} />} {...props} />;
}
