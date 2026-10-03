"use client";

import { BadgeCheck, Bot, ChevronDown, Info, Loader2, SendHorizontal, ShieldAlert, Sparkles } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ProvenanceBadge, type Provenance } from "@/components/ai/labels";
import { PageHeader } from "@/components/common/primitives";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAskCopilot } from "@/lib/queries";
import { useQuery } from "@tanstack/react-query";
import type { CopilotAnswer } from "@/lib/types";
import { cn } from "@/lib/utils";

const SUGGESTED = [
  "Why did our spending increase this month?",
  "Can we afford our trip?",
  "Which category increased the most?",
  "What caused our financial pressure?",
  "Who is paying most of the group expenses?",
  "What can we change to reach our goal?",
];

type Msg = { role: "user"; content: string } | { role: "assistant"; content: string; answer: CopilotAnswer } | { role: "error"; content: string };

/** Render answer text, turning [F3] citations into evidence chips. */
function AnswerText({ text, onCite, active }: { text: string; onCite: (id: string) => void; active: string | null }) {
  const parts = text.split(/(\[F\d+\])/g);
  return (
    <p className="whitespace-pre-line text-[15px] leading-relaxed text-ink">
      {parts.map((part, i) => {
        const m = part.match(/^\[(F\d+)\]$/);
        if (!m) return <span key={i}>{part}</span>;
        return (
          <button
            key={i}
            type="button"
            onClick={() => onCite(m[1])}
            className={cn(
              "mx-0.5 inline-flex -translate-y-0.5 items-center rounded-md px-1.5 py-0 align-middle text-[10px] font-bold",
              active === m[1] ? "bg-brand-blue text-white" : "bg-brand-blue-soft text-brand-blue-deep hover:bg-[#dbe8f8]",
            )}
            aria-label={`Show evidence ${m[1]}`}
          >
            {m[1]}
          </button>
        );
      })}
    </p>
  );
}

function AssistantMessage({ answer, onFollowUp, hideNotice }: { answer: CopilotAnswer; onFollowUp: (q: string) => void; hideNotice: boolean }) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState<string | null>(null);
  const g = answer.grounding;
  return (
    <div className="flex gap-3">
      <span className="mt-1 grid size-9 shrink-0 place-items-center rounded-xl bg-brand-yellow text-brand-blue-deep" aria-hidden>
        <Sparkles className="size-[18px]" />
      </span>
      <div className="min-w-0 flex-1 rounded-2xl rounded-tl-md border border-line bg-white p-4 shadow-[var(--shadow-card)]">
        <AnswerText
          text={answer.answer}
          active={active}
          onCite={(id) => {
            setActive(id);
            setOpen(true);
          }}
        />
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3">
          {answer.mode === "llm" ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-[#f1edfd] px-2 py-0.5 text-[11px] font-semibold text-[#4a3aa7]">
              <Bot className="size-3" aria-hidden /> Worded by AI from verified facts
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-[#eef2f7] px-2 py-0.5 text-[11px] font-semibold text-[#344054]">
              <Bot className="size-3" aria-hidden /> Composed by GroupWise engine
            </span>
          )}
          {g.numbers_checked > 0 &&
            (g.passed ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-good-soft px-2 py-0.5 text-[11px] font-semibold text-good">
                <BadgeCheck className="size-3" aria-hidden /> {g.verified}/{g.numbers_checked} figures verified against your data
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full bg-bad-soft px-2 py-0.5 text-[11px] font-semibold text-bad">
                <ShieldAlert className="size-3" aria-hidden /> Unverified figures removed
              </span>
            ))}
          <span className="text-[11px] text-ink-muted">Intent: {answer.intent.label}</span>
        </div>
        {answer.notice && !hideNotice && (
          <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-brand-blue-softer px-2.5 py-2 text-xs text-ink">
            <Info className="mt-0.5 size-3.5 shrink-0 text-brand-blue" aria-hidden /> {answer.notice}
          </p>
        )}
        <p className="mt-2 text-[11px] text-ink-muted">{answer.basis}</p>
        {answer.facts.length > 0 && (
          <div className="mt-2">
            <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="inline-flex items-center gap-1 text-xs font-semibold text-brand-blue hover:text-brand-blue-deep">
              {open ? "Hide" : "Show"} evidence ({answer.facts.length})
              <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} aria-hidden />
            </button>
            {open && (
              <ul className="mt-2 space-y-1.5">
                {answer.facts.map((f) => (
                  <li key={f.id} className={cn("rounded-lg border p-2.5 text-xs transition-colors", active === f.id ? "border-brand-blue bg-brand-blue-softer" : "border-line bg-surface")}>
                    <div className="mb-1 flex flex-wrap items-center gap-1.5">
                      <span className="rounded bg-white px-1.5 font-bold text-brand-blue-deep">{f.id}</span>
                      <ProvenanceBadge kind={f.type as Provenance} withTooltip={false} />
                      <span className="text-ink-muted">source: {f.source}</span>
                    </div>
                    <p className="text-ink">{f.statement}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        {answer.follow_ups.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {answer.follow_ups.map((q) => (
              <button key={q} type="button" onClick={() => onFollowUp(q)} className="rounded-full border border-line px-2.5 py-1 text-xs font-medium text-ink hover:border-brand-blue hover:bg-brand-blue-soft">
                {q}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function AskPage() {
  const { groupId } = useParams<{ groupId: string }>();
  const ask = useAskCopilot(groupId);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const { data: config } = useQuery({ queryKey: ["config"], queryFn: () => api<{ llm: { available: boolean; reason: string | null } }>("/meta/config", { auth: false }), staleTime: 60_000 });

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, ask.isPending]);

  async function send(q: string) {
    const question = q.trim().slice(0, 500);
    if (!question || ask.isPending) return;
    setInput("");
    const history = messages
      .filter((m): m is Exclude<Msg, { role: "error" }> => m.role !== "error")
      .slice(-4)
      .map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    try {
      const answer = await ask.mutateAsync({ question, history });
      setMessages((prev) => [...prev, { role: "assistant", content: answer.answer, answer }]);
    } catch (e) {
      setMessages((prev) => [...prev, { role: "error", content: (e as Error).message }]);
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col">
      <PageHeader eyebrow="AI copilot" title="Ask GroupWise" subtitle="Plain-English answers about this group's money — every figure comes from your data and is checked before you see it." />
      {config && !config.llm.available && (
        <p className="mb-4 flex items-start gap-2 rounded-xl border border-brand-blue/15 bg-brand-blue-softer px-3 py-2.5 text-sm text-ink">
          <Info className="mt-0.5 size-4 shrink-0 text-brand-blue" aria-hidden />
          The language model isn&apos;t connected right now, so answers are composed by GroupWise&apos;s deterministic engine from the same verified facts. Everything else works normally.
        </p>
      )}

      <div className="flex-1 space-y-5 pb-4">
        {messages.length === 0 && (
          <div className="card-surface p-5">
            <p className="mb-3 text-sm font-semibold text-ink">Try asking</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {SUGGESTED.map((q) => (
                <button key={q} type="button" onClick={() => send(q)} className="rounded-xl border border-line bg-surface px-3 py-2.5 text-left text-sm font-medium text-ink hover:border-brand-blue hover:bg-brand-blue-soft">
                  {q}
                </button>
              ))}
            </div>
            <p className="mt-4 text-xs text-ink-muted">
              GroupWise answers only about this group&apos;s shared finances. It can&apos;t give investment, loan or tax advice, and it never judges anyone — it describes observable payments only.
            </p>
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex justify-end">
              <p className="max-w-[85%] rounded-2xl rounded-tr-md bg-brand-blue px-4 py-2.5 text-[15px] text-white">{m.content}</p>
            </div>
          ) : m.role === "assistant" ? (
            <AssistantMessage key={i} answer={m.answer} onFollowUp={send} hideNotice={!!config && !config.llm.available && m.answer.mode === "template" && !m.answer.grounding.rejected_llm_numbers} />
          ) : (
            <p key={i} role="alert" className="rounded-xl bg-bad-soft px-3 py-2 text-sm text-bad">
              AI Copilot is temporarily unavailable ({m.content}). Your core financial features are still working.
            </p>
          ),
        )}
        {ask.isPending && (
          <div className="flex items-center gap-3 text-sm text-ink-muted" aria-live="polite">
            <span className="grid size-9 place-items-center rounded-xl bg-brand-yellow-soft">
              <Loader2 className="size-4 animate-spin text-brand-blue-deep" aria-hidden />
            </span>
            Computing facts from your group&apos;s data…
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="sticky bottom-20 z-20 lg:bottom-4"
      >
        <div className="flex items-end gap-2 rounded-2xl border border-line bg-white p-2 shadow-[var(--shadow-lift)]">
          <label htmlFor="ask" className="sr-only">
            Ask a question about this group&apos;s money
          </label>
          <textarea
            id="ask"
            rows={1}
            maxLength={500}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            placeholder="Ask about spending, goals, forecasts, balances…"
            className="max-h-32 min-h-11 flex-1 resize-none bg-transparent px-2 py-2.5 text-[15px] text-ink outline-none placeholder:text-ink-muted"
          />
          <Button type="submit" size="icon" disabled={!input.trim() || ask.isPending} aria-label="Send question">
            <SendHorizontal className="size-5" aria-hidden />
          </Button>
        </div>
      </form>
    </div>
  );
}
