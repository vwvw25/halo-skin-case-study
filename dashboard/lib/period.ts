import { dashboard } from "@/lib/data";
import { monthLabel } from "@/lib/format";

/** Acquisition months present in the snapshot, ascending ISO (yyyy-mm-01). */
export const MONTHS: string[] = dashboard.cohort_triangle.rows.map(
  (r) => r.acquired,
);

export const MONTH_OPTIONS = MONTHS.map((iso, index) => ({
  index,
  iso,
  label: monthLabel(iso),
}));

export interface Period {
  fromIndex: number;
  toIndex: number;
}

export const FULL_PERIOD: Period = { fromIndex: 0, toIndex: MONTHS.length - 1 };

export function periodBounds(period: Period): {
  start: Date;
  end: Date;
  months: string[];
} {
  const lo = Math.min(period.fromIndex, period.toIndex);
  const hi = Math.max(period.fromIndex, period.toIndex);
  const start = new Date(MONTHS[lo] + "T00:00:00");
  const endMonth = new Date(MONTHS[hi] + "T00:00:00");
  const end = new Date(endMonth.getFullYear(), endMonth.getMonth() + 1, 0); // last day of that month
  return { start, end, months: MONTHS.slice(lo, hi + 1) };
}

export function periodLabel(period: Period): string {
  const lo = Math.min(period.fromIndex, period.toIndex);
  const hi = Math.max(period.fromIndex, period.toIndex);
  return `${monthLabel(MONTHS[lo])} – ${monthLabel(MONTHS[hi])}`;
}
