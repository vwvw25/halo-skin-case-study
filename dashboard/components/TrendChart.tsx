"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { dashboard } from "@/lib/data";
import { usd, weekLabel } from "@/lib/format";

const data = dashboard.weekly_trend.slice(-26).map((w) => ({
  week: weekLabel(w.week),
  spend: w.spend,
  cac: w.cac,
}));

export function TrendChart() {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="#e6e8eb" vertical={false} />
        <XAxis dataKey="week" tickLine={false} axisLine={false} interval={3} />
        <YAxis
          yAxisId="spend"
          tickLine={false}
          axisLine={false}
          width={48}
          tickFormatter={(v) => `$${Math.round(v / 1000)}k`}
        />
        <YAxis
          yAxisId="cac"
          orientation="right"
          tickLine={false}
          axisLine={false}
          width={44}
          tickFormatter={(v) => `$${Math.round(v)}`}
        />
        <Tooltip
          formatter={(v: number, name) => [usd(v, name === "cac" ? 2 : 0), name === "cac" ? "CAC" : "Spend"]}
          contentStyle={{ fontSize: 12, borderColor: "#e6e8eb" }}
        />
        <Bar yAxisId="spend" dataKey="spend" fill="#5eead4" radius={[2, 2, 0, 0]} />
        <Line
          yAxisId="cac"
          dataKey="cac"
          stroke="#b45309"
          strokeWidth={2}
          dot={false}
          connectNulls
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
