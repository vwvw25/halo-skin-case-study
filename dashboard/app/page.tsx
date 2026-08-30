import { DashboardBody } from "@/components/DashboardBody";
import { dashboard } from "@/lib/data";

export default function Page() {
  return (
    <main className="mx-auto max-w-6xl px-5 py-8">
      <header className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <div className="text-lg font-bold uppercase tracking-[0.14em]">
            Halo<span className="text-accent">.</span>Skin
          </div>
          <h1 className="mt-0.5 text-sm font-medium text-muted">
            Acquisition dashboard — LTV:CAC &amp; target-cohort capture
          </h1>
        </div>
        <div className="text-right text-xs text-muted">Meta Marketing API × Shopify · mock data</div>
      </header>

      <DashboardBody />

      <footer className="mt-8 border-t border-line pt-3 text-xs text-muted">
        Portfolio case study · fictional brand · numbers generated from a seeded model. Snapshot:{" "}
        {dashboard.as_of}.
      </footer>
    </main>
  );
}
