import type { LayoutComponent } from "./types"
import { TopnavLayout } from "./TopnavLayout"
import { SidebarLayout } from "./SidebarLayout"

/** Eingebaute Layout-Gerüste, die ein Theme-Paket per Name wählen kann
 *  (theme.json → "layout": "topnav"). So muss ein einfaches User-Theme kein
 *  eigenes layout.tsx mitbringen, nur Farben/Variablen ändern. */
export const BUILTIN_LAYOUTS: Record<string, LayoutComponent> = {
  topnav: TopnavLayout,
  sidebar: SidebarLayout,
}

export const DEFAULT_LAYOUT_NAME = "topnav"

export function getBuiltinLayout(name: string | null | undefined): LayoutComponent {
  if (name && name in BUILTIN_LAYOUTS) return BUILTIN_LAYOUTS[name]
  return BUILTIN_LAYOUTS[DEFAULT_LAYOUT_NAME]
}
