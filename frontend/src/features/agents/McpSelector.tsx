import { Server } from "lucide-react"
import type { McpServerBrief } from "./api"

interface Props {
  available: McpServerBrief[]
  selected: string[]
  onChange: (next: string[]) => void
}

export function McpSelector({ available, selected, onChange }: Props) {
  if (available.length === 0) {
    return <p className="text-xs text-zinc-600">Noch keine MCP-Server angelegt — siehe MCP-Tab.</p>
  }
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
      {available.map((s) => {
        const checked = selected.includes(s.id)
        return (
          <button
            key={s.id}
            type="button"
            onClick={() => {
              const next = checked ? selected.filter((id) => id !== s.id) : [...selected, s.id]
              onChange(next)
            }}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-left transition-all ${
              checked
                ? "border-violet-500/40 bg-violet-500/[8%]"
                : "border-white/[6%] bg-white/[2%] hover:bg-white/[4%]"
            }`}
          >
            <Server size={12} className={checked ? "text-violet-300" : "text-zinc-500"} />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-zinc-200 truncate">{s.name}</p>
              <p className="text-[10.5px] text-zinc-500 mt-0.5">
                {s.id} · {s.connected ? "verbunden" : "nicht verbunden"}
              </p>
            </div>
          </button>
        )
      })}
    </div>
  )
}
