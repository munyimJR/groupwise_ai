import Link from "next/link";

import { LogoMark } from "@/components/brand/logo";

export default function NotFound() {
  return (
    <div className="grid min-h-dvh place-items-center bg-surface px-4">
      <div className="text-center">
        <LogoMark className="mx-auto size-14" />
        <h1 className="mt-4 text-2xl font-extrabold text-ink">Page not found</h1>
        <p className="mt-1 text-sm text-ink-muted">The page you&apos;re looking for doesn&apos;t exist or was moved.</p>
        <Link href="/" className="mt-5 inline-flex h-10 items-center rounded-xl bg-brand-yellow px-4 text-sm font-bold text-ink hover:bg-brand-yellow-strong">
          Go home
        </Link>
      </div>
    </div>
  );
}
