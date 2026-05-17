import { useTranslation } from "react-i18next"
import { relTime, type KnownAgent } from "./_agentLinkHelpers"

interface Props {
  agents: KnownAgent[]
  locale: string
}

export function AgentLinkKnownAgents({ agents, locale }: Props) {
  const { t } = useTranslation("system")
  return (
    <div className="pt-1 border-t border-white/[6%]">
      <p className="text-[10.5px] uppercase tracking-wider text-zinc-500 mb-1.5">
        {t("agentlink.known_agents", { count: agents.length })}
      </p>
      <div className="space-y-1">
        {agents.map(a => (
          <div key={a.agent_id} className="flex items-center gap-2 text-[11px]">
            <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${a.online ? "bg-emerald-400" : "bg-zinc-600"}`} title={a.online ? "Online" : "Offline"} />
            <span className="text-zinc-200 truncate flex-1 min-w-0">
              {a.name || a.agent_id}
            </span>
            {a.type && (
              <span className="text-zinc-600 text-[10px] whitespace-nowrap">{a.type}</span>
            )}
            <span className="text-zinc-500 font-mono whitespace-nowrap" title={a.last_seen}>
              {relTime(a.last_seen, locale)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
