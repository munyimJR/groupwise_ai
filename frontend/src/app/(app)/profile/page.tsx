"use client";

import { BookOpen, Download, Loader2, LogOut, ShieldCheck, User } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Card, CardHeading, LinkButton, MemberAvatar, PageHeader } from "@/components/common/primitives";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
}

export default function ProfilePage() {
  const { user, provider, signOut, refreshUser } = useAuth();
  const [name, setName] = useState(user?.display_name ?? "");
  const [busy, setBusy] = useState(false);
  const [install, setInstall] = useState<InstallPromptEvent | null>(null);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setInstall(e as InstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  if (!user) return null;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/me", { method: "PATCH", body: { display_name: name.trim() } });
      await refreshUser();
      toast.success("Profile updated");
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader eyebrow="Account" title="Profile & settings" />
      <div className="space-y-5">
        <Card>
          <div className="flex items-center gap-4">
            <MemberAvatar name={user.display_name} color={user.avatar_color} size={64} />
            <div className="min-w-0">
              <p className="text-xl font-extrabold text-ink">{user.display_name}</p>
              <p className="truncate text-sm text-ink-muted">
                {user.is_demo ? "Demo sandbox account (synthetic data)" : user.email}
                {" · "}
                {provider === "supabase" ? "Signed in with Supabase Auth" : provider === "demo" ? "Demo session" : "GroupWise account"}
              </p>
              {user.expires_at && <p className="text-xs text-ink-muted">This sandbox resets on {new Date(user.expires_at).toLocaleString()}.</p>}
            </div>
          </div>
        </Card>

        <Card>
          <CardHeading icon={User} title="Your details" />
          <form onSubmit={save} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1 space-y-1.5">
              <Label htmlFor="p-name">Display name</Label>
              <Input id="p-name" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} />
            </div>
            <Button type="submit" disabled={busy || !name.trim() || name.trim() === user.display_name}>
              {busy && <Loader2 className="size-4 animate-spin" aria-hidden />} Save
            </Button>
          </form>
          <p className="mt-2 text-xs text-ink-muted">Your name updates in every group you belong to.</p>
        </Card>

        <Card>
          <CardHeading icon={ShieldCheck} title="Privacy & AI" />
          <ul className="space-y-2 text-sm text-ink">
            <li>• This prototype runs on synthetic data — no real customer information is used.</li>
            <li>• AI explains computed facts; it never moves money, blocks expenses or makes decisions for you.</li>
            <li>• Expense descriptions are treated as data; the AI copilot cannot be instructed through them.</li>
          </ul>
          <LinkButton href="/how-it-works" variant="soft" className="mt-4">
            <BookOpen className="size-4" aria-hidden /> How the AI works
          </LinkButton>
        </Card>

        <Card>
          <CardHeading icon={Download} title="Install the app" subtitle="GroupWise works as an installable web app on Android, iOS and desktop" />
          {install ? (
            <Button onClick={() => install.prompt()}>Install GroupWise</Button>
          ) : (
            <p className="text-sm text-ink-muted">On mobile, use your browser&apos;s “Add to Home screen”. On desktop Chrome or Edge, use the install icon in the address bar.</p>
          )}
        </Card>

        <Button variant="outline" onClick={() => signOut()} className="w-full sm:w-auto">
          <LogOut className="size-4" aria-hidden /> Sign out
        </Button>
      </div>
    </div>
  );
}
