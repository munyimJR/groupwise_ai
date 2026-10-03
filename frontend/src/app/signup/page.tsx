"use client";

import { CheckCircle2, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthLayout } from "@/components/auth/auth-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth";

export default function SignupPage() {
  const { signUp, status } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState(false);

  useEffect(() => {
    if (status === "authenticated") router.replace("/groups");
  }, [status, router]);

  const tooShort = password.length > 0 && password.length < 8;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) return setError("Use at least 8 characters for your password.");
    setBusy(true);
    try {
      const res = await signUp(name.trim(), email.trim(), password);
      if (res.needsConfirmation) setConfirm(true);
      else router.replace("/groups");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (confirm)
    return (
      <AuthLayout title="Check your email" subtitle="Confirm your address to finish creating your account.">
        <p className="flex items-start gap-2 rounded-xl bg-good-soft p-3 text-sm text-good">
          <CheckCircle2 className="mt-0.5 size-4 shrink-0" aria-hidden /> We sent a confirmation link to {email}. After confirming, sign in.
        </p>
        <Link href="/login" className="mt-6 inline-block font-semibold text-brand-blue hover:underline">
          Go to sign in →
        </Link>
      </AuthLayout>
    );

  return (
    <AuthLayout title="Create your account" subtitle="Start a group, invite friends, and let GroupWise make sense of shared money.">
      <form onSubmit={submit} className="space-y-4" noValidate>
        <div className="space-y-1.5">
          <Label htmlFor="name">Your name</Label>
          <Input id="name" autoComplete="name" required maxLength={80} value={name} onChange={(e) => setName(e.target.value)} className="h-11" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="h-11" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            aria-invalid={tooShort}
            aria-describedby="pw-help"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="h-11"
          />
          <p id="pw-help" className={tooShort ? "text-xs text-bad" : "text-xs text-ink-muted"}>
            At least 8 characters.
          </p>
        </div>
        {error && (
          <p role="alert" className="rounded-xl bg-bad-soft px-3 py-2 text-sm text-bad">
            {error}
          </p>
        )}
        <Button type="submit" size="lg" className="w-full" disabled={busy || !name || !email || !password}>
          {busy && <Loader2 className="size-4 animate-spin" aria-hidden />}
          {busy ? "Creating account…" : "Create account"}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-ink-muted">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-brand-blue hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
