import { Wrench } from "lucide-react"
import type { McpTool } from "./types"

export function McpToolList({ tools }: { tools: McpTool[] }) {
  if (tools.length === 0) {
    return <p className="text-xs text-zinc-600">Noch keine Tools — Server connecten zum Laden.</p>
  }
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
      {tools.map((t) => (
        <div key={t.name} className="px-3 py-2 rounded-lg border border-white/[6%] bg-white/[2%]">
          <div className="flex items-center gap-2">
            <Wrench size={11} className="text-violet-400 flex-shrink-0" />
            <p className="text-xs font-mono text-zinc-200 truncate">{t.name}</p>
          </div>
          <p className="text-[10.5px] text-zinc-500 mt-1 leading-snug line-clamp-2">{t.description}</p>
        </div>
      ))}
    </div>
  )
}
