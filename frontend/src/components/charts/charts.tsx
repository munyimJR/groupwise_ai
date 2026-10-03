"use client";

import { Bar, CartesianGrid, ComposedChart, ErrorBar, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis, Area, Cell } from "recharts";

import { fmtDate, taka, takaCompact } from "@/lib/format";
import type { ForecastDay } from "@/lib/types";
import { cn } from "@/lib/utils";
import { categoryColor, chart, foldCategories } from "@/lib/viz";

function TooltipBox({ title, rows }: { title: string; rows: { label: string; value: string; color?: string; dash?: boolean }[] }) {
  return (
    <div className="rounded-xl border border-line bg-white px-3 py-2 text-xs shadow-[var(--shadow-lift)]">
      <p className="mb-1 font-semibold text-ink">{title}</p>
      {rows.map((r) => (
        <p key={r.label} className="flex items-center justify-between gap-4 text-ink-muted">
          <span className="inline-flex items-center gap-1.5">
            {r.color && <span className={cn("inline-block h-2 w-2 rounded-full", r.dash && "h-0.5 w-3 rounded-none")} style={{ background: r.color }} />}
            {r.label}
          </span>
          <span className="tabular font-semibold text-ink">{r.value}</span>
        </p>
      ))}
    </div>
  );
}

export function LegendRow({ items }: { items: { label: string; color: string; kind?: "dot" | "line" | "band" }[] }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted" aria-hidden>
      {items.map((i) => (
        <span key={i.label} className="inline-flex items-center gap-1.5">
          <span
            className={cn(i.kind === "line" ? "h-0.5 w-4" : i.kind === "band" ? "h-2.5 w-4 rounded-sm" : "size-2.5 rounded-[3px]")}
            style={{ background: i.color }}
          />
          {i.label}
        </span>
      ))}
    </div>
  );
}

/** Daily spending (columns) with a 7-day moving average (line). */
export function SpendTrendChart({ data, days = 60, height = 220 }: { data: { date: string; total: number; ma7: number }[]; days?: number; height?: number }) {
  const rows = data.slice(-days);
  return (
    <figure>
      <LegendRow items={[{ label: "Daily spending", color: "#b9d2f2" }, { label: "7-day average", color: chart.primary, kind: "line" }]} />
      <div style={{ height }} className="mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke={chart.grid} />
            <XAxis dataKey="date" tickFormatter={(d) => fmtDate(d)} tick={{ fontSize: 11, fill: chart.axis }} axisLine={{ stroke: chart.baseline }} tickLine={false} minTickGap={28} />
            <YAxis tickFormatter={(v) => takaCompact(v)} tick={{ fontSize: 11, fill: chart.axis }} axisLine={false} tickLine={false} width={52} />
            <Tooltip
              cursor={{ fill: "rgba(0,87,184,0.06)" }}
              content={({ active, payload }) =>
                active && payload?.length ? (
                  <TooltipBox
                    title={fmtDate(String(payload[0].payload.date))}
                    rows={[
                      { label: "Spent", value: taka(payload[0].payload.total), color: "#b9d2f2" },
                      { label: "7-day average", value: taka(payload[0].payload.ma7), color: chart.primary, dash: true },
                    ]}
                  />
                ) : null
              }
            />
            <Bar dataKey="total" fill="#b9d2f2" radius={[4, 4, 0, 0]} maxBarSize={16} />
            <Line dataKey="ma7" stroke={chart.primary} strokeWidth={2} dot={false} strokeLinecap="round" type="monotone" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="sr-only">Daily group spending for the last {days} days with a seven-day moving average.</figcaption>
    </figure>
  );
}

/** Forecast columns with an 80% range whisker; projected pressure days highlighted. */
export function ForecastChart({ daily, pressureDates, height = 240 }: { daily: ForecastDay[]; pressureDates: string[]; height?: number }) {
  const rows = daily.map((d) => ({ ...d, err: [d.total - d.low, d.high - d.total], pressure: pressureDates.includes(d.date) }));
  return (
    <figure>
      <LegendRow
        items={[
          { label: "Projected spending", color: chart.primary },
          { label: "High-pressure day", color: "#f5c400" },
          { label: "80% range", color: chart.inkMuted, kind: "line" },
        ]}
      />
      <div style={{ height }} className="mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 12, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke={chart.grid} />
            <XAxis
              dataKey="date"
              tickFormatter={(d, i) => `${rows[i]?.dow ?? ""} ${fmtDate(d).split(" ")[0]}${rows[i]?.pressure ? " ▲" : ""}`}
              tick={{ fontSize: 11, fill: chart.axis }}
              axisLine={{ stroke: chart.baseline }}
              tickLine={false}
              interval={rows.length > 14 ? "preserveStartEnd" : 0}
              minTickGap={8}
            />
            <YAxis tickFormatter={(v) => takaCompact(v)} tick={{ fontSize: 11, fill: chart.axis }} axisLine={false} tickLine={false} width={52} />
            <Tooltip
              cursor={{ fill: "rgba(0,87,184,0.06)" }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const p = payload[0].payload as (typeof rows)[number];
                const cats = Object.entries(p.by_category).sort((a, b) => b[1] - a[1]).slice(0, 3);
                return (
                  <TooltipBox
                    title={`${p.dow} ${fmtDate(p.date)}${p.pressure ? " · high pressure" : ""}`}
                    rows={[
                      { label: "Projected", value: taka(p.total), color: p.pressure ? "#f5c400" : chart.primary },
                      { label: "80% range", value: `${taka(p.low)}–${taka(p.high)}` },
                      ...cats.map(([c, v]) => ({ label: c, value: taka(v), color: categoryColor(c) })),
                    ]}
                  />
                );
              }}
            />
            <Bar dataKey="total" radius={[4, 4, 0, 0]} maxBarSize={24}>
              {rows.map((r) => (
                <Cell key={r.date} fill={r.pressure ? "#f5c400" : chart.primary} />
              ))}
              <ErrorBar dataKey="err" width={6} stroke={chart.inkMuted} strokeWidth={1.25} />
            </Bar>
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="sr-only">Projected daily spending with an 80% range; high-pressure days are marked with a triangle.</figcaption>
    </figure>
  );
}

/** Cumulative contributions (actual) and the projection to the deadline vs the target. */
export function GoalProjectionChart({
  weekly,
  startDate,
  deadline,
  saved,
  target,
  rateWeekly,
  scenarioRateWeekly,
  daysLeft,
  height = 240,
}: {
  weekly: { start: string; amount: number }[];
  startDate: string;
  deadline: string;
  saved: number;
  target: number;
  rateWeekly: number;
  scenarioRateWeekly?: number;
  daysLeft: number;
  height?: number;
}) {
  const start = new Date(`${startDate}T00:00:00`).getTime();
  const end = new Date(`${deadline}T00:00:00`).getTime();
  const today = end - Math.max(0, daysLeft) * 86400000;
  const rows: { t: number; actual?: number; projected?: number; scenario?: number }[] = [];
  let cum = 0;
  weekly.forEach((w) => {
    cum += w.amount;
    const t = Math.min(new Date(`${w.start}T00:00:00`).getTime() + 6 * 86400000, today);
    rows.push({ t, actual: cum });
  });
  if (!rows.length) rows.push({ t: start, actual: 0 });
  const last = rows[rows.length - 1];
  last.actual = saved;
  last.projected = saved;
  if (scenarioRateWeekly !== undefined) last.scenario = saved;
  const weeksLeft = Math.max(0, (end - last.t) / (7 * 86400000));
  const steps = Math.max(1, Math.ceil(weeksLeft));
  for (let i = 1; i <= steps; i++) {
    const frac = Math.min(i, weeksLeft) ;
    const t = last.t + frac * 7 * 86400000;
    const row: (typeof rows)[number] = { t, projected: saved + rateWeekly * frac };
    if (scenarioRateWeekly !== undefined) row.scenario = saved + scenarioRateWeekly * frac;
    rows.push(row);
  }
  const maxY = Math.max(target * 1.1, ...rows.map((r) => Math.max(r.projected ?? 0, r.scenario ?? 0, r.actual ?? 0)));
  return (
    <figure>
      <LegendRow
        items={[
          { label: "Saved so far", color: chart.primary, kind: "line" },
          { label: "Projected (current pace)", color: "#86b6ef", kind: "line" },
          ...(scenarioRateWeekly !== undefined ? [{ label: "What-If scenario", color: "#11805a", kind: "line" as const }] : []),
          { label: "Target", color: "#f5c400", kind: "line" },
        ]}
      />
      <div style={{ height }} className="mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 12, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke={chart.grid} />
            <XAxis
              dataKey="t"
              type="number"
              domain={[start, end]}
              scale="time"
              tickFormatter={(t) => new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" }).format(new Date(t))}
              tick={{ fontSize: 11, fill: chart.axis }}
              axisLine={{ stroke: chart.baseline }}
              tickLine={false}
              minTickGap={30}
            />
            <YAxis domain={[0, maxY]} tickFormatter={(v) => takaCompact(v)} tick={{ fontSize: 11, fill: chart.axis }} axisLine={false} tickLine={false} width={52} />
            <ReferenceLine y={target} stroke="#f5c400" strokeWidth={2} label={{ value: `Target ${taka(target)}`, position: "insideTopLeft", fill: chart.ink, fontSize: 11 }} />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const p = payload[0].payload as (typeof rows)[number];
                const r: { label: string; value: string; color?: string }[] = [];
                if (p.actual !== undefined) r.push({ label: "Saved", value: taka(p.actual), color: chart.primary });
                if (p.projected !== undefined) r.push({ label: "Projected", value: taka(p.projected), color: "#86b6ef" });
                if (p.scenario !== undefined) r.push({ label: "Scenario", value: taka(p.scenario), color: "#11805a" });
                return <TooltipBox title={new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(p.t))} rows={r} />;
              }}
            />
            <Area dataKey="actual" stroke="none" fill={chart.primarySoft} type="monotone" connectNulls={false} />
            <Line dataKey="actual" stroke={chart.primary} strokeWidth={2} dot={false} type="monotone" connectNulls={false} />
            <Line dataKey="projected" stroke="#86b6ef" strokeWidth={2} strokeDasharray="6 4" dot={false} connectNulls />
            {scenarioRateWeekly !== undefined && <Line dataKey="scenario" stroke="#11805a" strokeWidth={2} dot={false} connectNulls />}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="sr-only">Goal savings so far and the projection to the deadline compared with the target.</figcaption>
    </figure>
  );
}

/** Horizontal category bars with direct labels (accessible HTML, no colour-only identity). */
export function CategoryBars({ rows, showChange = false, max = 7 }: { rows: { category: string; current: number; change_pct?: number | null; share_pct?: number }[]; showChange?: boolean; max?: number }) {
  const folded = foldCategories(rows, (r) => r.current).slice(0, max);
  const byCat = Object.fromEntries(rows.map((r) => [r.category, r]));
  const top = Math.max(...folded.map((f) => f.value), 1);
  const total = folded.reduce((s, f) => s + f.value, 0) || 1;
  return (
    <ul className="space-y-2.5" aria-label="Spending by category">
      {folded.map((f) => {
        const src = byCat[f.category];
        return (
          <li key={f.category} className="grid grid-cols-[minmax(84px,120px)_1fr_auto] items-center gap-3 text-sm">
            <span className="flex items-center gap-2 truncate font-medium text-ink">
              <span className="size-2.5 shrink-0 rounded-[3px]" style={{ background: f.color }} aria-hidden />
              {f.category}
            </span>
            <span className="h-2.5 overflow-hidden rounded-full bg-[#f1f4f8]">
              <span className="block h-full rounded-full" style={{ width: `${(f.value / top) * 100}%`, background: f.color }} />
            </span>
            <span className="tabular text-right text-[13px] font-semibold text-ink">
              {taka(f.value)}
              <span className="ml-1.5 font-normal text-ink-muted">{Math.round((f.value / total) * 100)}%</span>
              {showChange && src?.change_pct !== undefined && src?.change_pct !== null && (
                <span className={cn("ml-1.5 text-xs font-semibold", src.change_pct > 0 ? "text-warn" : "text-good")}>
                  {src.change_pct > 0 ? "▲" : "▼"} {Math.abs(src.change_pct).toFixed(0)}%
                </span>
              )}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
