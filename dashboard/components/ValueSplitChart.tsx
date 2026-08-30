"use client";

import { useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { dashboard } from "@/lib/data";
import { usd } from "@/lib/format";

type Metric = "cum_revenue" | "cum_cm";

const NAME = dashboard.assumptions.target_cohort.name;
const rows = dashboard.value_by_target;
const months = [...new Set(rows.map((r) => r.month_index))].sort(
  (a, b) => a - b,
);

function buildData(metric: Metric) {
  return months.map((m) => {
    const at = (seg: string) =>
      rows.find((r) => r.month_index === m && r.segment === seg)?.[metric];
    return {
      month: `M${m}`,
      target: at("target"),
      other: at("other"),
      blended: at("blended"),
    };
  });
}

const LABELS: Record<string, string> = {
  target: NAME,
  other: "Everyone else",
  blended: "Blended average",
};

export function ValueSplitChart() {
  const [metric, setMetric] = useState<Metric>("cum_revenue");
  const data = buildData(metric);
  const kind = metric === "cum_revenue" ? "revenue" : "contribution margin";
  const last = data[data.length - 1];
  const multiple =
    last && last.other && last.target
      ? (last.target / last.other).toFixed(1)
      : "—";

  return (
    <div>
      <div className="mb-3 flex w-fit overflow-hidden rounded-md border border-line text-xs">
        {(["cum_revenue", "cum_cm"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMetric(m)}
            className={`px-2.5 py-1 ${metric === m ? "bg-accent text-white" : "bg-surface text-muted"}`}
          >
            {m === "cum_revenue" ? "Revenue" : "Contribution margin"}
          </button>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <LineChart
          data={data}
          margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
        >
          <CartesianGrid stroke="#e6e8eb" vertical={false} />
          <XAxis dataKey="month" tickLine={false} axisLine={false} />
          <YAxis
            tickLine={false}
            axisLine={false}
            width={48}
            tickFormatter={(v) => `$${Math.round(v)}`}
          />
          <Tooltip
            formatter={(value, name) => [
              usd(Number(value)),
              LABELS[String(name)] ?? String(name),
            ]}
            contentStyle={{ fontSize: 12, borderColor: "#e6e8eb" }}
          />
          <Legend
            formatter={(name) => LABELS[String(name)] ?? String(name)}
            wrapperStyle={{ fontSize: 12 }}
          />
          <Line
            dataKey="target"
            stroke="#0f766e"
            strokeWidth={2.5}
            dot={{ r: 2 }}
            isAnimationActive={false}
          />
          <Line
            dataKey="blended"
            stroke="#8b949e"
            strokeWidth={2}
            strokeDasharray="5 4"
            dot={false}
            isAnimationActive={false}
          />
          <Line
            dataKey="other"
            stroke="#b45309"
            strokeWidth={2}
            dot={{ r: 2 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>

      <p className="mt-2 text-xs text-muted">
        Cumulative {kind} per customer by month of life. {NAME} reach{" "}
        <span className="font-medium text-ink">{multiple}×</span> the value of
        everyone else by month {months[months.length - 1]} — and the blended
        average tracks the lower line, because {NAME} are a minority. Averaging
        hides the split.
      </p>
    </div>
  );
}
