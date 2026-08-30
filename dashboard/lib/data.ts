import raw from "@/data/dashboard.json";

export interface Assumptions {
  ltv_horizon_months: number;
  target_cohort: {
    name: string;
    seed_campaign: string;
    min_orders: number;
    window_days: number;
    min_aov: number;
    requires_premium_sku: boolean;
  };
  healthy_ltv_cac: number;
}

export interface ValueByTargetRow {
  month_index: number;
  segment: "target" | "other" | "blended";
  n: number;
  cum_revenue: number;
  cum_cm: number;
}

export interface Headline {
  blended_cac: number;
  blended_cm_ltv_12: number;
  blended_ltv_cac: number | null;
  customers_total: number;
  target_cohort_share: number;
}

export interface WeeklyPoint {
  week: string;
  spend: number;
  impressions: number;
  clicks: number;
  new_customers: number;
  cac: number | null;
  first_order_cm: number | null;
  repeat_rate_30d: number | null;
}

export interface MaturationPoint {
  tenure_month: number;
  cum_cm_per_customer: number;
}

export interface CohortPoint {
  acquisition_month: string;
  cohort_size: number;
  observed_age_months: number;
  realized_cm_per_customer: number;
  projected_cm_per_customer: number;
  maturity: "realized" | "projected";
}

export interface CampaignRow {
  name: string;
  customers: number;
  cac: number | null;
  cm_ltv_12: number;
  ltv_cac: number | null;
  payback_months: number | null;
  realized_share: number;
}

export interface StrategyLtvRow {
  strategy: string;
  customers: number;
  cac: number | null;
  cm_ltv_12: number;
  ltv_cac: number | null;
  payback_months: number | null;
}

export interface CaptureRow {
  acquisition_strategy: string;
  customers: number;
  matured: number;
  realized_capture_rate: number | null;
  predicted_capture_rate: number | null;
  blended_capture_rate: number | null;
}

export interface CohortTriangleRow {
  acquired: string;
  cohort_size: number;
  repeat_rate: number | null;
  cac: number | null;
  first_order_revenue: number | null;
  first_order_cm: number | null;
  revenue: (number | null)[];
  cm: (number | null)[];
}

export interface CohortTriangle {
  months: number[];
  rows: CohortTriangleRow[];
}

export interface Dashboard {
  brand: string;
  as_of: string;
  assumptions: Assumptions;
  headline: Headline;
  weekly_trend: WeeklyPoint[];
  monthly_spend: {
    period: string;
    spend: number;
    new_customers: number;
    cac: number | null;
  }[];
  maturation_curve: MaturationPoint[];
  cohort_ltv: CohortPoint[];
  ltv_cac_by_campaign: CampaignRow[];
  ltv_cac_by_strategy: StrategyLtvRow[];
  capture_by_strategy: CaptureRow[];
  cohort_triangle: CohortTriangle;
  value_by_target: ValueByTargetRow[];
}

export const dashboard = raw as unknown as Dashboard;

export const STRATEGY_LABELS: Record<string, string> = {
  prospecting_broad: "Prospecting — Broad",
  prospecting_interest: "Prospecting — Interest",
  lookalike: "Lookalike",
  advantage_plus: "Advantage+",
  retargeting: "Retargeting",
  awareness: "Awareness",
};

export const ACQUISITION_STRATEGIES = new Set([
  "prospecting_broad",
  "prospecting_interest",
  "lookalike",
  "advantage_plus",
]);
