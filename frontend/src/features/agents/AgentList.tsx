import { Crown, Plus, User, Wrench } from "lucide-react"
import { useTranslation } from "react-i18next"
import { HelpButton } from "@/i18n/HelpButton"
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

const TYPE_PILL: Record<string, string> = {
  master: "bg-amber-500/[8%] border-amber-500/25 text-amber-300",
  project: "bg-violet-500/[8%] border-violet-500/25 text-violet-300",
  specialist: "bg-sky-500/[8%] border-sky-500/25 text-sky-300",
}

export function AgentList({ agents, activeId, onSelect, onNew }: Props) {
  const { t } = useTranslation("agents")
  const { t: tCommon } = useTranslation("common")
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-3 border-b border-white/[6%]">
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">{t("list_title")}</p>
        <div className="flex items-center gap-1">
          <HelpButton topic="agents" />
          <button
            onClick={onNew}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs text-zinc-300 hover:text-zinc-100 hover:bg-white/5 transition-colors"
          >
            <Plus size={13} /> {tCommon("actions.new")}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {agents.length === 0 && (
          <p className="text-xs text-zinc-600 text-center py-6">{t("no_agents")}</p>
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
              <span className={`flex items-center gap-1 px-1.5 py-0.5 rounded-full border text-[10px] flex-shrink-0 ${TYPE_PILL[a.type] ?? TYPE_PILL.specialist}`}>
                <Icon size={9} />
                {t(`type.${a.type}`)}
              </span>
              <div className="flex-1 min-w-0">
                <p className={`text-sm truncate ${active ? "text-white" : "text-zinc-300"}`}>{a.name}</p>
                <p className="text-[10px] text-zinc-600 mt-0.5 truncate font-mono">{a.llm_model}</p>
              </div>
              {dim && (
                <span className="px-1.5 py-0.5 rounded-full bg-zinc-500/[8%] border border-zinc-500/20 text-[10px] text-zinc-500 flex-shrink-0">
                  off
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
