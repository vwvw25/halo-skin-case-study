import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Halo Skin — Acquisition Dashboard",
  description: "LTV:CAC and target-cohort capture across Meta acquisition, from mock data.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
