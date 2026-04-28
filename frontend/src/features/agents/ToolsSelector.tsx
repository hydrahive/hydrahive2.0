import { Check } from "lucide-react"
import type { ToolMeta } from "./types"

interface Props {
  available: ToolMeta[]
  selected: string[]
  onChange: (next: string[]) => void
}

export function ToolsSelector({ available, selected, onChange }: Props) {
  const set = new Set(selected)

  function toggle(name: string) {
    const next = new Set(set)
    if (next.has(name)) next.delete(name)
    else next.add(name)
    onChange(Array.from(next))
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
      {available.map((t) => {
        const checked = set.has(t.name)
        return (
          <button
            key={t.name}
            type="button"
            onClick={() => toggle(t.name)}
            className={`flex items-start gap-2 px-3 py-2 rounded-lg border text-left transition-all ${
              checked
                ? "border-violet-500/40 bg-violet-500/[8%]"
                : "border-white/[6%] bg-white/[2%] hover:bg-white/[4%]"
            }`}
          >
            <div
              className={`mt-0.5 w-4 h-4 rounded flex items-center justify-center flex-shrink-0 transition-all ${
                checked
                  ? "bg-gradient-to-br from-indigo-600 to-violet-600 shadow shadow-violet-900/20"
                  : "border border-zinc-600"
              }`}
            >
              {checked && <Check size={11} className="text-white" />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-mono text-zinc-200">{t.name}</p>
              <p className="text-[10.5px] text-zinc-500 mt-0.5 leading-snug line-clamp-2">{t.description}</p>
            </div>
          </button>
        )
      })}
    </div>
  )
}
