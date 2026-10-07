"use client";

import {
  AlertTriangle,
  ArrowRight,
  BadgeCheck,
  Bot,
  CalendarClock,
  Eye,
  FlaskConical,
  Lock,
  Receipt,
  ShieldCheck,
  Tags,
  Target,
  TrendingUp,
  Users,
  Wallet,
} from "lucide-react";
import Link from "next/link";

import { DemoButton } from "@/components/auth/demo-button";
import { Logo } from "@/components/brand/logo";
import { LinkButton } from "@/components/common/primitives";
import { HoverLift } from "@/components/common/motion";
import { useAuth } from "@/lib/auth";

const PIPELINE = [
  { icon: Receipt, title: "Record", body: "Exact shared expenses, splits and settlements." },
  { icon: TrendingUp, title: "Understand", body: "Patterns, unusual entries and what may come next." },
  { icon: BadgeCheck, title: "Decide", body: "Goals, scenarios and clear next steps for your group." },
];

const QUESTIONS = [
  "Where is our money going?",
  "Why did our spending change?",
  "What is likely to happen next week?",
  "What looks unusual?",
  "Can we reach our trip goal?",
  "What should we change?",
];

const FEATURES = [
  { icon: Tags, title: "Smart categorization", method: "ML classifier (TF-IDF + logistic regression)", body: "Type “Lunch at Kacchi Bhai 850” — amount, merchant and category are understood, with confidence and the words that drove it. Corrections are remembered." },
  { icon: AlertTriangle, title: "Unusual expense detection", method: "Isolation Forest + robust statistics", body: "Flags spikes, odd hours, rare categories and duplicates against your group's own history — with reasons. Nothing is ever blocked." },
  { icon: CalendarClock, title: "Cash-flow forecast", method: "Seasonal model + recurring-bill detection", body: "Next 7–30 days of spending with an 80% range, the high-pressure days, and why." },
  { icon: Target, title: "Goal planner", method: "Projection + Monte-Carlo simulation", body: "Will the trip fund make it? See the projected gap, the likelihood, and what would close it." },
  { icon: FlaskConical, title: "What-If simulator", method: "Scenario engine on the forecast", body: "Cut dining 15%? Expenses up 20%? See savings, pressure and goal impact instantly." },
  { icon: Bot, title: "Ask GroupWise", method: "Grounded LLM copilot", body: "Ask in plain English. Answers cite computed facts, and every figure is verified against your data." },
  { icon: Wallet, title: "Wallet-connected settle-up", method: "Wallet integration · exact math, not AI", body: "Import your wallet's transactions (auto-categorized), then pay or request through the wallet. Fewest payments, recorded only when the wallet confirms." },
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
        <section className="relative overflow-hidden border-b border-line bg-white">
          <div className="relative mx-auto grid max-w-6xl gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:gap-16 lg:py-24">
            <div className="max-w-xl">
              <p className="mb-5 text-xs font-bold uppercase tracking-[0.16em] text-brand-blue">Shared finance for groups</p>
              <h1 className="max-w-[13ch] text-[52px] font-extrabold leading-[0.98] tracking-[-0.04em] text-ink sm:text-[64px] lg:text-[68px]">
                Shared money, <span className="text-brand-blue">made clear.</span>
              </h1>
              <p className="mt-6 max-w-lg text-base leading-7 text-ink-muted sm:text-lg">
                Track expenses, settle balances, and plan shared goals with explainable insight.
              </p>
              <div className="mt-7 flex flex-col gap-3 sm:flex-row">
                {status === "authenticated" ? (
                  <HoverLift>
                    <LinkButton href="/groups" size="lg">
                      Open my dashboard <ArrowRight className="size-4" aria-hidden />
                    </LinkButton>
                  </HoverLift>
                ) : (
                  <>
                    <HoverLift>
                      <DemoButton />
                    </HoverLift>
                    <HoverLift>
                      <LinkButton href="/signup" size="lg" variant="outline">
                        Create a free account
                      </LinkButton>
                    </HoverLift>
                  </>
                )}
              </div>
              <p className="mt-3 text-xs text-ink-muted">Private sandbox · Three synthetic groups · No sign-up required</p>
            </div>

            <div className="card-surface p-5 sm:p-7" aria-label="How GroupWise turns transactions into decisions">
              <div className="flex items-end justify-between gap-4 border-b border-line pb-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.14em] text-brand-blue">One clear routine</p>
                  <p className="mt-1 text-lg font-bold text-ink">From shared spending to a shared plan.</p>
                </div>
                <span className="hidden size-10 shrink-0 place-items-center rounded-xl bg-brand-yellow text-ink sm:grid" aria-hidden>
                  <BadgeCheck className="size-5" />
                </span>
              </div>
              <div className="divide-y divide-line">
                {PIPELINE.map((step) => (
                  <div key={step.title} className="flex items-start gap-3 py-4 first:pt-5 last:pb-1">
                    <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-surface text-brand-blue">
                      <step.icon className="size-5" aria-hidden />
                    </span>
                    <div>
                      <p className="text-sm font-bold text-ink">{step.title}</p>
                      <p className="mt-0.5 text-[13px] leading-5 text-ink-muted">{step.body}</p>
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-4 border-t border-line pt-4 text-sm text-ink-muted">
                <span className="font-semibold text-ink">People stay in control.</span> GroupWise explains the numbers and shows the assumptions.
              </p>
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
                <HoverLift key={f.title} className="h-full">
                  <article className="card-surface flex h-full flex-col p-5">
                  <span className="grid size-9 place-items-center rounded-lg bg-surface text-brand-blue">
                    <f.icon className="size-5" aria-hidden />
                  </span>
                  <h3 className="mt-3 text-base font-bold text-ink">{f.title}</h3>
                  <p className="mt-1 text-[13px] text-ink-muted">{f.body}</p>
                  <p className="mt-auto pt-3 text-xs font-semibold text-brand-blue-deep">{f.method}</p>
                  </article>
                </HoverLift>
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

        <section className="border-t border-line bg-surface">
          <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
            <div className="grid gap-7 rounded-2xl border border-brand-blue/15 bg-brand-blue-soft/40 p-6 sm:p-8 lg:grid-cols-[1fr_auto] lg:items-center">
              <div className="max-w-2xl">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-brand-blue">Try the workspace</p>
                <h2 className="mt-2 text-2xl font-extrabold leading-tight text-ink sm:text-3xl">See how your group money fits together.</h2>
                <p className="mt-2 text-sm leading-6 text-ink-muted">Explore three synthetic groups with shared expenses, balances and goals ready to review.</p>
              </div>
              {status === "authenticated" ? (
                <HoverLift>
                  <LinkButton href="/groups" size="lg">
                    Open my dashboard <ArrowRight className="size-4" aria-hidden />
                  </LinkButton>
                </HoverLift>
              ) : (
                <HoverLift>
                  <DemoButton />
                </HoverLift>
              )}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-5 px-4 py-9 sm:px-6 md:flex-row md:items-end md:justify-between">
          <Logo className="scale-90" />
          <p className="max-w-2xl text-[11px] leading-5 text-ink-muted">
            GroupWise AI is an independent hackathon prototype for digital financial services. It is not affiliated with or endorsed by upay or
            any financial institution. All demo data is synthetic. Not financial advice.
          </p>
        </div>
      </footer>
    </div>
  );
}
