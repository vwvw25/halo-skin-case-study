// Copy the canonical dashboard payload into the app so it builds standalone (and on Vercel,
// where the build root is dashboard/). Run automatically before dev and build.
import { copyFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const source = resolve(here, "../../data/dashboard.json");
const dest = resolve(here, "../data/dashboard.json");

if (existsSync(source)) {
  copyFileSync(source, dest);
  console.log(`synced ${source} -> ${dest}`);
} else if (existsSync(dest)) {
  console.log(`source ${source} not found; using committed ${dest}`);
} else {
  console.error(`no dashboard data at ${source} or ${dest} — run \`uv run halo-report monthly\` first`);
  process.exit(1);
}
