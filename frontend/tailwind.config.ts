import type { Config } from "tailwindcss";

/**
 * Palette note: the greens are a deliberate agricultural identity, not a
 * generic SaaS blue. Contrast ratios for text colours against their
 * backgrounds are kept at or above WCAG AA — farmers use these screens
 * outdoors in bright sunlight, where low-contrast grey-on-white disappears.
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        soil: {
          50: "#faf7f2",
          100: "#f0e9dd",
          700: "#6b5335",
          900: "#3d2f1f",
        },
        leaf: {
          50: "#f0f9f1",
          100: "#dcf2df",
          200: "#bbe5c2",
          300: "#8dd199",
          400: "#57b569",
          500: "#349748",
          600: "#247937",
          700: "#1e602e",
          800: "#1b4c28",
          900: "#173f23",
        },
        harvest: {
          50: "#fef8ec",
          100: "#fbecc8",
          400: "#f0b429",
          500: "#de911d",
          700: "#a55d07",
        },
      },
      fontFamily: {
        // Noto Sans covers Devanagari, so Marathi and Hindi render with the
        // same family as English instead of falling back to a mismatched font.
        sans: ["var(--font-noto)", "system-ui", "sans-serif"],
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.35s ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;
