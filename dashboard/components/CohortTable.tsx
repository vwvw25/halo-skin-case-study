"use client";

import { useMemo, useState } from "react";
import { dashboard } from "@/lib/data";
import type { CohortTriangleRow } from "@/lib/data";
import { monthLabel, pct, usd } from "@/lib/format";
import type { Period } from "@/lib/period";

type Metric = "revenue" | "cm";

const TRI = dashboard.cohort_triangle;
const MONTHS = TRI.months;

const series = (row: CohortTriangleRow, metric: Metric) =>
  metric === "revenue" ? row.revenue : row.cm;
const firstOrder = (row: CohortTriangleRow, metric: Metric) =>
  metric === "revenue" ? row.first_order_revenue : row.first_order_cm;
const cohortLtv = (row: CohortTriangleRow, metric: Metric) => {
  const s = series(row, metric).filter((v): v is number => v != null);
  return s.length ? s[s.length - 1] : null;
};

/** light mint → deep teal, on a single scale spanning the visible cells (first order + all months) */
function makeHeat(values: number[]) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  return (value: number | null): { backgroundColor: string; color: string } => {
    if (value == null)
      return { backgroundColor: "transparent", color: "transparent" };
    const t = max > min ? (value - min) / (max - min) : 0;
    const eased = Math.pow(t, 1.35); // lift the low end so early months stay pale
    const l = Math.round(96 - eased * 54); // 96% (pale) → 42% (deep)
    return {
      backgroundColor: `hsl(168, 42%, ${l}%)`,
      color: l < 55 ? "#ffffff" : "#1f2328",
    };
  };
}

export function CohortTable({ period }: { period: Period }) {
  const [metric, setMetric] = useState<Metric>("revenue");
  const lo = Math.min(period.fromIndex, period.toIndex);
  const hi = Math.max(period.fromIndex, period.toIndex);
  const rows = useMemo(() => TRI.rows.slice(lo, hi + 1), [lo, hi]);

  const heat = useMemo(() => {
    const vals = rows.flatMap((r) => [
      ...series(r, metric).filter((v): v is number => v != null),
      ...(firstOrder(r, metric) != null
        ? [firstOrder(r, metric) as number]
        : []),
    ]);
    return makeHeat(vals.length ? vals : [0, 1]);
  }, [rows, metric]);

  const avgByMonth = MONTHS.map((_, i) => {
    const vals = rows
      .map((r) => series(r, metric)[i])
      .filter((v): v is number => v != null);
    return vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : null;
  });
  const avgFirstOrder = (() => {
    const vals = rows
      .map((r) => firstOrder(r, metric))
      .filter((v): v is number => v != null);
    return vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : null;
  })();
  const totalCustomers = rows.reduce((s, r) => s + r.cohort_size, 0);
  const weighted = (pick: (r: CohortTriangleRow) => number | null) =>
    totalCustomers === 0
      ? null
      : rows.reduce((s, r) => s + (pick(r) ?? 0) * r.cohort_size, 0) /
        totalCustomers;
  const blendedRepeat = weighted((r) => r.repeat_rate);
  const blendedCac = weighted((r) => r.cac);
  const blendedLtv = weighted((r) => cohortLtv(r, metric));
  const metricName = metric === "revenue" ? "revenue" : "contribution margin";

  return (
    <div>
      <div className="mb-3 flex w-fit overflow-hidden rounded-md border border-line text-xs">
        {(["revenue", "cm"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMetric(m)}
            className={`px-2.5 py-1 ${metric === m ? "bg-accent text-white" : "bg-surface text-muted"}`}
          >
            {m === "revenue" ? "Revenue" : "Contribution margin"}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] table-fixed text-xs">
          <colgroup>
            <col className="w-14" />
            <col className="w-20" span={5} />
            {MONTHS.map((m) => (
              <col key={m} className="w-14" />
            ))}
          </colgroup>
          <thead>
            <tr className="border-b border-ink text-right uppercase tracking-wide text-muted [&>th]:px-2 [&>th]:py-2 [&>th]:font-medium">
              <th className="!pl-0 text-left">Acquired</th>
              <th>Cohort</th>
              <th>Repeat</th>
              <th>CAC</th>
              <th>Cohort LTV</th>
              <th>First order</th>
              {MONTHS.map((m) => (
                <th key={m}>M{m}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const fo = heat(firstOrder(r, metric));
              return (
                <tr
                  key={r.acquired}
                  className="border-b border-line text-right [&>td]:px-2 [&>td]:py-1.5"
                >
                  <td className="!pl-0 whitespace-nowrap text-left text-ink">
                    {monthLabel(r.acquired)}
                  </td>
                  <td className="tabular-nums">
                    {r.cohort_size.toLocaleString("en-US")}
                  </td>
                  <td className="tabular-nums text-muted">
                    {pct(r.repeat_rate)}
                  </td>
                  <td className="tabular-nums">{usd(r.cac, 0)}</td>
                  <td className="font-semibold tabular-nums">
                    {usd(cohortLtv(r, metric))}
                  </td>
                  <td className="tabular-nums" style={fo}>
                    {usd(firstOrder(r, metric))}
                  </td>
                  {series(r, metric).map((v, i) => {
                    const c = heat(v);
                    return (
                      <td key={i} className="tabular-nums" style={c}>
                        {v == null ? "" : usd(v)}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
            <tr className="border-b border-ink text-right font-semibold [&>td]:px-2 [&>td]:py-2">
              <td className="!pl-0 text-left">Total</td>
              <td className="tabular-nums">
                {totalCustomers.toLocaleString("en-US")}
              </td>
              <td className="tabular-nums">{pct(blendedRepeat)}</td>
              <td className="tabular-nums">{usd(blendedCac, 0)}</td>
              <td className="tabular-nums">{usd(blendedLtv)}</td>
              <td className="tabular-nums">{usd(avgFirstOrder)}</td>
              {MONTHS.map((m) => (
                <td key={m} />
              ))}
            </tr>
            <tr className="text-right text-muted [&>td]:px-2 [&>td]:py-2">
              <td className="!pl-0 text-left">Average</td>
              <td colSpan={4} />
              <td className="tabular-nums">{usd(avgFirstOrder)}</td>
              {avgByMonth.map((v, i) => (
                <td key={i} className="tabular-nums">
                  {usd(v)}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <div className="mt-2 flex items-center justify-end gap-2 text-[11px] text-muted">
        <span>Cumulative {metricName} per customer</span>
        <span
          className="h-2 w-24 rounded"
          style={{
            background:
              "linear-gradient(90deg, hsl(168 42% 95%), hsl(168 42% 42%))",
          }}
        />
      </div>
    </div>
  );
}
