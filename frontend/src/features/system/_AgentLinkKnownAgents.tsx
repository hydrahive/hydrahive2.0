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
            <span className="px-2 py-0.5 rounded bg-violet-500/10 border border-violet-500/20 text-violet-200 font-mono truncate flex-1 min-w-0">
              {a.agent_id}
            </span>
            <span className="text-zinc-500 font-mono whitespace-nowrap" title={a.last_seen}>
              vor {relTime(a.last_seen, locale)}
            </span>
            <span className="text-zinc-600 font-mono whitespace-nowrap text-[10px]">
              {a.states} {t("agentlink.states")}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
