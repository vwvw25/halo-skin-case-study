import { Card } from "@/components/Card";
import { CampaignTable } from "@/components/CampaignTable";
import { CohortTable } from "@/components/CohortTable";
import { KpiRow } from "@/components/KpiRow";
import { MaturationChart } from "@/components/MaturationChart";
import { SegmentScatter } from "@/components/SegmentScatter";
import { TrendChart } from "@/components/TrendChart";
import { dashboard } from "@/lib/data";
import { monthLabel } from "@/lib/format";

export default function Page() {
  const asOf = new Date(dashboard.as_of + "T00:00:00").toLocaleDateString("en-US", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const tc = dashboard.assumptions.target_cohort;

  return (
    <main className="mx-auto max-w-6xl px-5 py-8">
      <header className="flex flex-wrap items-end justify-between gap-2 border-b-2 border-ink pb-3">
        <div>
          <div className="text-lg font-bold uppercase tracking-[0.14em]">
            Halo<span className="text-accent">.</span>Skin
          </div>
          <h1 className="mt-0.5 text-sm font-medium text-muted">
            Acquisition dashboard — LTV:CAC &amp; target-cohort capture
          </h1>
        </div>
        <div className="text-right text-xs text-muted">
          Data as of {asOf}
          <br />
          Meta Marketing API × Shopify · mock data
        </div>
      </header>

      <div className="mt-6">
        <KpiRow />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card
          title="Spend & CAC"
          subtitle="Weekly spend (bars) vs cost per acquired customer (line), last 26 weeks"
        >
          <TrendChart />
        </Card>

        <Card
          title="Cohort maturation"
          subtitle="CM-LTV per customer by acquisition month — realized to date vs projected to 12 months"
        >
          <MaturationChart />
        </Card>
      </div>

      <div className="mt-4">
        <Card
          title="Cumulative value per customer"
          subtitle="Each acquisition cohort's cumulative revenue (or contribution margin) per customer, by month of life. Triangular because recent cohorts have fewer months of history."
        >
          <CohortTable />
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-5">
        <Card
          title="Where each strategy lands"
          subtitle="LTV:CAC against target-cohort capture. Bubble size = customers. Teal = acquisition, amber = retargeting/awareness."
          className="lg:col-span-3"
        >
          <SegmentScatter />
          <p className="mt-2 text-xs text-muted">
            Retargeting sits far right on LTV:CAC but low on capture — it reacquires customers who
            would likely have returned anyway. Rank by both, not day-1 ROAS.
          </p>
        </Card>

        <Card title="Target cohort" subtitle="Halo Skin's high-value customer" className="lg:col-span-2">
          <ul className="space-y-2 text-sm text-ink">
            <li>≥ {tc.min_orders} orders in the first {tc.window_days} days</li>
            <li>average order value ≥ ${tc.min_aov.toFixed(0)}</li>
            <li>{tc.requires_premium_sku ? "at least one premium-line purchase" : "any SKU mix"}</li>
          </ul>
          <p className="mt-3 text-xs text-muted">
            Customers younger than {tc.window_days} days get a predicted verdict from their
            first-30-day behaviour; matured customers a realized one.
          </p>
        </Card>
      </div>

      <div className="mt-4">
        <Card
          title="LTV:CAC by campaign"
          subtitle={`12-month contribution-margin LTV ÷ CAC. Health line ${dashboard.assumptions.healthy_ltv_cac.toFixed(0)}×.`}
        >
          <CampaignTable />
        </Card>
      </div>

      <footer className="mt-8 border-t border-line pt-3 text-xs text-muted">
        Portfolio case study · fictional brand · numbers generated from a seeded model.
        First matured cohort: {monthLabel(dashboard.cohort_ltv[0]?.acquisition_month ?? dashboard.as_of)}.
      </footer>
    </main>
  );
}
