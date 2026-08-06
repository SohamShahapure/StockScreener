import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#0E1420",
          surface: "#161D2B",
          raised: "#1D2635",
          border: "#2A3345",
        },
        brass: {
          DEFAULT: "#C9A227",
          bright: "#E0BB3E",
          dim: "#8A7420",
        },
        gain: "#2DBE7E",
        loss: "#E5484D",
        ink2: "#E8EAED",
        muted: "#8A93A6",
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
        body: ["var(--font-body)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      borderRadius: {
        xl: "14px",
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.03) inset, 0 8px 24px -8px rgba(0,0,0,0.5)",
      },
    },
  },
  plugins: [],
};

export default config;
