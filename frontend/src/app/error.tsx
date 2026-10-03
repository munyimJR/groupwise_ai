"use client";

import { AlertTriangle } from "lucide-react";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="grid min-h-[60dvh] place-items-center px-4">
      <div className="max-w-sm text-center">
        <AlertTriangle className="mx-auto size-8 text-bad" aria-hidden />
        <h1 className="mt-3 text-xl font-extrabold text-ink">Something went wrong</h1>
        <p className="mt-1 text-sm text-ink-muted">An unexpected error happened while showing this page. Your data is safe.</p>
        <button type="button" onClick={reset} className="mt-5 inline-flex h-10 items-center rounded-xl bg-brand-yellow px-4 text-sm font-bold text-ink hover:bg-brand-yellow-strong">
          Try again
        </button>
      </div>
    </div>
  );
}
