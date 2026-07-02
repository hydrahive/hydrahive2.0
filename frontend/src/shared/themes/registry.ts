// Theme-Registry — führt eingebaute Themes und user-gebaute Theme-Pakete
// zusammen. User-Themes kommen aus themes/<id>/theme.json (Dropin-Ordner),
// eingelesen vom Generator scripts/gen-themes.mjs → index.generated.ts.
import { TopnavLayout } from "@/shared/layouts/TopnavLayout"
import { SidebarLayout } from "@/shared/layouts/SidebarLayout"
import { getBuiltinLayout } from "@/shared/layouts/builtins"
import type { ThemeMeta, GeneratedThemeEntry } from "./types"
import { userThemes } from "@/themes/index.generated"

export type { ThemeMeta } from "./types"

const BUILTIN_THEMES: ThemeMeta[] = [
  {
    id: "standard",
    name: "Standard",
    description: "Das Original — Menü oben, Waben-Glow, runde Panels.",
    layout: TopnavLayout,
    source: "builtin",
  },
  {
    id: "sidebar",
    name: "Sidebar (Test)",
    description: "Menü links in einer Seitenleiste, Inhalt rechts. Testdesign.",
    layout: SidebarLayout,
    source: "builtin",
  },
]

/** Wandelt ein generiertes Paket-Manifest in ein konsumierbares Theme.
 *  Eigenes layout.tsx hat Vorrang, sonst ein eingebautes Gerüst per Name. */
function resolveUserTheme(e: GeneratedThemeEntry): ThemeMeta {
  return {
    id: e.id,
    name: e.name,
    description: e.description,
    author: e.author || undefined,
    version: e.version || undefined,
    layout: e.customLayout ?? getBuiltinLayout(e.layoutName),
    variables: e.variables,
    css: e.css,
    preview: e.preview,
    source: "user",
  }
}

// User-Themes gewinnen bei ID-Kollision (überschreiben ein gleichnamiges Built-in).
const _userThemes = userThemes.map(resolveUserTheme)
const _userIds = new Set(_userThemes.map((t) => t.id))
export const THEMES: ThemeMeta[] = [
  ..._userThemes,
  ...BUILTIN_THEMES.filter((t) => !_userIds.has(t.id)),
].sort((a, b) => (a.source === b.source ? 0 : a.source === "builtin" ? -1 : 1))

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
  return THEMES.find((t) => t.id === id) ?? THEMES.find((t) => t.id === DEFAULT_THEME_ID) ?? THEMES[0]
}
