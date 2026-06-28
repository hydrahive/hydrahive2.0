import { useEffect, useState } from "react"
import { Crown, User, Wrench } from "lucide-react"
import { agentsApi } from "@/features/agents/api"
import type { Agent } from "@/features/agents/types"

interface Props {
  activeItem: string | null
  onSelect: (id: string) => void
}

const TYPE_ICON = { master: Crown, project: User, specialist: Wrench }
const TYPE_PILL: Record<string, string> = {
  master: "bg-amber-500/[8%] border-amber-500/25 text-amber-300",
  project: "bg-violet-500/[8%] border-violet-500/25 text-violet-300",
  specialist: "bg-sky-500/[8%] border-sky-500/25 text-sky-300",
}
const TYPE_AVATAR: Record<string, string> = {
  master: "/illustrations/agent-master.png",
  project: "/illustrations/agent-project.png",
  specialist: "/illustrations/agent-specialist.png",
}
// Sortier-Reihenfolge nach Typ: Master → Projekt-Agent → Spezialist, dann Name.
const TYPE_ORDER: Record<string, number> = { master: 0, project: 1, specialist: 2 }

/**
 * Submenü der Agenten-Gruppe: die echte Agentenliste mit Farbmarkierungen
 * (Master/Projekt/Spezialist), Avataren und off-Status — sortiert nach Typ und
 * Name. Kein Button davor (Tills Vorgabe), Auswahl steuert den Mittelbereich.
 */
export function AgentSubMenu({ activeItem, onSelect }: Props) {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    agentsApi.list()
      .then((list) => {
        const sorted = [...list].sort((a, b) => {
          const o = (TYPE_ORDER[a.type] ?? 9) - (TYPE_ORDER[b.type] ?? 9)
          return o !== 0 ? o : a.name.localeCompare(b.name)
        })
        setAgents(sorted)
      })
      .catch(() => setAgents([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-white/8 px-4 py-3">
        <h2 className="text-sm font-semibold text-zinc-200">Agenten</h2>
      </div>
      <div className="flex-1 space-y-1 overflow-y-auto p-2">
        {loading ? (
          <div className="h-20 animate-pulse rounded-lg bg-zinc-900/50" />
        ) : agents.length === 0 ? (
          <p className="px-3 py-6 text-center text-xs text-zinc-600">Keine Agenten.</p>
        ) : (
          agents.map((a) => {
            const Icon = TYPE_ICON[a.type] ?? Wrench
            const active = a.id === activeItem
            const dim = a.status !== "active"
            return (
              <div
                key={a.id}
                onClick={() => onSelect(a.id)}
                className={`group flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 transition-all ${
                  active
                    ? "bg-gradient-to-r from-indigo-600/20 to-violet-600/10 border-l-2 border-violet-500"
                    : "border-l-2 border-transparent hover:bg-white/[3%]"
                } ${dim ? "opacity-50" : ""}`}
              >
                <img
                  src={TYPE_AVATAR[a.type] ?? TYPE_AVATAR.specialist}
                  alt=""
                  className="h-8 w-8 shrink-0 object-contain drop-shadow-[0_0_5px_rgba(34,211,238,0.45)]"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className={`flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[9px] shrink-0 ${TYPE_PILL[a.type] ?? TYPE_PILL.specialist}`}>
                      <Icon size={8} />
                    </span>
                    <p className={`truncate text-sm ${active ? "text-white" : "text-zinc-300"}`}>{a.name}</p>
                  </div>
                  <p className="mt-0.5 truncate font-mono text-[10px] text-zinc-600">{a.llm_model}</p>
                </div>
                {dim && (
                  <span className="shrink-0 rounded-full border border-zinc-500/20 bg-zinc-500/[8%] px-1.5 py-0.5 text-[10px] text-zinc-500">off</span>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
