import { useState, type CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { Bot, Plus, X } from "lucide-react"
import type { Agent } from "@/features/agents/types"
import type { RoomAgent } from "./types"

interface AgentPanelProps {
  accent: string
  roomAgents: RoomAgent[]
  ownAgents: Agent[]
  onAttach: (agentId: string) => Promise<void>
  onDetach: (agentId: string) => Promise<void>
}

export function AgentPanel({ accent, roomAgents, ownAgents, onAttach, onDetach }: AgentPanelProps) {
  const { t } = useTranslation("teamchat")
  const [picking, setPicking] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)

  const attachedIds = new Set(roomAgents.map((a) => a.agent_id))
  const available = ownAgents.filter((a) => a.status === "active" && !attachedIds.has(a.id))

  async function withBusy(id: string, fn: () => Promise<void>) {
    setBusyId(id)
    try { await fn() } finally { setBusyId(null) }
  }

  return (
    <div className="box box-static overflow-hidden" style={{ "--c": accent } as CSSProperties}>
      <div className="box-h">
        <span className="ic"><Bot size={14} /></span>
        <span className="t">{t("agents")}</span>
        <button
          onClick={() => setPicking((v) => !v)}
          title={t("attach_agent")}
          className="r p-1 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/[6%] transition-all"
        >
          <Plus size={14} />
        </button>
      </div>
      <div className="box-b !p-1.5">
        {roomAgents.length === 0 && !picking && (
          <p className="text-xs text-zinc-500 italic px-2 py-3 text-center">{t("no_agents")}</p>
        )}

        {roomAgents.map((a) => (
          <div key={a.agent_id} className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-sm text-zinc-200 group">
            <span className="text-[11px]">🐙</span>
            <span className="truncate flex-1">{a.name ?? a.agent_id}</span>
            <button
              onClick={() => withBusy(a.agent_id, () => onDetach(a.agent_id))}
              disabled={busyId === a.agent_id}
              title={t("detach_agent")}
              className="p-0.5 rounded text-zinc-600 hover:text-rose-300 opacity-0 group-hover:opacity-100 transition-all disabled:opacity-40"
            >
              <X size={13} />
            </button>
          </div>
        ))}

        {picking && (
          <div className="mt-1.5 pt-1.5 border-t border-white/[6%]">
            {available.length === 0 ? (
              <p className="text-xs text-zinc-500 italic px-2 py-2 text-center">{t("no_available_agents")}</p>
            ) : (
              available.map((a) => (
                <button
                  key={a.id}
                  onClick={() => withBusy(a.id, async () => { await onAttach(a.id); setPicking(false) })}
                  disabled={busyId === a.id}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-sm text-zinc-400 hover:text-zinc-100 hover:bg-white/[5%] transition-all disabled:opacity-40"
                >
                  <Plus size={13} className="shrink-0 opacity-60" />
                  <span className="truncate">{a.name}</span>
                </button>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
