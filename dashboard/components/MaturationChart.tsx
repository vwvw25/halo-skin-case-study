"use client";

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
import { monthLabel, usd } from "@/lib/format";
import { periodBounds, type Period } from "@/lib/period";

export function MaturationChart({ period }: { period: Period }) {
  const { months } = periodBounds(period);
  const inRange = new Set(months);
  const data = dashboard.cohort_ltv
    .filter((c) => inRange.has(c.acquisition_month))
    .map((c) => ({
      month: monthLabel(c.acquisition_month),
      realized: c.realized_cm_per_customer,
      projected: c.projected_cm_per_customer,
    }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
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
            name === "realized" ? "Realized to date" : "Projected 12-mo",
          ]}
          contentStyle={{ fontSize: 12, borderColor: "#e6e8eb" }}
        />
        <Legend
          formatter={(name) =>
            name === "realized" ? "Realized to date" : "Projected 12-mo"
          }
          iconType="plainline"
          wrapperStyle={{ fontSize: 12 }}
        />
        <Line
          dataKey="realized"
          stroke="#0f766e"
          strokeWidth={2}
          dot={{ r: 2 }}
          isAnimationActive={false}
        />
        <Line
          dataKey="projected"
          stroke="#b45309"
          strokeWidth={2}
          strokeDasharray="5 4"
          dot={{ r: 2 }}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
