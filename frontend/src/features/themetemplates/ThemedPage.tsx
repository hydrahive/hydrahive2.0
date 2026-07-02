import type { ReactNode } from "react"
import { getStoredThemeId, getTheme } from "@/shared/themes/registry"
import { renderTemplate } from "./TemplateRenderer"
import { TemplateBoundary } from "./TemplateBoundary"

/** Rendert für eine Route entweder das Theme-Template (falls das aktive Theme
 *  eines mitbringt) oder die eingebaute React-Seite (Fallback).
 *
 *  <ThemedPage route="buddy" fallback={<BuddyPage/>} />
 *
 *  Kein/kaputtes Template → immer die echte Seite. Rein additiv. */
export function ThemedPage({ route, fallback }: { route: string; fallback: ReactNode }) {
  const theme = getTheme(getStoredThemeId())
  const html = theme.templates?.[route]

  if (!html || !html.trim()) return <>{fallback}</>

  return (
    <TemplateBoundary fallback={fallback}>
      {renderTemplate(html)}
    </TemplateBoundary>
  )
}
