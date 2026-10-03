"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { LogoMark } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/shell/app-shell";
import { useAuth } from "@/lib/auth";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { status, refreshUser } = useAuth();
  const [retrying, setRetrying] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "anonymous") router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [status, router, pathname]);

  if (status === "unreachable") {
    return (
      <div className="grid min-h-dvh place-items-center bg-surface px-4" role="alert">
        <div className="max-w-sm text-center">
          <LogoMark className="mx-auto size-12" />
          <h1 className="mt-4 text-xl font-extrabold text-ink">Can&apos;t reach GroupWise right now</h1>
          <p className="mt-1 text-sm text-ink-muted">The server may be waking up (free hosting can take up to a minute). You&apos;re still signed in.</p>
          <Button
            className="mt-5"
            disabled={retrying}
            onClick={async () => {
              setRetrying(true);
              try {
                await refreshUser();
              } catch {
                /* still unreachable */
              } finally {
                setRetrying(false);
              }
            }}
          >
            {retrying ? "Trying…" : "Try again"}
          </Button>
        </div>
      </div>
    );
  }
  if (status !== "authenticated") {
    return (
      <div className="grid min-h-dvh place-items-center bg-surface" aria-busy="true">
        <div className="flex flex-col items-center gap-3 text-sm text-ink-muted">
          <LogoMark className="size-12 animate-pulse" />
          {status === "loading" ? "Loading your groups…" : "Redirecting to sign in…"}
        </div>
      </div>
    );
  }
  return <AppShell>{children}</AppShell>;
}
