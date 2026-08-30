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

const data = dashboard.cohort_ltv.map((c) => ({
  month: monthLabel(c.acquisition_month),
  realized: c.realized_cm_per_customer,
  projected: c.projected_cm_per_customer,
}));

export function MaturationChart() {
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
          formatter={(v: number, name) => [usd(v), name === "realized" ? "Realized to date" : "Projected 12-mo"]}
          contentStyle={{ fontSize: 12, borderColor: "#e6e8eb" }}
        />
        <Legend
          formatter={(name) => (name === "realized" ? "Realized to date" : "Projected 12-mo")}
          iconType="plainline"
          wrapperStyle={{ fontSize: 12 }}
        />
        <Line dataKey="realized" stroke="#0f766e" strokeWidth={2} dot={{ r: 2 }} />
        <Line
          dataKey="projected"
          stroke="#b45309"
          strokeWidth={2}
          strokeDasharray="5 4"
          dot={{ r: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
