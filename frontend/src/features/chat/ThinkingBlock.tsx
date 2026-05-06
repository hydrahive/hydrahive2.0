import { useState } from "react"
import { Brain, ChevronDown, ChevronRight } from "lucide-react"

interface Props {
  text: string
}

export function ThinkingBlock({ text }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left text-xs text-indigo-300/70 hover:text-indigo-200 transition-colors"
      >
        <Brain size={11} className="flex-shrink-0" />
        <span className="flex-1 font-medium">Reasoning</span>
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
      </button>
      {open && (
        <div className="px-3 pb-3 text-xs text-indigo-200/60 font-mono whitespace-pre-wrap leading-relaxed border-t border-indigo-500/15 pt-2">
          {text}
        </div>
      )}
    </div>
  )
}
