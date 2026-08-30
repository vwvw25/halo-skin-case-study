/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // fully static: one page, one JSON import, no server runtime
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
