import { Component, type ErrorInfo, type ReactNode } from "react"

interface Props {
  children: ReactNode
  /** ändert sich der Key (z.B. Routen-Pfad), wird der Fehler zurückgesetzt */
  resetKey?: string
}

interface State {
  error: Error | null
}

/**
 * Fängt Render-Fehler einer Akte-View ab, damit ein einzelner Komponenten-
 * Fehler nicht die ganze Seite schwärzt. Zeigt die Fehlermeldung lesbar an.
 */
export class AkteErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Akte-View Fehler:", error, info.componentStack)
  }

  componentDidUpdate(prev: Props) {
    if (prev.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null })
    }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-6 space-y-2">
          <h2 className="text-sm font-semibold text-red-300">
            Dieser Bereich konnte nicht geladen werden
          </h2>
          <p className="text-xs text-zinc-400">
            Ein Fehler in der Anzeige wurde abgefangen — der Rest der Akte bleibt nutzbar.
          </p>
          <pre className="text-[11px] text-zinc-500 whitespace-pre-wrap break-words mt-2">
            {this.state.error.message}
          </pre>
          <button
            onClick={() => this.setState({ error: null })}
            className="mt-2 text-xs text-zinc-400 hover:text-zinc-200 px-3 py-1.5 rounded-lg border border-white/[6%] hover:bg-white/[4%] transition-colors"
          >
            Erneut versuchen
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
