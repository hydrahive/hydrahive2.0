// Theme-Registry — mitgelieferte Themes. Ein Theme wählt ein Layout-Gerüst und
// kann CSS-Variablen (--hh-*) überschreiben. Später kommen hier user-gebaute
// Themes (Paket-Loader, Etappe 2) additiv dazu.
import type { LayoutComponent } from "@/shared/layouts/types"
import { TopnavLayout } from "@/shared/layouts/TopnavLayout"
import { SidebarLayout } from "@/shared/layouts/SidebarLayout"

export interface ThemeMeta {
  id: string
  name: string
  description: string
  /** Layout-Gerüst dieses Themes. */
  layout: LayoutComponent
  /** Optionale CSS-Variablen-Overrides (--hh-*). */
  variables?: Record<string, string>
}

export const THEMES: ThemeMeta[] = [
  {
    id: "standard",
    name: "Standard",
    description: "Das Original — Menü oben, Waben-Glow, runde Panels.",
    layout: TopnavLayout,
  },
  {
    id: "sidebar",
    name: "Sidebar (Test)",
    description: "Menü links in einer Seitenleiste, Inhalt rechts. Testdesign.",
    layout: SidebarLayout,
  },
]

const STORAGE_KEY = "hh-active-theme"
export const DEFAULT_THEME_ID = "standard"

export function getStoredThemeId(): string {
  const v = typeof localStorage !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null
  if (v && THEMES.some((t) => t.id === v)) return v
  return DEFAULT_THEME_ID
}

export function storeThemeId(id: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, id)
  } catch {
    /* ignore */
  }
}

export function getTheme(id: string): ThemeMeta {
  return THEMES.find((t) => t.id === id) ?? THEMES[0]
}
