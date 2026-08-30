export const usd = (v: number | null | undefined, digits = 0): string =>
  v == null || Number.isNaN(v)
    ? "—"
    : v.toLocaleString("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: digits,
      });

export const pct = (v: number | null | undefined, digits = 0): string =>
  v == null || Number.isNaN(v) ? "—" : `${(v * 100).toFixed(digits)}%`;

export const ratio = (v: number | null | undefined): string =>
  v == null || Number.isNaN(v) ? "—" : `${v.toFixed(1)}×`;

export const count = (v: number | null | undefined): string =>
  v == null || Number.isNaN(v) ? "—" : Math.round(v).toLocaleString("en-US");

export const payback = (v: number | null | undefined): string =>
  v == null || Number.isNaN(v) ? "—" : v < 1 ? "<1 mo" : `${Math.round(v)} mo`;

export const monthLabel = (iso: string): string =>
  new Date(iso + "T00:00:00").toLocaleDateString("en-US", {
    month: "short",
    year: "2-digit",
  });

export const weekLabel = (iso: string): string =>
  new Date(iso + "T00:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
