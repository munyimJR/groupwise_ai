"use client";

import { AlertTriangle, Bell, CheckCheck, Lightbulb, Receipt, Scale, Target, UserPlus, type LucideIcon } from "lucide-react";
import { useRouter } from "next/navigation";

import { EmptyState, ErrorState, LoadingBlock, PageHeader } from "@/components/common/primitives";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import { useNotifications } from "@/lib/queries";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";

const ICONS: Record<string, { icon: LucideIcon; cls: string }> = {
  anomaly: { icon: AlertTriangle, cls: "bg-bad-soft text-bad" },
  expense: { icon: Receipt, cls: "bg-brand-blue-soft text-brand-blue" },
  insight: { icon: Lightbulb, cls: "bg-brand-yellow-soft text-[#7a5b00]" },
  goal: { icon: Target, cls: "bg-good-soft text-good" },
  settlement: { icon: Scale, cls: "bg-brand-blue-soft text-brand-blue" },
  member: { icon: UserPlus, cls: "bg-brand-blue-soft text-brand-blue" },
};

export default function NotificationsPage() {
  const { data, isLoading, error, refetch } = useNotifications();
  const qc = useQueryClient();
  const router = useRouter();

  async function readAll() {
    await api("/notifications/read-all", { method: "POST" });
    qc.invalidateQueries({ queryKey: ["notifications"] });
  }

  async function open(id: string, link: string | null) {
    api(`/notifications/${id}/read`, { method: "POST" }).then(() => qc.invalidateQueries({ queryKey: ["notifications"] }));
    if (link) router.push(link);
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        eyebrow="Inbox"
        title="Notifications"
        subtitle="Unusual expenses, goal and forecast alerts, and activity from your groups."
        actions={
          data?.unread ? (
            <Button variant="outline" onClick={readAll}>
              <CheckCheck className="size-4" aria-hidden /> Mark all as read
            </Button>
          ) : undefined
        }
      />
      {isLoading ? (
        <LoadingBlock rows={5} />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data?.items.length ? (
        <EmptyState icon={Bell} title="You're all caught up" body="Alerts about unusual expenses, goals and spending pressure will appear here." />
      ) : (
        <ul className="card-surface divide-y divide-line overflow-hidden p-0">
          {data.items.map((n) => {
            const meta = ICONS[n.kind] ?? ICONS.expense;
            const Icon = meta.icon;
            return (
              <li key={n.id}>
                <button type="button" onClick={() => open(n.id, n.link)} className={cn("flex w-full items-start gap-3 px-4 py-3.5 text-left hover:bg-surface", !n.is_read && "bg-brand-blue-softer")}>
                  <span className={cn("grid size-9 shrink-0 place-items-center rounded-xl", meta.cls)}>
                    <Icon className="size-4" aria-hidden />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2">
                      <span className="text-sm font-bold text-ink">{n.title}</span>
                      {!n.is_read && (
                        <span className="rounded-full bg-brand-blue px-1.5 text-xs font-bold text-white">
                          New<span className="sr-only"> notification</span>
                        </span>
                      )}
                    </span>
                    <span className="mt-0.5 block text-sm text-ink-muted">{n.body}</span>
                    <span className="mt-1 block text-xs text-ink-muted">
                      {n.group_name ? `${n.group_name} · ` : ""}
                      {relativeTime(n.created_at)}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
