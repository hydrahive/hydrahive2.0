export type ThemeId = "violet" | "cool" | "warm" | "forest" | "mono"

export interface ThemeMeta {
  id: ThemeId
  name: string
  description: string
  /** Preview-Gradient für Theme-Picker. Hex-Farben für CSS background. */
  preview: { from: string; to: string }
}

export const THEMES: ThemeMeta[] = [
  { id: "violet", name: "Violet (Standard)", description: "Indigo + Violet — die Original-HydraHive-Farbe.",
    preview: { from: "#4f46e5", to: "#7c3aed" } },
  { id: "cool",   name: "Cool",   description: "Sky + Cyan — kühl und technisch.",
    preview: { from: "#0284c7", to: "#0891b2" } },
  { id: "warm",   name: "Warm",   description: "Orange + Amber — energisch und kontrastreich.",
    preview: { from: "#ea580c", to: "#d97706" } },
  { id: "forest", name: "Forest", description: "Emerald + Teal — beruhigend, gut bei langem Arbeiten.",
    preview: { from: "#059669", to: "#0d9488" } },
  { id: "mono",   name: "Mono",   description: "Zinc-Grautöne — minimal, ohne Akzentfarbe.",
    preview: { from: "#3f3f46", to: "#52525b" } },
]

const STORAGE_KEY = "hh-theme"

export function getStoredTheme(): ThemeId {
  const v = (typeof localStorage !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null) as ThemeId | null
  if (v && THEMES.some((t) => t.id === v)) return v
  return "violet"
}

export function applyTheme(id: ThemeId): void {
  if (typeof document === "undefined") return
  if (id === "violet") {
    document.documentElement.removeAttribute("data-theme")
  } else {
    document.documentElement.setAttribute("data-theme", id)
  }
  try { localStorage.setItem(STORAGE_KEY, id) } catch { /* ignore */ }
}
