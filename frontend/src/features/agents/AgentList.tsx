import { Crown, Plus, User, Wrench } from "lucide-react"
import type { Agent } from "./types"

interface Props {
  agents: Agent[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
}

const TYPE_ICON = {
  master: Crown,
  project: User,
  specialist: Wrench,
}

export function AgentList({ agents, activeId, onSelect, onNew }: Props) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-3 border-b border-white/[6%]">
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">Agents</p>
        <button
          onClick={onNew}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs text-zinc-300 hover:text-zinc-100 hover:bg-white/5 transition-colors"
        >
          <Plus size={13} /> Neu
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {agents.length === 0 && (
          <p className="text-xs text-zinc-600 text-center py-6">Noch kein Agent</p>
        )}
        {agents.map((a) => {
          const Icon = TYPE_ICON[a.type] ?? Wrench
          const active = a.id === activeId
          const dim = a.status !== "active"
          return (
            <div
              key={a.id}
              className={`group flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all ${
                active
                  ? "bg-gradient-to-r from-indigo-600/20 to-violet-600/10 border-l-2 border-violet-500"
                  : "hover:bg-white/[3%] border-l-2 border-transparent"
              } ${dim ? "opacity-50" : ""}`}
              onClick={() => onSelect(a.id)}
            >
              <Icon
                size={14}
                className={active ? "text-violet-300" : "text-zinc-500"}
              />
              <div className="flex-1 min-w-0">
                <p className={`text-sm truncate ${active ? "text-white" : "text-zinc-300"}`}>{a.name}</p>
                <p className="text-xs text-zinc-600 mt-0.5 truncate">
                  {a.type} · {a.llm_model}
                </p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
