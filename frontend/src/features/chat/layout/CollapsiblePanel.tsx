import { ChevronLeft, ChevronRight } from "lucide-react"

interface Props {
  side: "left" | "right"
  open: boolean
  onToggle: () => void
  width: number
  children: React.ReactNode
}

export function CollapsiblePanel({ side, open, onToggle, width, children }: Props) {
  const ChevOpen = side === "left" ? ChevronLeft : ChevronRight
  const ChevClosed = side === "left" ? ChevronRight : ChevronLeft
  const borderSide = side === "left" ? "border-r" : "border-l"

  if (!open) {
    return (
      <div className={`w-8 flex-shrink-0 ${borderSide} border-white/[8%] bg-white/[1%] flex items-start justify-center pt-3`}>
        <button onClick={onToggle} className="p-1 rounded text-zinc-500 hover:text-violet-300 hover:bg-white/5 transition-colors">
          <ChevClosed size={14} />
        </button>
      </div>
    )
  }

  return (
    <aside className={`flex-shrink-0 ${borderSide} border-white/[8%] bg-white/[1%] flex flex-col`} style={{ width }}>
      <div className="flex-1 min-h-0 flex flex-col">{children}</div>
      <button onClick={onToggle} className="flex items-center justify-center py-1.5 border-t border-white/[6%] text-zinc-600 hover:text-violet-300 hover:bg-white/5 transition-colors">
        <ChevOpen size={13} />
      </button>
    </aside>
  )
}
