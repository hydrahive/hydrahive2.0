/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Redesign „freundlich/dunkel-neon": die Box-/App-Töne zentral umbiegen.
        // 276 bestehende bg-zinc-900/950-Boxen werden so an EINER Stelle wärmer +
        // angehoben — ohne 37 Komponenten anzufassen. Übrige zinc-Töne (Text) bleiben.
        zinc: {
          900: "#1c2334", // Box-/Panel-Fläche (vorher #18181b) — angehoben, wärmer
          950: "#0f1320", // App-/Tiefen-Dunkel (vorher #09090b)
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // Helligkeitsstufen — Werte stehen NUR in index.css (--hh-s-*), hier nur Verweise.
        s: {
          "grund": "rgb(var(--hh-s-grund) / <alpha-value>)",
          "tief": "rgb(var(--hh-s-tief) / <alpha-value>)",
          "box": "rgb(var(--hh-s-box) / <alpha-value>)",
          "kopf": "rgb(var(--hh-s-kopf) / <alpha-value>)",
          "innen": "rgb(var(--hh-s-innen) / <alpha-value>)",
          "hebung": "rgb(var(--hh-s-hebung) / <alpha-value>)",
          "rand": "rgb(var(--hh-s-rand) / <alpha-value>)",
          "rand-hover": "rgb(var(--hh-s-rand-hover) / <alpha-value>)",
        },
      },
      // UI-Standard Regel 1 (docs/specs/ui-standard.md): zinc-500 nur als TEXTfarbe anheben.
      // #71717a hatte auf dem Panel #1c2334 nur 3,24:1 (AA verlangt 4,5:1); #94949e: 5,22:1.
      // Flächen/Ränder (bg-/border-/ring-zinc-500) bleiben bewusst #71717a.
      textColor: ({ theme }) => ({
        zinc: { ...theme("colors.zinc"), 500: "#94949e" },
      }),
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
}
