"use client";

import { Loader2, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useInvalidateGroup } from "@/lib/queries";
import type { GoalPlan } from "@/lib/types";

function defaultDeadline() {
  const d = new Date();
  d.setMonth(d.getMonth() + 4);
  return d.toISOString().slice(0, 10);
}

export function CreateGoalDialog({ groupId, trigger }: { groupId: string; trigger?: React.ReactElement }) {
  const router = useRouter();
  const invalidate = useInvalidateGroup(groupId);
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [target, setTarget] = useState("");
  const [deadline, setDeadline] = useState(defaultDeadline);
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const g = await api<GoalPlan>(`/groups/${groupId}/goals`, { body: { title, target: Number(target), deadline, description: description || null } });
      invalidate();
      toast.success(`Goal “${g.title}” created`);
      router.push(`/g/${groupId}/goals/${g.goal_id}`);
    } catch (err) {
      toast.error((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={trigger ?? <Button />}>
        <Plus className="size-4" aria-hidden /> New goal
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={submit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Create a shared goal</DialogTitle>
            <DialogDescription>GroupWise projects whether the group will reach it, based on how it actually saves.</DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="goal-title">Goal</Label>
            <Input id="goal-title" required maxLength={80} placeholder="Cox's Bazar Trip" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="goal-target">Target (৳)</Label>
              <Input id="goal-target" type="number" inputMode="decimal" min="1" required placeholder="40000" value={target} onChange={(e) => setTarget(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="goal-deadline">Deadline</Label>
              <Input id="goal-deadline" type="date" required value={deadline} onChange={(e) => setDeadline(e.target.value)} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="goal-desc">Notes (optional)</Label>
            <Textarea id="goal-desc" rows={2} maxLength={280} value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={busy || !title.trim() || !(Number(target) > 0)}>
              {busy && <Loader2 className="size-4 animate-spin" aria-hidden />} Create goal
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
