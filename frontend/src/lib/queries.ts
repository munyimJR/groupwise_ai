"use client";

import { keepPreviousData, useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";
import type {
  Balances,
  CopilotAnswer,
  Dashboard,
  Dynamics,
  Expense,
  Forecast,
  GoalPlan,
  GroupDetail,
  GroupSummary,
  Health,
  Insight,
  NotificationItem,
  Prediction,
  Recommendation,
  SpendingReport,
  TaxonomyCategory,
  WhatIfResult,
} from "./types";

export const keys = {
  groups: ["groups"] as const,
  group: (id: string) => ["g", id] as const,
};

export function useGroups(enabled = true) {
  return useQuery({ queryKey: keys.groups, queryFn: () => api<GroupSummary[]>("/groups"), enabled });
}

export function useGroup(id: string | undefined) {
  return useQuery({ queryKey: [...keys.group(id ?? ""), "detail"], queryFn: () => api<GroupDetail>(`/groups/${id}`), enabled: !!id });
}

export function useDashboard(id: string) {
  return useQuery({ queryKey: [...keys.group(id), "dashboard"], queryFn: () => api<Dashboard>(`/groups/${id}/dashboard`) });
}

export interface ExpenseFilters {
  q?: string;
  category?: string;
  flagged?: boolean;
}

export function useExpenses(id: string, filters: ExpenseFilters) {
  return useInfiniteQuery({
    queryKey: [...keys.group(id), "expenses", filters],
    initialPageParam: 0,
    queryFn: ({ pageParam }) => {
      const p = new URLSearchParams({ limit: "25", offset: String(pageParam) });
      if (filters.q) p.set("q", filters.q);
      if (filters.category) p.set("category", filters.category);
      if (filters.flagged) p.set("flagged", "true");
      return api<{ items: Expense[]; total: number; offset: number; limit: number }>(`/groups/${id}/expenses?${p}`);
    },
    getNextPageParam: (last) => (last.offset + last.limit < last.total ? last.offset + last.limit : undefined),
    placeholderData: keepPreviousData,
  });
}

export function useExpense(id: string, expenseId: string) {
  return useQuery({ queryKey: [...keys.group(id), "expense", expenseId], queryFn: () => api<Expense>(`/groups/${id}/expenses/${expenseId}`) });
}

export function useBalances(id: string) {
  return useQuery({ queryKey: [...keys.group(id), "balances"], queryFn: () => api<Balances>(`/groups/${id}/balances`) });
}

export function useSettlements(id: string) {
  return useQuery({
    queryKey: [...keys.group(id), "settlements"],
    queryFn: () => api<{ id: string; from_name: string; to_name: string; amount: number; occurred_at: string; note: string | null }[]>(`/groups/${id}/settlements`),
  });
}

export function useInsights(id: string) {
  return useQuery({
    queryKey: [...keys.group(id), "insights"],
    queryFn: () => api<{ insights: Insight[]; recommendations: Recommendation[]; anomalies: Expense[] }>(`/groups/${id}/insights`),
  });
}

export function useSpending(id: string, days: number) {
  return useQuery({
    queryKey: [...keys.group(id), "spending", days],
    queryFn: () => api<SpendingReport>(`/groups/${id}/analytics/spending?days=${days}`),
    placeholderData: keepPreviousData,
  });
}

export function useForecast(id: string, horizon: number) {
  return useQuery({
    queryKey: [...keys.group(id), "forecast", horizon],
    queryFn: () => api<Forecast>(`/groups/${id}/forecast?horizon=${horizon}`),
    placeholderData: keepPreviousData,
  });
}

export function useDynamics(id: string) {
  return useQuery({ queryKey: [...keys.group(id), "dynamics"], queryFn: () => api<Dynamics>(`/groups/${id}/dynamics`) });
}

export function useHealth(id: string) {
  return useQuery({ queryKey: [...keys.group(id), "health"], queryFn: () => api<Health>(`/groups/${id}/health`) });
}

export function useGoals(id: string) {
  return useQuery({ queryKey: [...keys.group(id), "goals"], queryFn: () => api<GoalPlan[]>(`/groups/${id}/goals`) });
}

export function useGoal(id: string, goalId: string) {
  return useQuery({ queryKey: [...keys.group(id), "goal", goalId], queryFn: () => api<GoalPlan>(`/groups/${id}/goals/${goalId}`), enabled: !!goalId });
}

export interface WhatIfInput {
  category_changes: Record<string, number>;
  overall_change_pct: number;
  extra_monthly_contribution: number;
  goal_id?: string | null;
  redirect_savings: boolean;
}

export function useWhatIf(id: string, input: WhatIfInput) {
  return useQuery({
    queryKey: [...keys.group(id), "whatif", input],
    queryFn: () => api<WhatIfResult>(`/groups/${id}/what-if`, { body: input }),
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });
}

export function useNotifications(enabled = true) {
  return useQuery({
    queryKey: ["notifications"],
    queryFn: () => api<{ unread: number; items: NotificationItem[] }>("/notifications"),
    enabled,
    refetchInterval: 60_000,
  });
}

export function useTaxonomy() {
  return useQuery({ queryKey: ["taxonomy"], queryFn: () => api<TaxonomyCategory[]>("/meta/taxonomy", { auth: false }), staleTime: Infinity });
}

export function useCategorize(text: string, groupId: string) {
  return useQuery({
    queryKey: ["categorize", groupId, text],
    queryFn: ({ signal }) =>
      api<{ parsed: { description: string; amount: number | null; merchant: string | null }; prediction: Prediction }>("/categorize", {
        body: { text, group_id: groupId },
        signal,
      }),
    enabled: text.trim().length >= 3,
    staleTime: 5 * 60_000,
    placeholderData: keepPreviousData,
  });
}

/** Invalidate everything derived from a group's data after a mutation. */
export function useInvalidateGroup(id: string) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: keys.group(id) });
    qc.invalidateQueries({ queryKey: keys.groups });
    qc.invalidateQueries({ queryKey: ["notifications"] });
  };
}

export function useGroupMutation<TBody, TResult>(id: string, path: string | ((b: TBody) => string), method = "POST") {
  const invalidate = useInvalidateGroup(id);
  return useMutation({
    mutationFn: (body: TBody) => api<TResult>(typeof path === "function" ? path(body) : path, { method, body }),
    onSuccess: invalidate,
  });
}

export function useAskCopilot(id: string) {
  return useMutation({
    mutationFn: (body: { question: string; history: { role: "user" | "assistant"; content: string }[] }) =>
      api<CopilotAnswer>(`/groups/${id}/copilot`, { body }),
  });
}
