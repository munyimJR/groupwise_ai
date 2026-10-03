"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Users } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Logo } from "@/components/brand/logo";
import { ErrorState, LinkButton } from "@/components/common/primitives";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

interface Preview {
  group_name: string;
  group_type: string;
  member_count: number;
  claimable_members: { id: string; display_name: string }[];
}

export default function JoinPage() {
  const { code } = useParams<{ code: string }>();
  const { status } = useAuth();
  const router = useRouter();
  const qc = useQueryClient();
  const [claim, setClaim] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { data, isLoading, error } = useQuery({ queryKey: ["invite", code], queryFn: () => api<Preview>(`/invites/${code}`, { auth: false }), retry: false });

  async function join() {
    setBusy(true);
    try {
      const res = await api<{ group_id: string }>(`/invites/${code}/join`, { body: { claim_member_id: claim } });
      await qc.invalidateQueries({ queryKey: ["groups"] });
      toast.success(`You joined ${data?.group_name}`);
      router.push(`/g/${res.group_id}`);
    } catch (e) {
      toast.error((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-dvh place-items-center bg-surface px-4 py-10">
      <div className="w-full max-w-md">
        <Link href="/" className="mb-6 inline-block" aria-label="GroupWise AI home">
          <Logo />
        </Link>
        {isLoading ? (
          <div className="card-surface flex items-center gap-2 p-6 text-sm text-ink-muted">
            <Loader2 className="size-4 animate-spin" aria-hidden /> Checking invite…
          </div>
        ) : error || !data ? (
          <ErrorState error={error} />
        ) : (
          <div className="card-surface p-6">
            <span className="grid size-12 place-items-center rounded-2xl bg-brand-yellow text-brand-blue-deep">
              <Users className="size-6" aria-hidden />
            </span>
            <h1 className="mt-4 text-2xl font-extrabold text-ink">Join “{data.group_name}”</h1>
            <p className="mt-1 text-sm text-ink-muted">
              {data.member_count} members share expenses here. Joining lets you add expenses, see balances and get the group&apos;s insights.
            </p>
            {status !== "authenticated" ? (
              <div className="mt-6 space-y-2">
                <LinkButton href={`/login?next=${encodeURIComponent(`/join/${code}`)}`} className="w-full" size="lg">
                  Sign in to join
                </LinkButton>
                <LinkButton href="/signup" variant="outline" className="w-full">
                  Create an account
                </LinkButton>
              </div>
            ) : (
              <>
                {data.claimable_members.length > 0 && (
                  <fieldset className="mt-5">
                    <legend className="mb-2 text-sm font-semibold text-ink">Already in the group as one of these? (optional)</legend>
                    <div className="flex flex-wrap gap-2">
                      {data.claimable_members.map((m) => (
                        <button
                          key={m.id}
                          type="button"
                          role="radio"
                          aria-checked={claim === m.id}
                          onClick={() => setClaim(claim === m.id ? null : m.id)}
                          className={cn("rounded-full border px-3 py-1.5 text-sm font-semibold", claim === m.id ? "border-brand-blue bg-brand-blue-soft text-brand-blue-deep" : "border-line text-ink")}
                        >
                          {m.display_name}
                        </button>
                      ))}
                    </div>
                    <p className="mt-2 text-xs text-ink-muted">Claiming links your account to that member&apos;s existing expenses.</p>
                  </fieldset>
                )}
                <Button size="lg" className="mt-6 w-full" onClick={join} disabled={busy}>
                  {busy && <Loader2 className="size-4 animate-spin" aria-hidden />} Join group
                </Button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
