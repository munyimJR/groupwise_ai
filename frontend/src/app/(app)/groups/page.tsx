"use client";

import { AlertTriangle, Link2, Loader2, Plus, Users } from "lucide-react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { AvatarStack, BalanceTag, EmptyState, ErrorState, LoadingBlock, PageHeader } from "@/components/common/primitives";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { relativeTime, taka } from "@/lib/format";
import { useGroups } from "@/lib/queries";
import { selectClass } from "@/lib/utils";
import type { GroupSummary } from "@/lib/types";

const TYPES = [
  { value: "friends", label: "Friends" },
  { value: "roommates", label: "Roommates" },
  { value: "trip", label: "Trip" },
  { value: "event", label: "Event / club" },
  { value: "other", label: "Other" },
];

function CreateGroupDialog() {
  const router = useRouter();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("friends");
  const [description, setDescription] = useState("");
  const [members, setMembers] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const g = await api<GroupSummary>("/groups", {
        body: { name, group_type: type, description: description || null, member_names: members.split(",").map((m) => m.trim()).filter(Boolean) },
      });
      await qc.invalidateQueries({ queryKey: ["groups"] });
      toast.success(`“${g.name}” created. Share the invite link from Members.`);
      router.push(`/g/${g.id}`);
    } catch (err) {
      toast.error((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button />}>
        <Plus className="size-4" aria-hidden /> New group
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={submit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Create a group</DialogTitle>
            <DialogDescription>For roommates, a friend circle, a trip or a club.</DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="g-name">Group name</Label>
            <Input id="g-name" required maxLength={80} placeholder="e.g. Cox's Bazar 2026" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="g-type">Type</Label>
            <select id="g-type" value={type} onChange={(e) => setType(e.target.value)} className={selectClass}>
              {TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="g-desc">Description (optional)</Label>
            <Textarea id="g-desc" maxLength={280} rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="g-members">Add members by name (optional)</Label>
            <Input id="g-members" placeholder="Rony, Galib, Nahid" value={members} onChange={(e) => setMembers(e.target.value)} />
            <p className="text-xs text-ink-muted">Comma-separated. They can claim their spot later through the invite link.</p>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={busy || !name.trim()}>
              {busy && <Loader2 className="size-4 animate-spin" aria-hidden />} Create group
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function JoinDialog() {
  const router = useRouter();
  const [code, setCode] = useState("");
  return (
    <Dialog>
      <DialogTrigger render={<Button variant="outline" />}>
        <Link2 className="size-4" aria-hidden /> Join with code
      </DialogTrigger>
      <DialogContent className="sm:max-w-sm">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const c = code.trim().split("/").pop();
            if (c) router.push(`/join/${c}`);
          }}
          className="space-y-4"
        >
          <DialogHeader>
            <DialogTitle>Join a group</DialogTitle>
            <DialogDescription>Paste an invite link or code shared by a group member.</DialogDescription>
          </DialogHeader>
          <Input aria-label="Invite link or code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="https://…/join/AbC123xYz0" />
          <DialogFooter>
            <Button type="submit" disabled={!code.trim()}>
              Continue
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function GroupsPage() {
  const { data, isLoading, error, refetch } = useGroups();
  const { user } = useAuth();
  const router = useRouter();
  const [seeding, setSeeding] = useState(false);

  async function loadSample() {
    setSeeding(true);
    try {
      const res = await api<{ groups: { id: string }[] }>("/me/sample-data", { method: "POST" });
      await refetch();
      router.push(`/g/${res.groups[0].id}`);
    } catch (e) {
      toast.error((e as Error).message);
      setSeeding(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Groups"
        title={user ? `Hi, ${user.display_name.split(" ")[0]}` : "Your groups"}
        subtitle="Each group has its own shared ledger, insights, forecasts and goals."
        actions={
          <>
            <JoinDialog />
            <CreateGroupDialog />
          </>
        }
      />
      {isLoading ? (
        <LoadingBlock rows={3} />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data?.length ? (
        <EmptyState
          icon={Users}
          title="No groups yet"
          body="Create a group for your flat, friends or next trip — or load sample groups with synthetic data to explore every feature."
          action={
            <Button variant="soft" onClick={loadSample} disabled={seeding}>
              {seeding && <Loader2 className="size-4 animate-spin" aria-hidden />} Load sample groups
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {data.map((g) => (
            <Link key={g.id} href={`/g/${g.id}`} className="card-surface group flex flex-col gap-4 p-5 transition-shadow hover:shadow-[var(--shadow-lift)]">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs font-bold uppercase tracking-wider text-brand-blue">{TYPES.find((t) => t.value === g.group_type)?.label ?? "Group"}</p>
                  <h2 className="truncate text-lg font-extrabold text-ink group-hover:text-brand-blue-deep">{g.name}</h2>
                  {g.description && <p className="line-clamp-2 text-xs text-ink-muted">{g.description}</p>}
                </div>
                <AvatarStack members={g.members} />
              </div>
              <div className="grid grid-cols-2 gap-3 rounded-xl bg-surface p-3">
                <div>
                  <p className="text-xs text-ink-muted">Spent · 30 days</p>
                  <p className="tabular text-lg font-extrabold text-ink">{taka(g.total_30d)}</p>
                </div>
                <div>
                  <p className="text-xs text-ink-muted">Your balance</p>
                  <BalanceTag net={g.my_net} size="sm" you />
                </div>
              </div>
              <div className="flex items-center justify-between text-xs text-ink-muted">
                <span>{g.last_activity ? `Last activity ${relativeTime(g.last_activity)}` : "No expenses yet"}</span>
                {g.flagged_count > 0 && (
                  <span className="inline-flex items-center gap-1 font-semibold text-bad">
                    <AlertTriangle className="size-3.5" aria-hidden /> {g.flagged_count} to review
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
