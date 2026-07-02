import { Component, type ReactNode } from "react"

/** Fehlergrenze fürs Template-Rendering. Bricht ein Baustein oder das Markup,
 *  wird `fallback` gezeigt statt einer weißen/schwarzen Seite. */
export class TemplateBoundary extends Component<
  { fallback: ReactNode; children: ReactNode },
  { failed: boolean; message: string }
> {
  state = { failed: false, message: "" }

  static getDerivedStateFromError(err: unknown) {
    return { failed: true, message: err instanceof Error ? err.message : String(err) }
  }

  render() {
    if (this.state.failed) return this.props.fallback
    return this.props.children
  }
}
