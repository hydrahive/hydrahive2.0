import type { ReactNode } from "react"
import { ChevronDown, ChevronUp, Eye, EyeOff } from "lucide-react"

interface Props {
  label: string
  hidden: boolean
  isFirst: boolean
  isLast: boolean
  onUp: () => void
  onDown: () => void
  onToggle: () => void
  children: ReactNode
}

/** Rahmen um ein Widget im Anpassen-Modus: Titel + Hoch/Runter/Sichtbarkeit.
 *  Bewusst Buttons statt Drag&Drop — eindeutig bedienbar, kein Rätselraten. */
export function WidgetFrame({
  label, hidden, isFirst, isLast, onUp, onDown, onToggle, children,
}: Props) {
  return (
    <div className={`rounded-xl border border-dashed border-white/15 p-2 transition-opacity ${hidden ? "opacity-45" : ""}`}>
      <div className="flex items-center gap-1.5 mb-2 px-1">
        <span className="text-xs font-medium text-zinc-300 flex-1 truncate">{label}</span>

        <button
          onClick={onUp}
          disabled={isFirst}
          title="Nach oben"
          className="p-1 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-white/[7%] disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
        >
          <ChevronUp size={15} />
        </button>
        <button
          onClick={onDown}
          disabled={isLast}
          title="Nach unten"
          className="p-1 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-white/[7%] disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
        >
          <ChevronDown size={15} />
        </button>
        <button
          onClick={onToggle}
          title={hidden ? "Einblenden" : "Ausblenden"}
          className="p-1 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-white/[7%] transition-colors"
        >
          {hidden ? <EyeOff size={15} /> : <Eye size={15} />}
        </button>
      </div>

      {!hidden && <div>{children}</div>}
    </div>
  )
}
