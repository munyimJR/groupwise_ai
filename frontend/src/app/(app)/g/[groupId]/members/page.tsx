"use client";

import { Copy, LogOut, RefreshCw, Settings, Share2, UserPlus } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Card, CardHeading, ErrorState, LoadingBlock, MemberAvatar, PageHeader } from "@/components/common/primitives";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { fmtDateYear } from "@/lib/format";
import { useGroup, useInvalidateGroup } from "@/lib/queries";
import { selectClass } from "@/lib/utils";
import type { GroupDetail } from "@/lib/types";

export default function MembersPage() {
  const { groupId } = useParams<{ groupId: string }>();
  const router = useRouter();
  const { data: g, isLoading, error, refetch } = useGroup(groupId);
  const invalidate = useInvalidateGroup(groupId);
  const [newMember, setNewMember] = useState("");
  const [busy, setBusy] = useState(false);
  const inviteUrl = g ? `${typeof window !== "undefined" ? window.location.origin : ""}/join/${g.invite_code}` : "";


  async function run(fn: () => Promise<unknown>, ok: string) {
    setBusy(true);
    try {
      await fn();
      invalidate();
      toast.success(ok);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function share() {
    const data = { title: `Join ${g?.name} on GroupWise AI`, text: `Join our group “${g?.name}” on GroupWise AI`, url: inviteUrl };
    if (navigator.share) {
      try {
        await navigator.share(data);
        return;
      } catch {
        /* cancelled */
      }
    }
    await navigator.clipboard.writeText(inviteUrl);
    toast.success("Invite link copied");
  }

  if (isLoading) return <LoadingBlock rows={4} />;
  if (error || !g) return <ErrorState error={error} onRetry={() => refetch()} />;
  const active = g.members_detail.filter((m) => m.status === "active");
  const left = g.members_detail.filter((m) => m.status !== "active");
  const isOwner = g.my_role === "owner";

  return (
    <div>
      <PageHeader eyebrow={g.name} title="Members & settings" subtitle="Invite people, add members who don't use the app yet, and manage the group." />
      <div className="grid gap-5 lg:grid-cols-2">
        <div className="space-y-5">
          <Card>
            <CardHeading icon={Share2} title="Invite link" subtitle="Anyone with the link can join after signing in" />
            <div className="flex gap-2">
              <Input readOnly value={inviteUrl} aria-label="Invite link" className="font-mono text-xs" onFocus={(e) => e.currentTarget.select()} />
              <Button
                variant="outline"
                size="icon"
                aria-label="Copy invite link"
                onClick={async () => {
                  await navigator.clipboard.writeText(inviteUrl);
                  toast.success("Invite link copied");
                }}
              >
                <Copy className="size-4" aria-hidden />
              </Button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button onClick={share}>
                <Share2 className="size-4" aria-hidden /> Share invite
              </Button>
              {isOwner && (
                <Button
                  variant="ghost"
                  disabled={busy}
                  onClick={() => run(() => api(`/groups/${groupId}/invite/regenerate`, { method: "POST" }), "New invite link created — the old one no longer works.")}
                >
                  <RefreshCw className="size-4" aria-hidden /> Reset link
                </Button>
              )}
            </div>
          </Card>

          <Card>
            <CardHeading icon={UserPlus} title={`Members (${active.length})`} />
            <ul className="divide-y divide-line">
              {active.map((m) => (
                <li key={m.id} className="flex items-center justify-between gap-3 py-2.5">
                  <span className="flex items-center gap-2.5">
                    <MemberAvatar name={m.display_name} color={m.avatar_color} size={34} />
                    <span>
                      <span className="block text-sm font-semibold text-ink">
                        {m.display_name}
                        {m.is_you && <span className="font-normal text-ink-muted"> (you)</span>}
                      </span>
                      <span className="block text-xs text-ink-muted">
                        {m.role === "owner" ? "Owner" : m.is_app_user ? "Member" : "Not on GroupWise yet — can claim this spot via the invite link"}
                      </span>
                    </span>
                  </span>
                </li>
              ))}
            </ul>
            {left.length > 0 && <p className="mt-2 text-xs text-ink-muted">Former members: {left.map((m) => m.display_name).join(", ")}</p>}
            <form
              className="mt-4 flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                if (!newMember.trim()) return;
                run(() => api(`/groups/${groupId}/members`, { body: { display_name: newMember.trim() } }), `${newMember.trim()} added`).then(() => setNewMember(""));
              }}
            >
              <Input aria-label="New member name" placeholder="Add someone by name" value={newMember} onChange={(e) => setNewMember(e.target.value)} maxLength={80} />
              <Button type="submit" variant="soft" disabled={busy || !newMember.trim()}>
                Add
              </Button>
            </form>
          </Card>
        </div>

        <div className="space-y-5">
          <SettingsCard
            key={g.data_version}
            group={g}
            busy={busy}
            onSave={(body) => run(() => api(`/groups/${groupId}`, { method: "PATCH", body }), "Settings saved")}
          />

          <Card className="border-bad/20">
            <CardHeading icon={LogOut} title="Leave group" subtitle="You can leave once your balance is settled" />
            <Dialog>
              <DialogTrigger render={<Button variant="destructive" />}>Leave this group</DialogTrigger>
              <DialogContent className="sm:max-w-sm">
                <DialogHeader>
                  <DialogTitle>Leave “{g.name}”?</DialogTitle>
                  <DialogDescription>Your history stays in the group ledger. You can rejoin with the invite link.</DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <Button
                    variant="destructive"
                    disabled={busy}
                    onClick={async () => {
                      setBusy(true);
                      try {
                        await api(`/groups/${groupId}/leave`, { method: "POST" });
                        try {
                          localStorage.removeItem("gw:lastGroup");
                        } catch {}
                        invalidate();
                        toast.success("You left the group.");
                        router.push("/groups");
                      } catch (e) {
                        toast.error((e as Error).message);
                        setBusy(false);
                      }
                    }}
                  >
                    Leave group
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </Card>
        </div>
      </div>
    </div>
  );
}

function SettingsCard({ group, busy, onSave }: { group: GroupDetail; busy: boolean; onSave: (body: { name: string; group_type: string; monthly_budget: number }) => void }) {
  const [name, setName] = useState(group.name);
  const [type, setType] = useState<string>(group.group_type);
  const [budget, setBudget] = useState(group.monthly_budget ? String(group.monthly_budget / 100) : "");
  return (
    <Card>
      <CardHeading icon={Settings} title="Group settings" subtitle={`Created ${fmtDateYear(group.created_at.replace("Z", ""))}`} />
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          onSave({ name, group_type: type, monthly_budget: budget ? Number(budget) : 0 });
        }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="s-name">Name</Label>
          <Input id="s-name" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="s-type">Type</Label>
          <select id="s-type" value={type} onChange={(e) => setType(e.target.value)} className={selectClass}>
            <option value="friends">Friends</option>
            <option value="roommates">Roommates</option>
            <option value="trip">Trip</option>
            <option value="event">Event / club</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="s-budget">Monthly budget (৳, optional)</Label>
          <Input id="s-budget" type="number" min="0" inputMode="numeric" value={budget} onChange={(e) => setBudget(e.target.value)} />
        </div>
        <Button type="submit" disabled={busy || !name.trim()}>
          Save settings
        </Button>
      </form>
    </Card>
  );
}
