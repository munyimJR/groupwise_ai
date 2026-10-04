"use client";

import {
  AlertTriangle,
  ArrowRight,
  BadgeCheck,
  Bot,
  CalendarClock,
  Database,
  Eye,
  FlaskConical,
  Lock,
  Receipt,
  Scale,
  ShieldCheck,
  Sparkles,
  Tags,
  Target,
  TrendingUp,
  Users,
} from "lucide-react";
import Link from "next/link";

import { DemoButton } from "@/components/auth/demo-button";
import { Logo } from "@/components/brand/logo";
import { LinkButton } from "@/components/common/primitives";
import { useAuth } from "@/lib/auth";

const PIPELINE = [
  { icon: Receipt, title: "Transactions", body: "Shared expenses, splits and settlements — exact to the paisa." },
  { icon: Database, title: "Financial intelligence", body: "Patterns, drivers and group dynamics computed from your data." },
  { icon: TrendingUp, title: "Prediction", body: "Cash-flow forecast, unusual-expense detection, goal likelihood." },
  { icon: Sparkles, title: "Recommendation", body: "Explainable suggestions with a simulated outcome." },
  { icon: BadgeCheck, title: "Your decision", body: "AI recommends. Your group stays in control." },
];

const QUESTIONS = [
  "Where is our money going?",
  "Why did our spending change?",
  "What is likely to happen next week?",
  "What looks unusual?",
  "Can we reach our trip goal?",
  "What should we change?",
  "Who is carrying most of the upfront costs?",
];

const FEATURES = [
  { icon: Tags, title: "Smart categorization", method: "ML classifier (TF-IDF + logistic regression)", body: "Type “Lunch at Kacchi Bhai 850” — amount, merchant and category are understood, with confidence and the words that drove it. Corrections are remembered." },
  { icon: AlertTriangle, title: "Unusual expense detection", method: "Isolation Forest + robust statistics", body: "Flags spikes, odd hours, rare categories and duplicates against your group's own history — with reasons. Nothing is ever blocked." },
  { icon: CalendarClock, title: "Cash-flow forecast", method: "Seasonal model + recurring-bill detection", body: "Next 7–30 days of spending with an 80% range, the high-pressure days, and why." },
  { icon: Target, title: "Goal planner", method: "Projection + Monte-Carlo simulation", body: "Will the trip fund make it? See the projected gap, the likelihood, and what would close it." },
  { icon: FlaskConical, title: "What-If simulator", method: "Scenario engine on the forecast", body: "Cut dining 15%? Expenses up 20%? See savings, pressure and goal impact instantly." },
  { icon: Users, title: "Group dynamics", method: "Behavioural analytics (observable payments only)", body: "Who fronts the money, how long reimbursements take, and a fairer payer rotation." },
  { icon: Bot, title: "Ask GroupWise", method: "Grounded LLM copilot", body: "Ask in plain English. Answers cite computed facts, and every figure is verified against your data." },
  { icon: Scale, title: "Settle up, simplified", method: "Deterministic algorithm — not AI", body: "Exact balances and the minimum set of payments to clear everyone." },
];

const RESPONSIBLE = [
  { icon: Lock, title: "Synthetic data only", body: "The prototype uses generated data — no real customer information." },
  { icon: Eye, title: "Explainable", body: "Every prediction shows its evidence, method and confidence." },
  { icon: Tags, title: "Clearly labelled", body: "Facts, predictions, assumptions and recommendations are marked apart." },
  { icon: ShieldCheck, title: "Grounded AI", body: "The language model never calculates money; it explains verified facts." },
];

export default function LandingPage() {
  const { status } = useAuth();
  return (
    <div className="min-h-dvh bg-white">
      <header className="sticky top-0 z-30 border-b border-line/70 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
          <Link href="/" aria-label="GroupWise AI home">
            <Logo />
          </Link>
          <nav className="flex items-center gap-1 sm:gap-2" aria-label="Site">
            <Link href="/how-it-works" className="hidden rounded-lg px-3 py-2.5 text-sm font-semibold text-ink hover:bg-surface sm:block">
              How the AI works
            </Link>
            {status === "authenticated" ? (
              <LinkButton href="/groups" variant="blue">
                Open app
              </LinkButton>
            ) : (
              <>
                <Link href="/login" className="tap-target rounded-lg px-3 py-2.5 text-sm font-semibold text-ink hover:bg-surface">
                  Sign in
                </Link>
                <DemoButton size="default" label="Try demo" className="hidden sm:inline-flex" />
              </>
            )}
          </nav>
        </div>
      </header>

      <main id="main" tabIndex={-1} className="outline-none">
        <section className="relative overflow-hidden border-b border-line bg-gradient-to-b from-white to-surface">
          <div className="pointer-events-none absolute -right-24 -top-24 size-[420px] rounded-full bg-brand-yellow/30 blur-3xl" aria-hidden />
          <div className="relative mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:py-20">
            <div>
              <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-brand-blue/15 bg-brand-blue-soft px-3 py-1 text-xs font-bold text-brand-blue-deep">
                <Sparkles className="size-3.5" aria-hidden /> Shared financial intelligence for groups
              </p>
              <h1 className="text-[38px] font-extrabold leading-[1.05] tracking-tight text-ink sm:text-5xl lg:text-[56px]">
                Split expenses. <span className="text-brand-blue">Understand spending.</span> Predict what&apos;s next.{" "}
                <span className="relative whitespace-nowrap">
                  <span className="relative z-10">Decide better together.</span>
                  <span className="absolute inset-x-0 bottom-1 -z-0 h-3 rounded bg-brand-yellow sm:bottom-2" aria-hidden />
                </span>
              </h1>
              <p className="mt-5 max-w-xl text-base text-ink-muted sm:text-lg">
                GroupWise AI helps roommates, friends and travel groups understand where shared money goes, see financial pressure coming,
                catch unusual expenses and plan goals — with AI that explains itself.
              </p>
              <div className="mt-7 flex flex-col gap-3 sm:flex-row">
                {status === "authenticated" ? (
                  <LinkButton href="/groups" size="lg">
                    Open my dashboard <ArrowRight className="size-4" aria-hidden />
                  </LinkButton>
                ) : (
                  <>
                    <DemoButton />
                    <LinkButton href="/signup" size="lg" variant="outline">
                      Create a free account
                    </LinkButton>
                  </>
                )}
              </div>
              <p className="mt-3 text-xs text-ink-muted">One click, no sign-up: a private sandbox with three synthetic groups. Synthetic data only.</p>
            </div>

            <div className="card-surface relative p-5 sm:p-6" aria-label="How GroupWise turns transactions into decisions">
              <p className="mb-4 text-xs font-bold uppercase tracking-[0.12em] text-ink-muted">From transactions to decisions</p>
              <ol className="space-y-3">
                {PIPELINE.map((step, i) => (
                  <li key={step.title} className="flex items-start gap-3">
                    <span className={i === PIPELINE.length - 1 ? "grid size-10 shrink-0 place-items-center rounded-xl bg-brand-yellow text-ink" : "grid size-10 shrink-0 place-items-center rounded-xl bg-brand-blue-soft text-brand-blue"}>
                      <step.icon className="size-5" aria-hidden />
                    </span>
                    <div>
                      <p className="text-sm font-bold text-ink">
                        <span className="mr-1.5 text-ink-muted">{i + 1}.</span>
                        {step.title}
                      </p>
                      <p className="text-[13px] text-ink-muted">{step.body}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
          <div className="grid gap-8 lg:grid-cols-2 lg:items-center">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-brand-blue">Beyond “who owes whom”</p>
              <h2 className="mt-2 text-3xl font-extrabold leading-tight text-ink">An expense splitter answers one question. GroupWise answers the ones that matter.</h2>
              <p className="mt-3 text-ink-muted">
                Fragmented group spending makes it hard to see shared responsibility, understand behaviour and anticipate pressure. GroupWise
                combines exact shared-expense management with financial intelligence built for people who manage money together.
              </p>
            </div>
            <ul className="grid gap-2 sm:grid-cols-2">
              {QUESTIONS.map((q) => (
                <li key={q} className="flex items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2.5 text-sm font-semibold text-ink">
                  <span className="grid size-6 shrink-0 place-items-center rounded-full bg-brand-yellow text-xs font-bold">?</span>
                  {q}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="border-y border-line bg-surface">
          <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-brand-blue">What&apos;s inside</p>
            <h2 className="mt-2 max-w-2xl text-3xl font-extrabold text-ink">Purposeful AI — each feature does one job, and says how it did it.</h2>
            <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {FEATURES.map((f) => (
                <article key={f.title} className="card-surface flex flex-col p-5">
                  <span className="grid size-10 place-items-center rounded-xl bg-brand-blue-soft text-brand-blue">
                    <f.icon className="size-5" aria-hidden />
                  </span>
                  <h3 className="mt-3 text-base font-bold text-ink">{f.title}</h3>
                  <p className="mt-1 text-[13px] text-ink-muted">{f.body}</p>
                  <p className="mt-auto pt-3 text-xs font-semibold text-brand-blue-deep">{f.method}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
          <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-brand-blue">Responsible by design</p>
              <h2 className="mt-2 text-3xl font-extrabold text-ink">AI recommends. Your group decides.</h2>
              <p className="mt-3 text-ink-muted">
                Money is personal. GroupWise never blocks a transaction, never judges people, and never lets a language model invent a number.
              </p>
              <LinkButton href="/how-it-works" variant="soft" className="mt-5">
                See models, metrics &amp; safeguards <ArrowRight className="size-4" aria-hidden />
              </LinkButton>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {RESPONSIBLE.map((r) => (
                <div key={r.title} className="rounded-2xl border border-line p-4">
                  <r.icon className="size-5 text-brand-blue" aria-hidden />
                  <p className="mt-2 font-bold text-ink">{r.title}</p>
                  <p className="text-[13px] text-ink-muted">{r.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="bg-brand-blue-deep text-white">
          <div className="mx-auto flex max-w-6xl flex-col items-start gap-5 px-4 py-12 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-2xl font-extrabold text-white sm:text-3xl">See it with a real group&apos;s worth of data.</h2>
              <p className="mt-1 text-white/75">Three synthetic groups — classmates, roommates and a finished trip — ready to explore.</p>
            </div>
            {status === "authenticated" ? (
              <LinkButton href="/groups" size="lg">
                Open my dashboard
              </LinkButton>
            ) : (
              <DemoButton />
            )}
          </div>
        </section>
      </main>

      <footer className="border-t border-line bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-8 text-xs text-ink-muted sm:px-6 md:flex-row md:items-center md:justify-between">
          <Logo className="scale-90" />
          <p className="max-w-2xl">
            GroupWise AI is an independent hackathon prototype for digital financial services. It is not affiliated with or endorsed by upay or
            any financial institution. All demo data is synthetic. Not financial advice.
          </p>
        </div>
      </footer>
    </div>
  );
}
