"use client";

import {
  ArrowLeftRight,
  Bell,
  BookOpen,
  ChevronDown,
  FlaskConical,
  Home,
  LayoutDashboard,
  Lightbulb,
  LogOut,
  Plus,
  Receipt,
  Scale,
  Sparkles,
  Target,
  TrendingUp,
  User,
  UserPlus,
  Users,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useParams, usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Logo, LogoMark } from "@/components/brand/logo";
import { MemberAvatar } from "@/components/common/primitives";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/lib/auth";
import { useGroups, useNotifications } from "@/lib/queries";
import { cn } from "@/lib/utils";

const LAST_GROUP = "gw:lastGroup";

export function useCurrentGroupId(): string | null {
  const params = useParams<{ groupId?: string }>();
  // The shell renders client-side only (after auth), so reading storage lazily is safe.
  const [last] = useState<string | null>(() => {
    try {
      return localStorage.getItem(LAST_GROUP);
    } catch {
      return null;
    }
  });
  useEffect(() => {
    if (params.groupId) {
      try {
        localStorage.setItem(LAST_GROUP, params.groupId);
      } catch {}
    }
  }, [params.groupId]);
  return params.groupId ?? last;
}

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  exact?: boolean;
  badge?: string;
}

function groupNav(id: string): { title: string; items: NavItem[] }[] {
  return [
    {
      title: "Money",
      items: [
        { href: `/g/${id}`, label: "Dashboard", icon: LayoutDashboard, exact: true },
        { href: `/g/${id}/transactions`, label: "Transactions", icon: Receipt },
        { href: `/g/${id}/balances`, label: "Balances & settle up", icon: Scale },
      ],
    },
    {
      title: "Intelligence",
      items: [
        { href: `/g/${id}/insights`, label: "Insights", icon: Lightbulb },
        { href: `/g/${id}/forecast`, label: "Forecast", icon: TrendingUp },
        { href: `/g/${id}/goals`, label: "Goals", icon: Target },
        { href: `/g/${id}/what-if`, label: "What-If", icon: FlaskConical },
        { href: `/g/${id}/ask`, label: "Ask GroupWise", icon: Sparkles, badge: "AI" },
        { href: `/g/${id}/dynamics`, label: "Group dynamics", icon: ArrowLeftRight },
      ],
    },
    { title: "Group", items: [{ href: `/g/${id}/members`, label: "Members & invite", icon: UserPlus }] },
  ];
}

function isActive(pathname: string, item: NavItem) {
  return item.exact ? pathname === item.href : pathname === item.href || pathname.startsWith(`${item.href}/`);
}

function GroupSwitcher({ currentId, className }: { currentId: string | null; className?: string }) {
  const { data: groups } = useGroups();
  const router = useRouter();
  const current = groups?.find((g) => g.id === currentId);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <button
            type="button"
            className={cn(
              "flex w-full min-w-0 items-center gap-2 rounded-xl border border-line bg-white px-3 py-2 text-left hover:border-brand-blue/40",
              className,
            )}
          />
        }
      >
        <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-brand-blue-soft text-brand-blue">
          <Users className="size-4" aria-hidden />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-[10px] font-semibold uppercase tracking-wider text-ink-muted">Group</span>
          <span className="block truncate text-sm font-bold text-ink">{current?.name ?? "Choose a group"}</span>
        </span>
        <ChevronDown className="size-4 text-ink-muted" aria-hidden />
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-64" align="start">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Your groups</DropdownMenuLabel>
          {groups?.map((g) => (
            <DropdownMenuItem key={g.id} onClick={() => router.push(`/g/${g.id}`)} className={cn(g.id === currentId && "bg-brand-yellow-soft")}>
              <span className="truncate font-medium">{g.name}</span>
              <span className="ml-auto text-xs text-ink-muted">{g.member_count}</span>
            </DropdownMenuItem>
          ))}
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => router.push("/groups")}>
          <Plus className="size-4" aria-hidden /> Create or join a group
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function NotificationBell() {
  const { data } = useNotifications();
  const unread = data?.unread ?? 0;
  return (
    <Link
      href="/notifications"
      className="relative grid size-10 place-items-center rounded-xl text-ink hover:bg-brand-blue-soft"
      aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
    >
      <Bell className="size-5" aria-hidden />
      {unread > 0 && (
        <span className="absolute right-1.5 top-1.5 grid min-w-4 place-items-center rounded-full bg-bad px-1 text-[10px] font-bold leading-4 text-white">
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </Link>
  );
}

function UserMenu() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  if (!user) return null;
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<button type="button" className="rounded-full" aria-label="Account menu" />}>
        <MemberAvatar name={user.display_name} color={user.avatar_color} size={36} />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuGroup>
          <DropdownMenuLabel>
            <span className="block truncate font-semibold text-ink">{user.display_name}</span>
            <span className="block truncate text-xs font-normal text-ink-muted">{user.is_demo ? "Demo sandbox" : user.email}</span>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => router.push("/profile")}>
          <User className="size-4" aria-hidden /> Profile & settings
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push("/how-it-works")}>
          <BookOpen className="size-4" aria-hidden /> How the AI works
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => signOut()}>
          <LogOut className="size-4" aria-hidden /> Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function Sidebar({ groupId }: { groupId: string | null }) {
  const pathname = usePathname();
  const sections = groupId ? groupNav(groupId) : [];
  const globalItems: NavItem[] = [
    { href: "/groups", label: "All groups", icon: Users, exact: true },
    { href: "/notifications", label: "Notifications", icon: Bell },
    { href: "/profile", label: "Profile", icon: User },
    { href: "/how-it-works", label: "How the AI works", icon: BookOpen },
  ];
  return (
    <aside className="sticky top-0 hidden h-dvh w-[264px] shrink-0 flex-col border-r border-line bg-white lg:flex">
      <div className="px-5 pb-4 pt-5">
        <Link href={groupId ? `/g/${groupId}` : "/groups"} aria-label="GroupWise AI home">
          <Logo />
        </Link>
      </div>
      <div className="px-4">
        <GroupSwitcher currentId={groupId} />
      </div>
      {groupId && (
        <div className="px-4 pt-3">
          <Link
            href={`/g/${groupId}/add`}
            className="flex h-11 items-center justify-center gap-2 rounded-xl bg-brand-yellow text-sm font-bold text-ink shadow-[0_1px_0_rgb(0_0_0/0.06)] hover:bg-brand-yellow-strong"
          >
            <Plus className="size-4" aria-hidden /> Add expense
          </Link>
        </div>
      )}
      <nav className="mt-3 flex-1 overflow-y-auto px-3 pb-4" aria-label="Main">
        {sections.map((s) => (
          <div key={s.title} className="mt-3">
            <p className="px-3 pb-1 text-[10.5px] font-bold uppercase tracking-[0.12em] text-ink-muted">{s.title}</p>
            {s.items.map((item) => (
              <NavLink key={item.href} item={item} active={isActive(pathname, item)} />
            ))}
          </div>
        ))}
        <div className="mt-3">
          <p className="px-3 pb-1 text-[10.5px] font-bold uppercase tracking-[0.12em] text-ink-muted">Account</p>
          {globalItems.map((item) => (
            <NavLink key={item.href} item={item} active={isActive(pathname, item)} />
          ))}
        </div>
      </nav>
    </aside>
  );
}

function NavLink({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "relative flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
        active ? "bg-brand-blue-soft font-semibold text-brand-blue-deep" : "text-ink hover:bg-surface",
      )}
    >
      {active && <span className="absolute inset-y-2 left-0 w-1 rounded-r-full bg-brand-yellow-strong" aria-hidden />}
      <Icon className={cn("size-[18px]", active ? "text-brand-blue" : "text-ink-muted")} aria-hidden />
      {item.label}
      {item.badge && <span className="ml-auto rounded-md bg-brand-yellow px-1.5 py-0.5 text-[10px] font-bold text-ink">{item.badge}</span>}
    </Link>
  );
}

function BottomNav({ groupId }: { groupId: string | null }) {
  const pathname = usePathname();
  const items: (NavItem & { primary?: boolean })[] = groupId
    ? [
        { href: `/g/${groupId}`, label: "Home", icon: Home, exact: true },
        { href: "/groups", label: "Groups", icon: Users, exact: true },
        { href: `/g/${groupId}/add`, label: "Add", icon: Plus, primary: true },
        { href: `/g/${groupId}/insights`, label: "Insights", icon: Lightbulb },
        { href: `/g/${groupId}/goals`, label: "Goals", icon: Target },
      ]
    : [
        { href: "/groups", label: "Groups", icon: Users, exact: true },
        { href: "/notifications", label: "Alerts", icon: Bell },
        { href: "/profile", label: "Profile", icon: User },
      ];
  return (
    <nav className="safe-bottom fixed inset-x-0 bottom-0 z-40 border-t border-line bg-white/95 backdrop-blur lg:hidden" aria-label="Primary">
      <ul className="mx-auto flex max-w-md items-end justify-around px-2 pt-1.5">
        {items.map((item) => {
          const active = isActive(pathname, item);
          const Icon = item.icon;
          if (item.primary)
            return (
              <li key={item.href} className="-mt-5">
                <Link
                  href={item.href}
                  className="grid size-14 place-items-center rounded-2xl bg-brand-yellow text-ink shadow-[var(--shadow-lift)] ring-4 ring-white active:scale-95"
                  aria-label="Add expense"
                >
                  <Plus className="size-6" strokeWidth={2.5} aria-hidden />
                </Link>
              </li>
            );
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn("flex min-w-14 flex-col items-center gap-0.5 rounded-xl px-2 pb-1.5 pt-1 text-[11px] font-semibold", active ? "text-brand-blue" : "text-ink-muted")}
              >
                <span className={cn("grid h-7 w-12 place-items-center rounded-full", active && "bg-brand-blue-soft")}>
                  <Icon className="size-5" aria-hidden />
                </span>
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

function DemoBanner() {
  const { user } = useAuth();
  const resets = useMemo(
    () =>
      user?.expires_at
        ? new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }).format(new Date(user.expires_at))
        : null,
    [user],
  );
  if (!user?.is_demo) return null;
  return (
    <div className="border-b border-brand-yellow-strong/40 bg-brand-yellow-soft px-4 py-1.5 text-center text-xs text-ink">
      <strong>Demo sandbox</strong> — synthetic data only, private to you{resets ? `, resets ${resets}` : ""}. Add expenses freely.
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const groupId = useCurrentGroupId();
  return (
    <div className="flex min-h-dvh bg-surface">
      <Sidebar groupId={groupId} />
      <div className="flex min-w-0 flex-1 flex-col">
        <DemoBanner />
        <header className="sticky top-0 z-30 border-b border-line bg-white/90 backdrop-blur">
          <div className="mx-auto flex h-16 max-w-[1240px] items-center gap-3 px-4 sm:px-6">
            <Link href={groupId ? `/g/${groupId}` : "/groups"} className="lg:hidden" aria-label="GroupWise AI home">
              <LogoMark className="size-9" />
            </Link>
            <div className="min-w-0 flex-1 lg:max-w-xs">
              <div className="lg:hidden">
                <GroupSwitcher currentId={groupId} className="border-transparent bg-transparent px-1 py-1 hover:border-transparent" />
              </div>
            </div>
            <div className="ml-auto flex items-center gap-1">
              {groupId && (
                <Link
                  href={`/g/${groupId}/ask`}
                  className="hidden h-10 items-center gap-2 rounded-xl border border-line px-3 text-sm font-semibold text-brand-blue-deep hover:bg-brand-blue-soft sm:flex"
                >
                  <Sparkles className="size-4 text-brand-blue" aria-hidden /> Ask GroupWise
                </Link>
              )}
              {groupId && (
                <Link href={`/g/${groupId}/ask`} className="grid size-10 place-items-center rounded-xl text-brand-blue hover:bg-brand-blue-soft sm:hidden" aria-label="Ask GroupWise">
                  <Sparkles className="size-5" aria-hidden />
                </Link>
              )}
              <NotificationBell />
              <UserMenu />
            </div>
          </div>
        </header>
        <main id="main" className="mx-auto w-full max-w-[1240px] flex-1 px-4 pb-28 pt-5 sm:px-6 lg:pb-12 lg:pt-7">
          {children}
        </main>
      </div>
      <BottomNav groupId={groupId} />
    </div>
  );
}
