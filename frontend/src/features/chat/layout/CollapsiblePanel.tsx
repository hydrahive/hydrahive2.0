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
  // Handle mittig auf der inneren Trennlinie — kollidiert nie mit Panel-Inhalt
  const handlePos = side === "left" ? "right-0 translate-x-1/2" : "left-0 -translate-x-1/2"

  if (!open) {
    return (
      <div className={`w-8 flex-shrink-0 ${borderSide} border-white/[8%] bg-white/[1%] flex items-start justify-center pt-3`}>
        <button onClick={onToggle} title="Aufklappen"
          className="p-1 rounded text-zinc-500 hover:text-violet-300 hover:bg-white/5 transition-colors">
          <ChevClosed size={14} />
        </button>
      </div>
    )
  }

  return (
    <aside className={`relative flex-shrink-0 ${borderSide} border-white/[8%] bg-white/[1%] flex flex-col min-w-0`} style={{ width }}>
      <button onClick={onToggle} title="Einklappen"
        className={`absolute top-1/2 -translate-y-1/2 ${handlePos} z-20 w-5 h-10 rounded-md flex items-center justify-center
          text-zinc-500 hover:text-violet-300 bg-zinc-800/90 border border-white/10 shadow-md transition-colors`}>
        <ChevOpen size={13} />
      </button>
      <div className="flex-1 min-h-0 min-w-0 flex flex-col overflow-hidden">{children}</div>
    </aside>
  )
}
