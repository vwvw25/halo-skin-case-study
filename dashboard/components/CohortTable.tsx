"use client";

import { useMemo, useState } from "react";
import { dashboard } from "@/lib/data";
import type { CohortTriangleRow } from "@/lib/data";
import { count, monthLabel, pct, ratio, usd } from "@/lib/format";

type Metric = "revenue" | "cm";

const TRI = dashboard.cohort_triangle;
const MONTHS = TRI.months;
const LABELS = TRI.rows.map((r) => r.acquired);

function series(row: CohortTriangleRow, metric: Metric): (number | null)[] {
  return metric === "revenue" ? row.revenue : row.cm;
}
function firstOrder(row: CohortTriangleRow, metric: Metric): number | null {
  return metric === "revenue" ? row.first_order_revenue : row.first_order_cm;
}
function cohortLtv(row: CohortTriangleRow, metric: Metric): number | null {
  const s = series(row, metric).filter((v): v is number => v != null);
  return s.length ? s[s.length - 1] : null;
}

/** teal→ink green scale, matched to the rest of the dashboard */
function heat(value: number | null, min: number, max: number): { bg: string; fg: string } {
  if (value == null) return { bg: "transparent", fg: "transparent" };
  const t = max > min ? (value - min) / (max - min) : 0;
  // light mint at t=0, deep teal at t=1
  const l = 96 - t * 68;
  return { bg: `hsl(168 45% ${l}%)`, fg: l < 55 ? "#ffffff" : "#1f2328" };
}

export function CohortTable() {
  const [metric, setMetric] = useState<Metric>("revenue");
  const [from, setFrom] = useState(0);
  const [to, setTo] = useState(LABELS.length - 1);

  const lo = Math.min(from, to);
  const hi = Math.max(from, to);
  const rows = useMemo(() => TRI.rows.slice(lo, hi + 1), [lo, hi]);

  const cellValues = rows.flatMap((r) => series(r, metric).filter((v): v is number => v != null));
  const min = Math.min(...cellValues, 0);
  const max = Math.max(...cellValues, 1);

  const totalCustomers = rows.reduce((s, r) => s + r.cohort_size, 0);
  const weighted = (fn: (r: CohortTriangleRow) => number | null) =>
    totalCustomers === 0
      ? null
      : rows.reduce((s, r) => s + (fn(r) ?? 0) * r.cohort_size, 0) / totalCustomers;

  const blendedLtv = weighted((r) => cohortLtv(r, metric));
  const blendedCac = weighted((r) => r.cac);
  const blendedRepeat = weighted((r) => r.repeat_rate);
  const blendedFirstOrder = weighted((r) => firstOrder(r, metric));

  // prior equal-length window, for the delta
  const windowLen = hi - lo + 1;
  const priorRows = TRI.rows.slice(Math.max(0, lo - windowLen), lo);
  const priorCustomers = priorRows.reduce((s, r) => s + r.cohort_size, 0);
  const priorLtv =
    priorCustomers === 0
      ? null
      : priorRows.reduce((s, r) => s + (cohortLtv(r, metric) ?? 0) * r.cohort_size, 0) /
        priorCustomers;
  const ltvDelta = priorLtv && blendedLtv ? blendedLtv / priorLtv - 1 : null;

  const avgByMonth = MONTHS.map((_, i) => {
    const vals = rows.map((r) => series(r, metric)[i]).filter((v): v is number => v != null);
    return vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : null;
  });
  const avgFirstOrder = (() => {
    const vals = rows.map((r) => firstOrder(r, metric)).filter((v): v is number => v != null);
    return vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : null;
  })();

  function exportCsv() {
    const header = [
      "Acquired",
      "Cohort size",
      "Repeat %",
      "CAC",
      "Cohort LTV",
      "First order",
      ...MONTHS.map((m) => `Month ${m}`),
    ];
    const body = rows.map((r) => [
      monthLabel(r.acquired),
      r.cohort_size,
      r.repeat_rate ?? "",
      r.cac ?? "",
      cohortLtv(r, metric) ?? "",
      firstOrder(r, metric) ?? "",
      ...series(r, metric).map((v) => v ?? ""),
    ]);
    const csv = [header, ...body].map((line) => line.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `halo-skin-cohorts-${metric}-${dashboard.as_of}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const metricName = metric === "revenue" ? "revenue" : "contribution margin";

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm">
          <div className="flex overflow-hidden rounded-md border border-line">
            <button
              onClick={() => setMetric("revenue")}
              className={`px-2.5 py-1 text-xs ${metric === "revenue" ? "bg-accent text-white" : "bg-surface text-muted"}`}
            >
              Revenue
            </button>
            <button
              onClick={() => setMetric("cm")}
              className={`px-2.5 py-1 text-xs ${metric === "cm" ? "bg-accent text-white" : "bg-surface text-muted"}`}
            >
              Contribution margin
            </button>
          </div>
          <span className="rounded-md border border-line px-2.5 py-1 text-xs text-muted">
            <select
              value={from}
              onChange={(e) => setFrom(Number(e.target.value))}
              className="bg-transparent outline-none"
            >
              {LABELS.map((l, i) => (
                <option key={l} value={i}>
                  {monthLabel(l)}
                </option>
              ))}
            </select>
            {" – "}
            <select
              value={to}
              onChange={(e) => setTo(Number(e.target.value))}
              className="bg-transparent outline-none"
            >
              {LABELS.map((l, i) => (
                <option key={l} value={i}>
                  {monthLabel(l)}
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

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <MiniKpi
          label={`Blended ${metricName} LTV`}
          value={usd(blendedLtv)}
          note={
            ltvDelta == null
              ? `weighted, ${windowLen} cohorts`
              : `${ltvDelta >= 0 ? "▲" : "▼"} ${pct(Math.abs(ltvDelta))} vs prior ${windowLen} mo`
          }
          good={ltvDelta == null ? undefined : ltvDelta >= 0}
        />
        <MiniKpi label="Blended CAC" value={usd(blendedCac, 2)} note={`repeat rate ${pct(blendedRepeat)}`} />
        <MiniKpi
          label="LTV : CAC"
          value={blendedLtv && blendedCac ? ratio(blendedLtv / blendedCac) : "—"}
          note={
            blendedFirstOrder && blendedCac && blendedFirstOrder >= blendedCac
              ? "CAC recovered on first order"
              : "recovered over repeat orders"
          }
        />
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-xs">
          <thead>
            <tr className="border-b border-ink text-left uppercase tracking-wide text-muted [&>th]:whitespace-nowrap [&>th]:px-2 [&>th]:py-2 [&>th]:font-medium">
              <th className="!pl-0">Acquired</th>
              <th className="text-right">Cohort</th>
              <th className="text-right">Repeat</th>
              <th className="text-right">CAC</th>
              <th className="text-right">Cohort LTV</th>
              <th className="text-right">First order</th>
              {MONTHS.map((m) => (
                <th key={m} className="text-right">
                  M{m}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.acquired} className="border-b border-line [&>td]:px-2 [&>td]:py-1.5">
                <td className="!pl-0 whitespace-nowrap text-ink">{monthLabel(r.acquired)}</td>
                <td className="text-right tabular-nums">{count(r.cohort_size)}</td>
                <td className="text-right tabular-nums text-muted">{pct(r.repeat_rate)}</td>
                <td className="text-right tabular-nums">{usd(r.cac, 0)}</td>
                <td className="text-right font-semibold tabular-nums">{usd(cohortLtv(r, metric))}</td>
                <td className="text-right tabular-nums text-muted">{usd(firstOrder(r, metric))}</td>
                {series(r, metric).map((v, i) => {
                  const c = heat(v, min, max);
                  return (
                    <td
                      key={i}
                      className="text-right tabular-nums"
                      style={{ background: c.bg, color: c.fg }}
                    >
                      {v == null ? "" : usd(v)}
                    </td>
                  );
                })}
              </tr>
            ))}
            <tr className="border-b border-ink font-semibold [&>td]:px-2 [&>td]:py-2">
              <td className="!pl-0">Total</td>
              <td className="text-right tabular-nums">{count(totalCustomers)}</td>
              <td className="text-right tabular-nums">{pct(blendedRepeat)}</td>
              <td className="text-right tabular-nums">{usd(blendedCac, 0)}</td>
              <td className="text-right tabular-nums">{usd(blendedLtv)}</td>
              <td className="text-right tabular-nums">{usd(avgFirstOrder)}</td>
              {MONTHS.map((m) => (
                <td key={m} />
              ))}
            </tr>
            <tr className="text-muted [&>td]:px-2 [&>td]:py-2">
              <td className="!pl-0">Average</td>
              <td colSpan={4} />
              <td className="text-right tabular-nums">{usd(avgFirstOrder)}</td>
              {avgByMonth.map((v, i) => (
                <td key={i} className="text-right tabular-nums">
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
          style={{ background: "linear-gradient(90deg, hsl(168 45% 94%), hsl(168 45% 30%))" }}
        />
      </div>
    </div>
  );
}

function MiniKpi({
  label,
  value,
  note,
  good,
}: {
  label: string;
  value: string;
  note?: string;
  good?: boolean;
}) {
  return (
    <div className="rounded-md border border-line bg-canvas p-3">
      <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-0.5 text-lg font-semibold text-ink">{value}</div>
      {note && (
        <div
          className={`text-[11px] ${good === undefined ? "text-muted" : good ? "text-accent" : "text-bad"}`}
        >
          {note}
        </div>
      )}
    </div>
  );
}
