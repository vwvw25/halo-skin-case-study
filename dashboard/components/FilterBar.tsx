"use client";

import { dashboard } from "@/lib/data";
import { monthLabel } from "@/lib/format";
import { MONTHS, MONTH_OPTIONS, type Period } from "@/lib/period";

export function FilterBar({
  period,
  setPeriod,
}: {
  period: Period;
  setPeriod: (p: Period) => void;
}) {
  const lo = Math.min(period.fromIndex, period.toIndex);
  const hi = Math.max(period.fromIndex, period.toIndex);

  function exportCsv() {
    const tri = dashboard.cohort_triangle;
    const rows = tri.rows.slice(lo, hi + 1);
    const header = [
      "Acquired",
      "Cohort size",
      "Repeat %",
      "CAC",
      "Revenue LTV",
      "CM LTV",
      "First order revenue",
      "First order CM",
      ...tri.months.map((m) => `Revenue M${m}`),
      ...tri.months.map((m) => `CM M${m}`),
    ];
    const body = rows.map((r) => {
      const rev = r.revenue.filter((v): v is number => v != null);
      const cm = r.cm.filter((v): v is number => v != null);
      return [
        monthLabel(r.acquired),
        r.cohort_size,
        r.repeat_rate ?? "",
        r.cac ?? "",
        rev.length ? rev[rev.length - 1] : "",
        cm.length ? cm[cm.length - 1] : "",
        r.first_order_revenue ?? "",
        r.first_order_cm ?? "",
        ...r.revenue.map((v) => v ?? ""),
        ...r.cm.map((v) => v ?? ""),
      ];
    });
    const csv = [header, ...body].map((line) => line.join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `halo-skin-cohorts-${MONTHS[lo]}_${MONTHS[hi]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-ink py-3">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-xs uppercase tracking-wide text-muted">
          Acquisition period
        </span>
        <span className="flex items-center gap-1 rounded-md border border-line bg-surface px-2.5 py-1 text-xs">
          <select
            aria-label="From month"
            value={lo}
            onChange={(e) =>
              setPeriod({ ...period, fromIndex: Number(e.target.value) })
            }
            className="bg-transparent outline-none"
          >
            {MONTH_OPTIONS.map((o) => (
              <option key={o.iso} value={o.index}>
                {o.label}
              </option>
            ))}
          </select>
          <span className="text-muted">–</span>
          <select
            aria-label="To month"
            value={hi}
            onChange={(e) =>
              setPeriod({ ...period, toIndex: Number(e.target.value) })
            }
            className="bg-transparent outline-none"
          >
            {MONTH_OPTIONS.map((o) => (
              <option key={o.iso} value={o.index}>
                {o.label}
              </option>
            ))}
          </select>
        </span>
      </div>
      <button
        onClick={exportCsv}
        className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"
      >
        ↓ Export CSV
      </button>
    </div>
  );
}
