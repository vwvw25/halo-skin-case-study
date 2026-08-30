"use client";

import {
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { ACQUISITION_STRATEGIES, STRATEGY_LABELS, dashboard } from "@/lib/data";
import { pct, ratio } from "@/lib/format";

const captureByStrategy = new Map(
  dashboard.capture_by_strategy.map((c) => [c.acquisition_strategy, c]),
);

const points = dashboard.ltv_cac_by_strategy
  .map((s) => {
    const cap = captureByStrategy.get(s.strategy);
    return {
      strategy: s.strategy,
      label: STRATEGY_LABELS[s.strategy] ?? s.strategy,
      ltv_cac: s.ltv_cac ?? 0,
      capture: cap?.realized_capture_rate ?? 0,
      customers: s.customers,
      isAcquisition: ACQUISITION_STRATEGIES.has(s.strategy),
    };
  })
  .filter((p) => p.ltv_cac > 0 && p.capture > 0);

const blendedCapture = dashboard.headline.target_cohort_share;

export function SegmentScatter() {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ScatterChart margin={{ top: 12, right: 16, bottom: 16, left: 4 }}>
        <CartesianGrid stroke="#e6e8eb" />
        <XAxis
          type="number"
          dataKey="ltv_cac"
          name="LTV:CAC"
          tickLine={false}
          axisLine={false}
          domain={[0, 6]}
          ticks={[0, 1, 2, 3, 4, 5, 6]}
          tickFormatter={(v) => `${v}×`}
          label={{
            value: "LTV:CAC (12-mo)",
            position: "insideBottom",
            offset: -8,
            fontSize: 11,
          }}
        />
        <YAxis
          type="number"
          dataKey="capture"
          name="Capture"
          tickLine={false}
          axisLine={false}
          width={44}
          tickFormatter={(v) => `${Math.round(v * 100)}%`}
          label={{
            value: "Target capture",
            angle: -90,
            position: "insideLeft",
            fontSize: 11,
          }}
        />
        <ZAxis type="number" dataKey="customers" range={[80, 900]} />
        <ReferenceLine
          x={dashboard.assumptions.healthy_ltv_cac}
          stroke="#8b949e"
          strokeDasharray="4 4"
          label={{
            value: "3× health line",
            fontSize: 10,
            fill: "#8b949e",
            position: "top",
          }}
        />
        <ReferenceLine
          y={blendedCapture}
          stroke="#8b949e"
          strokeDasharray="4 4"
        />
        <Tooltip
          cursor={{ strokeDasharray: "3 3" }}
          content={({ payload }) => {
            const p = payload?.[0]?.payload as
              (typeof points)[number] | undefined;
            if (!p) return null;
            return (
              <div className="rounded border border-line bg-surface px-2 py-1.5 text-xs">
                <div className="font-semibold">{p.label}</div>
                <div>LTV:CAC {ratio(p.ltv_cac)}</div>
                <div>Capture {pct(p.capture)}</div>
                <div className="text-muted">
                  {p.customers.toLocaleString()} customers
                </div>
              </div>
            );
          }}
        />
        <Scatter data={points} isAnimationActive={false}>
          {points.map((p) => (
            <Cell
              key={p.strategy}
              fill={p.isAcquisition ? "#0f766e" : "#b45309"}
              fillOpacity={0.75}
            />
          ))}
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  );
}
