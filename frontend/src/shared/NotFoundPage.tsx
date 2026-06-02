import { Link } from "react-router-dom"
import { EmptyState } from "./EmptyState"

export function NotFoundPage() {
  return (
    <div className="flex items-center justify-center min-h-[70vh]">
      <EmptyState
        src="/illustrations/404-confused.png"
        size={180}
        title="Seite nicht gefunden"
        hint="Diese Adresse führt ins Leere — die Hydra ist genauso ratlos wie du."
      >
        <Link
          to="/"
          className="mt-3 inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm text-zinc-200 bg-white/[5%] border border-white/[10%] hover:bg-white/[8%] hover:border-white/20 transition-all"
        >
          ← Zurück zum Start
        </Link>
      </EmptyState>
    </div>
  )
}
