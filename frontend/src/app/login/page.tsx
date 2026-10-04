"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { AuthLayout } from "@/components/auth/auth-layout";
import { DemoButton } from "@/components/auth/demo-button";
import { PasswordInput } from "@/components/auth/password-input";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth";

function safeNext(next: string | null) {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/groups";
}

function LoginForm() {
  const { signIn, status } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNext(params.get("next"));
  const expired = params.get("expired") === "1";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Only bounce visitors who arrive already signed in; sign-in and demo handle their own navigation.
  const initialStatus = useRef(status);
  useEffect(() => {
    if (initialStatus.current === "loading" && status !== "loading") initialStatus.current = status;
    if (initialStatus.current === "authenticated") router.replace(next);
  }, [status, router, next]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await signIn(email.trim(), password);
      router.replace(next);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Welcome back" subtitle="Sign in to see your groups' shared finances.">
      {expired && (
        <p role="status" className="mb-4 rounded-xl bg-warn-soft px-3 py-2 text-sm text-warn">
          Your session has expired. Please sign in again.
        </p>
      )}
      <form onSubmit={submit} className="space-y-4" noValidate>
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="h-11" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <PasswordInput id="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} className="h-11" />
        </div>
        {error && (
          <p role="alert" className="rounded-xl bg-bad-soft px-3 py-2 text-sm text-bad">
            {error}
          </p>
        )}
        <Button type="submit" size="lg" className="w-full" disabled={busy || !email || !password}>
          {busy && <Loader2 className="size-4 animate-spin" aria-hidden />}
          {busy ? "Signing in…" : "Sign in"}
        </Button>
      </form>
      <div className="my-6 flex items-center gap-3 text-xs text-ink-muted">
        <span className="h-px flex-1 bg-line" /> or <span className="h-px flex-1 bg-line" />
      </div>
      <DemoButton variant="outline" className="w-full" label="Explore the demo instead" />
      <p className="mt-6 text-center text-sm text-ink-muted">
        New to GroupWise?{" "}
        <Link href="/signup" className="font-semibold text-brand-blue hover:underline">
          Create an account
        </Link>
      </p>
    </AuthLayout>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
