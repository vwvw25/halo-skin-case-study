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
import { periodBounds, type Period } from "@/lib/period";

export function TrendChart({ period }: { period: Period }) {
  const { start, end } = periodBounds(period);
  const data = dashboard.weekly_trend
    .filter((w) => {
      const d = new Date(w.week + "T00:00:00");
      return d >= start && d <= end;
    })
    .map((w) => ({ week: weekLabel(w.week), spend: w.spend, cac: w.cac }));
  const interval = Math.max(0, Math.ceil(data.length / 8) - 1);

  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart
        data={data}
        margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
      >
        <CartesianGrid stroke="#e6e8eb" vertical={false} />
        <XAxis
          dataKey="week"
          tickLine={false}
          axisLine={false}
          interval={interval}
          minTickGap={16}
        />
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
          formatter={(value, name) => {
            const isCac = name === "cac";
            return [usd(Number(value), isCac ? 2 : 0), isCac ? "CAC" : "Spend"];
          }}
          contentStyle={{ fontSize: 12, borderColor: "#e6e8eb" }}
        />
        <Bar
          yAxisId="spend"
          dataKey="spend"
          fill="#5eead4"
          radius={[2, 2, 0, 0]}
          isAnimationActive={false}
        />
        <Line
          yAxisId="cac"
          dataKey="cac"
          stroke="#b45309"
          strokeWidth={2}
          dot={false}
          connectNulls
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
