import type { LayoutComponent } from "@/shared/layouts/types"

/** Aufgelöstes Theme, wie es der Picker und der LayoutHost konsumieren. */
export interface ThemeMeta {
  id: string
  name: string
  description: string
  /** Layout-Gerüst dieses Themes (built-in oder mitgeliefert). */
  layout: LayoutComponent
  /** CSS-Variablen-Overrides (--hh-*). */
  variables?: Record<string, string>
  /** Optionales rohes CSS (aus theme.css), scoped injiziert wenn aktiv. */
  css?: string
  /** Optionales Vorschaubild (aufgelöste URL). */
  preview?: string
  author?: string
  version?: string
  /** Herkunft — eingebaut oder aus einem Theme-Paket. */
  source: "builtin" | "user"
}

/** Rohform eines User-Theme-Pakets, wie sie der Generator (gen-themes.mjs)
 *  aus themes/<id>/theme.json erzeugt. Wird von resolveUserTheme() zu ThemeMeta. */
export interface GeneratedThemeEntry {
  id: string
  name: string
  description: string
  author?: string
  version?: string
  /** Name eines eingebauten Layout-Gerüsts (topnav/sidebar/…) oder null,
   *  wenn das Paket ein eigenes layout.tsx mitbringt. */
  layoutName: string | null
  /** Eigenes Layout-Gerüst aus dem Paket (layout.tsx default export). */
  customLayout?: LayoutComponent
  variables?: Record<string, string>
  css?: string
  preview?: string
}
