import { useTranslation } from "react-i18next"
import { AdminStatus } from "@/features/cockpit/admin/ui"
import { relTime, type KnownAgent } from "./_agentLinkHelpers"

interface Props {
  agents: KnownAgent[]
  locale: string
}

export function AgentLinkKnownAgents({ agents, locale }: Props) {
  const { t } = useTranslation("system")
  return (
    <div className="border-t border-[#2a364b] pt-3">
      <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.12em] text-[#8d9ab0]">
        {t("agentlink.known_agents", { count: agents.length })}
      </p>
      <div className="space-y-1.5">
        {agents.map(a => (
          <div key={a.agent_id} className="flex items-center gap-2 text-[11px]">
            <AdminStatus
              tone={a.online ? "success" : "danger"}
              dot
              className="border-0 bg-transparent p-0"
            >
              <span className="sr-only">{a.online ? "Online" : "Offline"}</span>
            </AdminStatus>
            <span className="min-w-0 flex-1 truncate text-[#e8eef8]">
              {a.name || a.agent_id}
            </span>
            {a.type && (
              <span className="whitespace-nowrap text-[10px] text-[#5b6675]">{a.type}</span>
            )}
            <span className="whitespace-nowrap font-mono text-[#8d9ab0]" title={a.last_seen}>
              {relTime(a.last_seen, locale)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
