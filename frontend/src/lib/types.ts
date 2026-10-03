// API response types. All money values are integer paisa (৳1 = 100 paisa).

export type Paisa = number;

export interface User {
  id: string;
  email: string | null;
  display_name: string;
  auth_provider: "local" | "supabase" | "demo";
  is_demo: boolean;
  avatar_color: string;
  expires_at: string | null;
}

export interface GroupSummary {
  id: string;
  name: string;
  description: string | null;
  group_type: "friends" | "roommates" | "trip" | "event" | "other";
  member_count: number;
  my_member_id: string;
  my_role: string;
  my_net: Paisa;
  total_30d: Paisa;
  total_all_time: Paisa;
  expense_count: number;
  flagged_count: number;
  last_activity: string | null;
  members: { id: string; name: string; color: string }[];
}

export interface Member {
  id: string;
  display_name: string;
  role: "owner" | "member" | "guest";
  status: "active" | "left";
  avatar_color: string;
  is_app_user: boolean;
  is_you: boolean;
  joined_at: string;
}

export interface GroupDetail extends GroupSummary {
  currency: string;
  monthly_budget: Paisa | null;
  created_at: string;
  data_version: number;
  members_detail: Member[];
  invite_code: string;
  invite_url: string;
}

export interface AnomalyReason {
  signal: string;
  strength: number;
  text: string;
  evidence: Record<string, unknown>;
}

export interface Expense {
  id: string;
  description: string;
  merchant: string | null;
  amount: Paisa;
  payer_member_id: string;
  payer_name: string;
  category: string;
  subcategory: string;
  subcategory_label: string;
  expense_type: string;
  category_source: "ai" | "user" | "feedback";
  category_confidence: number | null;
  occurred_at: string;
  payment_method: string;
  split_method: string;
  anomaly: { score: number | null; status: "none" | "flagged" | "valid" | "dismissed"; reasons: AnomalyReason[] };
  participant_count: number;
  notes?: string | null;
  created_at?: string;
  participants?: { member_id: string; name: string; share: Paisa }[];
  reasons?: AnomalyReason[];
}

export interface Prediction {
  subcategory: string;
  subcategory_label: string;
  category: string;
  expense_type: string;
  confidence: number;
  needs_confirmation: boolean;
  alternatives: { subcategory: string; label: string; category: string; probability: number }[];
  signals: string[];
  known_merchant: string | null;
  source: "ai" | "feedback";
  note?: string;
  model: { name: string; version: string };
}

export interface AnomalyResult {
  score: number;
  flagged: boolean;
  signals: Record<string, number>;
  reasons: AnomalyReason[];
  history_count: number;
  limited_history: boolean;
}

export interface Insight {
  id: string;
  kind: "spending_trend" | "anomaly" | "forecast" | "goal" | "dynamics" | "settlement";
  severity: "info" | "warning" | "alert" | "positive";
  title: string;
  observation: string;
  inference: string | null;
  why: string[];
  action: { text: string; link: string } | null;
  confidence: { level: "high" | "medium" | "low"; value: number; basis: string };
  method: string;
  evidence: Record<string, unknown>;
}

export interface Recommendation {
  key: string;
  priority: number;
  kind: string;
  title: string;
  text: string;
  expected_outcome: string;
  impact?: Record<string, number>;
  assumption?: string;
  link: string;
  method: string;
}

export interface HealthFactor {
  key: string;
  label: string;
  weight: number;
  score: number | null;
  value: string;
  explanation: string;
  contribution?: number;
}

export interface Health {
  status: "ok" | "insufficient_data";
  score?: number;
  band?: string;
  factors: HealthFactor[];
  formula?: string;
  disclaimer: string;
  message?: string;
}

export interface ForecastDay {
  date: string;
  dow: string;
  total: Paisa;
  low: Paisa;
  high: Paisa;
  by_category: Record<string, Paisa>;
}

export interface Forecast {
  status: "ok" | "insufficient_data" | "inactive";
  message?: string;
  horizon_days?: number;
  total?: Paisa;
  interval?: { low: Paisa; high: Paisa; level: number };
  confidence?: "high" | "medium" | "low";
  daily?: ForecastDay[];
  by_category?: { category: string; total: Paisa }[];
  pressure_days?: { date: string; dow: string; total: Paisa }[];
  recurring?: { label: string; category: string; amount: Paisa; next_date: string; occurrences: number }[];
  comparison?: { last_period_actual: Paisa; avg_daily_8w: Paisa; change_vs_last_period_pct: number | null };
  drivers?: { kind: string; text: string; category?: string }[];
  history_days?: number;
  transactions_used?: number;
  backtest?: { n_windows: number; weekly_mape?: number; mae_7day?: number; baseline_mean28_mae_7day?: number };
  model?: { name: string; version: string; method: string; weekly_mape: number | null };
  member_shares?: { member_id: string; name: string; share_pct: number; expected: Paisa }[];
  excluded_unusual?: number;
}

export interface GoalPlan {
  goal_id: string;
  title: string;
  description: string | null;
  target: Paisa;
  saved: Paisa;
  remaining: Paisa;
  start_date: string;
  deadline: string;
  days_left: number;
  weeks_left: number;
  progress_pct: number;
  status: "achieved" | "deadline_passed" | "not_started" | "on_track" | "at_risk" | "off_track";
  projection: {
    projected_amount: Paisa;
    on_track_pct: number;
    gap: Paisa;
    rate_weekly: Paisa;
    rate_monthly: Paisa;
    recent_rate_weekly: Paisa;
    required_weekly: Paisa;
    required_monthly: Paisa;
    gap_monthly: Paisa;
    completion_date_at_current_rate: string | null;
    likelihood_pct: number;
    simulated_range: { p10: Paisa; p50: Paisa; p90: Paisa };
    simulations: number;
  };
  weekly_history: { week: number; start: string; amount: Paisa }[];
  contributors: { member_id: string; name: string; amount: Paisa; share_pct: number }[];
  discretionary: { total: Paisa; dining: Paisa; by_category: Record<string, Paisa> };
  scenarios: { key: string; label: string; text: string; assumption?: string; reduction_pct?: number; category?: string }[];
  explanation: string;
  method: string;
  recent_contributions?: { id: string; member_id: string; name: string; amount: Paisa; occurred_at: string; note: string | null }[];
}

export interface SpendingCategory {
  category: string;
  color: string;
  current: Paisa;
  previous: Paisa;
  change: Paisa;
  change_pct: number | null;
  share_pct: number;
  count: number;
}

export interface SpendingReport {
  period_days: number;
  period: { start: string; end: string };
  total: Paisa;
  previous_total: Paisa;
  change: Paisa;
  change_pct: number | null;
  change_pct_excluding_unusual: number | null;
  unusual_in_period: { id: string; amount: Paisa; description: string }[];
  count: number;
  previous_count: number;
  average_expense: Paisa;
  largest_expense: { id: string; amount: Paisa; description: string; category: string; date: string } | null;
  daily_average: Paisa;
  categories: SpendingCategory[];
  focus: { category: string; change: Paisa; change_pct: number | null; current: Paisa; previous: Paisa; count: number } | null;
  drivers: {
    segment: string;
    subcategory_label: string;
    day_type: "weekend" | "weekday";
    current: Paisa;
    previous: Paisa;
    change: Paisa;
    share_of_change_pct: number;
    count_current: number;
    count_previous: number;
    avg_current: Paisa;
    avg_previous: Paisa;
    frequency_effect: Paisa;
    ticket_size_effect: Paisa;
    mainly: "frequency" | "ticket_size";
  }[];
  members: { member_id: string; name: string; color: string; paid: Paisa; consumed: Paisa; paid_share_pct: number }[];
  weekend_share_pct: number;
  by_weekday: { dow: string; total: Paisa }[];
  daily_series: { date: string; total: Paisa; ma7: Paisa }[];
  weekly_series: { week_start: string; total: Paisa }[];
  top_merchants: { merchant: string; total: Paisa; count: number }[];
  basis: string;
  method: string;
}

export interface DynamicsMember {
  member_id: string;
  name: string;
  color: string;
  paid: Paisa;
  paid_count: number;
  paid_share_pct: number;
  consumed: Paisa;
  consumed_share_pct: number;
  imbalance_pct: number;
  high_value_paid_share_pct: number;
  avg_settle_days: number | null;
  avg_wait_days: number | null;
  open_debt: Paisa;
  oldest_open_debt_days: number;
  is_you?: boolean;
}

export interface Dynamics {
  status: "ok" | "insufficient_data";
  message?: string;
  window_days?: number;
  basis?: string;
  total?: Paisa;
  contribution_balance_index?: number;
  median_settle_days?: number | null;
  high_value_threshold?: Paisa;
  members?: DynamicsMember[];
  insights?: { kind: string; severity: string; title: string; text: string; member_id?: string }[];
  recommendations?: { key: string; title: string; text: string; suggested_next_payer?: { member_id: string; name: string } }[];
  responsible_note: string;
  method?: string;
}

export interface Balances {
  total_spent: Paisa;
  members: {
    member_id: string;
    name: string;
    color: string;
    status: string;
    paid: Paisa;
    share: Paisa;
    settlements_sent: Paisa;
    settlements_received: Paisa;
    net: Paisa;
    direction: "gets" | "owes" | "settled";
    is_you: boolean;
  }[];
  transfers: { from_member_id: string; from_name: string; to_member_id: string; to_name: string; amount: Paisa; involves_you: boolean }[];
  naive_transfer_count: number;
  simplified_transfer_count: number;
  outstanding_total: Paisa;
  method: string;
  my_member_id: string;
}

export interface Dashboard {
  group: { id: string; name: string; group_type: string; member_count: number; monthly_budget: Paisa | null };
  me: { member_id: string; name: string; net: Paisa; paid: Paisa; share: Paisa };
  spending: Pick<SpendingReport, "total" | "previous_total" | "change_pct" | "change_pct_excluding_unusual" | "count" | "average_expense" | "categories" | "daily_series" | "period_days" | "basis">;
  health: Health;
  insights: Insight[];
  recommendation: Recommendation | null;
  recommendations: Recommendation[];
  forecast: Forecast;
  goals: GoalPlan[];
  dynamics: { status: string; insights: { kind: string; severity: string; title: string; text: string }[]; contribution_balance_index?: number; members: DynamicsMember[] };
  balances: { outstanding_total: Paisa; simplified_transfer_count: number; naive_transfer_count: number };
  recent_expenses: Expense[];
  llm: { available: boolean; model: string; reason: string | null };
  as_of: string;
}

export interface WhatIfResult {
  status: "ok" | "insufficient_data";
  message?: string;
  basis: string;
  baseline_total: Paisa;
  scenario_total: Paisa;
  monthly_savings: Paisa;
  categories: { category: string; baseline: Paisa; scenario: Paisa; change: Paisa; change_pct: number }[];
  members: { member_id: string; name: string; baseline: Paisa; scenario: Paisa; is_you: boolean }[];
  pressure: { next_7_days: Paisa; recent_weekly_avg: Paisa; ratio: number; level: "low" | "moderate" | "high"; pressure_days: string[] } | null;
  goal: {
    goal_id: string;
    title: string;
    target: Paisa;
    saved: Paisa;
    deadline: string;
    baseline: { projected: Paisa; on_track_pct: number; gap: Paisa; likelihood_pct: number; completion_date: string | null };
    scenario: { projected: Paisa; on_track_pct: number; gap: Paisa; likelihood_pct: number; completion_date: string | null; monthly_to_goal: Paisa };
  } | null;
  recommendation: string | null;
  assumption: string;
  method: string;
}

export interface Fact {
  id: string;
  type: "fact" | "prediction" | "assumption" | "recommendation";
  statement: string;
  source: string;
}

export interface CopilotAnswer {
  question: string;
  answer: string;
  mode: "llm" | "template";
  notice: string | null;
  intent: { name: string; label: string; confidence: number; method: string };
  facts: Fact[];
  cited_fact_ids: string[];
  grounding: { numbers_checked: number; verified: number; unverified: number[]; passed: boolean; rejected_llm_numbers?: number[] };
  basis: string;
  follow_ups: string[];
  llm: { available: boolean; model: string | null };
}

export interface NotificationItem {
  id: string;
  kind: string;
  title: string;
  body: string;
  link: string | null;
  is_read: boolean;
  group_id: string | null;
  group_name: string | null;
  created_at: string;
}

export interface TaxonomyCategory {
  category: string;
  color: string;
  subcategories: { key: string; label: string; expense_type: string; discretionary: boolean }[];
}
