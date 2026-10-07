import { Sparkles } from "lucide-react";
import Link from "next/link";

import { Logo } from "@/components/brand/logo";

export function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <div className="flex flex-col px-5 py-6 sm:px-10">
        <Link href="/" aria-label="GroupWise AI home">
          <Logo />
        </Link>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-10">
          <h1 className="text-[28px] font-extrabold text-ink">{title}</h1>
          <p className="mt-1 text-sm text-ink-muted">{subtitle}</p>
          <div className="mt-7">{children}</div>
        </div>
        <p className="text-center text-xs text-ink-muted">Hackathon prototype · synthetic data · not affiliated with any financial institution</p>
      </div>
      <div className="relative hidden overflow-hidden border-l border-line bg-surface lg:block">
        <div className="relative flex h-full flex-col justify-end p-12 text-ink">
          <Sparkles className="mb-4 size-7 text-brand-blue" aria-hidden />
          <p className="max-w-md text-3xl font-bold leading-tight">“GroupWise doesn&apos;t just tell groups where their money went.”</p>
          <p className="mt-3 max-w-md text-ink-muted">
            It helps them understand what is happening, anticipate what comes next, and make better financial decisions together.
          </p>
        </div>
      </div>
    </div>
  );
}
