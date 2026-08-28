import type { Config } from "tailwindcss";

/**
 * Palette: a restrained government/enterprise identity.
 * `ink` carries the institutional weight (deep navy), `accent` is used sparingly for
 * emphasis so the interface reads as official rather than decorative.
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
        ink: {
          50: "#f3f6fb",
          100: "#e5ecf6",
          200: "#c6d7ec",
          300: "#95b5db",
          400: "#5d8dc6",
          500: "#3a6cae",
          600: "#2a5390",
          700: "#234375",
          800: "#213a62",
          900: "#0f2a4d",
          950: "#0a1c33",
        },
        accent: {
          50: "#fff8ed",
          100: "#ffefd4",
          200: "#ffdba8",
          300: "#ffc071",
          400: "#ff9c38",
          500: "#fd7d12",
          600: "#ee6108",
          700: "#c54809",
          800: "#9c3910",
          900: "#7e3110",
        },
        surface: {
          DEFAULT: "#ffffff",
          muted: "#f7f9fc",
          sunken: "#eef2f8",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15,42,77,0.04), 0 8px 24px -12px rgba(15,42,77,0.18)",
        lift: "0 2px 6px rgba(15,42,77,0.06), 0 20px 40px -20px rgba(15,42,77,0.28)",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.35s cubic-bezier(0.16,1,0.3,1) both",
        shimmer: "shimmer 1.6s infinite",
      },
    },
  },
  plugins: [],
};

export default config;
