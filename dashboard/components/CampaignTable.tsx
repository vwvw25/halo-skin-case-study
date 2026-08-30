import { dashboard } from "@/lib/data";
import { count, pct, payback, ratio, usd } from "@/lib/format";

export function CampaignTable() {
  const rows = [...dashboard.ltv_cac_by_campaign].sort(
    (a, b) => (b.ltv_cac ?? 0) - (a.ltv_cac ?? 0),
  );
  const healthy = dashboard.assumptions.healthy_ltv_cac;

  return (
    <div className="overflow-x-auto">
      <p className="mb-2 text-xs text-muted">
        CM-LTV is the projected 12-month contribution margin per customer.
      </p>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-ink text-left text-[11px] uppercase tracking-wide text-muted [&>th]:whitespace-nowrap">
            <th className="py-2 pr-3 font-medium">Campaign</th>
            <th className="py-2 px-3 text-right font-medium">Customers</th>
            <th className="py-2 px-3 text-right font-medium">CAC</th>
            <th className="py-2 px-3 text-right font-medium">CM-LTV</th>
            <th className="py-2 px-3 text-right font-medium">LTV:CAC</th>
            <th className="py-2 px-3 text-right font-medium">Payback</th>
            <th className="py-2 pl-3 text-right font-medium">Matured</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.name} className="border-b border-line last:border-ink">
              <td className="py-2 pr-3 text-ink">{r.name}</td>
              <td className="py-2 px-3 text-right tabular-nums">
                {count(r.customers)}
              </td>
              <td className="py-2 px-3 text-right tabular-nums">
                {usd(r.cac, 2)}
              </td>
              <td className="py-2 px-3 text-right tabular-nums">
                {usd(r.cm_ltv_12)}
              </td>
              <td
                className={`py-2 px-3 text-right font-semibold tabular-nums ${
                  (r.ltv_cac ?? 0) >= healthy
                    ? "text-accent"
                    : (r.ltv_cac ?? 0) < 1.5
                      ? "text-bad"
                      : "text-ink"
                }`}
              >
                {ratio(r.ltv_cac)}
              </td>
              <td className="py-2 px-3 text-right tabular-nums">
                {payback(r.payback_months)}
              </td>
              <td className="py-2 pl-3 text-right tabular-nums text-muted">
                {pct(r.realized_share)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
