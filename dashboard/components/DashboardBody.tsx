"use client";

import { useState } from "react";
import { Card } from "@/components/Card";
import { CampaignTable } from "@/components/CampaignTable";
import { CohortTable } from "@/components/CohortTable";
import { FilterBar } from "@/components/FilterBar";
import { KpiRow } from "@/components/KpiRow";
import { MaturationChart } from "@/components/MaturationChart";
import { SegmentScatter } from "@/components/SegmentScatter";
import { TrendChart } from "@/components/TrendChart";
import { dashboard } from "@/lib/data";
import { FULL_PERIOD, periodLabel, type Period } from "@/lib/period";

export function DashboardBody() {
  const [period, setPeriod] = useState<Period>(FULL_PERIOD);
  const tc = dashboard.assumptions.target_cohort;

  return (
    <>
      <FilterBar period={period} setPeriod={setPeriod} />

      <div className="mt-6">
        <KpiRow />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card
          title="Spend & CAC"
          subtitle={`Weekly spend (bars) vs cost per acquired customer (line) · ${periodLabel(period)}`}
        >
          <TrendChart period={period} />
        </Card>

        <Card
          title="Cohort maturation"
          subtitle={`CM-LTV per customer by acquisition month — realized to date vs projected to 12 months · ${periodLabel(period)}`}
        >
          <MaturationChart period={period} />
        </Card>
      </div>

      <div className="mt-4">
        <Card
          title="Cumulative value per customer"
          subtitle="Each acquisition cohort's cumulative revenue (or contribution margin) per customer, by month of life. Triangular because recent cohorts have fewer months of history."
        >
          <CohortTable period={period} />
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-5">
        <Card
          title="Where each strategy lands"
          subtitle="LTV:CAC against target-cohort capture, all-time. Bubble size = customers. Teal = acquisition, amber = retargeting/awareness."
          className="lg:col-span-3"
        >
          <SegmentScatter />
          <p className="mt-2 text-xs text-muted">
            Retargeting sits far right on LTV:CAC but low on capture — it
            reacquires customers who would likely have returned anyway. Rank by
            both, not day-1 ROAS.
          </p>
        </Card>

        <Card
          title="Target cohort"
          subtitle="Halo Skin's high-value customer"
          className="lg:col-span-2"
        >
          <ul className="space-y-2 text-sm text-ink">
            <li>
              ≥ {tc.min_orders} orders in the first {tc.window_days} days
            </li>
            <li>average order value ≥ ${tc.min_aov.toFixed(0)}</li>
            <li>
              {tc.requires_premium_sku
                ? "at least one premium-line purchase"
                : "any SKU mix"}
            </li>
          </ul>
          <p className="mt-3 text-xs text-muted">
            Customers younger than {tc.window_days} days get a predicted verdict
            from their first-30-day behaviour; matured customers a realized one.
          </p>
        </Card>
      </div>

      <div className="mt-4">
        <Card
          title="LTV:CAC by campaign"
          subtitle={`12-month contribution-margin LTV ÷ CAC, all-time. Health line ${dashboard.assumptions.healthy_ltv_cac.toFixed(0)}×.`}
        >
          <CampaignTable />
        </Card>
      </div>
    </>
  );
}
