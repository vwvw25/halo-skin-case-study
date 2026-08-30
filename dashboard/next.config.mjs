/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // fully static: one page, one JSON import, no server runtime
  output: "export",
  images: { unoptimized: true },
  // CI's `dashboard` job runs `npm run lint` as its own gate; skip the redundant
  // (and, with flat config, warning-noisy) lint pass inside `next build`.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
