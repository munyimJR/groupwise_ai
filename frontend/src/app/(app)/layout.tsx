"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { LogoMark } from "@/components/brand/logo";
import { AppShell } from "@/components/shell/app-shell";
import { useAuth } from "@/lib/auth";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "anonymous") router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [status, router, pathname]);

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
