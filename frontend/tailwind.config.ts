import type { Config } from "tailwindcss";
import plugin from "tailwindcss/plugin";

/**
 * IMCS palette, mirroring docs/color-palette.md. This is the only frontend
 * file that contains hex values; everything else uses the tokens below.
 */
const palette = {
  light: { primary: "#16324F", surface: "#F5F5F5", card: "#FFFFFF", content: "#1A1A1A" },
  dark: { primary: "#3D6E9E", surface: "#0A0A0A", card: "#171717", content: "#F5F5F5" },
  status: { available: "#22C55E", busy: "#F59E0B", conflict: "#EF4444" },
};

type ThemedToken = keyof typeof palette.light;

// "#16324F" -> "22 50 79", so opacity modifiers like `bg-primary/20` still work.
const toRgbChannels = (hex: string) =>
  [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)).join(" ");

const themeVariables = (theme: Record<ThemedToken, string>) =>
  Object.fromEntries(
    Object.entries(theme).map(([token, hex]) => [`--color-${token}`, toRgbChannels(hex)]),
  );

const themedColor = (token: ThemedToken) => `rgb(var(--color-${token}) / <alpha-value>)`;

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        primary: themedColor("primary"),
        surface: themedColor("surface"),
        card: themedColor("card"),
        content: themedColor("content"),
        status: palette.status,
      },
    },
  },
  plugins: [
    // Themed tokens resolve through CSS variables that swap with the OS color
    // scheme, so components never need `dark:` variants for palette colors.
    plugin(({ addBase }) => {
      addBase({
        ":root": { ...themeVariables(palette.light), colorScheme: "light" },
        "@media (prefers-color-scheme: dark)": {
          ":root": { ...themeVariables(palette.dark), colorScheme: "dark" },
        },
      });
    }),
  ],
};

export default config;
