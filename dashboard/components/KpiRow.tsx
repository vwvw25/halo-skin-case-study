import { dashboard } from "@/lib/data";
import { count, pct, ratio, usd } from "@/lib/format";

function Kpi({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="rounded-lg border border-line border-t-2 border-t-accent bg-surface p-4">
      <div className="text-[11px] uppercase tracking-wide text-muted">
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold text-ink">{value}</div>
      {note && <div className="mt-0.5 text-[11px] text-muted">{note}</div>}
    </div>
  );
}

export function KpiRow() {
  const h = dashboard.headline;
  const a = dashboard.assumptions;
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
      <Kpi
        label="Current CAC"
        value={usd(h.blended_cac, 2)}
        note="most recent month, attributed"
      />
      <Kpi
        label={`${a.ltv_horizon_months}-mo CM-LTV`}
        value={usd(h.blended_cm_ltv_12)}
        note="projected, per customer"
      />
      <Kpi
        label="Blended LTV:CAC"
        value={ratio(h.blended_ltv_cac)}
        note={`health line ${a.healthy_ltv_cac.toFixed(0)}×`}
      />
      <Kpi
        label="Target-cohort share"
        value={pct(h.target_cohort_share)}
        note="of matured customers"
      />
      <Kpi
        label="Customers"
        value={count(h.customers_total)}
        note="attributed to Meta"
      />
    </div>
  );
}
