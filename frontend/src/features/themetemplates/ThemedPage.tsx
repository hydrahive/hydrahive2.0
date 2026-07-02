import { Component, type ReactNode } from "react"
import { getStoredThemeId, getTheme } from "@/shared/themes/registry"
import { renderTemplate } from "./TemplateRenderer"

/** Fehlergrenze: bricht das Template-Rendering (z.B. defekter Baustein), fällt
 *  die Seite auf die eingebaute React-Version zurück — Sicherheitsregel 1:
 *  das aktuelle Design geht nie verloren. */
class TemplateBoundary extends Component<
  { fallback: ReactNode; children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}

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
