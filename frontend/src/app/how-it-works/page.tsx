"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowRight, Bot, Calculator, Cpu, Database, Eye, FlaskConical, Lock, Scale, ShieldCheck, UserCheck } from "lucide-react";
import Link from "next/link";

import { Logo } from "@/components/brand/logo";
import { LinkButton } from "@/components/common/primitives";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface ModelsResponse {
  evaluation: {
    generated_at: string;
    label: string;
    categorizer: { n_test: number; n_train: number; n_classes: number; subcategory: Record<string, number>; category: Record<string, number>; accuracy_when_confident: number; confident_share: number };
    anomaly: { validation: Record<string, number>; test: { precision: number; recall: number; f1: number; false_positive_rate: number; groups: number; transactions: number; injected_anomalies: number; recall_by_kind: Record<string, number> } };
    forecast: { groups: number; windows: number; mae_7day: number; rmse_7day: number; baseline_mean28: { mae_7day: number; rmse_7day: number }; baseline_lastweek: { mae_7day: number }; mae_improvement_vs_mean28_pct: number; weekly_mape: number; bias_pct: number };
  } | null;
  validation: {
    generated_at: string;
    categorizer: {
      comparison: Record<string, { sub_accuracy: number; sub_accuracy_ci: [number, number] }>;
      calibration: { ece: number };
      calibration_temperature_scaled?: { ece: number; temperature: number };
      stress_set?: { n: number; groupwise: { sub_accuracy: number }; keyword_rules: { sub_accuracy: number } };
    };
    anomaly: {
      comparison: Record<string, { f1: number; f1_ci: [number, number] }>;
      prospective?: { online_past_only: { f1: number }; batch_same_transactions: { f1: number } };
    };
    forecast: {
      comparison: Record<string, { mae_7day: number; mae_ci: [number, number] }>;
      interval_80?: { coverage: number; coverage_before_tuning?: number };
      leakage?: { future_data_changes_forecast: boolean };
    };
  } | null;
  models: { key: string; name: string; type: string; version: string; method: string; inputs: string; outputs: string; limitations: string }[];
  deterministic: { name: string; method: string }[];
}

const pct = (v: number, d = 1) => `${(v * 100).toFixed(d)}%`;

const FLOW = [
  { icon: Database, title: "Your group's data", body: "Expenses, splits, settlements, goals (PostgreSQL / Supabase)" },
  { icon: Calculator, title: "Deterministic finance", body: "Exact balances & debt simplification — not AI" },
  { icon: Cpu, title: "Analytics & ML", body: "Categorizer · anomaly detector · forecast · goal simulation" },
  { icon: Scale, title: "Structured facts", body: "Typed as fact / prediction / assumption / recommendation" },
  { icon: Bot, title: "LLM explanation layer", body: "Words only — every figure is re-checked against the facts" },
  { icon: UserCheck, title: "You decide", body: "Review, accept or dismiss. Nothing is automatic." },
];

export default function HowItWorksPage() {
  const { status } = useAuth();
  const { data } = useQuery({ queryKey: ["models"], queryFn: () => api<ModelsResponse>("/meta/models", { auth: false }), staleTime: Infinity });
  const ev = data?.evaluation;

  return (
    <div className="min-h-dvh bg-surface">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" aria-label="GroupWise AI home">
            <Logo />
          </Link>
          <LinkButton href={status === "authenticated" ? "/groups" : "/"} variant="outline">
            {status === "authenticated" ? "Back to the app" : "Home"}
          </LinkButton>
        </div>
      </header>
      <main className="mx-auto max-w-6xl space-y-10 px-4 py-10 sm:px-6">
        <section>
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-brand-blue">Transparency</p>
          <h1 className="mt-2 text-3xl font-extrabold text-ink sm:text-4xl">How GroupWise AI works</h1>
          <p className="mt-3 max-w-3xl text-ink-muted">
            GroupWise separates exact financial logic, statistical/ML models and the language model, so every number can be traced to your data and
            every prediction is labelled as one. The language model never calculates money.
          </p>
        </section>

        <section aria-labelledby="arch">
          <h2 id="arch" className="mb-4 text-xl font-extrabold text-ink">Architecture: data → intelligence → explanation → your decision</h2>
          <ol className="grid gap-3 md:grid-cols-3 lg:grid-cols-6">
            {FLOW.map((f, i) => (
              <li key={f.title} className="relative">
                <div className={i === FLOW.length - 1 ? "h-full rounded-2xl border border-brand-yellow-strong/50 bg-brand-yellow-soft p-4" : "card-surface h-full p-4"}>
                  <f.icon className="size-5 text-brand-blue" aria-hidden />
                  <p className="mt-2 text-sm font-bold text-ink">
                    {i + 1}. {f.title}
                  </p>
                  <p className="mt-1 text-xs text-ink-muted">{f.body}</p>
                </div>
                {i < FLOW.length - 1 && (
                  <>
                    <ArrowRight className="absolute -right-3 top-1/2 z-10 hidden size-4 -translate-y-1/2 text-ink-muted lg:block" aria-hidden />
                    <ArrowDown className="mx-auto my-1 size-4 text-ink-muted md:hidden" aria-hidden />
                  </>
                )}
              </li>
            ))}
          </ol>
        </section>

        <section aria-labelledby="layers" className="grid gap-4 lg:grid-cols-3">
          <h2 id="layers" className="sr-only">
            Deterministic logic, ML models and LLM components
          </h2>
          <div className="card-surface p-5">
            <p className="flex items-center gap-2 font-bold text-ink">
              <Calculator className="size-5 text-brand-blue" aria-hidden /> Deterministic business logic
            </p>
            <ul className="mt-3 space-y-2 text-sm">
              {data?.deterministic.map((d) => (
                <li key={d.name}>
                  <span className="font-semibold text-ink">{d.name}</span>
                  <span className="block text-xs text-ink-muted">{d.method}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="card-surface p-5">
            <p className="flex items-center gap-2 font-bold text-ink">
              <Cpu className="size-5 text-brand-blue" aria-hidden /> ML / statistical models
            </p>
            <ul className="mt-3 space-y-2 text-sm">
              {data?.models
                .filter((m) => m.key !== "copilot")
                .map((m) => (
                  <li key={m.key}>
                    <span className="font-semibold text-ink">{m.name}</span>
                    <span className="block text-xs text-ink-muted">{m.method}</span>
                  </li>
                ))}
            </ul>
          </div>
          <div className="card-surface p-5">
            <p className="flex items-center gap-2 font-bold text-ink">
              <Bot className="size-5 text-brand-blue" aria-hidden /> LLM components
            </p>
            <ul className="mt-3 space-y-2 text-sm">
              {data?.models
                .filter((m) => m.key === "copilot")
                .map((m) => (
                  <li key={m.key}>
                    <span className="font-semibold text-ink">{m.name}</span>
                    <span className="block text-xs text-ink-muted">{m.method}</span>
                  </li>
                ))}
              <li className="text-xs text-ink-muted">If the LLM is unavailable or fails the grounding check, a deterministic answer is shown instead. Every other feature works without it.</li>
            </ul>
          </div>
        </section>

        <section aria-labelledby="eval">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
            <h2 id="eval" className="text-xl font-extrabold text-ink">Model evaluation</h2>
            <span className="rounded-full bg-warn-soft px-3 py-1 text-xs font-bold text-warn">Synthetic-data simulation · prototype validation</span>
          </div>
          {!ev ? (
            <p className="text-sm text-ink-muted">Evaluation results are not available.</p>
          ) : (
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="card-surface p-5">
                <p className="font-bold text-ink">Expense categorization</p>
                <p className="text-xs text-ink-muted">
                  {ev.categorizer.n_test} test examples using merchants & phrasings never seen in training · {ev.categorizer.n_classes} subcategories
                </p>
                <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                  <Metric label="Category accuracy" value={pct(ev.categorizer.category.accuracy)} />
                  <Metric label="Subcategory accuracy" value={pct(ev.categorizer.subcategory.accuracy)} />
                  <Metric label="Macro F1 (subcat.)" value={pct(ev.categorizer.subcategory.f1_macro)} />
                  <Metric label="Accuracy when confident" value={pct(ev.categorizer.accuracy_when_confident)} />
                </dl>
                <p className="mt-2 text-xs text-ink-muted">Confident on {pct(ev.categorizer.confident_share, 0)} of cases; otherwise the app asks the user to confirm.</p>
              </div>
              <div className="card-surface p-5">
                <p className="font-bold text-ink">Unusual expense detection</p>
                <p className="text-xs text-ink-muted">
                  Test: {ev.anomaly.test.groups} unseen groups · {ev.anomaly.test.transactions.toLocaleString()} transactions · {ev.anomaly.test.injected_anomalies} labelled anomalies
                </p>
                <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                  <Metric label="Precision" value={pct(ev.anomaly.test.precision)} />
                  <Metric label="Recall" value={pct(ev.anomaly.test.recall)} />
                  <Metric label="F1" value={pct(ev.anomaly.test.f1)} />
                  <Metric label="False-positive rate" value={pct(ev.anomaly.test.false_positive_rate, 2)} />
                </dl>
                <p className="mt-2 text-xs text-ink-muted">
                  Recall by type: {Object.entries(ev.anomaly.test.recall_by_kind).map(([k, v]) => `${k} ${pct(v, 0)}`).join(" · ")}
                </p>
              </div>
              <div className="card-surface p-5">
                <p className="font-bold text-ink">Cash-flow forecast (7 days)</p>
                <p className="text-xs text-ink-muted">
                  Rolling-origin backtest · {ev.forecast.groups} groups · {ev.forecast.windows} windows
                </p>
                <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                  <Metric label="MAE (7-day total)" value={`৳${ev.forecast.mae_7day.toLocaleString()}`} />
                  <Metric label="Baseline MAE (28-day avg)" value={`৳${ev.forecast.baseline_mean28.mae_7day.toLocaleString()}`} />
                  <Metric label="RMSE (7-day total)" value={`৳${ev.forecast.rmse_7day.toLocaleString()}`} />
                  <Metric label="Improvement vs baseline" value={`${ev.forecast.mae_improvement_vs_mean28_pct}%`} />
                </dl>
                <p className="mt-2 text-xs text-ink-muted">
                  Weekly error {pct(ev.forecast.weekly_mape, 0)}, bias {ev.forecast.bias_pct > 0 ? "+" : ""}
                  {ev.forecast.bias_pct}%. Intervals come from each group&apos;s own backtest.
                </p>
              </div>
            </div>
          )}
          {ev && <p className="mt-3 text-xs text-ink-muted">Generated {ev.generated_at}. Thresholds were tuned on validation seeds and reported on separate test seeds.</p>}
        </section>

        {data?.validation && <Validation v={data.validation} />}

        <section aria-labelledby="ra" className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <h2 id="ra" className="col-span-full text-xl font-extrabold text-ink">Responsible AI safeguards</h2>
          {[
            { icon: Lock, t: "Privacy", b: "Synthetic data only. Service keys stay server-side; the database rejects direct client access (row-level security)." },
            { icon: Eye, t: "Explainability", b: "Every insight shows the observation, the inference, the evidence, the method and a confidence level." },
            { icon: Scale, t: "Transparency", b: "Facts, model predictions, assumptions, AI-worded explanations and recommendations are labelled differently." },
            { icon: UserCheck, t: "Human oversight", b: "AI recommends; people decide. Unusual expenses are flagged for review, never blocked." },
            { icon: ShieldCheck, t: "AI security", b: "Out-of-scope and prompt-injection requests are caught; expense text is treated as data; unverifiable numbers are rejected." },
            { icon: FlaskConical, t: "No overclaiming", b: "Projections say “projected”; likelihoods are simulations; What-If results are scenarios, not measured savings." },
          ].map((x) => (
            <div key={x.t} className="card-surface p-5">
              <x.icon className="size-5 text-brand-blue" aria-hidden />
              <p className="mt-2 font-bold text-ink">{x.t}</p>
              <p className="mt-1 text-sm text-ink-muted">{x.b}</p>
            </div>
          ))}
        </section>

        <section aria-labelledby="path" className="card-surface p-6">
          <h2 id="path" className="text-xl font-extrabold text-ink">Path to a digital financial service</h2>
          <ol className="mt-4 grid gap-3 md:grid-cols-4">
            {["Synthetic data (today)", "Prototype validation with student groups", "Controlled validation on governed, anonymised or aggregated data", "Potential integration with an MFS backend"].map((s, i) => (
              <li key={s} className="rounded-xl bg-surface p-4 text-sm font-semibold text-ink">
                <span className="mb-1 block text-xs font-bold text-brand-blue">Step {i + 1}</span>
                {s}
              </li>
            ))}
          </ol>
          <p className="mt-4 text-xs text-ink-muted">
            GroupWise AI is an independent hackathon prototype. It has no official integration with upay or any financial institution and no access to private
            financial data, and it makes no claims about business results.
          </p>
        </section>
      </main>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-surface p-2.5">
      <dt className="text-xs text-ink-muted">{label}</dt>
      <dd className="tabular text-lg font-extrabold text-ink">{value}</dd>
    </div>
  );
}

function Comparison({ title, rows, fmt }: { title: string; rows: [string, number, [number, number]][]; fmt: (v: number) => string }) {
  const best = rows.length - 1;
  return (
    <div className="card-surface p-5">
      <p className="font-bold text-ink">{title}</p>
      <table className="mt-3 w-full text-sm">
        <tbody>
          {rows.map(([name, v, ci], i) => (
            <tr key={name} className={i === best ? "font-bold text-ink" : "text-ink-muted"}>
              <td className="py-1 pr-3">{name}</td>
              <td className="tabular py-1 text-right">
                {fmt(v)}
                <span className="block text-xs font-normal text-ink-muted">
                  {fmt(ci[0])}–{fmt(ci[1])}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Validation({ v }: { v: NonNullable<ModelsResponse["validation"]> }) {
  const pick = <T,>(o: Record<string, T>, keys: string[]) => keys.filter((k) => k in o).map((k) => [k, o[k]] as const);
  const cat = Object.entries(v.categorizer.comparison);
  const catRows = ["Keyword", "Naive", "GroupWise as deployed"]
    .map((prefix) => cat.find(([k]) => k.startsWith(prefix)))
    .filter((r): r is (typeof cat)[number] => !!r)
    .map(([k, s]) => [k, s.sub_accuracy, s.sub_accuracy_ci] as [string, number, [number, number]]);
  const anRows = pick(v.anomaly.comparison, ["Rule: amount > 3x the group's median for that subcategory", "Isolation Forest only", "Hybrid without Isolation Forest", "GroupWise hybrid (all signals)"]).map(
    ([k, s]) => [k, s.f1, s.f1_ci] as [string, number, [number, number]],
  );
  const fcRows = pick(v.forecast.comparison, ["Mean of previous 28 days", "Same weekday, 4-week average", "GroupWise without recurring bills", "GroupWise forecast"]).map(
    ([k, s]) => [k, s.mae_7day, s.mae_ci] as [string, number, [number, number]],
  );
  return (
    <section aria-labelledby="val">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <h2 id="val" className="text-xl font-extrabold text-ink">Does each model beat simple rules?</h2>
        <span className="rounded-full bg-warn-soft px-3 py-1 text-xs font-bold text-warn">Synthetic test data · 95% confidence intervals</span>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Comparison title="Categorization: subcategory accuracy" rows={catRows} fmt={(x) => pct(x)} />
        <Comparison title="Unusual expenses: F1" rows={anRows} fmt={(x) => pct(x)} />
        <Comparison title="Forecast: 7-day error (MAE, lower is better)" rows={fcRows} fmt={(x) => `৳${Math.round(x).toLocaleString()}`} />
      </div>
      <ul className="mt-4 grid gap-2 text-sm text-ink md:grid-cols-2">
        {v.categorizer.stress_set && (
          <li className="card-surface p-3">
            <strong>Hand-written test:</strong> {pct(v.categorizer.stress_set.groupwise.sub_accuracy)} on {v.categorizer.stress_set.n} descriptions the data generator never
            produced (keyword rules: {pct(v.categorizer.stress_set.keyword_rules.sub_accuracy)}).
          </li>
        )}
        <li className="card-surface p-3">
          <strong>Calibration:</strong> categorizer calibration error {v.categorizer.calibration.ece.toFixed(3)}
          {v.categorizer.calibration_temperature_scaled && `, ${v.categorizer.calibration_temperature_scaled.ece.toFixed(3)} after temperature scaling`}.
          {v.forecast.interval_80 && ` Forecast 80% range covers ${pct(v.forecast.interval_80.coverage, 0)} of outcomes`}
          {v.forecast.interval_80?.coverage_before_tuning !== undefined && ` (was ${pct(v.forecast.interval_80.coverage_before_tuning, 0)} before tuning)`}.
        </li>
        {v.anomaly.prospective && (
          <li className="card-surface p-3">
            <strong>No look-ahead:</strong> scoring each expense with past data only gives F1 {pct(v.anomaly.prospective.online_past_only.f1)} (batch:{" "}
            {pct(v.anomaly.prospective.batch_same_transactions.f1)}).
            {v.forecast.leakage && !v.forecast.leakage.future_data_changes_forecast && " Forecasts don't change when future data is supplied."}
          </li>
        )}
        <li className="card-surface p-3">
          <strong>What is learned:</strong> two trained models (categorizer, Isolation Forest) and one fitted statistical forecaster. Goal likelihood is a
          simulation; drivers and dynamics are analytics. Real-user accuracy is measured in the pilot.
        </li>
      </ul>
      <p className="mt-3 text-xs text-ink-muted">Generated {v.generated_at}. Full method: docs/MODEL_VALIDATION.md.</p>
    </section>
  );
}

