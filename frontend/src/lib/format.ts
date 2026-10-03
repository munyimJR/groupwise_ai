const intl0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const intl2 = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Format integer paisa as taka, e.g. 825000 → "৳8,250". */
export function taka(paisa: number | null | undefined, opts: { decimals?: boolean; sign?: boolean } = {}): string {
  if (paisa === null || paisa === undefined || Number.isNaN(paisa)) return "—";
  const value = paisa / 100;
  const body = opts.decimals && Math.round(value) !== value ? intl2.format(Math.abs(value)) : intl0.format(Math.abs(Math.round(value)));
  const sign = value < 0 ? "−" : opts.sign && value > 0 ? "+" : "";
  return `${sign}৳${body}`;
}

/** Compact taka for chart axes: 1250000 → "৳12.5k". */
export function takaCompact(paisa: number): string {
  const v = paisa / 100;
  if (Math.abs(v) >= 100000) return `৳${(v / 100000).toFixed(1).replace(/\.0$/, "")}L`;
  if (Math.abs(v) >= 1000) return `৳${(v / 1000).toFixed(1).replace(/\.0$/, "")}k`;
  return `৳${Math.round(v)}`;
}

export function pct(v: number | null | undefined, opts: { sign?: boolean; digits?: number } = {}): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const d = opts.digits ?? 0;
  const s = opts.sign && v > 0 ? "+" : v < 0 ? "−" : "";
  return `${s}${Math.abs(v).toFixed(d)}%`;
}

export function likelihood(v: number): string {
  if (v < 1) return "<1%";
  if (v > 99) return ">99%";
  return `${Math.round(v)}%`;
}

const dateFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" });
const dateYearFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });
const timeFmt = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit" });
const weekdayFmt = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short" });

/** Expense times are Asia/Dhaka wall-clock times without a timezone suffix. */
export function parseLocal(iso: string): Date {
  return new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
}

export const fmtDate = (iso: string) => dateFmt.format(parseLocal(iso));
export const fmtDateYear = (iso: string) => dateYearFmt.format(parseLocal(iso));
export const fmtTime = (iso: string) => timeFmt.format(parseLocal(iso));
export const fmtWeekday = (iso: string) => weekdayFmt.format(parseLocal(iso));

export function relativeTime(iso: string): string {
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} h ago`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} d ago`;
  return dateFmt.format(d);
}

export function dayLabel(iso: string): string {
  const d = parseLocal(iso);
  const today = new Date();
  const y = new Date(today);
  y.setDate(today.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return "Today";
  if (d.toDateString() === y.toDateString()) return "Yesterday";
  return weekdayFmt.format(d);
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

export function toLocalInputValue(d = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
