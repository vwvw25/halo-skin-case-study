import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1f2328",
        muted: "#8b949e",
        line: "#e6e8eb",
        accent: "#0f766e",
        "accent-soft": "#5eead4",
        warn: "#b45309",
        bad: "#b42318",
        surface: "#ffffff",
        canvas: "#f6f8fa",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
